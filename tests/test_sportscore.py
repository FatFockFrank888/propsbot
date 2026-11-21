import io
import json
import time
import urllib.error
from urllib.parse import parse_qs, urlparse

from propsbot.sources.sportscore import DAILY_CAP, SportScoreResults, slugs

KO = 1795376700.0   # 2026-11-17 19:45 UTC


def m(home, away, ts, status, text, h=None, a=None):
    return {"home": home, "away": away, "home_score": h, "away_score": a, "status": status, "status_text": text,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(ts)), "competition": "X"}


def test_slugs():
    assert slugs("South Shields FC") == ["south-shields-fc", "south-shields"]
    assert slugs("Eastern District SA") == ["eastern-district-sa", "eastern-district"]
    assert slugs("Académico Viseu") == ["academico-viseu"]


def test_day_then_team_lookup_finished_and_delayed(tmp_path):
    calls = []

    def opener(req, timeout=0):
        calls.append(req.full_url)
        assert req.headers.get("X-api-key") == "k"
        q = parse_qs(urlparse(req.full_url).query)
        if q.get("team") == ["south-shields"]:
            data = [m("South Shields", "Harborough Town", KO, "upcoming", "Delayed")]
        elif "team" in q:
            data = []
        else:   # hela dagen: bara tidiga matcher (taket 200)
            data = [m("Eastern District", "Eastern SC", KO - 12 * 3600, "finished", "Finished", "1", "0")]
        return io.BytesIO(json.dumps({"sport": "football", "count": len(data), "matches": data}).encode())

    ss = SportScoreResults(tmp_path / "s.json", api_key="k", opener=opener)
    now = KO + 3 * 86400
    assert ss.final_score("Eastern District SA", "Eastern Sports Club", KO - 12 * 3600, now) == (1, 0)
    assert len(calls) == 1                                                     # fanns i dagslistan
    assert ss.final_score("South Shields FC", "Harborough Town FC", KO, now) is None
    assert ss.void_reason("South Shields FC", "Harborough Town FC", KO, now) == "uppskjuten"
    n = len(calls)
    ss.save(now)
    ss2 = SportScoreResults(tmp_path / "s.json", api_key="k", opener=opener)
    assert ss2.void_reason("South Shields FC", "Harborough Town FC", KO, now) == "uppskjuten" and len(calls) == n


def test_cap_disabled_and_401(tmp_path):
    assert not SportScoreResults(tmp_path / "a.json", api_key="").enabled
    ss = SportScoreResults(tmp_path / "b.json", api_key="k", opener=lambda *a, **k: 1 / 0)
    ss.st["anrop"][time.strftime("%Y-%m-%d", time.gmtime())] = DAILY_CAP
    assert ss.final_score("A", "B", KO, KO + 86400) is None and "dagstak" in ss.error

    def bad(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "x", {}, None)
    ss = SportScoreResults(tmp_path / "c.json", api_key="k", opener=bad)
    assert ss.final_score("A", "B", KO, KO + 86400) is None and ss.st["stopp"]
