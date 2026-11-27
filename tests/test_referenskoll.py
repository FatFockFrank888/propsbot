import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("referenskoll", Path(__file__).parent.parent / "tools" / "referenskoll.py")
rk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rk)

DAY = 1795790000.0  # 2026-11-27 UTC


def bet(pin=None, dk=None, sport="nba", ts=DAY):
    return {"sport": sport, "bokford": str(ts), "pin_stang_p": pin, "dk_stang_p": dk}


def test_coverage_counts_pin_dk_and_either():
    d = rk.coverage_by_day([bet(0.5, None), bet(None, 0.4), bet(None, None), bet(0.5, 0.5), bet(0.5, sport="fotboll")])
    day = d["2026-11-27"]
    assert day == {"n": 4, "pin": 2, "dk": 2, "minst": 3}


def test_old_bets_before_logging_start_are_ignored():
    assert rk.coverage_by_day([bet(ts=1794000000.0)]) == {}


def test_source_status_flags_missing_and_zero_rows():
    ok = rk.source_status("DK/FD: 0 nya, krediter kvar 120\nDraftKings via ESPN: 11 matcher, 728 spelarodds (referens)")
    assert all(x[2] for x in ok)
    bad = rk.source_status("DK/FD: krediter kvar 0\nDraftKings via ESPN: 0 matcher, 0 spelarodds")
    assert not any(x[2] for x in bad)
    assert not rk.source_status("inget")[0][2]
