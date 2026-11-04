"""Count distribution for shots on goal: negative binomial (Poisson when dispersion is 0)."""

from __future__ import annotations

import math
from dataclasses import dataclass


def pmf(k: int, mu: float, alpha: float) -> float:
    """P(X = k) for a negative binomial with mean mu and Var = mu + alpha * mu^2."""
    if k < 0:
        return 0.0
    if mu <= 0.0:
        return 1.0 if k == 0 else 0.0
    if alpha <= 1e-9:
        return math.exp(-mu + k * math.log(mu) - math.lgamma(k + 1))
    r = 1.0 / alpha
    log_p = (
        math.lgamma(k + r)
        - math.lgamma(r)
        - math.lgamma(k + 1)
        + r * math.log(r / (r + mu))
        + k * math.log(mu / (r + mu))
    )
    return math.exp(log_p)


def cdf(k: int, mu: float, alpha: float) -> float:
    if k < 0:
        return 0.0
    return min(1.0, sum(pmf(i, mu, alpha) for i in range(k + 1)))


@dataclass(frozen=True)
class LineProbs:
    over: float
    under: float
    push: float

    def side(self, side: str) -> float:
        if side == "over":
            return self.over
        if side == "under":
            return self.under
        raise ValueError(f"unknown side {side!r}")


def line_probs(line: float, mu: float, alpha: float) -> LineProbs:
    """Over/under/push probabilities for a shots-on-goal line (half or whole number)."""
    if line < 0:
        raise ValueError("line must be >= 0")
    is_whole = abs(line - round(line)) < 1e-9
    if is_whole:
        k = int(round(line))
        push = pmf(k, mu, alpha)
        under = cdf(k - 1, mu, alpha)
    else:
        push = 0.0
        under = cdf(math.floor(line), mu, alpha)
    over = max(0.0, 1.0 - under - push)
    return LineProbs(over=over, under=under, push=push)
