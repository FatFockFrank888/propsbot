import math
import random

import pytest

from propsbot.market import devig_power
from propsbot.quant import devig


def _pair(rnd, m):
    p = rnd.uniform(0.05, 0.95)
    # sätt marginal m med power-struktur: o_i = 1/q_i, Σ q_i = 1 + m
    return [1 / (p * (1 + m)), 1 / ((1 - p) * (1 + m))]


def test_power_sums_to_one_random():
    rnd = random.Random(1)
    for _ in range(1000):
        m = rnd.uniform(-0.02, 0.15)
        n = rnd.choice([2, 3])
        ps = [rnd.uniform(0.05, 1.0) for _ in range(n)]
        s = sum(ps)
        odds = [1 / (x / s * (1 + m)) for x in ps]
        if min(odds) <= 1.0:
            continue
        p, k = devig.power(odds)
        assert abs(sum(p) - 1) < 1e-9
        assert abs(sum((1 / o) ** k for o in odds) - 1) < 1e-9


def test_k_sign_follows_margin():
    _, k_pos = devig.power([1.90, 1.90])
    _, k_neg = devig.power([2.10, 2.10])
    assert k_pos > 1 > k_neg


def test_equal_odds_equal_probs():
    p, _ = devig.power([1.87, 1.87])
    assert abs(p[0] - 0.5) < 1e-12


def test_power_lowers_longshot_vs_proportional():
    odds = [1.25, 4.20]
    assert devig.power(odds)[0][1] < devig.proportional(odds)[1]


def test_matches_existing_devig_power():
    for odds in ([1.80, 2.05], [1.50, 2.70], [3.4, 3.3, 2.2]):
        assert max(abs(a - b) for a, b in zip(devig.power(odds)[0], devig_power(odds))) < 1e-6


def test_invalid_input_raises():
    with pytest.raises(ValueError):
        devig.power([1.0, 2.0])
    with pytest.raises(ValueError):
        devig.power([2.0])
    with pytest.raises(ValueError):
        devig.power([])


def test_one_sided_and_logit_clip():
    assert abs(devig.one_sided(2.0, 0.07) - 1 / 2.14) < 1e-12
    assert math.isfinite(devig.base_logit(0.0)) and math.isfinite(devig.base_logit(1.0))
    assert abs(devig.sigmoid(devig.base_logit(0.3)) - 0.3) < 1e-12
    assert abs(devig.margin([1.9, 1.9]) - (2 / 1.9 - 1)) < 1e-12
