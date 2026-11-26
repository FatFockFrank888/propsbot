"""Engångssond: finns bet365 + fotbollsprops i OddsPapi? Skriver bara sammanfattningar (aldrig nyckeln). Max 3 anrop."""
import json, os, sys, time, urllib.parse, urllib.request

KEY = os.environ.get("ODDS_PAPI_KEY", "")
BASE = "https://api.oddspapi.io/v4"


def get(path, **params):
    params["apiKey"] = KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "probe"}), timeout=60) as r:
            hdr = {k: v for k, v in r.headers.items() if "limit" in k.lower() or "remain" in k.lower() or "request" in k.lower()}
            return r.status, hdr, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}, e.read()[:400].decode("utf8", "replace")


def shape(o, depth=0, maxd=5):
    if depth >= maxd:
        return "…"
    if isinstance(o, dict):
        return {k: shape(v, depth + 1, maxd) for k, v in list(o.items())[:6]}
    if isinstance(o, list):
        return [shape(o[0], depth + 1, maxd)] if o else []
    return o if not isinstance(o, str) else o[:30]


def find_players(o, path=""):
    out = []
    if isinstance(o, dict):
        if o.get("playerName"):
            out.append((path, o["playerName"]))
        for k, v in o.items():
            out += find_players(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += find_players(v, f"{path}[]")
    return out


if not KEY:
    sys.exit("ODDS_PAPI_KEY saknas")
st, hdr, t = get("tournaments", sportId=10)
print("tournaments", st, hdr)
if isinstance(t, list):
    want = ("premier league", "la liga", "serie a", "bundesliga", "ligue 1", "champions league", "europa league", "conference league", "eredivisie")
    for x in t:
        n = str(x.get("tournamentName") or x.get("name") or "").lower()
        if any(w == n or n.endswith(w) and "women" not in n for w in want) and x.get("categorySlug", x.get("categoryName", "")) is not None:
            print({k: x[k] for k in x if k in ("tournamentId", "tournamentName", "categoryName", "futureFixtures", "upcomingFixtures")})
    print("antal turneringar", len(t))
else:
    print(str(t)[:400])
time.sleep(1.5)
st, hdr, o = get("odds-by-tournaments", tournamentIds=17, bookmakers="bet365")
print("odds-by-tournaments EPL bet365", st, hdr)
if isinstance(o, (list, dict)):
    fx = o if isinstance(o, list) else o.get("data", o)
    print("typ", type(fx).__name__, "antal", len(fx))
    first = fx[0] if isinstance(fx, list) and fx else fx
    print("struktur:", json.dumps(shape(first), ensure_ascii=False)[:2500])
    pl = find_players(fx)
    print("spelarprop-rader:", len(pl), pl[:8])
    mk = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "markets" and isinstance(v, dict):
                    mk.update(v.keys())
                walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(fx)
    print("marknads-id antal", len(mk), sorted(mk)[:60])
else:
    print(str(o)[:400])
