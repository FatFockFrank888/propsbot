"""Engångssond 6: den aktiva matchen i detalj (marknads-id, linje, pris, färskhet). Max 2 anrop."""
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
cat = {str(m["marketId"]): (str(m.get("marketType")), m.get("handicap"), str(m.get("period")), m.get("marketName")) for m in mk}
time.sleep(1.5)
st, o = get("odds-by-tournaments", tournamentIds="17,8,23,35,34", bookmakers="bet365")
act = [f for f in o if f["bookmakerOdds"]["bet365"].get("bookmakerIsActive")]
print("aktiva matcher:", [(f["fixtureId"], f["tournamentId"], f["startTime"], f["bookmakerOdds"]["bet365"]["bookmakerFixtureId"]) for f in act])
print("alla bookmakerFixtureId (start):", sorted((f["startTime"][:16], f["bookmakerOdds"]["bet365"]["bookmakerFixtureId"], f["tournamentId"]) for f in o)[:14])
for f in act[:1]:
    b = f["bookmakerOdds"]["bet365"]
    rows = defaultdict(list)
    for mid, m in b["markets"].items():
        c = cat.get(mid, ("?", None, "?", "?"))
        for oid, out in m["outcomes"].items():
            for pid, p in (out.get("players") or {}).items():
                if p.get("active"):
                    rows[(mid, c[0], c[1], c[2], c[3])].append((p["playerName"], p["price"], p.get("changedAt"), p.get("mainLine")))
    print("aktiva spelarmarknader i matchen:", len(rows))
    for k, v in sorted(rows.items(), key=lambda kv: (kv[0][1], str(kv[0][2])))[:60]:
        print("MKT", k[0], k[1], k[2], k[3], "|", str(k[4])[:50], "| n=%d" % len(v), v[:2])
