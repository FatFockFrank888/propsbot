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

MARKETS = ("1x2", "total", "ah", "corners", "cah", "corners_home", "corners_away")
# Hörnor: bara Smarkets som referens (Pinnacle saknar hörnor i det öppna flödet). Börsen handlas tunnare
# där, så edge räknas mot det försiktiga priset: mitten minus halva spreaden.
SINGLE_REF = ("corners", "cah", "corners_home", "corners_away")
CORNER_MARKETS = SINGLE_REF
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
        elif lab == "corners 3-way handicap":
            # Kambis 3-vägs hörnhandikapp (heltal h för hemmalaget) = tvåvägs halvlinjer:
            # "1" = hemma h − 0,5, "2" = borta −h − 0,5 (krysset används inte).
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                h = o["line"] / 1000
                if abs(h - round(h)) > 1e-9:
                    continue
                if o.get("type") == "OT_ONE":
                    _put(out, ("cah", h - 0.5, "home"), o["odds"] / 1000)
                elif o.get("type") == "OT_TWO":
                    _put(out, ("cah", -h - 0.5, "away"), o["odds"] / 1000)
        elif lab.startswith("total corners by ") and " - " not in lab:
            team = lab[len("total corners by "):]
            nk = name_key(team)
            side = "home" if nk == hk or nk in hk or hk in nk else "away" if nk == ak or nk in ak or ak in nk else None
            for o in outs if side else []:
                if o.get("line") is None or not o.get("odds"):
                    continue
                ln = o["line"] / 1000
                ou = "over" if o.get("type") == "OT_OVER" else "under" if o.get("type") == "OT_UNDER" else None
                if ou and _half(ln):
                    _put(out, (f"corners_{side}", ln, ou), o["odds"] / 1000)
        elif lab in ("total corners", "total corners - full time"):
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                ln = o["line"] / 1000
                side = "over" if o.get("type") == "OT_OVER" else "under" if o.get("type") == "OT_UNDER" else None
                if side and _half(ln):
                    _put(out, ("corners", ln, side), o["odds"] / 1000)
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
    if mk == "corners":
        return "Hörnor", f"hörnor {'över' if side == 'over' else 'under'} {line:g}"
    if mk in ("corners_home", "corners_away"):
        t = home if mk == "corners_home" else away
        return t, f"{t} hörnor {'över' if side == 'over' else 'under'} {line:g}"
    if mk == "cah":
        return team, f"hörnhandikapp {line:+g}".replace("+-", "-")
    return team, f"handikapp {line:+g}".replace("+-", "-")


