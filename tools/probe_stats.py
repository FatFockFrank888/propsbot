"""Engångssond: svarar FotMob (matchDetails, playerData) och Understat utan nyckel, och vad ger de per spelare?"""
import json, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Referer": "https://www.fotmob.com/"}

def get(url, headers=None, raw=False):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read()
            return r.status, (b.decode("utf8", "replace") if raw else json.loads(b))
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {str(e)[:120]}"

def keys(o, n=14):
    return list(o.keys())[:n] if isinstance(o, dict) else type(o).__name__

day = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
st, d = get(f"https://www.fotmob.com/api/data/matches?date={day}")
pri = [m for lg in d.get("leagues", []) if lg.get("primaryId") in (47, 87, 54, 55, 53, 42, 73, 77) for m in lg.get("matches", []) if (m.get("status") or {}).get("finished")]
mid = pri[0]["id"]
time.sleep(1)
st, m = get(f"https://www.fotmob.com/api/data/matchDetails?matchId={mid}")
ps = m["content"]["playerStats"]
print("match", mid, "spelare", len(ps), "shotmap-skott", len((m["content"].get("shotmap") or {}).get("shots", [])))
fld = [v for v in ps.values() if not v.get("isGoalkeeper")]
v = fld[3] if len(fld) > 3 else fld[0]
print("spelare-nycklar", list(v.keys()))
print("namn", v.get("name"), "| stats typ", type(v.get("stats")).__name__)
st_ = v.get("stats")
print(json.dumps(st_, ensure_ascii=False)[:1800])
shots = (m["content"].get("shotmap") or {}).get("shots", [])
print("shotmap[0]", json.dumps(shots[0], ensure_ascii=False)[:500] if shots else None)
time.sleep(1)
pid = v.get("id")
st, p = get(f"https://www.fotmob.com/api/data/playerData?id={pid}")
rm = p.get("recentMatches") or []
print("recentMatches", len(rm), "nycklar", list(rm[0].keys()) if rm else None)
print(json.dumps(rm[0], ensure_ascii=False)[:900] if rm else None)
