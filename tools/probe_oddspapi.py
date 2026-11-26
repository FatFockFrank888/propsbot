"""Engångssond 7: lagnamn (fixtures/participants). Max 2 anrop."""
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
for path, params in (("fixtures", {"tournamentId": 17}), ("participants", {"sportId": 10})):
    st, d = get(path, **params)
    print(path, st, type(d).__name__, len(d) if hasattr(d, "__len__") else "")
    if isinstance(d, list) and d:
        print(" första:", json.dumps(d[0], ensure_ascii=False)[:700])
    elif isinstance(d, dict):
        print(" nycklar/första:", json.dumps({k: (str(v)[:80]) for k, v in list(d.items())[:6]}, ensure_ascii=False)[:700])
    else:
        print(str(d)[:400])
    time.sleep(1.5)
