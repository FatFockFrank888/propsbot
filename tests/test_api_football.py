import io
import json
import time
import urllib.error

from propsbot.sources.api_football import DAILY_CAP, ApiFootballResults

KO = 1794726000.0  # 2026-11-15 07:00 UTC


def _resp(rows):
    return {"errors": [], "results": len(rows), "response": rows}


def _fx(home, away, status, ft=(None, None), ts=KO, fid=1):
    return {"fixture": {"id": fid, "timestamp": ts, "status": {"short": status}},
            "teams": {"home": {"name": home}, "away": {"name": away}},
            "goals": {"home": ft[0], "away": ft[1]}, "score": {"fulltime": {"home": ft[0], "away": ft[1]}}}


class Opener:
    def __init__(self, payload):
        self.payload, self.calls = payload, []

    def __call__(self, req, timeout=0):
        self.calls.append(req.full_url)
        if isinstance(self.payload, Exception):
            raise self.payload
        return io.BytesIO(json.dumps(self.payload).encode())


def test_finished_postponed_and_cache(tmp_path):
    op = Opener(_resp([_fx("Eastern District", "Eastern Sports Club", "FT", (1, 0)),
                       _fx("South Shields", "Harborough Town", "PST", ts=KO + 60, fid=2),
                       _fx("Honda FC", "Verspah Oita", "NS", ts=KO + 120, fid=3)]))
    af = ApiFootballResults(tmp_path / "s.json", api_key="k", opener=op)
    now = KO + 3 * 86400
    assert af.final_score("Eastern District SA", "Eastern Sports Club", KO, now) == (1, 0)
    assert af.final_score("South Shields FC", "Harborough Town FC", KO + 60, now) is None
    assert af.void_reason("South Shields FC", "Harborough Town FC", KO + 60, now) == "uppskjuten"
    assert af.final_score("Honda FC", "Verspah Oita", KO + 120, now) is None          # ingen slutstatus
    assert af.void_reason("Honda FC", "Verspah Oita", KO + 120, now) is None
    n = len(op.calls)
    assert n <= 3 and all("date=" in u for u in op.calls)
    af.save(now)
    af2 = ApiFootballResults(tmp_path / "s.json", api_key="k", opener=op)
    assert af2.final_score("Eastern District SA", "Eastern Sports Club", KO, now) == (1, 0)
    assert len(op.calls) == n                                                       # färdig dag: från läget


def test_quota_error_stops_for_the_day(tmp_path):
    op = Opener({"errors": {"requests": "You have reached the request limit for the day"}, "response": []})
    af = ApiFootballResults(tmp_path / "s.json", api_key="k", opener=op)
    assert af.final_score("A", "B", KO, KO + 86400) is None and "request limit" in af.error
    calls = len(op.calls)
    af.final_score("C", "D", KO + 86400 * 5, KO + 86400 * 6)                        # ny dag i läget, samma UTC-dygn
    assert len(op.calls) == calls                                                    # inga fler anrop i dag


def test_disabled_without_key_and_daily_cap(tmp_path):
    af = ApiFootballResults(tmp_path / "s.json", api_key="")
    assert not af.enabled and af.final_score("A", "B", KO) is None
    op = Opener(_resp([]))
    af = ApiFootballResults(tmp_path / "s2.json", api_key="k", opener=op)
    af.st["anrop"][time.strftime("%Y-%m-%d", time.gmtime())] = DAILY_CAP
    assert af.final_score("A", "B", KO, KO + 86400) is None and op.calls == [] and "dagstak" in af.error


def test_http_401_pauses(tmp_path):
    op = Opener(urllib.error.HTTPError("u", 401, "x", {}, None))
    af = ApiFootballResults(tmp_path / "s.json", api_key="k", opener=op)
    assert af.final_score("A", "B", KO, KO + 86400) is None and "fel nyckel" in af.error
    assert af.st["stopp"] == time.strftime("%Y-%m-%d", time.gmtime())
