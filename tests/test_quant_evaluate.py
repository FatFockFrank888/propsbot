import math

from propsbot.quant import evaluate
from propsbot.skarp_clv import clv_pp


def test_metrics_by_hand():
    p, y = [0.8, 0.3, 0.5, 0.9], [1, 0, 1, 0]
    ll = -(math.log(0.8) + math.log(0.7) + math.log(0.5) + math.log(0.1)) / 4
    assert abs(evaluate.logloss(p, y) - ll) < 1e-12
    assert abs(evaluate.brier(p, y) - (0.04 + 0.09 + 0.25 + 0.81) / 4) < 1e-12
    assert evaluate.ece([0.5, 0.5], [1, 0]) == 0.0


def test_clv_matches_skarp_clv():
    b = {"skarp_stang_p": 0.55, "odds": 2.0}
    assert abs(evaluate.clv_pp(0.55, 2.0) - clv_pp(b)) < 1e-12
    assert evaluate.clv_pp(None, 2.0) is None


def test_boot_ci_and_promote():
    lo, hi = evaluate.boot_ci([1.0] * 10 + [3.0] * 10, list(range(20)))
    assert lo < 2.0 < hi
    assert not evaluate.promote(149, (0.5, 2.0), [True, True, True])
    assert evaluate.promote(150, (0.5, 2.0), [True, True, False])
    assert not evaluate.promote(500, (-0.1, 2.0), [True, True, True])
    assert not evaluate.promote(500, (0.1, 2.0), [True, False, False])
