"""NBA sides & totals (18/11): Kambis moneyline, spread och totala poäng mot Pinnacle.

Samma kedja och regler som fotbollens sides (sides.evaluate): Pinnacles pris utan marginal är facit,
edge = p_pinnacle × Kambi-odds − 1, minsta/högsta edge, oddsram, Pinnacles insatsgräns, alternativa
linjer +1 % edge, max oddsfall, sharp money, ett spel per match. Allt gäller hela matchen inklusive
förlängning (Pinnacle period 0, Kambis "Including Overtime").

Utklassningsrisk (nba_minutes.p_blowout, P(|marginal| > 15) ur Pinnacles spread): vid en väntad
utklassning går tempot ner och startarna sätter sig i fjärde perioden, vilket drar ner totalen. Över
på totala poäng spelas därför inte när risken är över nba_sides_blowout_max (40 % ≈ spread 11,5).

Bokföring: nba_sides_spel.json (klarar alla regler), nba_sides_skugga.json (>= 1 % edge men stoppat).
Ingen egen notis – nivåerna (tiers.py) tar spelen därifrån; bara A Tier ger notis.
Rättning: ESPN:s scoreboard (slutresultat inkl. förlängning). Heltalslinjer: push = insatsen tillbaka.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .ledger import Ledger
from .market import devig_power

NBA_SIDE_MARKETS = ("ml", "spread", "game_total")
KAMBI: dict = {}        # match_id -> {bolag: {(marknad, linje, sida): odds}} (fylls av nba.kambi_nba_props)
PIN: dict = {}          # match_id -> {(marknad, linje, sida): (p, gräns, alternativ)} (fylls av nba.pinnacle_nba_props)
LABELS: dict = {}       # Kambis marknadsnamn som tolkats (diagnos)
_SKIP = (" by ", "player", "quarter", "half", "1st", "2nd", "3rd", "4th", "race to", "odd/even", "margin",
         "3-way", "double", "first", "last", "without")
# fotbollens resultatfunktion: moneyline = 1x2 utan oavgjort, spread = handikapp, total = mål
RESULT_MK = {"ml": "1x2", "spread": "ah", "game_total": "total"}


def _line_ok(x: float) -> bool:
    return abs(x * 2 - round(x * 2)) < 1e-9          # hela och halva poäng (inga kvartslinjer i NBA)


def _side(o: dict, home: str, away: str) -> str | None:
    """Hemma/borta efter lagnamnet på utfallet (säkrast); annars Kambis typ (OT_ONE = hemma)."""
    from difflib import SequenceMatcher
    from .sources.props_text import team_key
    nm = o.get("participant") or o.get("englishLabel") or o.get("label") or ""
    if nm and nm not in ("1", "2"):
        rh = SequenceMatcher(None, team_key(nm), team_key(home)).ratio()
        ra = SequenceMatcher(None, team_key(nm), team_key(away)).ratio()
        if max(rh, ra) >= 0.6 and abs(rh - ra) > 0.1:
            return "home" if rh > ra else "away"
    return {"OT_ONE": "home", "OT_TWO": "away"}.get(o.get("type"))


def kambi_main(raw: dict, home: str, away: str) -> dict:
    """{(marknad, linje, sida): odds} ur Kambis betoffer-svar för en NBA-match (hela matchen inkl. förlängning)."""
    out: dict = {}

    def put(k, o):
        out[k] = max(out.get(k, 0.0), o)
    for bo in (raw or {}).get("betOffers", []) or []:
        lab = ((bo.get("criterion") or {}).get("englishLabel") or "").strip().lower()
        typ = ((bo.get("betOfferType") or {}).get("englishName") or "").strip().lower()
        if "overtime" not in lab or any(w in lab for w in _SKIP):
            continue
        outs = bo.get("outcomes") or []
        if any(o.get("status", "OPEN") != "OPEN" for o in outs):
            continue
        # bara matchens egna marknader: "Point Spread/Handicap", "Total Points", "Moneyline" (inte lagens
        # assist/trepoängare o.d. – "Atlanta Hawks assists - Including Overtime" är också Over/Under)
        if lab.startswith(("point spread", "handicap")):
            mk = "spread"
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                side = _side(o, home, away)
                ln = o["line"] / 1000
                if side and _line_ok(ln):
                    put((mk, ln, side), o["odds"] / 1000)
        elif lab.startswith("total points"):
            mk = "game_total"
            for o in outs:
                if o.get("line") is None or not o.get("odds"):
                    continue
                side = {"OT_OVER": "over", "OT_UNDER": "under"}.get(o.get("type"))
                ln = o["line"] / 1000
                if side and _line_ok(ln):
                    put((mk, ln, side), o["odds"] / 1000)
        elif lab.startswith(("moneyline", "including overtime", "match odds")):
            if len(outs) != 2 or any(o.get("type") == "OT_CROSS" or not o.get("odds") for o in outs):
                continue
            sides = [_side(o, home, away) for o in outs]
            if sorted(x or "" for x in sides) != ["away", "home"]:
                continue
            mk = "ml"
            for o, sd in zip(outs, sides):
                put(("ml", 0.0, sd), o["odds"] / 1000)
        else:
            continue
        LABELS[lab] = mk
    return out


def pinnacle_main(markets: list, matchup_id: int) -> dict:
    """{(marknad, linje, sida): (p_fair, gräns, alternativ)} – Pinnacle utan marginal, hela matchen."""
    from .sources.pinnacle_public import american_to_decimal
    out: dict = {}
    for m in markets or []:
        if m.get("matchupId") != matchup_id or m.get("period", 0) != 0 or m.get("status", "open") != "open":
            continue
        lim = max((x.get("amount") or 0 for x in m.get("limits") or []), default=0)
        alt = bool(m.get("isAlternate"))
        d = {p.get("designation"): p for p in m.get("prices") or []}
        try:
            if m.get("type") == "moneyline":
                if all(k in d and d[k].get("price") is not None for k in ("home", "away")) and "draw" not in d:
                    ps = devig_power([american_to_decimal(float(d[k]["price"])) for k in ("home", "away")])
                    for k, p in zip(("home", "away"), ps):
                        out[("ml", 0.0, k)] = (p, lim, alt)
            elif m.get("type") in ("total", "spread"):
                a, b = ("over", "under") if m["type"] == "total" else ("home", "away")
                if a in d and b in d and d[a].get("price") is not None and d[b].get("price") is not None:
                    ps = devig_power([american_to_decimal(float(d[a]["price"])), american_to_decimal(float(d[b]["price"]))])
                    mk = "game_total" if m["type"] == "total" else "spread"
                    for side, p in zip((a, b), ps):
                        ln = float(d[side].get("points") or 0.0)
                        k = (mk, ln, side)
                        if not _line_ok(ln) or (k in out and alt and not out[k][2]):
                            continue
                        out[k] = (p, lim, alt)
        except (TypeError, ValueError):
            continue
    return out


def label(mk: str, line: float, side: str, home: str, away: str) -> tuple[str, str]:
    team = home if side == "home" else away
    if mk == "ml":
        return team, f"{team} vinner (inkl. förlängning)"
    if mk == "spread":
        return team, f"{team} {line:+g}".replace("+-", "-")
    return "Poäng", f"totala poäng {'över' if side == 'over' else 'under'} {line:g}"


def _settings(s: dict) -> dict:
    return dict(s, sides_markets=list(NBA_SIDE_MARKETS),
                sides_min_edge=s.get("nba_sides_min_edge", 0.03),
                sides_max_edge=s.get("nba_sides_max_edge", 0.15),
                sides_odds_window=s.get("nba_sides_odds_window", [1.40, 6.50]),
                sides_shadow_min_edge=s.get("nba_sides_shadow_min_edge", 0.01),
                sides_min_pin_limit=s.get("nba_sides_min_pin_limit", 500))


def blowout_block(xs: list[dict], spread_home: float | None, s: dict) -> int:
    """Över på totalen stoppas vid hög utklassningsrisk. Ett annat spel i matchen får då ta platsen."""
    from .nba_minutes import p_blowout
    if spread_home is None:
        return 0
    pb = p_blowout(spread_home)
    lim = s.get("nba_sides_blowout_max", 0.40)
    n = 0
    for x in xs:
        mk, _ln, side = x["key"]
        x["p_utklassning"] = pb
        if mk == "game_total" and side == "over" and pb > lim:
            if x["playable"]:
                n += 1
            x["playable"] = False
            x["reasons"].append(f"utklassningsrisk {pb:.0%} (spread {spread_home:+g}) – över på totalen spelas inte")
    if n and not any(x["playable"] for x in xs):   # släpp näst bästa spel i matchen som bara stoppades av "ett per match"
        rest = sorted((x for x in xs if x["reasons"] == ["redan ett spel i matchen (störst edge vinner)"]),
                      key=lambda x: -x["edge"])
        if rest:
            rest[0]["playable"], rest[0]["reasons"] = True, []
    return n


def _record(lg: Ledger, evd: dict, x: dict, s: dict, now: float) -> dict | None:
    from .sides import _bet
    if any(b.get("match_id") == evd["id"] for b in lg.bets):
        return None                                   # ett spel per match och bokföring
    b = _bet(evd, x, s, now)
    if b["key"] in lg.by_key:
        return None
    mk, line, side = x["key"]
    b["spelare"], b["spel_text"] = label(mk, line, side, evd["home_team"], evd["away_team"])
    b["spelare_id"] = "match"
    b["p_utklassning"] = x.get("p_utklassning")
    b["id"] = len(lg.bets) + 1
    lg.bets.append(b)
    lg.by_key[b["key"]] = b
    return b


def espn_scores(bets: list[dict], client, now: float) -> dict:
    """{match_id: (hemmapoäng, bortapoäng)} för avslutade matcher (ESPN:s scoreboard)."""
    from .nba import ESPN_NBA
    from .sources.http import SourceError
    from .sources.props_text import same_match
    out, boards = {}, {}
    for b in bets:
        if b["status"] != "öppen" or not b.get("avspark") or now < b["avspark"] + 3 * 3600 or b["match_id"] in out:
            continue
        if now > b["avspark"] + 14 * 86400:
            continue
        for d in (0, -1):
            day = (datetime.fromtimestamp(b["avspark"], timezone.utc) + timedelta(days=d)).strftime("%Y%m%d")
            if day not in boards:
                try:
                    boards[day] = client.get(f"{ESPN_NBA}/scoreboard", {"dates": day}, ttl=1800) or {}
                except SourceError:
                    boards[day] = {}
            for ev in boards[day].get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                if not ((ev.get("status") or {}).get("type") or {}).get("completed"):
                    continue
                t = {x.get("homeAway"): x for x in comp.get("competitors", [])}
                if "home" not in t or "away" not in t:
                    continue
                st = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
                if same_match(b["hemma"], b["borta"], b["avspark"], t["home"].get("team", {}).get("displayName", ""),
                              t["away"].get("team", {}).get("displayName", ""), st):
                    try:
                        out[b["match_id"]] = (int(float(t["home"]["score"])), int(float(t["away"]["score"])))
                    except (KeyError, TypeError, ValueError):
                        pass
            if b["match_id"] in out:
                break
    return out


def settle(lg: Ledger, scores: dict) -> list[str]:
    from .sides import result_units
    log = []
    for b in lg.bets:
        if b["status"] != "öppen" or b["match_id"] not in scores:
            continue
        hg, ag = scores[b["match_id"]]
        res = result_units(RESULT_MK[b["marknad"]], b["linje"], b["sida"], hg, ag, b["odds"], b["insats_pct"])
        status = "vunnen" if res > 1e-12 else "förlorad" if res < -1e-12 else "push"
        b.update(status=status, utfall=f"{hg}–{ag}", resultat_enheter=res)
        log.append(f"NBA sides rättad: {b['match']} {b['spel_text']} -> {status} ({hg}–{ag})")
    return log


def run(root: Path, events: list[dict], settings: dict, diag, spreads: dict | None = None) -> dict:
    """events: NBA-matcherna (evd) från skanningen. Kambi- och Pinnacle-priserna ligger i KAMBI/PIN."""
    from .sides import History
    now = time.time()
    s = _settings(settings)
    playable = set(s["playable_books"])
    hist = History(root / "nba_sides_historik.json")
    spel, skugga = Ledger(root / "nba_sides_spel.json"), Ledger(root / "nba_sides_skugga.json")
    from .sides import evaluate
    n_ev = n_lines = n_bo = 0
    new_spel, new_sk, latest, best = [], [], {}, []
    max_h = s.get("nba_sides_max_hours", 24)
    for evd in events:
        km, pm = KAMBI.get(evd["id"]), PIN.get(evd["id"])
        if not km or not pm:
            continue
        xs = evaluate(evd, km, pm, s, hist, now, playable)
        n_bo += blowout_block(xs, (spreads or {}).get(evd["id"]), s)
        n_ev += 1
        for x in xs:
            mk, line, side = x["key"]
            latest[f"{evd['id']}|{mk}|{line:g}|{side}|{x['book']}"] = x["odds"]
            latest[(evd["id"], mk, line, side)] = x.get("p_pin", x["p"])
            n_lines += 1
            best.append((x["edge"], evd, x))
            if not (0 < evd["commence_time"] - now <= max_h * 3600):
                continue
            if x["playable"]:
                b = _record(spel, evd, x, s, now)
                if b:
                    new_spel.append(b)
            elif x["edge"] >= s["sides_shadow_min_edge"]:
                b = _record(skugga, evd, x, s, now)
                if b:
                    new_sk.append(b)
    for lg in (spel, skugga):   # stängning före avspark: bolagets senaste odds och Pinnacles sannolikhet
        for b in lg.bets:
            if b["status"] != "öppen" or now >= b["avspark"]:
                continue
            if b["key"] in latest:
                b["stangning"] = latest[b["key"]]
            pk = (b["match_id"], b["marknad"], b["linje"], b["sida"])
            if pk in latest:
                b["pin_stang_p"] = latest[pk]
    try:
        from .sources.http import JsonClient
        scores = espn_scores(spel.bets + skugga.bets, JsonClient(root / ".cache_odds", ttl_s=900), now)
        for lg in (spel, skugga):
            for line in settle(lg, scores):
                diag.lines.append("  " + line)
    except Exception as e:  # noqa: BLE001 – rättningen får aldrig stoppa skanningen
        diag.log(f"NBA sides rättning: FEL {type(e).__name__}: {e}")
    hist.save(now)
    spel.save()
    skugga.save()
    top = sorted(best, key=lambda t: -t[0])[:3]
    diag.log(f"NBA sides/totals: {n_ev} matcher med Kambi + Pinnacle, {n_lines} linjer, {len(new_spel)} nya spel, "
             f"{len(new_sk)} nya skuggspel, {n_bo} över stoppade (utklassning); bästa edge "
             + ", ".join(f"{e:+.1%} ({label(*x['key'], ev['home_team'], ev['away_team'])[1]})" for e, ev, x in top))
    if LABELS:
        diag.log("NBA sides: Kambis marknader " + "; ".join(f"{k} -> {v}" for k, v in sorted(LABELS.items()))[:400])
    return {"spel": spel, "skugga": skugga, "new": new_spel}