def evaluate(evd: dict, kambi_by_book: dict, pin: dict, s: dict, hist: History, now: float,
             playable: set[str], wait_reason: str | None = None, smk: dict | None = None) -> list[dict]:
    """Alla Kambi-linjer som Pinnacle också har, med edge och regelbeslut.
    wait_reason: t.ex. "väntar på startelvor" – stoppar alla linjer i matchen."""
    out = []
    keys = set().union(*[set(v) for v in kambi_by_book.values()]) if kambi_by_book else set()
    lo, hi = s.get("sides_odds_window", [1.40, 6.00])
    for key in keys:
        if key[0] not in s.get("sides_markets", MARKETS):
            continue
        single = key[0] in SINGLE_REF
        if single and not (smk and key in smk):
            continue
        if not single and key not in pin:
            continue
        offers = [(v[key], b) for b, v in kambi_by_book.items() if key in v and b in playable]
        if not offers:
            continue
        odds, book = max(offers)
        # hörnor: försiktigt pris = mitten minus halva spreaden (spread i baspunkter)
        p_pin, lim, alt = pin[key] if not single else (smk[key][0] - smk[key][1] / 20000, 10 ** 6, False)
        # Två skarpa referenser: Pinnacle och Smarkets (börs). Finns Smarkets-priset (snäv spread) är
        # facit medelvärdet, och Smarkets måste också visa positivt värde – annars inget spel.
        sm = (smk or {}).get(key)
        p_smk = sm[0] if sm else None
        p = (p_pin + p_smk) / 2 if p_smk is not None and not single else p_pin
        edge = p * odds - 1
        mk, line, side = key
        hk = f"{evd['id']}|{mk}|{line:g}|{side}"
        h = hist.update(hk, p_pin, odds, now)
        reasons = [wait_reason] if wait_reason else []
        if p_smk is not None and not single and p_smk * odds - 1 < 0:
            reasons.append(f"Smarkets håller inte med: edge mot börsen {p_smk * odds - 1:+.1%}")
        low = lim < s.get("sides_low_limit", 2000)     # svagare Pinnacle-linje (ofta lägre divisioner)
        need = (s.get("sides_min_edge", 0.03) + (s.get("sides_alt_extra_edge", 0.01) if alt else 0.0)
                + (s.get("sides_single_ref_extra_edge", 0.01) if single else 0.0)
                + (s.get("sides_low_limit_extra_edge", 0.01) if low else 0.0))
        if edge < need:
            reasons.append(f"edge {edge:.1%} < {need:.0%}" + (" (alternativ linje)" if alt else "")
                           + (f" (Pinnacles gräns {lim:.0f})" if low else ""))
        if edge > s.get("sides_max_edge", 0.10):
            reasons.append(f"edge {edge:.1%} orimlig (> {s.get('sides_max_edge', 0.10):.0%}) – gammal linje eller nyhet")
        if not (lo <= odds <= hi):
            reasons.append(f"odds {odds:.2f} utanför {lo:.2f}–{hi:.2f}")
        if lim < s.get("sides_min_pin_limit", 500):
            reasons.append(f"Pinnacles gräns {lim:.0f} – för svag referens")
        if odds < h["max_odds"] * (1 - s.get("max_odds_drop", 0.03)):
            reasons.append(f"oddset har fallit {1 - odds / h['max_odds']:.1%} från {h['max_odds']:.2f} – för sent")
        move = (p_pin - h["p0"]) * 100
        if now - h["ts"] >= s.get("sharp_min_age_s", 1800):
            if move <= -s.get("sharp_against_pp", 2.0):
                reasons.append(f"sharp money mot oss: Pinnacle {move:+.1f} pe")
            elif move >= s.get("sharp_with_pp", 1.5):
                reasons.append(f"sharp money med oss: Pinnacle {move:+.1f} pe")
        blocked = [r for r in reasons if not r.startswith("sharp money med")]
        out.append({"key": key, "odds": odds, "book": book, "p": p, "edge": edge, "limit": lim, "alt": alt,
                    "p_pin": p_pin, "p_smk": p_smk, "playable": not blocked, "reasons": reasons})
    # ett spel per match och grupp (mål-marknader / hörnor) – störst edge vinner
    for grp in (False, True):
        ok = sorted((x for x in out if x["playable"] and (x["key"][0] in CORNER_MARKETS) == grp), key=lambda x: -x["edge"])
        for x in ok[1:]:
            x["playable"] = False
            x["reasons"].append("redan ett spel i matchen (störst edge vinner)")
    return out


def _ceil2(x: float) -> float:
    """Spela från avrundas uppåt (aldrig under den verkliga tröskeln)."""
    import math
    return math.ceil(x * 100 - 1e-9) / 100


def _stake(p: float, odds: float, s: dict) -> float:
    b = odds - 1
    f = max(0.0, (p * b - (1 - p)) / b) * 0.25
    unit = 0.002
    cap = s.get("live_max_units", 5) if s.get("sides_live") else s.get("sides_max_units", 3)
    u = max(1, min(cap, round(f / unit))) if f > 0 else 0
    return u * unit


