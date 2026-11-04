"""Build projections for every skater playing on a given date."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from .config import Settings, previous_season
from .model import LineProbs, line_probs
from .nhl_api import PLAYOFFS, REGULAR_SEASON, Game, LogEntry, NhlApi, Skater, league_average_shots_against
from .projections import MeanEstimate, estimate_mean, opponent_factor, venue_factor

log = logging.getLogger(__name__)

FINISHED_STATES = {"OFF", "FINAL"}
LIVE_STATES = {"LIVE", "CRIT"}


@dataclass(frozen=True)
class Projection:
    game: Game
    skater: Skater
    opponent: str
    home: bool
    estimate: MeanEstimate
    opp_factor: float
    venue_factor: float
    mu: float
    active: bool
    last_game: date | None
    season_gp: int
    season_avg: float | None
    recent_shots: tuple[int, ...]  # most recent first, up to 10

    def probs(self, line: float, alpha: float) -> LineProbs:
        return line_probs(line, self.mu, alpha)

    def avg_last(self, n: int) -> float | None:
        shots = self.recent_shots[:n]
        return sum(shots) / len(shots) if shots else None

    def hit_rate(self, line: float, side: str = "over", n: int = 10) -> float | None:
        shots = self.recent_shots[:n]
        if not shots:
            return None
        hits = sum(1 for x in shots if (x > line if side == "over" else x < line))
        return hits / len(shots)


def _history_for(nhl: NhlApi, skater: Skater, game: Game, s: Settings) -> tuple[list[LogEntry], list[LogEntry]]:
    """(full history used for the model, current-season games only), both before game day."""
    current = nhl.game_log(skater.player_id, game.season, REGULAR_SEASON)
    if game.game_type == PLAYOFFS:
        current = current + nhl.game_log(skater.player_id, game.season, PLAYOFFS)
    current = sorted((e for e in current if e.game_date < game.game_date), key=lambda e: (e.game_date, e.game_id))
    history = current
    if len(current) < s.lookback_games:
        prev = [e for e in nhl.game_log(skater.player_id, previous_season(game.season), REGULAR_SEASON)]
        history = prev + current
    return history, current


def build_slate(
    nhl: NhlApi,
    s: Settings,
    day: date,
    *,
    teams: Iterable[str] | None = None,
    include_started: bool = False,
) -> list[Projection]:
    games = nhl.games_on(day)
    team_filter = {t.upper() for t in teams} if teams else None
    selected: list[Game] = []
    for g in games:
        if team_filter and g.home not in team_filter and g.away not in team_filter:
            continue
        if not include_started and (g.state in FINISHED_STATES or g.state in LIVE_STATES):
            log.info("Skipping %s @ %s (state %s)", g.away, g.home, g.state)
            continue
        selected.append(g)
    if not selected:
        return []

    season = selected[0].season
    defense = nhl.team_defense(season)
    if sum(t.games_played for t in defense.values()) < 32 * 3:
        log.info("Early season: blending opponent shot suppression with last season")
        prev = nhl.team_defense(previous_season(season))
        for abbrev, prev_def in prev.items():
            cur = defense.get(abbrev)
            if cur is None or cur.games_played < 3:
                defense[abbrev] = prev_def
    league_avg = league_average_shots_against(defense)

    tasks: list[tuple[Game, Skater, bool]] = []
    for g in selected:
        for team, home in ((g.home, True), (g.away, False)):
            for skater in nhl.roster(team):
                tasks.append((g, skater, home))

    with ThreadPoolExecutor(max_workers=s.http_workers) as pool:
        histories = list(pool.map(lambda t: _history_for(nhl, t[1], t[0], s), tasks))

    # A player is "active" if he played in his team's most recent game this season.
    team_last: dict[str, date] = {}
    for (g, skater, _), (_, current) in zip(tasks, histories):
        if current:
            last = current[-1].game_date
            if last > team_last.get(skater.team, date.min):
                team_last[skater.team] = last

    projections: list[Projection] = []
    for (g, skater, home), (history, current) in zip(tasks, histories):
        opponent = g.away if home else g.home
        est = estimate_mean(history, skater.position, s)
        of = opponent_factor(defense.get(opponent), league_avg, s)
        vf = venue_factor(home, s)
        last_game = current[-1].game_date if current else None
        team_latest = team_last.get(skater.team)
        if team_latest is None:
            active = bool(history)  # team has not played yet this season
        else:
            active = last_game is not None and last_game >= team_latest
        played = [e for e in history if e.toi > 0]
        projections.append(
            Projection(
                game=g,
                skater=skater,
                opponent=opponent,
                home=home,
                estimate=est,
                opp_factor=of,
                venue_factor=vf,
                mu=est.base_mu * of * vf,
                active=active,
                last_game=last_game,
                season_gp=len(current),
                season_avg=(sum(e.shots for e in current) / len(current)) if current else None,
                recent_shots=tuple(e.shots for e in reversed(played[-10:])),
            )
        )
    return projections
