"""Provar om externa datakällor svarar från den här servern (för beslut om nya källor).

Just nu: börser och prediktionsmarknader (där begränsade, skarpa spelare spelar).
Letar efter NBA-/fotbollsprops och skriver ut antal + exempel i körningens logg.
"""
import json
import re
import urllib.request

from .sources.http import UA

PROP_WORDS = re.compile(r"points|rebounds|assists|threes|3-pointers|pts|shots on target|"
                        r"player|o/u|over|anytime", re.I)


def _get(url: str, n: int = 60_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read(n).decode("utf-8", "replace")


def kalshi() -> str:
    """Få anrop (Kalshi begränsar): poäng- och assistmarknader, alla fält med pris/volym."""
    import time
    base = "https://api.elections.kalshi.com/trade-api/v2"
    out = []
    for ser in ("KXNBAPTS", "KXNBAAST", "KXNBAREB"):
        time.sleep(1.5)
        _, b = _get(f"{base}/markets?series_ticker={ser}&status=open&limit=1000")
        ms = json.loads(b).get("markets", [])
        num = lambda m, *ks: next((float(m[k]) for k in ks if m.get(k) not in (None, "")), 0.0)
        vol = sum(num(m, "volume_fp", "volume") for m in ms)
        oi = sum(num(m, "open_interest_fp", "open_interest") for m in ms)
        quoted = [m for m in ms if num(m, "yes_bid_dollars", "yes_bid") > 0 and num(m, "yes_ask_dollars", "yes_ask") > 0]
        sp = sorted(num(m, "yes_ask_dollars", "yes_ask") - num(m, "yes_bid_dollars", "yes_bid") for m in quoted)
        top = sorted(ms, key=lambda m: -num(m, "volume_fp", "volume"))[:3]
        out.append(f"{ser}: {len(ms)} öppna, med bud {len(quoted)}, volym {vol:,.0f}, OI {oi:,.0f}, "
                   f"median spread {sp[len(sp)//2] if sp else None}")
        out += ["   " + m.get("title", "")[:45] + " | " + ", ".join(
            f"{k}={v}" for k, v in m.items() if any(w in k for w in ("bid", "ask", "volume", "interest", "close_time")))[:260]
            for m in top]
    return " || ".join(out)


def polymarket() -> str:
    _, body = _get("https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=nba")
    evs = json.loads(body)
    mk = [m for e in evs for m in e.get("markets", [])]
    # Bara matchprops ("X: Points O/U 24.5" o.d.), inte säsongsmarknader.
    props = [m for m in mk if re.search(r"points|rebounds|assists|threes", m.get("question", ""), re.I)
             and not re.search(r"season|career|lead the nba|mvp|20\d\d-\d\d", m.get("question", ""), re.I)]
    ou = [m for m in props if re.search(r"O/U", m.get("question", ""))]
    f = lambda m, k: float(m.get(k) or 0)
    liq = sum(f(m, "liquidity") for m in ou)
    vol = sum(f(m, "volume") for m in ou)
    top = sorted(ou, key=lambda m: -f(m, "volume"))[:8]
    ex = " || ".join(f"{m.get('question','')[:50]}: pris {m.get('outcomePrices')} bid {m.get('bestBid')} ask {m.get('bestAsk')} "
                     f"vol {f(m,'volume'):,.0f} likv {f(m,'liquidity'):,.0f}" for m in top)
    spreads = sorted(f(m, "bestAsk") - f(m, "bestBid") for m in ou if m.get("bestAsk") and m.get("bestBid"))
    med = spreads[len(spreads) // 2] if spreads else None
    return (f"spelar-O/U {len(ou)} (volym {vol:,.0f} USD, likviditet {liq:,.0f} USD, median spread {med}) || {ex}")


def plain(url: str) -> str:
    st, body = _get(url, 300)
    return f"{st} {body[:100]!r}"


def jsonish(url: str, keys=()) -> str:
    st, body = _get(url, 3_000_000)
    try:
        d = json.loads(body)
        info = ", ".join(f"{k}={len(d.get(k, []))}" for k in keys) if isinstance(d, dict) else f"lista {len(d)}"
        return f"{st} JSON ok {info}"
    except ValueError:
        return f"{st} inte JSON: {body[:80]!r}"


CHECKS = {
    # Fotbollsstatistik (fouls per spelare): vilka svarar från GitHub?
    "sofascore_events": lambda: jsonish("https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-11-01", ("events",)),
    "sofascore_lineups": lambda: jsonish("https://api.sofascore.com/api/v1/event/12436870/lineups", ("home",)),
    "fotmob_matches": lambda: jsonish("https://www.fotmob.com/api/matches?date=20261101", ("leagues",)),
    "fbref_pl": lambda: plain("https://fbref.com/en/comps/9/misc/Premier-League-Stats"),
    "understat": lambda: plain("https://understat.com/league/EPL"),
    "espn_summary": lambda: jsonish("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event=401878764", ("rosters",)),
}


def espn_fouls_fields() -> str:
    _, body = _get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event=401878764")
    d = json.loads(body)
    r = d["rosters"][0]["roster"][0]
    return ", ".join(sorted({s.get("name") or s.get("abbreviation") for s in r.get("stats", [])}))


def pinnacle_special_leagues() -> str:
    """Finns fouls/kort/hörnor som egna Pinnacle-ligor (t.ex. 'England - Premier League Bookings')?"""
    from .sources.pinnacle_public import BASE as base, GUEST_KEY
    req = urllib.request.Request(f"{base}/sports/29/leagues?all=false",
                                 headers={"User-Agent": UA, "Accept": "application/json", "X-API-Key": GUEST_KEY,
                                          "Referer": "https://www.pinnacle.com/"})
    with urllib.request.urlopen(req, timeout=25) as r:
        lg = json.loads(r.read().decode())
    from collections import Counter
    kinds = Counter()
    ex = {}
    for x in lg:
        n = x.get("name", "")
        for w in ("Foul", "Booking", "Card", "Corner", "Offside", "Shots", "Throw"):
            if w.lower() in n.lower():
                kinds[w] += 1
                ex.setdefault(w, []).append(f"{n}({x.get('matchupCount')})")
    return f"{len(lg)} ligor; " + "; ".join(f"{k}: {v} t.ex. {', '.join(ex[k][:4])}" for k, v in kinds.items())


def kambi_league_props() -> str:
    """Vilka ligor har spelarprops (skott på mål / fouls) hos Unibet, ATG och Svenska Spel?"""
    import time as _t
    from .sources.kambi_public import BASES
    from .sources.props_text import market_from_label

    def get(off, path, extra=""):
        url = f"{BASES[0]}/{off}/{path}?lang=en_GB&market=SE{extra}"
        _t.sleep(0.25)
        return json.loads(_get(url)[1])
    now = _t.time()
    leagues = {}
    paths_by_off = {}
    for off in ("ubse", "atg", "svenskaspel"):
        raw = get(off, "listView/football/all/all/all/matches.json", "&useCombined=true")
        ps = set()
        for it in raw.get("events", []):
            ev = it.get("event", it)
            if ev.get("state") not in (None, "NOT_STARTED"):
                continue
            path = " / ".join(p.get("englishName", p.get("name", "")) for p in ev.get("path", []))
            ps.add(path)
            if off == "ubse":
                leagues.setdefault(path, ev["id"])
        paths_by_off[off] = ps
    rows = []
    for path, eid in sorted(leagues.items())[:150]:
        try:
            bo = get("ubse", f"betoffer/event/{eid}.json", "&includeParticipants=true")
        except Exception:
            continue
        sot = fouls = 0
        for b in bo.get("betOffers", []):
            mk = market_from_label((b.get("criterion") or {}).get("englishLabel", ""))
            if mk and mk[0] == "shots_on_target":
                sot += 1
            elif mk and mk[0] == "fouls":
                fouls += 1
        if sot or fouls:
            on = "".join(x[0].upper() for x in ("atg", "svenskaspel") if path in paths_by_off[x])
            rows.append(f"{path} [SOT {sot}, fouls {fouls}, även {on or '-'}]")
    return f"{len(leagues)} ligor hos Unibet, {len(rows)} med SOT/fouls-props: " + " | ".join(rows)


def football_data() -> str:
    """football-data.co.uk: lagfouls (HF/AF), kort och domare per match + kommande matcher."""
    out = []
    for season in ("2627", "2526"):
        for div in ("E0", "E1", "SP1", "D1", "I1", "F1", "N1", "P1", "B1", "SC0", "T1", "G1"):
            try:
                st, body = _get(f"https://www.football-data.co.uk/mmz4281/{season}/{div}.csv", 2_000_000)
            except Exception as e:
                out.append(f"{season}/{div}: FEL {getattr(e, 'code', '')}")
                continue
            lines = body.strip().splitlines()
            head = lines[0].split(",") if lines else []
            has = [c for c in ("HF", "AF", "HY", "AY", "Referee") if c in head]
            out.append(f"{season}/{div}: {len(lines) - 1} matcher, {'/'.join(has)}")
        if any("matcher" in x and not x.endswith(": 0 matcher, ") for x in out if x.startswith(season)):
            break
    st, body = _get("https://www.football-data.co.uk/fixtures.csv", 2_000_000)
    lines = body.strip().splitlines()
    head = lines[0].split(",")
    ref = head.index("Referee") if "Referee" in head else None
    n_ref = sum(1 for l in lines[1:] if ref is not None and len(l.split(",")) > ref and l.split(",")[ref].strip())
    out.append(f"fixtures.csv: {len(lines) - 1} kommande, domare angiven i {n_ref}")
    return " | ".join(out)


def api_football() -> str:
    """API-Football med nyckel (secret API_FOOTBALL_KEY): kvot, aktuell säsong, spelarfouls."""
    import os
    key = (os.environ.get("API_FOOTBALL_KEY") or "").strip()
    if not key:
        return "ingen API_FOOTBALL_KEY"
    def get(path):
        req = urllib.request.Request("https://v3.football.api-sports.io" + path,
                                     headers={"x-apisports-key": key, "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())
    out = []
    st = get("/status")
    resp = st.get("response") or {}
    out.append(f"status: plan {((resp.get('subscription') or {}).get('plan'))}, anrop idag "
               f"{((resp.get('requests') or {}).get('current'))}/{((resp.get('requests') or {}).get('limit_day'))}, fel {st.get('errors')}")
    lg = get("/leagues?id=39&current=true")
    seasons = [(x.get("year"), (x.get("coverage") or {}).get("fixtures", {}).get("statistics_players"))
               for r in lg.get("response", []) for x in r.get("seasons", [])]
    out.append(f"PL aktuell säsong {seasons}, fel {lg.get('errors')}")
    year = seasons[0][0] if seasons else 2026
    fx = get(f"/fixtures?league=39&season={year}&status=FT&from=2026-10-01&to=2026-11-03")
    out.append(f"fixtures {year}: {fx.get('results')} st, fel {fx.get('errors')}")
    if fx.get("response"):
        fid = fx["response"][-1]["fixture"]["id"]
        pl = get(f"/fixtures/players?fixture={fid}")
        ps = [p for t in pl.get("response", []) for p in t.get("players", [])]
        if ps:
            f0 = ps[0]["statistics"][0].get("fouls")
            out.append(f"spelare i match {fid}: {len(ps)}, fouls-fält t.ex. {f0}")
        else:
            out.append(f"spelarstatistik: tom, fel {pl.get('errors')}")
    return " | ".join(out)


def transfermarkt() -> str:
    """dcaribou/transfermarkt-datasets: storlek, och om games.csv.gz har domare + kommande matcher."""
    import gzip, io, csv
    base = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
    out = []
    req = urllib.request.Request(base + "transfermarkt-datasets.duckdb", method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            out.append(f"duckdb {int(r.headers.get('Content-Length', 0)) / 1e6:.0f} MB")
    except Exception as e:
        out.append(f"duckdb FEL {e}")
    for name in ("games.csv.gz", "game_events.csv.gz", "appearances.csv.gz"):
        try:
            req = urllib.request.Request(base + name, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            txt = gzip.decompress(raw).decode("utf-8", "replace")
            rows = list(csv.DictReader(io.StringIO(txt)))
            cols = list(rows[0].keys()) if rows else []
            info = f"{name}: {len(raw) / 1e6:.0f} MB, {len(rows)} rader"
            if name == "games.csv.gz" and rows:
                dates = sorted(r.get("date", "") for r in rows)
                ref = sum(1 for r in rows if r.get("referee"))
                fut = sum(1 for r in rows if r.get("date", "") >= "2026-11-04")
                comps = len({r.get("competition_id") for r in rows})
                cl = [r for r in rows if r.get("competition_id") == "CL" and r.get("date", "") >= "2026-09-01"]
                info += f", domare i {ref}, senaste {dates[-1]}, framtida {fut}, tävlingar {comps}, CL i år {len(cl)}"
            info += f", kolumner {cols[:14]}"
            out.append(info)
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {e}")
    return " | ".join(out)


def uefa_referees() -> str:
    """UEFA:s öppna match-API: står domaren för kommande CL/EL/ECL-matcher?"""
    url = ("https://match.uefa.com/v5/matches?competitionId=1&fromDate=2026-11-04&toDate=2026-11-06"
           "&order=ASC&offset=0&limit=40")
    st, body = _get(url)
    ms = json.loads(body)
    out = []
    for m in ms[:20]:
        refs = [r for r in (m.get("referees") or []) if (r.get("role") or "").upper() == "REFEREE"]
        name = ((refs[0].get("person") or {}).get("translations", {}).get("name", {}).get("EN")) if refs else None
        out.append(f"{m.get('homeTeam', {}).get('internationalName')}–{m.get('awayTeam', {}).get('internationalName')}: {name or '–'}")
    return f"{st}, {len(ms)} matcher | " + " | ".join(out)


def pl_officials() -> str:
    """Premier Leagues officiella API (pulselive): domare för kommande matcher?"""
    req = urllib.request.Request(
        "https://footballapi.pulselive.com/football/fixtures?comps=1&pageSize=20&statuses=U&altIds=true",
        headers={"User-Agent": UA, "Origin": "https://www.premierleague.com", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode())
    fx = d.get("content", [])
    with_ref = [f for f in fx if any((o.get("role") or "").upper() in ("MAIN", "REFEREE") for o in f.get("matchOfficials", []) or [])]
    return f"{len(fx)} kommande, domare satt i {len(with_ref)}"


def espn_officials() -> str:
    """ESPN: står domaren (gameInfo.officials) i kommande och spelade matcher? Då kan vi bygga
    domarens fouls per match direkt ur ESPN i alla ligor, och veta domaren före avspark."""
    base = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    out = []
    for lg, day in (("uefa.champions", "20261104"), ("uefa.champions", "20261105"), ("eng.1", "20261107"),
                    ("esp.1", "20261108"), ("eng.1", "20261101")):
        try:
            sb = json.loads(_get(f"{base}/{lg}/scoreboard?dates={day}")[1])
        except Exception as e:
            out.append(f"{lg} {day}: FEL {e}")
            continue
        evs = sb.get("events", [])[:4]
        got = []
        for ev in evs:
            try:
                sm = json.loads(_get(f"{base}/{lg}/summary?event={ev['id']}")[1])
            except Exception:
                continue
            offs = (sm.get("gameInfo") or {}).get("officials") or []
            ref = next((o.get("displayName") or o.get("fullName") for o in offs), None)
            got.append(f"{ev.get('shortName')}: {ref or '–'}")
        out.append(f"{lg} {day} ({len(sb.get('events', []))} matcher): " + "; ".join(got))
    return " | ".join(out)


def worldfootball() -> str:
    return plain("https://www.worldfootball.net/schedule/champions-league-2026-2027-gruppe-a/0/")


def main() -> None:
    CHECKS["espn_officials"] = espn_officials
    CHECKS["worldfootball"] = worldfootball
    CHECKS["uefa_referees"] = uefa_referees
    CHECKS["pl_officials"] = pl_officials
    CHECKS["transfermarkt"] = transfermarkt
    CHECKS["football_data"] = football_data
    CHECKS["api_football"] = api_football
    CHECKS["statsbomb_open"] = lambda: plain("https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json")
    CHECKS["opta_player_stats"] = lambda: plain("https://optaplayerstats.statsperform.com/en_GB/soccer")
    CHECKS["kambi_league_props"] = kambi_league_props
    CHECKS["espn_stat_names"] = espn_fouls_fields
    CHECKS["pinnacle_special_leagues"] = pinnacle_special_leagues
    out = []
    for name, fn in CHECKS.items():
        try:
            out.append(f"{name}: {fn()}")
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {getattr(e, 'code', '')} {str(e)[:80]}")
    print("::notice title=probe::" + "%0A".join(x.replace("%", "%25").replace("\n", " ") for x in out))


if __name__ == "__main__":
    main()