def _bet(evd: dict, x: dict, s: dict, now: float) -> dict:
    mk, line, side = x["key"]
    who, txt = label(mk, line, side, evd["home_team"], evd["away_team"])
    return {
        "key": f"{evd['id']}|{mk}|{line:g}|{side}|{x['book']}", "id": 0, "bokford": now,
        "match_id": evd["id"], "match": f"{evd['home_team']} – {evd['away_team']}",
        "hemma": evd["home_team"], "borta": evd["away_team"], "liga": evd.get("league", ""),
        "avspark": evd["commence_time"], "spelare": who, "spelare_id": "hörnor" if mk in CORNER_MARKETS else "match",
        "marknad": mk, "linje": line, "sida": side, "spel_text": txt,
        "bolag": x["book"], "odds": x["odds"], "sannolikhet": x["p"], "ratt_odds": 1 / x["p"],
        "edge": x["edge"], "spela_fran": _ceil2((1 + s.get("sides_min_edge", 0.03)) / x["p"]),
        "insats_pct": _stake(x["p"], x["odds"], s), "stangning": x["odds"], "pin_p": x.get("p_pin", x["p"]),
        "pin_stang_p": x.get("p_pin", x["p"]), "smk_p": x.get("p_smk"), "smk_stang_p": x.get("p_smk"),
        "pin_grans": x["limit"], "alternativ_linje": x["alt"],
        "mindre_liga": bool(evd.get("extra")),
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
            "spela_fran": _ceil2((1 + s.get("sides_min_edge", 0.03)) / x["p"]),
            "insats_pct": st if play else 0.0, "insats_forslag": st, "spelbar": play,
            "live": bool(play and s.get("sides_live")), "forv_clv_pp": None, "clv_signal": False, "p_modell": None,
            "kommentar": "Pinnacle utan marginal" + (f" + Smarkets {x['p_smk']:.0%}" if x.get("p_smk") is not None else "")
                         + "; " + ("; ".join(x["reasons"]) or "klarar alla regler")
                         + ("" if in_window else f"; mer än {s.get('sides_max_hours', 24)} h till avspark")}


def _record(lg: Ledger, evd: dict, x: dict, s: dict, now: float) -> dict | None:
    grp = x["key"][0] in CORNER_MARKETS
    if any(b.get("match_id") == evd["id"] and (b.get("marknad") in CORNER_MARKETS) == grp for b in lg.bets):
        return None                                   # ett spel per match och grupp (mål / hörnor) och bokföring
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
    if mk in ("corners", "corners_home", "corners_away"):       # hg, ag = hörnor per lag
        n = hg + ag if mk == "corners" else hg if mk == "corners_home" else ag
        won = (n > ln) if side == "over" else (n < ln)
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
        mk, ln, side = b["marknad"], b["linje"], b["sida"]
        sc = scores.get(("corners", b["match_id"])) if mk in CORNER_MARKETS else scores.get(b["match_id"])
        if sc is None:
            continue
        hg, ag = sc
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
    for b in bets:            # hörnor: ESPN:s matchprotokoll (wonCorners per lag)
        if b.get("marknad") not in CORNER_MARKETS or b["status"] != "öppen" or ("corners", b["match_id"]) in out                 or not b.get("avspark") or now < b["avspark"] + 2.5 * 3600:
            continue
        cc = espn_corners(espn, client, b["hemma"], b["borta"], b["avspark"])
        if cc:
            out[("corners", b["match_id"])] = cc
    return out


def espn_corners(espn, client, home: str, away: str, start: float) -> tuple[int, int] | None:
    from .results import BASE
    hit = espn.find_any(home, away, start)
    if not hit:
        return None
    lg, ev = hit
    raw = client.get(f"{BASE}/{lg}/summary", {"event": ev["id"]}, ttl=1800) or {}
    comp = ((raw.get("header") or {}).get("competitions") or [{}])[0]
    if not ((comp.get("status") or {}).get("type") or {}).get("completed"):
        return None
    got = {}
    for t in (raw.get("boxscore") or {}).get("teams", []) or []:
        v = next((x.get("displayValue") for x in t.get("statistics", []) or [] if x.get("name") == "wonCorners"), None)
        if v is not None and t.get("homeAway") in ("home", "away"):
            got[t["homeAway"]] = int(float(v))
    return (got["home"], got["away"]) if len(got) == 2 else None


ESPORT = ("esport", "e-sport", "esoccer", "virtual", "fifa", "efootball", "cyber")


