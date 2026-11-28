"""Värde-parlayer (28/11, 2–4 ben 28/11): kombinerar redan godkända A/B-spel (NBA) till parlayer, bara
för att få bättre spridning av en liten kassa över färre spel – INTE skenlägg. Bygger bara på riktiga,
redan klassade +EV-ben; inga påhittade "vaska"-ben och ingen falsk bank-leg.

Antaganden som INTE är verifierade mot Paf, flagga om det visar sig fel:
  - combo_odds = produkten av bendes egna odds (ingen extra marginal utöver vad varje ben redan har).
    Om Paf lägger på egen marginal på parlayer blir verkligt värde sämre än här beräknat.
  - combo_p = produkten av bendes bokförda sannolikheter (antar oberoende -> bara ben från OLIKA matcher
    kombineras, för att hålla antagandet rimligt).
  - OBS fler ben (3–4) blåser upp den beräknade edgen rent mekaniskt (odds multipliceras, sannolikhet
    multipliceras ner, men produkten sväller fort) – det är en artefakt av oberoende-antagandet, inte
    bevis på bättre värde. Chansen att träffa alla 4 ben är låg även när varje ben för sig är +EV.

Insats: samma ¼ Kelly-skalning (15–45 kr) som tiers.py, men taket är alltid tier_stake_mid_kr (aldrig
maxbet) eftersom en parlays sammansatta risk är högre än ett enskilt ben.
"""
from __future__ import annotations

import csv
import json
import time
from itertools import combinations
from pathlib import Path

from .quant import kelly as quant_kelly

DEFAULTS = {
    "parlay_on": True,
    "parlay_min_edge": 0.08,     # högre än enskilda B-kravet (5 %) – kombinationens osäkerhet är större
    "parlay_max_legs": 4,
    "parlay_odds": [1.40, 6.50],  # samma ramar som enskilda ben, per ben
}


def _cfg(settings: dict) -> dict:
    return {k: settings.get(k, v) for k, v in DEFAULTS.items()}


def _leg_view(b: dict) -> dict:
    return {"ident": b["ident"], "match_id": b.get("match_id"), "match": b.get("match"),
            "spelare": b.get("spelare"), "marknad": b.get("marknad"), "linje": b.get("linje"),
            "sida": b.get("sida"), "odds": b.get("odds"), "sannolikhet": b.get("sannolikhet"),
            "bolag": b.get("bolag"), "avspark": b.get("avspark")}


def _score(combo: tuple[dict, ...]) -> tuple[float, float, float]:
    combo_p = combo_odds = 1.0
    for leg in combo:
        combo_p *= leg["sannolikhet"]
        combo_odds *= leg["odds"]
    return combo_p, combo_odds, combo_p * combo_odds - 1.0


def build_parlays(bets: list[dict], settings: dict, existing_idents: set[str]) -> list[dict]:
    """Bygger nya parlayer (2–parlay_max_legs ben) ur öppna A/B-spel (NBA), olika match per ben,
    combo-edge >= parlay_min_edge. Väljer högst edge först, ingen bets återanvänds i två parlayer
    samma körning. existing_idents: redan skapade parlay-idents, för att inte dubbelboka ett ben."""
    c = _cfg(settings)
    if not c["parlay_on"]:
        return []
    lo, hi = c["parlay_odds"]
    cands = [b for b in bets if b.get("sport") == "nba" and b.get("tier") in ("A", "B")
             and b.get("status") == "öppen" and b.get("sannolikhet") and b.get("odds")
             and lo <= b["odds"] <= hi]
    max_legs = max(2, int(c.get("parlay_max_legs", 4)))
    scored = []
    for size in range(2, max_legs + 1):
        for combo in combinations(cands, size):
            if len({leg.get("match_id") for leg in combo}) < size:   # kräver olika match per ben
                continue
            combo_p, combo_odds, combo_edge = _score(combo)
            if combo_edge >= c["parlay_min_edge"]:
                scored.append((combo_edge, combo_p, combo_odds, combo))
    scored.sort(key=lambda x: -x[0])
    used: set[str] = set()
    out = []
    for combo_edge, combo_p, combo_odds, combo in scored:
        idents = [leg["ident"] for leg in combo]
        if any(i in used for i in idents):
            continue
        ident = "parlay|" + "+".join(sorted(idents))
        if ident in existing_idents:
            used.update(idents)
            continue
        k_pct = quant_kelly.stake(combo_p, combo_odds)
        lo_kr, hi_kr = c.get("tier_stake_min_kr", 15.0), c.get("tier_stake_mid_kr", 30.0)
        frac = max(0.0, min(1.0, k_pct / 0.02))
        stake_kr = round(lo_kr + frac * (hi_kr - lo_kr), 1)
        out.append({"ident": ident, "typ": "Parlay", "sport": "nba", "ben": [_leg_view(leg) for leg in combo],
                    "combo_p": round(combo_p, 4), "combo_odds": round(combo_odds, 3),
                    "combo_edge": round(combo_edge, 4), "stake_kr": stake_kr,
                    "bokford": time.time(), "status": "öppen", "avspark": min(leg["avspark"] for leg in combo)})
        used.update(idents)
    return out


