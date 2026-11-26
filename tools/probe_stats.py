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
print("FOTMOB matches", day, st, keys(d) if st == 200 else d)
mid = pid = None
if st == 200:
    ms = [m for lg in d.get("leagues", []) for m in lg.get("matches", []) if (m.get("status") or {}).get("finished")]
    pri = [m for lg in d.get("leagues", []) if lg.get("primaryId") in (47, 87, 54, 55, 53, 42, 73, 77) for m in lg.get("matches", []) if (m.get("status") or {}).get("finished")]
    pick = (pri or ms or [None])[0]
    print(" ligor", len(d.get("leagues", [])), "avslutade", len(ms), "storliga", len(pri))
    mid = pick and pick.get("id")
time.sleep(1)
if mid:
    st, m = get(f"https://www.fotmob.com/api/data/matchDetails?matchId={mid}")
    print("FOTMOB matchDetails", mid, st, keys(m) if st == 200 else m)
    if st == 200:
        c = m.get("content", {})
        print(" content-nycklar", keys(c, 20))
        ps = c.get("playerStats") or {}
        print(" playerStats", len(ps))
        for k, v in list(ps.items())[:1]:
            print(" exempel spelare", v.get("name"), "| stats-grupper", [g.get("key") or g.get("title") for g in v.get("stats", [])][:6])
            for g in v.get("stats", [])[:1]:
                print("  ", json.dumps(g.get("stats"), ensure_ascii=False)[:500])
            pid = v.get("id")
        print(" lineup", keys(c.get("lineup"), 8))
time.sleep(1)
if pid:
    st, p = get(f"https://www.fotmob.com/api/data/playerData?id={pid}")
    print("FOTMOB playerData", pid, st, keys(p, 20) if st == 200 else p)
    if st == 200:
        print(" recentMatches", len(p.get("recentMatches") or []), json.dumps((p.get("recentMatches") or [None])[0], ensure_ascii=False)[:400])
time.sleep(1)
st, u = get("https://understat.com/getLeagueData/EPL/2026", {"X-Requested-With": "XMLHttpRequest", "Referer": "https://understat.com/league/EPL"})
print("UNDERSTAT league", st, keys(u) if st == 200 else u)
if st == 200:
    ms = [x for x in (u.get("dates") or []) if x.get("isResult")]
    print(" spelade", len(ms), "spelare", len(u.get("players") or []))
    if ms:
        time.sleep(1)
        st, mm = get(f"https://understat.com/getMatchData/{ms[-1]['id']}", {"X-Requested-With": "XMLHttpRequest"})
        print("UNDERSTAT match", st, keys(mm) if st == 200 else mm)
        if st == 200:
            pl = (mm.get("rosters") or {}).get("h") or {}
            first = list(pl.values())[:1]
            print(" spelarfält", json.dumps(first, ensure_ascii=False)[:500])
