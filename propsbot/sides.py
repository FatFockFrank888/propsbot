"""Fotboll sides & totals: Kambis 1X2, mål över/under och asiatiskt handikapp mot Pinnacle.

Pinnacles pris utan marginal är facit (skarpaste marknaden). Edge = p_pinnacle × Kambi-odds − 1.
Samma regler som övriga boten, anpassade för en stor och effektiv marknad:
  * edge >= sides_min_edge (3 %): mot Pinnacles huvudlinje är 3 % en verklig edge – 5 % händer
    nästan bara när en linje är gammal. 1–3 % bokförs som skugga för att mäta nivån.
  * edge <= sides_max_edge (10 %): större = gammal linje, fel match eller nyhet (laguppställning).
  * Pinnacles insatsgräns >= sides_min_pin_limit: låg gräns = svag liga, linjen inte skarp.
  * alternativa Pinnacle-linjer (högre marginal) kräver +1 % extra edge.
  * oddsram, max oddsfall 3 %, sharp money mot oss 2 pe (efter 30 min) – som övriga sporter.
  * ett spel per match (1X2, total och handikapp hänger ihop) – störst edge vinner.
  * halvlinjer (x,5) och asiatiska linjer: hela (push = insatsen tillbaka) och kvarts (halva
    insatsen på var närliggande linje). För hela/kvartslinjer är Pinnacles tvåvägspris redan
    utan push, så edge = p × odds − 1 är förväntad avkastning på den del som avgörs.
Bokföring: sides_spel.json (klarar alla regler), sides_skugga.json (>= 1 % edge men stoppat).
Notiser bara när sides_live = true.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .ledger import Ledger
from .market import devig_power

MARKETS = ("1x2", "total", "ah")
SIDE_SV = {"home": "1", "draw": "X", "away": "2"}


def _half(x: float) -> bool:
    return abs((abs(x) * 2) % 2 - 1) < 1e-9          # 0.5, 1.5, 2.5 …


def _line_ok(x: float) -> bool:
    """Halvlinjer och asiatiska linjer: hela (0, 1, 2 …) och kvarts (0.25, 0.75 …)."""
    return abs(x * 4 - round(x * 4)) < 1e-9


def parts(line: float) -> list[float]:
    """Asiatisk linje -> delinsatser: kvartslinje = halva på var sida (2.25 -> 2.0 och 2.5)."""
    q = round(line * 4)
    return [(q - 1) / 4, (q + 1) / 4] if q % 2 else [line]


def _put(out: dict, key: tuple, odds: float) -> None:
    out[key] = max(out.get(key, 0.0), odds)          # samma linje i flera erbjudanden: bästa priset


# ------------------------------------------------------------------ parsning
def kambi_main(raw: dict, home: str, away: str) -> dict:
    """{(marknad, linje, sida): odds} ur Kambis betoffer-svar. Linje för ah = sidans handikapp."""
    from .sources.props_text import name_key
    hk, ak = name_key(home), name_key(away)
    out: dict = {}
    for bo in raw.get("betOffers", []) or []:
        cr = bo.get("criterion", {}) or {}
        lab = (cr.get("englishLabel") or "").strip().lower()
        outs = bo.get("outcomes", []) or []
        if any(o.get("status", "OPEN") != "OPEN" for o in outs):
            continue
        if lab in ("full time", "match odds", "1x2", "match result", "full time result"):
            t = {o.get("type"): o.get("odds") for o in outs}
            for typ, side in (("OT_ONE", "home"), ("OT_CROSS", "draw"), ("OT_TWO", "away")):
                if t.get(typ):
                    out[("1x2", 0.0, side)] = t[typ] / 1000
        elif lab in ("total goals", "total goals - full time", "asian total", "asian total - full time"):
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                ln = o["line"] / 1000
                side = "over" if o.get("type") == "OT_OVER" else "under" if o.get("type") == "OT_UNDER" else None
                if side and _line_ok(ln):
                    _put(out, ("total", ln, side), o["odds"] / 1000)
        elif lab == "asian handicap":
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                ln = o["line"] / 1000
                nk = name_key(o.get("label") or o.get("participant") or "")
                side = "home" if nk == hk else "away" if nk == ak else None
                if side is None:      # namnen skiljer sig ibland något – ta ordningen (hemma först)
                    side = "home" if o is outs[0] else "away"
                if _line_ok(ln):
                    _put(out, ("ah", ln, side), o["odds"] / 1000)
    return out


def pinnacle_main(markets: list, matchup_id: int) -> dict:
    """{(marknad, linje, sida): (p_fair, gräns, alternativ)} – Pinnacle utan marginal."""
    from .sources.pinnacle_public import american_to_decimal
    out: dict = {}
    for m in markets or []:
        if m.get("matchupId") != matchup_id or m.get("period", 0) != 0 or m.get("status", "open") != "open":
            continue
        lim = max((x.get("amount") or 0 for x in m.get("limits") or []), default=0)
        alt = bool(m.get("isAlternate"))
        pr = m.get("prices") or []
        try:
            if m.get("type") == "moneyline":
                d = {p.get("designation"): p.get("price") for p in pr}
                if all(d.get(k) is not None for k in ("home", "draw", "away")):
                    ps = devig_power([american_to_decimal(float(d[k])) for k in ("home", "draw", "away")])
                    for k, p in zip(("home", "draw", "away"), ps):
                        out[("1x2", 0.0, k)] = (p, lim, alt)
            elif m.get("type") in ("total", "spread"):
                d = {p.get("designation"): p for p in pr}
                a, b = ("over", "under") if m["type"] == "total" else ("home", "away")
                if a in d and b in d and d[a].get("price") is not None and d[b].get("price") is not None:
                    ps = devig_power([american_to_decimal(float(d[a]["price"])), american_to_decimal(float(d[b]["price"]))])
                    mk = "total" if m["type"] == "total" else "ah"
                    for side, p in zip((a, b), ps):
                        ln = float(d[side].get("points") or 0.0)
                        k = (mk, ln, side)
                        if not _line_ok(ln) or (k in out and alt and not out[k][2]):
                            continue              # huvudlinjen går före en alternativ linje
                        out[k] = (p, lim, alt)
        except (TypeError, ValueError):
            continue
    return out


# ------------------------------------------------------------------ historik
class History:
    """Per linje: första sett, Pinnacles första sannolikhet, högsta Kambi-odds."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.d = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.d = {}

    def update(self, key: str, p_pin: float, odds: float, now: float) -> dict:
        h = self.d.setdefault(key, {"ts": now, "p0": p_pin, "max_odds": odds})
        h["max_odds"] = max(h["max_odds"], odds)
        h["last"] = now
        return h

    def save(self, now: float) -> None:
        self.d = {k: v for k, v in self.d.items() if now - v.get("last", now) < 3 * 86400}
        self.path.write_text(json.dumps(self.d), encoding="utf-8")


