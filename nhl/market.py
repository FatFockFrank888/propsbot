"""Market maths: quotes, de-vigging, line interpolation and reference consensus."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Iterable, Sequence

from .model import line_probs

# Odds API bookmaker key -> independence group. Books sharing a pricing platform share a group.
US_GROUPS = {
    "draftkings": "draftkings",
    "fanduel": "fanduel",
    "betmgm": "betmgm_us",
    "williamhill_us": "caesars",
    "williamhill": "caesars",  # normalised form of williamhill_us
    "fanatics": "fanatics",
    "espnbet": "espnbet",
    "hardrockbet": "hardrock",
    "betonlineag": "betonline",
    "betrivers": "kambi",  # Kambi-priced: never an independent reference for Kambi bets
    "ballybet": "kambi",
    "unibet_us": "kambi",
}
SHARP_GROUPS = {"pinnacle"}


@dataclass(frozen=True)
class Quote:
    source: str  # 'unibet', 'atg', 'us:draftkings', 'pinnacle', ...
    group: str  # independence group
    player: str
    line: float
    over: float | None  # decimal odds
    under: float | None
    ts: float  # unix time the price was observed
    playable: bool = False

    def price(self, side: str) -> float | None:
        return self.over if side == "over" else self.under


@dataclass(frozen=True)
class GroupFair:
    group: str
    p: float  # fair probability of the side (no-push conditional)
    two_sided: bool
    sharp: bool
    interpolated: bool
    from_line: float


# ------------------------------------------------------------------ basics
def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def expit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def blend_logit(probs: Sequence[float], weights: Sequence[float]) -> float:
    total = sum(weights)
    if not probs or total <= 0:
        raise ValueError("nothing to blend")
    return expit(sum(w * logit(p) for p, w in zip(probs, weights)) / total)


def power_devig(over: float, under: float) -> tuple[float, float]:
    """Power-method margin removal: find k with (1/o)^k + (1/u)^k = 1.

    Handles the favourite-longshot bias better than proportional scaling.
    """
    a, b = 1.0 / over, 1.0 / under
    lo, hi = 0.05, 20.0
    for _ in range(100):
        k = (lo + hi) / 2
        total = a ** k + b ** k
        if total > 1.0:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    pa, pb = a ** k, b ** k
    s = pa + pb
    return pa / s, pb / s


def one_sided_fair(odds: float, margin: float) -> float:
    return min(0.999, 1.0 / (odds * (1.0 + margin)))


# --------------------------------------------------------- line interpolation
def mu_for_over_prob(line: float, p_over: float, alpha: float) -> float:
    """Mean of the negative binomial whose P(X > line) equals p_over."""
    lo, hi = 1e-4, 30.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if line_probs(line, mid, alpha).over < p_over:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def shift_over_prob(p_over: float, from_line: float, to_line: float, alpha: float) -> float:
    """Move a fair over-probability from one line to a neighbouring line via a NB fit."""
    if abs(from_line - to_line) < 1e-9:
        return p_over
    mu = mu_for_over_prob(from_line, p_over, alpha)
    probs = line_probs(to_line, mu, alpha)
    decisive = probs.over + probs.under
    return probs.over / decisive if decisive > 0 else probs.over


# --------------------------------------------------------- reference consensus
def _fair_over(q: Quote) -> tuple[float, bool] | None:
    """(fair P(over), two_sided) from a single quote, or None."""
    if q.over and q.under:
        return power_devig(q.over, q.under)[0], True
    return None


def group_fairs(
    quotes: Iterable[Quote], line: float, side: str, alpha: float, one_sided_margin: float, max_interp: float
) -> list[GroupFair]:
    """One fair probability per independent reference group for (line, side)."""
    by_group: dict[str, list[Quote]] = {}
    for q in quotes:
        if q.playable or q.group == "kambi":
            continue
        by_group.setdefault(q.group, []).append(q)

    out: list[GroupFair] = []
    for group, qs in by_group.items():
        sharp = group in SHARP_GROUPS
        exact = [q for q in qs if abs(q.line - line) < 1e-9]
        two = [f for f in (_fair_over(q) for q in exact) if f]
        if two:
            p_over = statistics.median(p for p, _ in two)
            out.append(GroupFair(group, p_over if side == "over" else 1 - p_over, True, sharp, False, line))
            continue
        if side == "over":
            ones = [one_sided_fair(q.over, one_sided_margin) for q in exact if q.over]
            if ones:
                out.append(GroupFair(group, statistics.median(ones), False, sharp, False, line))
                continue
        # Neighbouring two-sided line, interpolated with the negative binomial.
        near = sorted(
            (q for q in qs if q.over and q.under and 0 < abs(q.line - line) <= max_interp + 1e-9),
            key=lambda q: abs(q.line - line),
        )
        if near:
            q = near[0]
            p_over = shift_over_prob(power_devig(q.over, q.under)[0], q.line, line, alpha)
            out.append(GroupFair(group, p_over if side == "over" else 1 - p_over, True, sharp, True, q.line))
    return out


def market_probability(fairs: Sequence[GroupFair], sharp_weight: float) -> float | None:
    if not fairs:
        return None
    return blend_logit([f.p for f in fairs], [sharp_weight if f.sharp else 1.0 for f in fairs])
