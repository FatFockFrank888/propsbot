"""Pure projection math: expected shots on goal from a player's game history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .config import Settings
from .nhl_api import LogEntry, TeamDefense

MIN_TOI_FOR_TOI_PROJECTION = 5.0  # games shorter than this are usually injuries / ejections


@dataclass(frozen=True)
class MeanEstimate:
    rate_per_min: float  # shrunk shots-on-goal per minute
    proj_toi: float  # projected minutes
    base_mu: float  # rate * toi, before matchup adjustments
    games_used: int


def decay_weights(n: int, half_life: float) -> list[float]:
    """Exponential weights, index 0 = most recent game."""
    if half_life <= 0:
        return [1.0] * n
    return [0.5 ** (i / half_life) for i in range(n)]


def estimate_mean(history: Sequence[LogEntry], position: str, s: Settings) -> MeanEstimate:
    """Shot rate (empirical-Bayes shrunk to a positional prior) x projected TOI.

    `history` must be chronological and contain only games played before the target game.
    """
    prior_rate = s.forward_prior_rate if position == "F" else s.defense_prior_rate
    default_toi = s.forward_default_toi if position == "F" else s.defense_default_toi

    played = [e for e in history if e.toi > 0]
    recent = played[-s.lookback_games:][::-1] if s.lookback_games > 0 else []

    weights = decay_weights(len(recent), s.rate_half_life)
    shots_w = sum(w * e.shots for w, e in zip(weights, recent))
    toi_w = sum(w * e.toi for w, e in zip(weights, recent))
    rate = (shots_w + prior_rate * s.prior_minutes) / (toi_w + s.prior_minutes) if (toi_w + s.prior_minutes) > 0 else prior_rate

    toi_window = recent[: s.toi_lookback_games]
    toi_games = [e for e in toi_window if e.toi >= MIN_TOI_FOR_TOI_PROJECTION] or toi_window
    if toi_games:
        tw = decay_weights(len(toi_games), s.toi_half_life)
        proj_toi = sum(w * e.toi for w, e in zip(tw, toi_games)) / sum(tw)
    else:
        proj_toi = default_toi

    return MeanEstimate(rate_per_min=rate, proj_toi=proj_toi, base_mu=rate * proj_toi, games_used=len(recent))


def opponent_factor(defense: TeamDefense | None, league_avg: float | None, s: Settings) -> float:
    """How many more/fewer shots the opponent allows than average, shrunk for small samples."""
    if defense is None or not league_avg:
        return 1.0
    gp = defense.games_played
    shrunk = (defense.shots_against_per_game * gp + league_avg * s.opp_shrink_games) / (gp + s.opp_shrink_games)
    return min(s.opp_factor_cap, max(s.opp_factor_floor, shrunk / league_avg))


def venue_factor(home: bool, s: Settings) -> float:
    return 1.0 + s.home_edge if home else 1.0 - s.home_edge
