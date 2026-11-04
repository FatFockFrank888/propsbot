"""Odds conversion, de-vigging, expected value and Kelly staking. Decimal odds throughout."""

from __future__ import annotations

import statistics
from typing import Iterable


def parse_odds(value: str | float | int) -> float:
    """Parse a price as decimal odds. Accepts decimal (1.85) or American (-120 / +150)."""
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            raise ValueError("empty odds value")
        num = float(text)
        is_american = text.startswith(("+", "-")) or abs(num) >= 100
    else:
        num = float(value)
        is_american = abs(num) >= 100
    if is_american:
        return american_to_decimal(num)
    if num <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {value!r}")
    return num


def american_to_decimal(price: float) -> float:
    if -100 < price < 100:
        raise ValueError(f"invalid American odds: {price}")
    return 1.0 + price / 100.0 if price > 0 else 1.0 + 100.0 / abs(price)


def decimal_to_american(dec: float) -> int:
    if dec <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {dec}")
    return round((dec - 1.0) * 100) if dec >= 2.0 else round(-100.0 / (dec - 1.0))


def implied_prob(dec: float) -> float:
    if dec <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {dec}")
    return 1.0 / dec


def fair_odds(prob: float) -> float | None:
    """Decimal odds with no margin for a probability, or None if degenerate."""
    if prob <= 0.0 or prob >= 1.0:
        return None
    return 1.0 / prob


def devig_two_way(over_dec: float, under_dec: float) -> tuple[float, float]:
    """Multiplicative (proportional) margin removal for a two-way market."""
    a, b = implied_prob(over_dec), implied_prob(under_dec)
    total = a + b
    return a / total, b / total


def overround(over_dec: float, under_dec: float) -> float:
    return implied_prob(over_dec) + implied_prob(under_dec) - 1.0


def consensus(values: Iterable[float]) -> float | None:
    vals = list(values)
    return statistics.median(vals) if vals else None


def expected_value(p_win: float, p_push: float, dec: float) -> float:
    """Expected profit per unit staked; pushes refund the stake."""
    p_lose = max(0.0, 1.0 - p_win - p_push)
    return p_win * (dec - 1.0) - p_lose


def kelly_fraction(p_win: float, p_push: float, dec: float) -> float:
    """Full-Kelly bankroll fraction. With pushes it equals Kelly on the no-push conditional probability."""
    decisive = p_win + max(0.0, 1.0 - p_win - p_push)
    if decisive <= 0.0:
        return 0.0
    p = p_win / decisive
    b = dec - 1.0
    if b <= 0.0:
        return 0.0
    return max(0.0, (b * p - (1.0 - p)) / b)