# ------------------------------------------------------------------ utvärdering
def label(mk: str, line: float, side: str, home: str, away: str) -> tuple[str, str]:
    """(urval, spel) för visning: ('Arsenal', '1X2: 1') osv."""
    team = home if side == "home" else away if side == "away" else "Oavgjort"
    if mk == "1x2":
        return team, f"1X2: {SIDE_SV[side]}"
    if mk == "total":
        return "Mål", f"{'över' if side == 'over' else 'under'} {line:g}"
    return team, f"handikapp {line:+g}".replace("+-", "-")


def evaluate(evd: dict, kambi_by_book: dict, pin: dict, s: dict, hist: History, now: float,
             playable: set[str], wait_reason: str | None = None) -> list[dict]:
    """Alla Kambi-linjer som Pinnacle också har, med edge och regelbeslut.
    wait_reason: t.ex. "väntar på startelvor" – stoppar alla linjer i matchen."""
    out = []
    keys = set().union(*[set(v) for v in kambi_by_book.values()]) if kambi_by_book else set()
    lo, hi = s.get("sides_odds_window", [1.60, 4.00])
    for key in keys:
        if key[0] not in s.get("sides_markets", MARKETS) or key not in pin:
            continue
        offers = [(v[key], b) for b, v in kambi_by_book.items() if key in v and b in playable]
        if not offers:
            continue
        odds, book = max(offers)
        p, lim, alt = pin[key]
        edge = p * odds - 1
        mk, line, side = key
        hk = f"{evd['id']}|{mk}|{line:g}|{side}"
        h = hist.update(hk, p, odds, now)
        reasons = [wait_reason] if wait_reason else []
        need = s.get("sides_min_edge", 0.03) + (s.get("sides_alt_extra_edge", 0.01) if alt else 0.0)
        if edge < need:
            reasons.append(f"edge {edge:.1%} < {need:.0%}" + (" (alternativ linje)" if alt else ""))
        if edge > s.get("sides_max_edge", 0.10):
            reasons.append(f"edge {edge:.1%} orimlig (> {s.get('sides_max_edge', 0.10):.0%}) – gammal linje eller nyhet")
        if not (lo <= odds <= hi):
            reasons.append(f"odds {odds:.2f} utanför {lo:.2f}–{hi:.2f}")
        if lim < s.get("sides_min_pin_limit", 1000):
            reasons.append(f"Pinnacles gräns {lim:.0f} – för svag referens")
        if odds < h["max_odds"] * (1 - s.get("max_odds_drop", 0.03)):
            reasons.append(f"oddset har fallit {1 - odds / h['max_odds']:.1%} från {h['max_odds']:.2f} – för sent")
        move = (p - h["p0"]) * 100
        if now - h["ts"] >= s.get("sharp_min_age_s", 1800):
            if move <= -s.get("sharp_against_pp", 2.0):
                reasons.append(f"sharp money mot oss: Pinnacle {move:+.1f} pe")
            elif move >= s.get("sharp_with_pp", 1.5):
                reasons.append(f"sharp money med oss: Pinnacle {move:+.1f} pe")
        blocked = [r for r in reasons if not r.startswith("sharp money med")]
        out.append({"key": key, "odds": odds, "book": book, "p": p, "edge": edge, "limit": lim, "alt": alt,
                    "playable": not blocked, "reasons": reasons})
    # ett spel per match – störst edge vinner
    ok = sorted((x for x in out if x["playable"]), key=lambda x: -x["edge"])
    for x in ok[1:]:
        x["playable"] = False
        x["reasons"].append("redan ett spel i matchen (störst edge vinner)")
    return out


