"""Engångssond 5: bet365-match 204015112 + aktiva spelarpriser per marknadstyp/period. Max 2 anrop."""
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
TARGET = "204015112"
st, mk = get("markets")
cat = {str(m["marketId"]): (str(m.get("marketType")), m.get("handicap"), str(m.get("period")), m.get("marketName")) for m in mk}
time.sleep(1.5)
st, o = get("odds-by-tournaments", tournamentIds="17,8,23,35,34", bookmakers="bet365")
print("odds", st, len(o) if isinstance(o, list) else str(o)[:300])
if isinstance(o, list):
    tot = defaultdict(Counter)
    found = None
    for f in o:
        b = f["bookmakerOdds"]["bet365"]
        if b.get("bookmakerFixtureId") == TARGET:
            found = f
        for mid, m in b["markets"].items():
            c = cat.get(mid, ("?", None, "?", "?"))
            if not c[0].startswith("playertotals-") and "scorer" not in c[0]:
                continue
            for out in m["outcomes"].values():
                for p in (out.get("players") or {}).values():
                    tot[(c[0], c[2])]["rader"] += 1
                    tot[(c[0], c[2])]["aktiva"] += bool(p.get("active"))
    print("MÅLMATCH hittad:", bool(found))
    if found:
        b = found["bookmakerOdds"]["bet365"]
        print("match:", {k: v for k, v in found.items() if k != "bookmakerOdds"}, {k: v for k, v in b.items() if k != "markets"})
        per = defaultdict(Counter)
        ex = {}
        for mid, m in b["markets"].items():
            c = cat.get(mid, ("?", None, "?", "?"))
            for oid, out in m["outcomes"].items():
                pl = out.get("players") or {}
                if not pl:
                    continue
                for pid, p in pl.items():
                    per[(c[0], c[2])]["rader"] += 1
                    per[(c[0], c[2])]["aktiva"] += bool(p.get("active"))
                    if p.get("active") and (c[0], c[2]) not in ex:
                        ex[(c[0], c[2])] = (mid, c[1], oid, p["playerName"], p["price"], p.get("changedAt"), p.get("mainLine"))
        for k, v in sorted(per.items()):
            print("MATCH", k, dict(v))
        for k, v in ex.items():
            print("EX", k, v)
        # under-utfall?
        mids = [mid for mid, m in b["markets"].items() if cat.get(mid, ("",))[0] in ("playertotals-shots", "playertotals-shotsongoal")]
        for mid in mids[:3]:
            print("outcomes-nycklar", mid, cat[mid][:3], list(b["markets"][mid]["outcomes"].keys()))
    print("ALLA matcher, aktiva spelarrader per typ/period (topp):", [(k, dict(v)) for k, v in sorted(tot.items(), key=lambda kv: -kv[1]["aktiva"])[:15]])
    print("matcher med bookmakerIsActive:", sum(1 for f in o if f["bookmakerOdds"]["bet365"].get("bookmakerIsActive")), "av", len(o))
