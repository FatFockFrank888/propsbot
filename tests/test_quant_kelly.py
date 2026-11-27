import itertools

from propsbot.decision import kelly_stake
from propsbot.quant import kelly


def _b(**kw):
    b = {"match_id": "m1", "player_id": "p1", "market": "shots", "p": 0.55, "odds": 2.0}
    b.update(kw)
    return b


def test_zero_for_non_positive_ev_and_bad_input():
    assert kelly.stake(0.5, 2.0) == 0.0
    assert kelly.stake(0.4, 2.0) == 0.0
    assert kelly.stake(0.0, 3.0) == 0.0
    assert kelly.stake(0.6, 1.0) == 0.0
    assert kelly.stake(None, 2.0) == 0.0


def test_cap_and_value():
    assert abs(kelly.stake(0.55, 2.0, cap=1.0) - 0.25 * 0.10) < 1e-12
    assert kelly.stake(0.55, 2.0) == 0.02
    for p, o in itertools.product([i / 20 for i in range(1, 20)], [1.1, 1.5, 2, 3, 6, 15]):
        assert 0.0 <= kelly.stake(p, o) <= 0.02


def test_same_as_decision_kelly():
    for p, o in itertools.product([0.3, 0.45, 0.6, 0.8], [1.4, 2.0, 3.5, 6.0]):
        assert abs(kelly.stake(p, o) - kelly_stake(p, o, 0.25, 0.02)) < 1e-12


def test_one_leg_per_player_family():
    out = kelly.portfolio([_b(market="shots", p=0.56), _b(market="shots_on_target", p=0.60)])
    st = {d["market"]: d for d in out}
    assert st["shots"]["stake"] == 0 and st["shots"]["status"] == "SAMMA_SPELARE"
    assert st["shots_on_target"]["stake"] > 0


def test_match_correlation_and_cap():
    legs = [_b(player_id=f"p{i}", p=0.6 + i * 0.01) for i in range(3)]
    out = kelly.portfolio(legs, per_match_cap=1.0)
    s = sorted(out, key=lambda d: -d["ev"])
    assert s[0]["stake"] == 0.02 and abs(s[1]["stake"] - 0.02 * 0.65) < 1e-12
    out2 = kelly.portfolio(legs)
    assert sum(d["stake"] for d in out2) <= 0.035 + 1e-12
    assert all(d["stake"] <= 0.02 for d in out2)


def test_gates():
    out = kelly.portfolio([_b(p=0.70, p_market=0.55), _b(player_id="x", p=0.52, min_ev=0.06),
                           _b(player_id="y", p=0.6, playable=False)])
    assert [d["status"] for d in out] == ["MANUAL_REVIEW", "UNDER_EV", "EJ_SPELBAR"]
    assert all(d["stake"] == 0 for d in out)


def test_units_and_half_kelly():
    assert kelly.units(0.02) == 2 and kelly.units(0.004) == 0 and kelly.units(0.012) == 1 and kelly.units(0.05) == 2
    full = kelly.portfolio([_b(p=0.53)])[0]["stake"]
    half = kelly.portfolio([_b(p=0.53, kelly_mult=0.5)])[0]["stake"]
    assert abs(half - full / 2) < 1e-12
