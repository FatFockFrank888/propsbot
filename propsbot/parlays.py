"""Värde-parlayer (28/11): kombinerar redan godkända A/B-spel (NBA) till 2-bens-parlayer, bara för att
få bättre spridning av en liten kassa över färre spel – INTE skenlägg. Bygger bara på riktiga, redan
klassade +EV-ben; inga påhittade "vaska"-ben och ingen falsk bank-leg.

Antaganden som INTE är verifierade mot Paf, flagga om det visar sig fel:
  - combo_odds = produkten av bendes egna odds (ingen extra marginal utöver vad varje ben redan har).
    Om Paf lägger på egen marginal på parlayer blir verkligt värde sämre än här beräknat.
  - combo_p = produkten av bendes bokförda sannolikheter (antar oberoende -> bara ben från OLIKA matcher
    kombineras, för att hålla antagandet rimligt).

Insats: samma ¼ Kelly-skalning (15–45 kr) som tiers.py, men taket är alltid tier_stake_mid_kr (aldrig
maxbet) eftersom en parlays sammansatta risk är högre än ett enskilt ben.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .quant import kelly as quant_kelly

DEFAULTS = {
    "parlay_on": True,
    "parlay_min_edge": 0.08,     # högre än enskilda B-kravet (5 %) – kombinationens osäkerhet är större
    "parlay_max_legs": 2,
    "parlay_odds": [1.40, 6.50],  # samma ramar som enskilda ben, per ben
}


def _cfg(settings: dict) -> dict:
    return {k: settings.get(k, v) for k, v in DEFAULTS.items()}


def _leg_view(b: dict) -> dict:
    return {"ident": b["ident"], "match_id": b.get("match_id"), "match": b.get("match"),
            "spelare": b.get("spelare"), "marknad": b.get("marknad"), "linje": b.get("linje"),
            "sida": b.get("sida"), "odds": b.get("odds"), "sannolikhet": b.get("sannolikhet"),
            "bolag": b.get("bolag"), "avspark": b.get("avspark")}


def build_parlays(bets: list[dict], settings: dict, existing_idents: set[str]) -> list[dict]:
    """Bygger nya 2-bens-parlayer ur öppna A/B-spel (NBA), olika match per ben, combo-edge >= parlay_min_edge.
    existing_idents: redan skapade parlay-idents denna/tidigare körning, för att inte dubbelboka ett ben."""
    c = _cfg(settings)
    if not c["parlay_on"]:
        return []
    lo, hi = c["parlay_odds"]
    cands = [b for b in bets if b.get("sport") == "nba" and b.get("tier") in ("A", "B")
             and b.get("status") == "öppen" and b.get("sannolikhet") and b.get("odds")
             and lo <= b["odds"] <= hi]
    used: set[str] = set()
    out = []
    for i, a in enumerate(cands):
        if a["ident"] in used:
            continue
        for b in cands[i + 1:]:
            if b["ident"] in used or b.get("match_id") == a.get("match_id"):
                continue
            combo_p = a["sannolikhet"] * b["sannolikhet"]
            combo_odds = a["odds"] * b["odds"]
            combo_edge = combo_p * combo_odds - 1.0
            if combo_edge < c["parlay_min_edge"]:
                continue
            ident = "parlay|" + "+".join(sorted((a["ident"], b["ident"])))
            if ident in existing_idents:
                used.add(a["ident"]); used.add(b["ident"])
                break
            k_pct = quant_kelly.stake(combo_p, combo_odds)
            lo_kr, hi_kr = c.get("tier_stake_min_kr", 15.0), c.get("tier_stake_mid_kr", 30.0)
            frac = max(0.0, min(1.0, k_pct / 0.02))
            stake_kr = round(lo_kr + frac * (hi_kr - lo_kr), 1)
            out.append({"ident": ident, "typ": "Parlay", "sport": "nba", "ben": [_leg_view(a), _leg_view(b)],
                        "combo_p": round(combo_p, 4), "combo_odds": round(combo_odds, 3),
                        "combo_edge": round(combo_edge, 4), "stake_kr": stake_kr,
                        "bokford": time.time(), "status": "öppen", "avspark": min(a["avspark"], b["avspark"])})
            used.add(a["ident"]); used.add(b["ident"])
            break
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


def run(root: Path, bets: list[dict], settings: dict, notify: bool = True, log=print) -> list[dict]:
    """Läser/sparar site/parlays.json: bygger nya parlayer, rättar öppna, pushar nya."""
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
    return parlays
