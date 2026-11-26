from propsbot.quant import fb_context as fc

D = 86400.0


def test_opp_factor_shrink_clip_nan():
    assert fc.opp_factor([], 12.0) == 1.0 and fc.opp_factor([10.0], 0) == 1.0
    assert fc.opp_factor([float("nan"), None], 12.0) == 1.0
    f = fc.opp_factor([18.0] * 5, 12.0, prior_n=5)
    assert abs(f - (90 + 60) / (10 * 12)) < 1e-12                    # 1,25 (halvvägs mot 1,5)
    assert fc.opp_factor([40.0] * 30, 12.0) == 1.25 and fc.opp_factor([0.0] * 30, 12.0) == 0.8
    assert fc.opp_factor([18.0] * 50, 12.0, prior_n=0, clip=(0, 9)) == 1.5


def test_home_rest_team():
    assert fc.home_factor(True, 0.1) == 1.1 and abs(fc.home_factor(False, 0.1) - 1 / 1.1) < 1e-12
    assert fc.home_factor(None, 0.1) == 1.0
    ko = 100 * D
    times = [90 * D, 97 * D, 100 * D, 104 * D]                       # samma match och en framtida
    assert fc.rest_days(times, ko) == 3.0                             # aldrig efter avspark
    assert fc.rest_days([ko + D], ko) is None and fc.rest_days([], ko) is None
    assert fc.rest_factor(3.0, 0.05) == 0.95 and fc.rest_factor(6.0, 0.05) == 1.0 and fc.rest_factor(None, 0.05) == 1.0
    assert fc.team_goal_factor(2.4, 1.2) == 1.7 and fc.team_goal_factor(None, 1.2) == 1.0
    assert abs(fc.team_goal_factor(1.5, 1.2) - 1.25) < 1e-12


def test_apply():
    assert fc.apply(2.0, {"opp": 1.2, "home": 1.1}, {}) == 2.0
    assert abs(fc.apply(2.0, {"opp": 1.21}, {"opp": 0.5}) - 2.2) < 1e-12
    assert fc.apply(2.0, {"opp": 0.0}, {"opp": 1.0}) == 2.0          # ogiltig faktor ignoreras
