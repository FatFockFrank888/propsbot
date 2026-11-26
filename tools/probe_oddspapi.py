"""Engångssond 4: aktiva fulltidsmarknader för skott/skott på mål, under-utfall, färskhet. Max 2 anrop."""
import json, os, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

KEY = os.environ.get("ODDS_PAPI_KEY", "")
BASE = "https://api.oddspapi.io/v4"


def get(path, **params):
    params["apiKey"] = KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "probe"}), timeout=90) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf8", "replace")


if not KEY:
    sys.exit("ODDS_PAPI_KEY saknas")
st, mk = get("markets")
cat = {}
for m in mk:
    t = str(m.get("marketType", ""))
    if t in ("playertotals-shots", "playertotals-shotsongoal", "playertotals-fouls", "playertotals-tackles", "playertotals-assists", "playertotals-cards") or t.startswith("playertotals-"):
        cat[str(m["marketId"])] = (t, m.get("handicap"), m.get("period"), m.get("marketName"))
soccer = {k: v for k, v in cat.items() if v[2] in ("fulltime", "result") or "fulltime" in str(v[2])}
print("playertotals-typer:", Counter(v[0] for v in cat.values()).most_common(40))
print("perioder för shots:", Counter(v[2] for v in cat.values() if v[0] == "playertotals-shots"))
print("shots fulltime-id:", sorted((k, v[1], v[2]) for k, v in cat.items() if v[0] == "playertotals-shots" and "fulltime" in str(v[2]))[:24])
print("shotsongoal fulltime-id:", sorted((k, v[1], v[2]) for k, v in cat.items() if v[0] == "playertotals-shotsongoal" and "fulltime" in str(v[2]))[:24])
time.sleep(1.5)
st, o = get("odds-by-tournaments", tournamentIds="17,8,23,35,34", bookmakers="bet365")
print("odds", st, len(o) if isinstance(o, list) else str(o)[:300])
if isinstance(o, list):
    print("fixture-nycklar:", sorted(o[0].keys()))
    stat = defaultdict(Counter)
    samples = []
    for f in o:
        b = f["bookmakerOdds"]["bet365"]
        for mid, m in b["markets"].items():
            c = cat.get(mid)
            if not c or c[0] not in ("playertotals-shots", "playertotals-shotsongoal") or "fulltime" not in str(c[2]):
                continue
            stat[c[0]]["marknader"] += 1
            stat[c[0]]["marketActive"] += bool(m.get("marketActive"))
            stat[c[0]]["antal_outcomes_%d" % len(m["outcomes"])] += 1
            for oid, out in m["outcomes"].items():
                for pid, p in (out.get("players") or {}).items():
                    stat[c[0]]["spelare"] += 1
                    stat[c[0]]["aktiv"] += bool(p.get("active"))
                    stat[c[0]]["mainLine"] += bool(p.get("mainLine"))
                    if p.get("active") and len(samples) < 8:
                        samples.append((f["fixtureId"], mid, c[0], c[1], oid, p["playerName"], p["price"], p.get("changedAt"), p.get("limit")))
    for k, v in stat.items():
        print("STAT", k, dict(v))
    for s in samples:
        print("SAMPLE", s)
    print("fixture-0 första 600 tecken:", json.dumps({k: v for k, v in o[0].items() if k != "bookmakerOdds"})[:600])
    print("fixturePath/bookmakerFixtureId:", {k: v for k, v in o[0]["bookmakerOdds"]["bet365"].items() if k != "markets"})
