"""PropLine (https://prop-line.com) – oberoende bolag för fotbollens spelarprops (DraftKings, FanDuel, Bovada, Hard Rock …).

Gratisnivån: 1 000 anrop/dygn. Nyckeln läses ur PROPLINE_API_KEY (GitHub-hemlighet, header X-API-Key); saknas den
hoppas allt över. Bara referens, aldrig spelbolag. Bolagsnamn blir "pl_<bolag>" och provider "propline".
Anropsbudget: matchlistan per liga hämtas högst var 3:e timme, odds per match högst var 60:e minut och bara för
matcher som startar inom fönstret; allt stoppar vid DAILY_STOP använda anrop (räknas ur svarshuvudet).
Marknader: skott på mål ("N+ Shots on Target" = över N−0,5, ensidigt) och skott. Kambi-baserade bolag (Unibet,
BetRivers) och DFS-sajter (ParlayPlay, Sleeper, PrizePicks, Underdog) används inte som röster.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from ..models import OddsQuote
from .props_text import name_key, same_match

BASE = "https://api.prop-line.com/v1"
LEAGUES = ["soccer_epl", "soccer_la_liga", "soccer_serie_a", "soccer_bundesliga", "soccer_ligue_1",
           "soccer_championship", "soccer_eredivisie", "soccer_primeira_liga", "soccer_scottish_premiership",
           "soccer_belgium_pro_league", "soccer_turkey_super_lig", "soccer_uefa_champions_league",
           "soccer_uefa_europa_league", "soccer_uefa_conference_league", "soccer_mls"]
MARKETS = {"player_shots_on_target": "shots_on_target", "player_shots": "shots"}
SKIP_BOOKS = {"unibet", "betrivers", "parlayplay", "sleeper", "prizepicks", "underdog", "pick6"}  # Kambi / DFS
STATE = "propline_lage.json"
DAILY_STOP = 850
EVENTS_TTL_S = 3 * 3600
ODDS_TTL_S = 3600


def _ts(iso) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def american_to_decimal(p: float) -> float | None:
    if not p or p == 0:
        return None
    return 1 + p / 100 if p > 0 else 1 + 100 / abs(p)


def parse(event: dict, match_id: str, ts: float, markets: dict | None = None) -> tuple[list[OddsQuote], dict[str, str]]:
    """Propline-händelse -> OddsQuote. Milstolpar ('2+ Shots on Target') = över 1,5; över/under med 'point' stöds också."""
    mk = markets or MARKETS
    quotes, names = [], {}
    for bm in event.get("bookmakers", []):
        key = bm.get("key") or ""
        if key in SKIP_BOOKS:
            continue
        for m in bm.get("markets", []):
            ours = mk.get(m.get("key"))
            if not ours:
                continue
            for o in m.get("outcomes", []):
                player, nm = o.get("description") or "", str(o.get("name") or "")
                odds = american_to_decimal(o.get("price"))
                if not player or not odds or odds <= 1.0:
                    continue
                ms = re.match(r"^(\d+)\+", nm)
                if ms:
                    line, side = int(ms.group(1)) - 0.5, "over"
                elif nm.lower() in ("over", "under") and o.get("point") is not None:
                    line, side = float(o["point"]), nm.lower()
                else:
                    continue
                pid = name_key(player)
                names.setdefault(pid, player)
                quotes.append(OddsQuote(book="pl_" + key, match_id=match_id, player_id=pid, market=ours, line=line,
                                        side=side, odds=round(odds, 3), ts=ts, provider="propline", variant=m["key"]))
    return quotes, names


def _get(path: str, key: str):
    req = urllib.request.Request(BASE + path, headers={"X-API-Key": key, "Accept": "application/json",
                                                       "User-Agent": "propsbot"})
    with urllib.request.urlopen(req, timeout=40) as r:
        remaining = r.headers.get("X-Daily-Remaining")
        return json.loads(r.read().decode("utf-8")), (int(remaining) if remaining and remaining.isdigit() else None)


def add_propline(root: Path, data: list, settings: dict, diag) -> int:
    key = (os.environ.get("PROPLINE_API_KEY") or "").strip()   # hemligheter kan ha radbrytning sist
    if not key or not settings.get("propline_enabled", True):
        diag.log("PropLine: av (ingen PROPLINE_API_KEY)") if not key else None
        return 0
    path = root / STATE
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        st = {}
    now = time.time()
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    if st.get("day") != day:
        st = {"day": day, "used": 0, "events": st.get("events", {}), "odds": {}}
    st.setdefault("events", {})
    st.setdefault("odds", {})
    window_h = settings.get("propline_window_h", 10)
    cap = settings.get("propline_daily_stop", DAILY_STOP)
    calls = 0

    def call(p):
        nonlocal calls
        if st["used"] >= cap:
            raise RuntimeError("dagsgräns")
        d, rem = _get(p, key)
        st["used"] += 1
        calls += 1
        if rem is not None:
            st["used"] = max(st["used"], 1000 - rem)
        return d

    n_quotes = 0
    try:
        soon = [(evd, qs, nm) for evd, qs, nm in data if evd.get("commence_time") and 0 < evd["commence_time"] - now <= window_h * 3600]
        if not soon:
            return 0
        for lg in settings.get("propline_leagues", LEAGUES):
            ent = st["events"].get(lg) or {}
            ttl = EVENTS_TTL_S if ent.get("list") else 600   # tom lista (t.ex. efter fel) förnyas efter 10 min
            if now - ent.get("ts", 0) > ttl:
                try:
                    ev = call(f"/sports/{lg}/events")
                    ent = {"ts": now, "list": [{k: e.get(k) for k in ("id", "home_team", "away_team", "commence_time")}
                                               for e in (ev if isinstance(ev, list) else ev.get("events", []))]}
                    st["events"][lg] = ent
                except RuntimeError:
                    raise
                except Exception as e:  # noqa: BLE001
                    diag.log(f"PropLine {lg}: {type(e).__name__}: {str(e)[:100]}")
                    ent = {"ts": now, "list": ent.get("list", [])}
                    st["events"][lg] = ent
        flat = [(lg, e) for lg, ent in st["events"].items() for e in ent.get("list", [])]
        for evd, qs, nm in soon:
            hit = next(((lg, e) for lg, e in flat if same_match(
                evd["home_team"], evd["away_team"], evd["commence_time"],
                e.get("home_team") or "", e.get("away_team") or "", _ts(e.get("commence_time")))), None)
            if not hit:
                continue
            lg, e = hit
            eid = str(e["id"])
            cached = st["odds"].get(eid)
            if not cached or now - cached.get("ts", 0) > ODDS_TTL_S:
                mk = ",".join(settings.get("propline_markets", ["player_shots_on_target"]))
                try:
                    ev = call(f"/sports/{lg}/events/{eid}/odds?markets={mk}")
                except RuntimeError:
                    raise
                except Exception as ex:  # noqa: BLE001
                    diag.log(f"PropLine odds {eid}: {type(ex).__name__}: {str(ex)[:100]}")
                    continue
                q, n = parse(ev, evd["id"], now)
                st["odds"][eid] = {"ts": now, "quotes": [[x.book, x.player_id, x.market, x.line, x.side, x.odds] for x in q],
                                   "names": n}
                cached = st["odds"][eid]
            q = [OddsQuote(book=b, match_id=evd["id"], player_id=pid, market=m, line=ln, side=sd, odds=od, ts=cached["ts"],
                           provider="propline") for b, pid, m, ln, sd, od in cached["quotes"]]
            qs.extend(q)
            nm.update({k: v for k, v in cached.get("names", {}).items() if k not in nm})
            n_quotes += len(q)
    except RuntimeError as ex:
        diag.log(f"PropLine: {ex} ({st['used']} anrop idag)")
    except Exception as ex:  # noqa: BLE001 – får aldrig stoppa skanningen
        diag.log(f"PropLine: FEL {type(ex).__name__}: {str(ex)[:150]}")
    finally:
        try:
            path.write_text(json.dumps(st), encoding="utf-8")
        except OSError:
            pass
    diag.log(f"PropLine: {calls} anrop denna körning ({st['used']}/1000 idag), {n_quotes} priser i bruk")
    return n_quotes
