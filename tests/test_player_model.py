"""Spelarmodellen mot ESPN-format (byggt efter känd struktur, inte inspelat)."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone

from propsbot.player_model import PlayerModel, model_probs, nb_over, poisson_over, prob_over
from propsbot.sources import http as httpmod
from propsbot.sources.http import JsonClient

NOW = time.time()
UP = NOW + 6 * 3600


class _R(io.BytesIO):
    def __init__(self, d):
        super().__init__(json.dumps(d).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def fake(req, timeout=20, **kw):
    path = urllib.parse.urlparse(req.full_url).path
    if path.endswith("/scoreboard"):
        if "/eng.1/" not in path:
            return _R({"events": []})
        return _R({"events": [{"id": "900", "date": iso(UP), "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"id": "1", "displayName": "Arsenal"}},
            {"homeAway": "away", "team": {"id": "2", "displayName": "Chelsea"}}]}]}]})
    if path.endswith("/schedule"):
        tid = path.split("/")[-2]
        return _R({"team": {"displayName": "T" + tid}, "events": [
            {"id": f"{tid}0{i}", "date": iso(NOW - (i + 1) * 7 * 86400),
             "competitions": [{"status": {"type": {"completed": True}}}]} for i in range(6)]})
    if path.endswith("/summary"):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)
        tid = q["event"][0][0]
        return _R({"header": {"competitions": [{"competitors": [{"id": tid, "score": "2"}]}]},
                   "rosters": [{"team": {"id": tid}, "roster": [
                       {"athlete": {"displayName": "Bukayo Saka" if tid == "1" else "Cole Palmer"},
                        "starter": True, "stats": [{"name": "totalShots", "value": 4},
                                                   {"name": "shotsOnTarget", "value": 2},
                                                   {"name": "totalGoals", "value": 1},
                                                   {"name": "goalAssists", "value": 0}]},
                       {"athlete": {"displayName": "Bänk Spelare"}, "starter": False, "subbedIn": False,
                        "stats": []}]}]})
    raise AssertionError(req.full_url)


def test_player_model(tmp_path, monkeypatch):
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)
    pm = PlayerModel(JsonClient(tmp_path / "c", min_interval_s=0), tmp_path / "espn")
    hit = pm.find_upcoming("Arsenal", "Chelsea", UP)
    assert hit[:4] == ("eng.1", "900", "1", "2")
    tm = pm.team("eng.1", "1", UP)
    saka = tm.players["bukayo saka"]
    assert saka.starts == 6 and 2.5 < saka.rate["shots"] < 4.0     # krympt mot lagets snitt
    assert "bank spelare" not in tm.players                        # spelade inte
    assert abs(tm.avg_goals - 2.0) < 1e-9
    m = model_probs(tm, 2.4)                                        # 20 % fler mål än snittet
    mu, _ = m[("bukayo saka", "goal")]
    assert mu > saka.rate["goal"]
    assert pm.store.fetched == 6
    pm2 = PlayerModel(JsonClient(tmp_path / "c2", min_interval_s=0), tmp_path / "espn")
    pm2.team("eng.1", "1", UP)
    assert pm2.store.fetched == 0                                   # permanent cache


def test_distributions():
    assert abs(poisson_over(1.0, 0.5) - (1 - 2.718281828 ** -1)) < 1e-6
    assert nb_over(2.0, 0.5, 1e6) - poisson_over(2.0, 0.5) < 1e-3   # NB -> Poisson
    assert nb_over(2.0, 4.5, 3.0) > poisson_over(2.0, 4.5)          # tjockare svans
    assert 0 < prob_over("shots", 2.5, 1.5) < 1
