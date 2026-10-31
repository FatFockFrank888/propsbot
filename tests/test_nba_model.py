"""NBA-modellen mot ESPN-format (byggt efter känd struktur, inte inspelat)."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone

from propsbot.nba_model import NbaModel
from propsbot.sources import http as httpmod
from propsbot.sources.http import JsonClient

NOW = time.time()
UP = NOW + 5 * 3600
LABELS = ["MIN", "FG", "3PT", "FT", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "+/-", "PTS"]


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


class _R(io.BytesIO):
    def __init__(self, d):
        super().__init__(json.dumps(d).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def athlete(name, mins, pts, reb, ast, starter=True):
    return {"athlete": {"displayName": name}, "starter": starter,
            "stats": [str(mins), "8-16", "2-5", "4-4", "1", "5", str(reb), str(ast), "1", "0", "2", "2", "+5", str(pts)]}


def fake(req, timeout=20, **kw):
    u = urllib.parse.urlparse(req.full_url)
    path, q = u.path, urllib.parse.parse_qs(u.query)
    if path.endswith("/scoreboard"):
        return _R({"events": [{"id": "1", "date": iso(UP), "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"id": "10", "displayName": "Boston Celtics"}},
            {"homeAway": "away", "team": {"id": "20", "displayName": "New York Knicks"}}]}]}]})
    if path.endswith("/schedule"):
        tid = path.split("/")[-2]
        return _R({"team": {"displayName": tid}, "events": [
            {"id": f"{tid}{i}", "date": iso(NOW - (i + 1) * 2 * 86400),
             "competitions": [{"status": {"type": {"completed": True}}}]} for i in range(6)]})
    if path.endswith("/summary"):
        eid = q["event"][0]
        tid = eid[:2]
        roster = [athlete("Star Player" if tid == "10" else "Other Star", 36, 30, 8, 6),
                  athlete("Hurt Guy" if tid == "10" else "Bench Guy", 30, 15, 4, 3),
                  athlete("Role Player", 20, 6, 3, 1, starter=False)]
        return _R({"header": {"competitions": [{"competitors": [{"id": tid, "score": "112"},
                                                                {"id": "99", "score": "108"}]}]},
                   "boxscore": {"players": [{"team": {"id": tid}, "statistics": [
                       {"labels": LABELS, "athletes": roster}]}]}})
    if path.endswith("/injuries"):
        return _R({"injuries": [{"injuries": [{"athlete": {"displayName": "Hurt Guy"}, "status": "Out"}]}]})
    raise AssertionError(req.full_url)


def test_nba_model(tmp_path, monkeypatch):
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)
    nm = NbaModel(JsonClient(tmp_path / "c", min_interval_s=0), tmp_path / "box")
    th, ta = nm.find_event("Boston Celtics", "New York Knicks", UP)
    assert (th, ta) == ("10", "20")
    t = nm.team("10", UP)
    star = t.players["star player"]
    assert abs(star.minutes - 36) < 1e-6 and 0.75 < star.per_min["points"] < 0.85
    assert abs(t.allowed - 108) < 1e-6
    exp = nm.expected(t, nm.team("20", UP), UP, 108.0)
    assert "hurt guy" not in exp                         # skadad -> ingen prognos
    assert exp["star player"]["_min"] > 36               # får del av skadades minuter
    e = exp["star player"]
    assert abs(e["pra"] - (e["points"] + e["rebounds"] + e["assists"])) < 1e-9
    assert nm.fetched == 12                              # 6 matcher per lag
