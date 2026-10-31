"""NBA-props: Kambi-bolagen mot Pinnacles tvåsidiga spelarodds.

Marknader: poäng, returer, assist, trepoängare, PRA (poäng + returer + assist).
Samma regler som fotboll: odds 1,40–6,00, minst 2 % edge, ¼ Kelly, bokföring,
skuggspel, parlays och notiser. Bästa pris jämförs mot konsensus från de ANDRA
källorna (Pinnacle väger tyngst, Kambi räknas som en röst).
Rättning mot ESPN:s NBA-boxscore.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Config
from .ledger import Ledger
from .models import OddsQuote
from .scan import evaluate_event_market_only, load_settings
from .sources.http import JsonClient, SourceError
from .sources.kambi_public import BASES, KambiEvent
from .sources.pinnacle_public import BASE as PIN_BASE, PinnaclePublic, american_to_decimal
from .sources.props_text import name_key, person_name, same_match, same_person

NBA_MARKETS = ("points", "rebounds", "assists", "threes", "steals", "blocks", "pra", "pr", "ra")
NBA_LABEL = {"points": "Poäng", "rebounds": "Returer", "assists": "Assist",
             "threes": "Trepoängare", "steals": "Steals", "blocks": "Blocks",
             "pra": "PRA", "pr": "Poäng + returer", "ra": "Returer + assist"}
EXCLUDE = ("quarter", "half", "1st", "2nd", "3rd", "4th", "first", "double", "triple",
           "turnover", "most", "team", "race", "odd", "even", "milestone",
           "highest", "lowest", "exact", "both", " or ", "&nbsp")
PIN_BASKETBALL = 4


def nba_market(label: str) -> str | None:
    s = label.lower()
    if any(w in s for w in EXCLUDE):
        return None
    if re.search(r"points?,? rebounds?,? (and|&|\+) assists?|pts\s*\+\s*rebs?\s*\+\s*asts?|\bpra\b", s):
        return "pra"
    if re.search(r"points?\s*(and|&|\+)\s*rebounds?|pts\s*\+\s*rebs?|\bp\+r\b", s):
        return "pr"
    if re.search(r"rebounds?\s*(and|&|\+)\s*assists?|rebs?\s*\+\s*asts?|\br\+a\b", s):
        return "ra"
    if re.search(r"\+|&| and ", s):          # andra kombinationer (P+A, S+B …) används inte
        return None
    if "steal" in s:
        return "steals"
    if "block" in s:
        return "blocks"
    if "3-point" in s or "3 point" in s or "three" in s or "3pt" in s:
        return "threes"
    if "rebound" in s:
        return "rebounds"
    if "assist" in s:
        return "assists"
    if "point" in s:
        return "points"
    return None


# ---------------------------------------------------------------- Kambi
def kambi_nba_events(c: JsonClient, offering: str, market: str, hours: float
                     ) -> tuple[list[KambiEvent], bool]:
    raw = None
    for b in BASES:
        try:
            raw = c.get(f"{b}/{offering}/listView/basketball/nba/all/all/matches.json",
                        {"lang": "en_GB", "market": market, "useCombined": "true"})
        except SourceError:
            continue
        if raw is not None:
            break
    if raw is None:
        return [], False
    now = time.time()
    out = []
    for item in raw.get("events", []):
        ev = item.get("event", item)
        try:
            start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            continue
        if not (now - 600 < start < now + hours * 3600) or ev.get("state") not in (None, "NOT_STARTED"):
            continue
        out.append(KambiEvent(int(ev["id"]), ev.get("homeName", ""), ev.get("awayName", ""), start, "NBA"))
    return out, True


def kambi_nba_props(c: JsonClient, offering: str, book: str, market: str, ev: KambiEvent,
                    match_id: str) -> tuple[list[OddsQuote], dict[str, str]]:
    raw = None
    for b in BASES:
        try:
            raw = c.get(f"{b}/{offering}/betoffer/event/{ev.event_id}.json",
                        {"lang": "en_GB", "market": market, "includeParticipants": "true"})
        except SourceError:
            continue
        if raw is not None:
            break
    if not raw:
        return [], {}
    now = time.time()
    qs, names = [], {}
    for bo in raw.get("betOffers", []):
        label = (bo.get("criterion", {}).get("englishLabel") or "").strip()
        mk = nba_market(label)
        if not mk:
            continue
        for o in bo.get("outcomes", []):
            if o.get("status", "OPEN") != "OPEN" or not o.get("odds") or o.get("line") is None:
                continue
            player = o.get("participant") or ""
            if not player or not (o.get("participantId") or o.get("participant")):
                continue
            t = (o.get("type") or "").upper()
            lab = (o.get("englishLabel") or o.get("label") or "").lower()
            if t == "OT_OVER" or lab == "over":
                side = "over"
            elif t == "OT_UNDER" or lab == "under":
                side = "under"
            else:
                continue
            line = o["line"] / 1000.0
            if abs(line - round(line)) < 1e-9:     # heltal = "minst N" -> över N-0,5
                line -= 0.5
            pid = name_key(player)
            names.setdefault(pid, person_name(player))
            qs.append(OddsQuote(book=book, match_id=match_id, player_id=pid, market=mk, line=line,
                                side=side, odds=o["odds"] / 1000.0, ts=now, provider="kambi",
                                variant=label.lower()))
    return qs, names


# ---------------------------------------------------------------- Pinnacle
def pinnacle_nba(pin: PinnaclePublic, hours: float):
    leagues = pin.c.get(f"{PIN_BASE}/sports/{PIN_BASKETBALL}/leagues", {"all": "false"}, ttl=3600) or []
    nba = [lg for lg in leagues if lg.get("name", "").strip().upper() == "NBA"]
    evs = []
    for lg in nba:
        evs += pin.events(lg, hours)
    return evs


def pinnacle_nba_props(pin: PinnaclePublic, ev, match_id: str) -> tuple[list[OddsQuote], dict]:
    related = pin.c.get(f"{PIN_BASE}/matchups/{ev.matchup_id}/related") or []
    markets = pin.c.get(f"{PIN_BASE}/matchups/{ev.matchup_id}/markets/related/straight") or []
    now = time.time()
    specials = {}
    for m in related:
        if m.get("type") != "special":
            continue
        sp = m.get("special", {})
        if "team" in (sp.get("category") or "").lower():
            continue
        desc = sp.get("description") or ""
        units = m.get("units") or ""
        inner = re.search(r"\((.*?)\)", desc)
        mk = nba_market(inner.group(1) if inner else f"{desc} {units}")
        if not mk:
            continue
        player = desc.split("(")[0].strip()
        pmap = {p["id"]: (p.get("name") or "").lower() for p in m.get("participants", []) if "id" in p}
        specials[int(m["id"])] = (player, mk, pmap)
    qs, names = [], {}
    for mkt in markets:
        sid = mkt.get("matchupId")
        if sid not in specials or mkt.get("isAlternate"):
            continue
        player, mk, pmap = specials[sid]
        for pr in mkt.get("prices", []):
            side = pmap.get(pr.get("participantId"), pr.get("designation") or "")
            if side not in ("over", "under") or pr.get("points") is None or pr.get("price") is None:
                continue
            pid = name_key(player)
            names.setdefault(pid, person_name(player))
            qs.append(OddsQuote(book="pinnacle", match_id=match_id, player_id=pid, market=mk,
                                line=float(pr["points"]), side=side,
                                odds=round(american_to_decimal(float(pr["price"])), 3), ts=now,
                                provider="pinnacle", variant=mk))
    return qs, names


# ---------------------------------------------------------------- rättning
ESPN_NBA = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
BOX_KEYS = {"points": ("PTS",), "rebounds": ("REB",), "assists": ("AST",), "threes": ("3PT",),
            "steals": ("STL",), "blocks": ("BLK",)}
COMBOS = {"pra": ("PTS", "REB", "AST"), "pr": ("PTS", "REB"), "ra": ("REB", "AST")}


def _box_value(labels: list[str], stats: list[str], market: str) -> float | None:
    def get(key):
        if key not in labels:
            return None
        v = stats[labels.index(key)]
        if key == "3PT":                     # "3-7" = 3 träffar av 7
            v = str(v).split("-")[0]
        try:
            return float(v)
        except ValueError:
            return None
    if market in COMBOS:
        parts = [get(k) for k in COMBOS[market]]
        return None if None in parts else sum(parts)
    return get(BOX_KEYS[market][0])


def settle_nba(ledger: Ledger, c: JsonClient, now: float | None = None) -> list[str]:
    now = now or time.time()
    log, cache = [], {}
    for b in ledger.bets:
        if b["status"] != "öppen" or not b.get("avspark") or now < b["avspark"] + 3.5 * 3600:
            continue
        mid = b["match_id"]
        if mid not in cache:
            cache[mid] = None
            for d in (0, -1):
                day = (datetime.fromtimestamp(b["avspark"], timezone.utc) + timedelta(days=d)).strftime("%Y%m%d")
                try:
                    board = c.get(f"{ESPN_NBA}/scoreboard", {"dates": day}, ttl=1800) or {}
                except SourceError:
                    continue
                for ev in board.get("events", []):
                    comp = (ev.get("competitions") or [{}])[0]
                    t = {x.get("homeAway"): x.get("team", {}).get("displayName", "") for x in comp.get("competitors", [])}
                    st = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
                    if same_match(b["hemma"], b["borta"], b["avspark"], t.get("home", ""), t.get("away", ""), st) \
                            and ev.get("status", {}).get("type", {}).get("completed"):
                        try:
                            cache[mid] = c.get(f"{ESPN_NBA}/summary", {"event": ev["id"]}, ttl=3600)
                        except SourceError:
                            pass
                if cache[mid]:
                    break
        summ = cache[mid]
        if not summ:
            continue
        found = None
        for team in (summ.get("boxscore") or {}).get("players", []) or []:
            for grp in team.get("statistics", []) or []:
                labels = grp.get("labels") or grp.get("names") or []
                for a in grp.get("athletes", []) or []:
                    if same_person((a.get("athlete") or {}).get("displayName", ""), b["spelare"]):
                        found = (labels, a)
        if not found:
            ledger.settle(b, None, played=False)
            log.append(f"NBA struken: {b['spelare']} ({b['match']})")
            continue
        labels, a = found
        stats = a.get("stats") or []
        if a.get("didNotPlay") or not stats:
            ledger.settle(b, None, played=False)
            continue
        val = _box_value(labels, stats, b["marknad"])
        if val is None:
            log.append(f"NBA rättning: statistik saknas för {b['spelare']} ({labels})")
            continue
        ledger.settle(b, int(val), True)
        log.append(f"NBA rättad: {b['spelare']} {b['marknad']} över {b['linje']} -> {b['status']} ({val:g})")
    return log


# ---------------------------------------------------------------- skanning
def nba_scan(root: Path, settings_path: Path) -> dict:
    from .free_scan import Diag, _unify_players
    settings = load_settings(settings_path)
    settings["kambi_hint_prefixes"] = list(set(settings["kambi_hint_prefixes"])
                                           | set(settings["kambi_offerings"].values()))
    cfg = Config()
    diag = Diag(dir=root / "diagnos_nba")
    diag.log(time.strftime("NBA-skanning %Y-%m-%d %H:%M"))
    hours = settings.get("nba_hours_ahead", 30)
    kc = JsonClient(root / ".cache_odds", ttl_s=90)
    working, events = {}, []
    for code, book in settings["kambi_offerings"].items():
        try:
            evs, ok = kambi_nba_events(kc, code, settings["kambi_market"], hours)
        except SourceError as e:
            diag.log(f"Kambi {book} ({code}) NBA: FEL {e}")
            continue
        if ok:
            working[code] = book
            if not events:
                events = evs
    diag.log(f"Kambi NBA: {len(events)} matcher, bolag: {', '.join(sorted(set(working.values())))}")
    t0 = time.time()
    per = {}
    for ev in sorted(events, key=lambda e: e.start)[: settings.get("nba_max_events", 15)]:
        evd = {"id": f"nba{ev.event_id}", "home_team": ev.home, "away_team": ev.away,
               "commence_time": ev.start, "league": "NBA"}
        qs_all, names = [], {}
        for code, book in working.items():
            try:
                qs, nm = kambi_nba_props(kc, code, book, settings["kambi_market"], ev, evd["id"])
            except SourceError:
                continue
            qs_all += qs
            names.update(nm)
        per[ev.event_id] = (evd, qs_all, names)
    diag.log(f"NBA tid: Kambi-props {time.time() - t0:.0f} s")
    t0 = time.time()
    try:
        pin = PinnaclePublic(JsonClient(root / ".cache_odds", ttl_s=60, min_interval_s=0.6))
        pevs = pinnacle_nba(pin, hours)
        n = 0
        for evd, qs_all, names in per.values():
            pe = next((p for p in pevs if same_match(evd["home_team"], evd["away_team"], evd["commence_time"],
                                                     p.home, p.away, p.start)), None)
            if not pe:
                continue
            try:
                qs, nm = pinnacle_nba_props(pin, pe, evd["id"])
            except SourceError:
                continue
            n += len(qs)
            qs_all += qs
            names.update(nm)
        diag.log(f"Pinnacle NBA: {len(pevs)} matcher, {n} spelarodds ({time.time() - t0:.0f} s)")
    except Exception as e:
        diag.log(f"Pinnacle NBA: FEL {type(e).__name__}: {e}")
    rows = []
    mc = Counter()
    for evd, qs_all, names in per.values():
        _unify_players(qs_all, names)
        mc.update(f"{q.book}:{q.market}" for q in qs_all)
        if qs_all:
            rows += evaluate_event_market_only(evd, qs_all, names, settings, cfg, time.time(), "NBA")
    diag.log("NBA-odds per bolag och marknad: " + ", ".join(f"{k} {v}" for k, v in sorted(mc.items())))
    rows.sort(key=lambda r: -r.row.decision.cand.edge)
    playable = [r for r in rows if r.row.decision.playable and r.row.decision.show]
    diag.log(f"NBA: {len(playable)} spelbara ben av {len(rows)}")
    for r in playable[:10]:
        c = r.row.decision.cand
        diag.log(f"NBA SPEL: {r.match} | {c.player_name} {c.market} över {c.line} | {c.best.book} "
                 f"{c.best.odds:.2f} | p {c.p:.1%} | edge {c.edge:.1%}")
    evd_by_id = {v[0]["id"]: v[0] for v in per.values()}
    ledger = Ledger(root / "nba_bokforing.json")
    new = ledger.record(rows, evd_by_id)
    ledger.update_closing(rows, time.time())
    shadow = Ledger(root / "nba_skugga.json")
    shadow.record(rows, evd_by_id, predicate=lambda r: (not r.row.decision.playable and r.row.decision.show
                                                       and r.row.decision.cand.edge >= 0.02))
    shadow.update_closing(rows, time.time())
    ec = JsonClient(root / ".cache_odds", ttl_s=900)
    for lg in (ledger, shadow):
        try:
            for line in settle_nba(lg, ec):
                diag.log(line)
        except Exception as e:
            diag.log(f"NBA rättning: {type(e).__name__}: {e}")
        lg.save()
    diag.save()
    return {"rows": rows, "playable": playable, "ledger": ledger, "shadow": shadow,
            "evd": evd_by_id, "diag": diag, "new": new}