def _stake(p: float, odds: float, s: dict) -> float:
    b = odds - 1
    f = max(0.0, (p * b - (1 - p)) / b) * 0.25
    unit = 0.002
    u = max(1, min(s.get("sides_max_units", 3), round(f / unit))) if f > 0 else 0
    return u * unit


def _bet(evd: dict, x: dict, s: dict, now: float) -> dict:
    mk, line, side = x["key"]
    who, txt = label(mk, line, side, evd["home_team"], evd["away_team"])
    return {
        "key": f"{evd['id']}|{mk}|{line:g}|{side}|{x['book']}", "id": 0, "bokford": now,
        "match_id": evd["id"], "match": f"{evd['home_team']} – {evd['away_team']}",
        "hemma": evd["home_team"], "borta": evd["away_team"], "liga": evd.get("league", ""),
        "avspark": evd["commence_time"], "spelare": who, "spelare_id": "match",
        "marknad": mk, "linje": line, "sida": side, "spel_text": txt,
        "bolag": x["book"], "odds": x["odds"], "sannolikhet": x["p"], "ratt_odds": 1 / x["p"],
        "edge": x["edge"], "spela_fran": round((1 + s.get("sides_min_edge", 0.03)) / x["p"], 2),
        "insats_pct": _stake(x["p"], x["odds"], s), "stangning": x["odds"], "pin_p": x["p"],
        "pin_stang_p": x["p"], "pin_grans": x["limit"], "alternativ_linje": x["alt"],
        "status": "öppen", "stopp": "; ".join(x["reasons"]), "utfall": None, "resultat_enheter": None,
    }