def extra_events(settings: dict, diag, cache_dir: Path, known: set[str]) -> list:
    """Mindre ligor och lägre divisioner (bara sides/totals): Kambis alla fotbollsmatcher utanför
    props-ligorna som startar inom sides_extra_hours. Bara huvudmarknaderna hämtas –
    ett anrop per match och bolag hos Kambi, två anrop totalt hos Pinnacle."""
    if not settings.get("sides_extra_leagues", True):
        return []
    from .sources.http import JsonClient, SourceError
    from .sources.kambi_public import KambiPublic
    from .sources.pinnacle_public import BASE as PBASE, SOCCER, PinnaclePublic, _ts
    from .sources.props_text import same_match
    now = time.time()
    hours = settings.get("sides_extra_hours", 3)
    offerings = {code: book for code, book in settings["kambi_offerings"].items() if book in settings["playable_books"]}
    kambi = KambiPublic(JsonClient(cache_dir, ttl_s=90), market=settings["kambi_market"])
    first = next(iter(offerings))
    evs, _raw = kambi.football_events(first, hours, [])
    evs = [e for e in evs if f"k{e.event_id}" not in known and not any(w in e.league.lower() for w in ESPORT)]
    evs = sorted(evs, key=lambda e: e.start)
    if not evs:
        diag.log("Sides mindre ligor: inga matcher inom tidsfönstret")
        return []
    # Pinnacle: alla fotbollsmatcher och raka marknader i två anrop
    try:
        pc = PinnaclePublic(JsonClient(cache_dir, ttl_s=60, min_interval_s=0.6)).c
        mus = pc.get(f"{PBASE}/sports/{SOCCER}/matchups") or []
        mks = pc.get(f"{PBASE}/sports/{SOCCER}/markets/straight", {"primaryOnly": "false"}) or []
    except SourceError as e:
        diag.log(f"Sides mindre ligor: Pinnacle FEL {e}")
        return []
    pins = []
    for m in mus:
        if m.get("type") != "matchup" or m.get("parent"):
            continue
        parts = {x.get("alignment"): x.get("name") for x in m.get("participants", [])}
        try:
            st = _ts(m["startTime"])
        except (KeyError, ValueError):
            continue
        if "home" in parts and "away" in parts and now < st < now + (hours + 1) * 3600:
            pins.append((int(m["id"]), parts["home"], parts["away"], st, (m.get("league") or {}).get("name", "")))
    # Matcha mot Pinnacle först (gratis), hämta sedan Kambi bara för matchade – fokus på mindre ligor.
    matched = []
    for ev in evs:
        pm = next((p for p in pins if same_match(ev.home, ev.away, ev.start, p[1], p[2], p[3])), None)
        if pm:
            pin = pinnacle_main(mks, pm[0])
            if pin:
                matched.append((ev, pin))
    matched = matched[: settings.get("sides_extra_max_events", 150)]
    # Kambi-bolagen delar oftast pris: i mindre ligor räcker sides_extra_books bolag (sparar anrop).
    offerings = dict(list(offerings.items())[: settings.get("sides_extra_books", 2)])
    out = []
    for ev, pin in matched:
        evd = {"id": f"k{ev.event_id}", "home_team": ev.home, "away_team": ev.away,
               "commence_time": ev.start, "league": ev.league, "extra": True, "pin_main": pin, "kambi_main": {}}
        for code, book in offerings.items():
            try:
                raw = kambi._get(code, f"betoffer/event/{ev.event_id}.json", {"includeParticipants": "true"})
            except SourceError:
                continue
            if raw:
                evd["kambi_main"][book] = kambi_main(raw, ev.home, ev.away)
        if evd["kambi_main"]:
            out.append((evd, [], {}))
    diag.log(f"Sides mindre ligor: {len(evs)} Kambi-matcher inom {hours} h, {len(pins)} Pinnacle-matcher, {len(matched)} med Pinnacle, "
             f"{len(out)} matchade: " + ", ".join(sorted({e['league'].replace('Football / ', '') for e, _, _ in out}))[:300])
    return out


