"""Engångssond 2: marknadsnamn för skott/skott på mål + utfallsstruktur + flera ligor i ett anrop. Max 2 anrop."""
import json, os, sys, time, urllib.parse, urllib.request

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
print("markets", st, type(mk).__name__, len(mk) if hasattr(mk, "__len__") else "")
names = {}
if isinstance(mk, list):
    print("markets-struktur:", json.dumps(mk[0], ensure_ascii=False)[:500])
    for m in mk:
        mid = str(m.get("marketId"))
        nm = f"{m.get('marketName') or m.get('name')} | {m.get('marketType', '')} | {m.get('handicap', '')} | {m.get('period', '')}"
        names[mid] = nm
        low = nm.lower()
        if ("shot" in low or "tackle" in low or "foul" in low or "assist" in low or "offside" in low) and "head" not in low and "player" in low and m.get("playerProp") and "." in str(m.get("handicap", "")) and str(m.get("handicap")) in ("0.5", "1.5", "2.5"):
            print("MARKNAD", mid, nm)
    pp = [m for m in mk if m.get("playerProp")]
    print("playerProp-marknader totalt:", len(pp))
    print("fotbollsliknande playerProp-namn:", sorted({str(m.get("marketName"))[:50] for m in pp if any(w in str(m.get("marketName")).lower() for w in ("shot","tackle","foul","assist","card","goal"))})[:40])
time.sleep(1.5)
st, o = get("odds-by-tournaments", tournamentIds="17,8,23,35,34", bookmakers="bet365")
print("multi-liga bet365", st, type(o).__name__)
if isinstance(o, list):
    from collections import Counter
    print("matcher per turnering", dict(Counter(f.get("tournamentId") for f in o)))
    f0 = next((f for f in o if f.get("tournamentId") == 17), o[0])
    b = f0["bookmakerOdds"]["bet365"]
    print("bookmakerOdds-nycklar", list(b.keys()))
    shots = [(mid, n) for mid, n in names.items() if "shot" in n.lower() and "head" not in n.lower()]
    shown = 0
    for mid, m in b["markets"].items():
        if mid in dict(shots) and shown < 2:
            print("EXEMPEL", mid, names.get(mid), json.dumps(m, ensure_ascii=False)[:1400]); shown += 1
    if not shown:
        for mid in list(b["markets"])[:1]:
            print("EXEMPEL(ingen skottmarknad hittad) ", mid, json.dumps(b["markets"][mid], ensure_ascii=False)[:1400])
    # vilka marknader har spelare i sample
    pm = []
    for mid, m in b["markets"].items():
        if "players" in json.dumps(m)[:3000]:
            pm.append(f"{mid}={names.get(mid, '?')[:40]}")
    print("marknader med spelare i EPL-match 1:", len(pm), pm[:40])
else:
    print(str(o)[:400])
