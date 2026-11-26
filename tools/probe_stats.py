"""Engångssond: API-Football (nyckel API_FOOTBALL_KEY). Max ~7 anrop. Skriver aldrig nyckeln."""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

KEY = (os.environ.get("API_FOOTBALL_KEY") or "").strip()
if not KEY:
    sys.exit("API_FOOTBALL_KEY saknas")
BASE = "https://v3.football.api-sports.io"

def get(path):
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            h = {k.lower(): v for k, v in r.headers.items()}
            time.sleep(7)   # gratisplanen: 10 anrop/minut
            return r.status, h, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}, e.read()[:300].decode("utf8", "replace")

def rate(h):
    return {k: h.get(k) for k in ("x-ratelimit-requests-limit", "x-ratelimit-requests-remaining", "x-ratelimit-limit", "x-ratelimit-remaining") if h.get(k)}

st, h, d = get("/status")
print("STATUS", st, json.dumps(d.get("response") if isinstance(d, dict) else d, ensure_ascii=False)[:500], rate(h))
yday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
st, h, d = get(f"/fixtures?date={yday}")
print("FIXTURES", yday, st, "fel:", d.get("errors") if isinstance(d, dict) else d, "antal:", d.get("results") if isinstance(d, dict) else None, rate(h))
fid = None
if isinstance(d, dict) and d.get("response"):
    big = (39, 140, 135, 78, 61, 2, 3, 848, 88, 94)
    fin = [f for f in d["response"] if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]
    pick = next((f for f in fin if f["league"]["id"] in big), fin[0] if fin else None)
    if pick:
        fid = pick["fixture"]["id"]
        print(" vald match", fid, pick["league"]["name"], pick["league"]["season"], pick["teams"]["home"]["name"], "-", pick["teams"]["away"]["name"])
if fid:
    st, h, d = get(f"/fixtures/players?fixture={fid}")
    print("PLAYERS", st, "fel:", d.get("errors") if isinstance(d, dict) else d, rate(h))
    if isinstance(d, dict) and d.get("response"):
        pl = d["response"][0]["players"]
        print(" spelare i laget", len(pl))
        best = max(pl, key=lambda p: (p["statistics"][0]["shots"].get("total") or 0))
        print(" exempel", best["player"]["name"], json.dumps(best["statistics"][0], ensure_ascii=False)[:700])
    st, h, d = get(f"/fixtures/lineups?fixture={fid}")
    print("LINEUPS (spelad match)", st, "fel:", d.get("errors") if isinstance(d, dict) else d, "lag:", len(d.get("response", [])) if isinstance(d, dict) else None)
st, h, d = get(f"/fixtures?date={today}")
print("FIXTURES idag", st, "fel:", d.get("errors") if isinstance(d, dict) else d, "antal:", d.get("results") if isinstance(d, dict) else None, rate(h))
if isinstance(d, dict) and d.get("response"):
    ns = [f for f in d["response"] if f["fixture"]["status"]["short"] == "NS"]
    if ns:
        f0 = ns[0]
        st, h, d2 = get(f"/fixtures/lineups?fixture={f0['fixture']['id']}")
        print("LINEUPS (kommande)", f0["league"]["name"], f0["fixture"]["date"], st, "lag:", len(d2.get("response", [])) if isinstance(d2, dict) else d2, rate(h))