def run(root: Path, data: list, settings: dict, diag, notify: bool = True) -> dict:
    """data: [(evd, quotes, names)] från collect(); evd har kambi_main och pin_main."""
    now = time.time()
    s = dict(settings)
    playable = set(s["playable_books"])
    hist = History(root / "sides_historik.json")
    spel, skugga = Ledger(root / "sides_spel.json"), Ledger(root / "sides_skugga.json")
    # Samlar data tills underlaget räcker; med bevisad CLV mot Pinnacles stängning går sides över till
    # samma villkor som NBA/NHL LIVE (notiser, ¼ Kelly upp till 5u) – automatiskt (graduation.py).
    if not s.get("sides_live"):
        from .graduation import check
        # Underlag: alla regelspel + skuggspel som klarade edgekravet och bara stoppades av startelvespärren
        # (de hade varit regelspel utan spärren – samma prissättning).
        min_e = s.get("sides_min_edge", 0.03)
        base = spel.counted + [b for b in skugga.counted if b.get("edge", 0) >= min_e
                               and (b.get("stopp") or "").startswith("väntar på startelvor")]
        clv = [(b["pin_stang_p"] - 1 / b["odds"]) * 100 for b in base
               if b.get("pin_stang_p") and b.get("odds") and b.get("avspark") and b["avspark"] < now]
        if check(root, "sides", clv, s, "Fotboll sides/totals", notify, diag.log):
            s["sides_live"] = True
    n_ev = n_lines = n_lu = 0
    from .lineups import Lineups
    from .sources.http import JsonClient
    lineups = Lineups(JsonClient(root / ".cache_odds", ttl_s=480, min_interval_s=0.25))
    new_spel, new_sk, best, radar = [], [], [], []
    latest: dict = {}
    max_h = s.get("sides_max_hours", 24)
    # Smarkets (börs, öppet API): andra skarpa referensen. Går långsamt (gräns för antal anrop).
    smk_src, n_smk, n_smk_try = None, 0, 0
    if s.get("sides_smarkets", True):
        from .sources.smarkets import SmarketsPublic
        smk_src = SmarketsPublic(JsonClient(root / ".cache_odds", ttl_s=90, min_interval_s=s.get("smarkets_interval_s", 1.0)))
    # Mindre ligor först: där är Kambi oftast felsatt, och Smarkets-anropen (begränsat antal) går dit först.
    for evd, _q, _n in sorted(data, key=lambda t: (not t[0].get("extra"), t[0].get("commence_time", 0))):
        km, pm = evd.get("kambi_main"), evd.get("pin_main")
        if not km or not pm:
            continue
        mtk = (evd["commence_time"] - now) / 60
        wait = None
        if 0 < mtk <= max_h * 60:
            from .lineups import gate
            lu = lineups.get(evd["id"], evd["home_team"], evd["away_team"], evd["commence_time"])                 if mtk <= s.get("lineup_lookup_minutes", 150) else None
            # Sides jämförs mot Pinnacle, som redan prisar in laguppställningar och nyheter: spärren
            # stoppade 138 skuggspel 7/11 som slog stängningen med +2 pe. Av som standard (sides_lineup_gate).
            wait = gate(lu, mtk, s) if s.get("sides_lineup_gate", False) else None
            n_lu += bool(lu and lu.published)
        smk = None
        if smk_src is not None and 0 < mtk <= max_h * 60 and n_smk_try < s.get("sides_smarkets_max_events", 80):
            try:
                eid = smk_src.find(evd["home_team"], evd["away_team"], evd["commence_time"])
                if eid:
                    n_smk_try += 1
                    smk = smk_src.main(eid) or None
                    n_smk += bool(smk)
            except Exception:  # noqa: BLE001 – Smarkets får aldrig stoppa skanningen
                smk = None
        for x in evaluate(evd, km, pm, s, hist, now, playable, wait, smk):
            mk, line, side = x["key"]
            latest[f"{evd['id']}|{mk}|{line:g}|{side}|{x['book']}"] = (x["odds"], x["p"])
            latest[(evd["id"], mk, line, side)] = x.get("p_pin", x["p"])
            if x.get("p_smk") is not None:
                latest[("smk", evd["id"], mk, line, side)] = x["p_smk"]
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
            if ("smk",) + pk in latest:
                b["smk_stang_p"] = latest[("smk",) + pk]
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
             f"{len(new_spel)} nya spel, {len(new_sk)} nya skuggspel, Smarkets-priser i {n_smk} av {n_smk_try}; bästa edge "
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