def _radar_row(evd: dict, x: dict, s: dict, in_window: bool) -> dict:
    """Samma format som props-radarn (export.radar_rows), så att sides syns i samma Radar-flik."""
    from datetime import datetime, timezone
    mk, line, side = x["key"]
    who, txt = label(mk, line, side, evd["home_team"], evd["away_team"])
    play = x["playable"] and in_window
    st = _stake(x["p"], x["odds"], s)
    return {"spelare": who, "match": f"{evd['home_team']} – {evd['away_team']}",
            "avspark": datetime.fromtimestamp(evd["commence_time"], timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "spel": txt, "marknad": mk, "sida": side, "prognos": None, "odds": x["odds"], "bolag": x["book"],
            "sannolikhet": x["p"], "ratt_odds": 1 / x["p"], "edge": x["edge"],
            "spela_fran": round((1 + s.get("sides_min_edge", 0.03)) / x["p"], 2),
            "insats_pct": st if play else 0.0, "insats_forslag": st, "spelbar": play,
            "live": bool(play and s.get("sides_live")), "forv_clv_pp": None, "clv_signal": False, "p_modell": None,
            "kommentar": "Pinnacle utan marginal; " + ("; ".join(x["reasons"]) or "klarar alla regler")
                         + ("" if in_window else f"; mer än {s.get('sides_max_hours', 24)} h till avspark")}


def _record(lg: Ledger, evd: dict, x: dict, s: dict, now: float) -> dict | None:
    if any(b.get("match_id") == evd["id"] for b in lg.bets):
        return None                                   # ett spel per match och bokföring
    b = _bet(evd, x, s, now)
    if b["key"] in lg.by_key:
        return None
    b["id"] = len(lg.bets) + 1
    lg.bets.append(b)
    lg.by_key[b["key"]] = b
    return b


def result_units(mk: str, ln: float, side: str, hg: int, ag: int, odds: float, stake: float) -> float:
    """Resultat i andel av bankrullen. Asiatiska linjer: push = insatsen tillbaka,
    kvartslinje = halva insatsen på var närliggande linje (halv vinst/halv förlust)."""
    if mk == "1x2":
        won = {"home": hg > ag, "draw": hg == ag, "away": ag > hg}[side]
        return (odds - 1) * stake if won else -stake
    res = 0.0
    ps = parts(ln)
    for l in ps:
        if mk == "total":
            m = (hg + ag - l) if side == "over" else (l - hg - ag)
        else:
            m = (hg + l - ag) if side == "home" else (ag + l - hg)
        part = stake / len(ps)
        res += (odds - 1) * part if m > 0 else 0.0 if m == 0 else -part
    return res


def settle(lg: Ledger, scores: dict) -> list[str]:
    """scores: {match_id: (hemmamål, bortamål)}."""
    log = []
    for b in lg.bets:
        if b["status"] != "öppen" or b["match_id"] not in scores:
            continue
        hg, ag = scores[b["match_id"]]
        mk, ln, side = b["marknad"], b["linje"], b["sida"]
        res = result_units(mk, ln, side, hg, ag, b["odds"], b["insats_pct"])
        status = "vunnen" if res > 1e-12 else "förlorad" if res < -1e-12 else "push"
        b.update(status=status, utfall=f"{hg}–{ag}", resultat_enheter=res)
        log.append(f"Sides rättad: {b['match']} {b['spel_text']} -> {b['status']} ({hg}–{ag})")
    return log


def espn_scores(bets: list[dict], client, now: float) -> dict:
    from .results import EspnResults
    espn = EspnResults(client)
    out = {}
    for b in bets:
        if b["status"] != "öppen" or not b.get("avspark") or now < b["avspark"] + 2.5 * 3600 or b["match_id"] in out:
            continue
        sc = espn.final_score(b["hemma"], b["borta"], b["avspark"])
        if sc:
            out[b["match_id"]] = sc
    return out


def run(root: Path, data: list, settings: dict, diag, notify: bool = True) -> dict:
    """data: [(evd, quotes, names)] från collect(); evd har kambi_main och pin_main."""
    now = time.time()
    s = settings
    playable = set(s["playable_books"])
    hist = History(root / "sides_historik.json")
    spel, skugga = Ledger(root / "sides_spel.json"), Ledger(root / "sides_skugga.json")
    n_ev = n_lines = n_lu = 0
    from .lineups import Lineups
    from .sources.http import JsonClient
    lineups = Lineups(JsonClient(root / ".cache_odds", ttl_s=480, min_interval_s=0.25))
    new_spel, new_sk, best, radar = [], [], [], []
    latest: dict = {}
    max_h = s.get("sides_max_hours", 24)
    for evd, _q, _n in data:
        km, pm = evd.get("kambi_main"), evd.get("pin_main")
        if not km or not pm:
            continue
        mtk = (evd["commence_time"] - now) / 60
        wait = None
        if 0 < mtk <= max_h * 60:
            from .lineups import gate
            lu = lineups.get(evd["id"], evd["home_team"], evd["away_team"], evd["commence_time"])                 if mtk <= s.get("lineup_lookup_minutes", 150) else None
            wait = gate(lu, mtk, s)
            n_lu += bool(lu and lu.published)
        for x in evaluate(evd, km, pm, s, hist, now, playable, wait):
            mk, line, side = x["key"]
            latest[f"{evd['id']}|{mk}|{line:g}|{side}|{x['book']}"] = (x["odds"], x["p"])
            latest[(evd["id"], mk, line, side)] = x["p"]
            n_lines += 1
            best.append((x["edge"], evd, x))
            in_window = 0 < evd["commence_time"] - now <= max_h * 3600
            if x["edge"] >= s.get("min_edge_display", 0.02) and evd["commence_time"] > now:
                radar.append(_radar_row(evd, x, s, in_window))
            if not in_window:
                continue
            if x["playable"]:
                b = _record(spel, evd, x, s, now)
                if b:
                    new_spel.append(b)
            elif x["edge"] >= s.get("sides_shadow_min_edge", 0.01):
                b = _record(skugga, evd, x, s, now)
                if b:
                    new_sk.append(b)
        n_ev += 1
    # stängning: senaste odds hos samma bolag och Pinnacles senaste sannolikhet före avspark
    for lg in (spel, skugga):
        for b in lg.bets:
            if b["status"] != "öppen" or now >= b["avspark"]:
                continue
            if b["key"] in latest:
                b["stangning"] = latest[b["key"]][0]
            pk = (b["match_id"], b["marknad"], b["linje"], b["sida"])
            if pk in latest:
                b["pin_stang_p"] = latest[pk]
    try:
        from .sources.http import JsonClient
        client = JsonClient(root / ".cache_odds", ttl_s=900)
        scores = espn_scores(spel.bets + skugga.bets, client, now)
        for lg in (spel, skugga):
            for line in settle(lg, scores):
                diag.lines.append("  " + line)
    except Exception as e:  # noqa: BLE001 – rättningen får aldrig stoppa skanningen
        diag.log(f"Sides rättning: FEL {type(e).__name__}: {e}")
    hist.save(now)
    radar.sort(key=lambda r: -r["edge"])
    (root / "sides_radar.json").write_text(json.dumps(radar[:300], ensure_ascii=False), encoding="utf-8")
    top = sorted(best, key=lambda t: -t[0])[:3]
    diag.log(f"Sides/totals: {n_ev} matcher med Kambi + Pinnacle, {n_lines} linjer, "
             f"{len(new_spel)} nya spel, {len(new_sk)} nya skuggspel, startelvor kända i {n_lu}; bästa edge "
             + ", ".join(f"{e:+.1%} ({ev['home_team']} {label(*x['key'], ev['home_team'], ev['away_team'])[1]})" for e, ev, x in top))
    sent = 0
    if notify and s.get("sides_live") and s.get("ntfy_topic") and new_spel:
        sent = _notify(root, new_spel, s)
    spel.save()
    skugga.save()
    return {"spel": spel, "skugga": skugga, "new": new_spel, "sent": sent}


def _notify(root: Path, bets: list[dict], s: dict) -> int:
    from .notify import PlayerGuard, send
    guard = PlayerGuard(root / "notis_spelare.json")
    sent = 0
    for b in bets:
        if guard.already_sent("fotboll", b["match_id"], "sides"):
            continue
        title = f"LIVE FOTBOLL SPELA: {b['match']} – {b['spelare']} {b['spel_text']}"
        from datetime import datetime, timezone
        ko = datetime.fromtimestamp(b["avspark"], timezone.utc).strftime("%Y-%m-%d %H:%M")
        msg = (f"{b['liga']} ({ko} UTC)\n{b['bolag']}: {b['odds']:.2f}  (spela från {b['spela_fran']:.2f})\n"
               f"Pinnacle utan marginal {b['sannolikhet']:.1%}, edge {b['edge']:.1%}\n"
               f"Insats: {round(b['insats_pct'] / 0.002)}/10 units")
        if send(s["ntfy_topic"], title, msg, tags="soccer"):
            guard.mark("fotboll", b["match_id"], "sides", b["key"])
            b["notis"] = True
            sent += 1
    guard.save()
    return sent
