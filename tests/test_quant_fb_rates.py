import math

from propsbot.quant.fb_rates import lambda_base, position_group, positional_priors, prior_for, shrunk_rate

PRIOR = 1.0     # skott per 90


def test_low_minutes_go_to_prior_high_to_own_rate():
    low, _ = shrunk_rate([{"min": 90, "n": 3, "age": 0}], PRIOR, 450)
    assert abs(low - PRIOR) / PRIOR < 0.4 and low < 3.0
    assert abs(low - (3 * 90 / 90 * 90 + 450 * PRIOR) / (90 + 450)) < 1e-12
    rows = [{"min": 90, "n": 3, "age": 0} for _ in range(34)]         # 3 060 min, egen takt 3,0
    high, m = shrunk_rate(rows, PRIOR, 450, half_life_matches=1e9)
    assert abs(high - 3.0) / 3.0 < 0.15 and abs(m - 3060) < 1e-6


def test_monotone_convergence():
    prev = None
    for n in range(1, 60):
        r, _ = shrunk_rate([{"min": 90, "n": 2, "age": 0}] * n, PRIOR, 450, half_life_matches=1e9)
        d = abs(r - 2.0)
        if prev is not None:
            assert d < prev
        prev = d


def test_extremes_of_m_prior():
    rows = [{"min": 45, "n": 1, "age": 0}]
    assert abs(shrunk_rate(rows, PRIOR, 0)[0] - 2.0) < 1e-12
    assert abs(shrunk_rate(rows, PRIOR, 1e12)[0] - PRIOR) < 1e-6


def test_decay_prev_season_and_reset():
    _, m = shrunk_rate([{"min": 90, "n": 0, "age": 13}], PRIOR, 0, half_life_matches=13)
    assert abs(m - 45) < 0.01
    _, m_prev = shrunk_rate([{"min": 90, "n": 0, "age": 0, "prev": True}], PRIOR, 0)
    assert abs(m_prev - 27) < 1e-9
    r, m0 = shrunk_rate([{"min": 900, "n": 50, "age": 0, "prev": True}], PRIOR, 450, reset_prev=True)
    assert m0 == 0 and r == PRIOR
    assert shrunk_rate([{"min": 0, "n": 0}], PRIOR, 450)[0] == PRIOR


def test_lambda_and_positions():
    assert lambda_base(1.8, 45) == 0.9
    assert position_group("CD-L") == "CB" and position_group("RB") == "FB" and position_group("AM-R") == "AM_W"
    assert position_group("CF-L") == "ST" and position_group("G") == "GK" and position_group("SUB") is None
    rows = ([{"liga": "eng.1", "grupp": "ST", "min": 900, "shots": 30}] +
            [{"liga": "eng.1", "grupp": "CB", "min": 900, "shots": 5}] +
            [{"liga": "esp.1", "grupp": "ST", "min": 450, "shots": 10}] +
            [{"liga": "eng.1", "grupp": "GK", "min": 900, "shots": 0}])
    pr = positional_priors(rows, "shots")
    assert abs(pr[("eng.1", "ST")] - 3.0) < 1e-12 and abs(pr[("eng.1", "CB")] - 0.5) < 1e-12
    assert ("esp.1", "ST") not in pr                                  # för få minuter
    assert abs(prior_for(pr, "esp.1", "ST") - 40 * 90 / 1350) < 1e-12  # faller tillbaka på alla ligor
    assert math.isnan(prior_for({}, "x", "ST"))