def _leg_result(ben: dict, bets_by_ident: dict) -> str | None:
    cur = bets_by_ident.get(ben["ident"])
    if cur is None:
        return None
    return cur.get("status")


def settle_parlays(parlays: list[dict], bets: list[dict]) -> None:
    """Sätter status på öppna parlayer utifrån bendes nuvarande status i huvudbokföringen.
    Vinst kräver ALLA ben vunna; ett förlorat ben räcker för förlust; struket ben -> struken."""
    by_ident = {b["ident"]: b for b in bets}
    for p in parlays:
        if p["status"] != "öppen":
            continue
        results = [_leg_result(ben, by_ident) for ben in p["ben"]]
        if any(r == "förlorad" for r in results):
            p["status"] = "förlorad"
            p["resultat_kr"] = -p["stake_kr"]
        elif any(r == "struken" for r in results):
            p["status"] = "struken"
            p["resultat_kr"] = 0.0
        elif all(r == "vunnen" for r in results):
            p["status"] = "vunnen"
            p["resultat_kr"] = round(p["stake_kr"] * (p["combo_odds"] - 1), 1)


def notify_parlays(parlays: list[dict], settings: dict, log=print) -> int:
    topic = settings.get("tier_ntfy_topic") or settings.get("ntfy_topic")
    if not topic or not parlays:
        return 0
    from .notify import send
    sent = 0
    for p in parlays:
        if p.get("notis"):
            continue
        rader = "\n".join(f"· {b['spelare'] or b['match']} {b['marknad']} "
                          f"{'under' if b['sida'] == 'under' else 'över'} {b['linje']:g} @ {b['odds']:.2f} "
                          f"({b['bolag']})" for b in p["ben"])
        title = f"PARLAY ({len(p['ben'])} ben) · NBA"
        msg = (f"{rader}\nKombinerat odds {p['combo_odds']:.2f} · edge {p['combo_edge']*100:+.1f} % "
              f"· insats {p['stake_kr']:.0f} kr")
        if send(topic, title, msg, priority=3, tags="basketball"):
            p["notis"] = True
            sent += 1
    log(f"Parlayer: {sent} notiser skickade")
    return sent


CSV_HEAD = ["Bokförd", "Antal ben", "Ben", "Kombinerad sannolikhet", "Kombinerat odds", "Edge (%)",
            "Insats (kr)", "Status", "Resultat (kr)", "Avspark"]


def _ben_text(ben: list[dict]) -> str:
    return " | ".join(f"{b['spelare'] or b['match']} {b['marknad']} "
                      f"{'under' if b['sida'] == 'under' else 'över'} {b['linje']:g} @ {b['odds']:.2f} "
                      f"({b['bolag']})" for b in ben)


def write_parlay_csv(parlays: list[dict], out_dir: Path) -> None:
    """site/csv/parlayer.csv – läses in i Google Sheets med IMPORTDATA, samma mönster som övriga CSV:er
    (se workbook.write_csv_exports)."""
    from datetime import datetime, timezone
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "parlayer.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEAD)
        for p in sorted(parlays, key=lambda x: -x["bokford"]):
            bok = datetime.fromtimestamp(p["bokford"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            av = datetime.fromtimestamp(p["avspark"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            w.writerow([bok, len(p["ben"]), _ben_text(p["ben"]), p["combo_p"], p["combo_odds"],
                       round(p["combo_edge"] * 100, 1), p["stake_kr"], p["status"],
                       p.get("resultat_kr", ""), av])


def run(root: Path, bets: list[dict], settings: dict, notify: bool = True, log=print) -> list[dict]:
    """Läser/sparar site/parlays.json + site/csv/parlayer.csv: bygger nya parlayer, rättar öppna, pushar nya."""
    path = root / "site" / "parlays.json"
    try:
        parlays = json.loads(path.read_text(encoding="utf-8")).get("parlayer", [])
    except (OSError, json.JSONDecodeError):
        parlays = []
    settle_parlays(parlays, bets)
    existing = {p["ident"] for p in parlays}
    nya = build_parlays(bets, {**_cfg(settings), **{k: settings[k] for k in
                        ("tier_stake_min_kr", "tier_stake_mid_kr") if k in settings}}, existing)
    parlays += nya
    if notify:
        notify_parlays(nya, settings, log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"uppdaterad_ts": time.time(), "parlayer": parlays}, ensure_ascii=False),
                    encoding="utf-8")
    write_parlay_csv(parlays, root / "site" / "csv")
    return parlays
