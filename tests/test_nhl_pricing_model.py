import math

import pytest

from nhl.model import cdf, line_probs, pmf
from nhl.pricing import (
    american_to_decimal,
    decimal_to_american,
    devig_two_way,
    expected_value,
    kelly_fraction,
    parse_odds,
)


def test_odds_conversions():
    assert american_to_decimal(150) == pytest.approx(2.5)
    assert american_to_decimal(-200) == pytest.approx(1.5)
    assert decimal_to_american(2.5) == 150
    assert decimal_to_american(1.5) == -200
    assert parse_odds("1,85") == pytest.approx(1.85)
    assert parse_odds("+120") == pytest.approx(2.2)
    assert parse_odds("-110") == pytest.approx(1.909, abs=1e-3)
    with pytest.raises(ValueError):
        parse_odds("0.9")


def test_devig_sums_to_one():
    o, u = devig_two_way(1.87, 1.87)
    assert o == pytest.approx(0.5)
    o, u = devig_two_way(1.60, 2.30)
    assert o + u == pytest.approx(1.0)
    assert o > u


def test_ev_and_kelly():
    assert expected_value(0.5, 0.0, 2.0) == pytest.approx(0.0)
    assert expected_value(0.55, 0.0, 2.0) == pytest.approx(0.10)
    assert kelly_fraction(0.55, 0.0, 2.0) == pytest.approx(0.10)
    assert kelly_fraction(0.40, 0.0, 2.0) == 0.0
    # push refunds stake: same as conditional probability Kelly
    assert kelly_fraction(0.44, 0.2, 2.0) == pytest.approx(kelly_fraction(0.55, 0.0, 2.0))


@pytest.mark.parametrize("alpha", [0.0, 0.05, 0.3])
def test_pmf_normalised_and_mean(alpha):
    mu = 2.7
    probs = [pmf(k, mu, alpha) for k in range(80)]
    assert sum(probs) == pytest.approx(1.0, abs=1e-9)
    assert sum(k * p for k, p in enumerate(probs)) == pytest.approx(mu, rel=1e-6)
    var = sum((k - mu) ** 2 * p for k, p in enumerate(probs))
    assert var == pytest.approx(mu + alpha * mu * mu, rel=1e-4)


def test_poisson_values():
    assert pmf(0, 2.0, 0.0) == pytest.approx(math.exp(-2))
    assert cdf(1, 2.0, 0.0) == pytest.approx(3 * math.exp(-2))


def test_line_probs_half_and_whole():
    half = line_probs(2.5, 2.4, 0.0)
    assert half.push == 0
    assert half.over + half.under == pytest.approx(1.0)
    assert half.under == pytest.approx(cdf(2, 2.4, 0.0))
    whole = line_probs(2.0, 2.4, 0.0)
    assert whole.push == pytest.approx(pmf(2, 2.4, 0.0))
    assert whole.over + whole.under + whole.push == pytest.approx(1.0)


def test_zero_mean():
    p = line_probs(0.5, 0.0, 0.05)
    assert p.over == 0.0 and p.under == 1.0
