import math

from propsbot.quant import kelly
from propsbot.quant.fb_minutes import Status, expected_minutes, gate, minutes_from_espn, status


def _e(starter, clock=None, out=False, inn=False):
    plays = [{"substitution": True, "clock": {"displayValue": clock}}] if clock else []
    return {"starter": starter, "subbedOut": out, "subbedIn": inn, "plays": plays}


def test_minutes_from_espn():
    assert minutes_from_espn(_e(True)) == 90
    assert minutes_from_espn(_e(True, "67'", out=True)) == 67
    assert minutes_from_espn(_e(True, "90'+2'", out=True)) == 90
    assert minutes_from_espn(_e(False, "67'", inn=True)) == 23
    assert minutes_from_espn(_e(False, "90'+4'", inn=True)) == 1
    assert minutes_from_espn(_e(False)) == 0
    assert minutes_from_espn(_e(True, "??", out=True)) is None


def test_status_and_gate_suppress_stakes():
    assert status(True) is Status.CONFIRMED_XI and status(False) is Status.BENCH
    assert status(None) is Status.UNKNOWN and status(True, "Doubtful") is Status.DOUBTFUL
    bets = []
    for i, st in enumerate((Status.BENCH, Status.DOUBTFUL, Status.UNKNOWN, Status.CONFIRMED_XI)):
        ok, extra, mult, _ = gate(st)
        bets.append({"match_id": "m", "player_id": f"p{i}", "market": "shots", "p": 0.6, "odds": 2.0,
                     "playable": ok, "min_ev": extra, "kelly_mult": mult})
    out = kelly.portfolio(bets)
    assert [d["stake"] for d in out[:3]] == [0.0, 0.0, 0.0]
    assert out[3]["stake"] > 0
    assert gate(Status.UNKNOWN)[1:3] == (0.025, 0.5)        # PRE_LINEUP: +2,5 % EV och halv Kelly (bara logg)


def test_expected_minutes():
    full = [(True, 90.0)] * 20
    assert abs(expected_minutes(full, prior_n=1.0) - 90) < 1
    assert 87 < expected_minutes(full) < 90            # standardpriorn (80 min, 3 matcher) krymper lite
    sixty = [(True, 60.0)] * 5
    assert abs(expected_minutes(sixty, prior_n=0.5) - 60) < 2
    assert expected_minutes([]) == 80.0                       # tom historik -> prior
    assert expected_minutes(full, Status.UNKNOWN) == 0.0
    sub = [(False, 20.0), (True, 90.0)] * 5
    assert abs(expected_minutes(sub, Status.BENCH, prior_n=0.1) - 20) < 1
    nan = [(True, math.nan), (True, 70.0)]
    assert 70 <= expected_minutes(nan, prior_n=0.0) <= 70.001
    # nyare matcher väger tyngre
    recent60 = [(True, 60.0)] * 5 + [(True, 90.0)] * 5
    assert expected_minutes(recent60, half_life_matches=2, prior_n=0) < 70
    for h in (full, sixty, sub, []):
        assert 0 <= expected_minutes(h) <= 95
