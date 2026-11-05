"""Client for the public NHL web/stats APIs (no key required)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from .config import season_for
from .http import HttpError, JsonClient
from .names import normalize_name

log = logging.getLogger(__name__)

WEB = "https://api-web.nhle.com/v1"
STATS = "https://api.nhle.com/stats/rest/en"

REGULAR_SEASON = 2
PLAYOFFS = 3

TTL_SCHEDULE = 15 * 60
TTL_ROSTER = 6 * 3600
TTL_LOG_CURRENT = 2 * 3600
TTL_LOG_PAST = 30 * 86400
TTL_TEAMS = 7 * 86400
TTL_TEAM_STATS = 6 * 3600


@dataclass(frozen=True)
class Game:
    game_id: int
    game_date: date
    start_utc: datetime | None
    home: str
    away: str
    state: str
    game_type: int
    season: str


@dataclass(frozen=True)
class Skater:
    player_id: int
    name: str
    team: str
    position: str  # 'F' or 'D'
    raw_position: str


@dataclass(frozen=True)
class LogEntry:
    game_id: int
    game_date: date
    team: str
    opponent: str
    home: bool
    shots: int
    toi: float  # minutes
    goals: int = 0
    assists: int = 0
    points: int = 0
    pp_goals: int = 0
    pp_points: int = 0


@dataclass(frozen=True)
class TeamDefense:
    abbrev: str
    games_played: int
    shots_against_per_game: float


def parse_toi(value: Any) -> float:
    if not value:
        return 0.0
    minutes, _, seconds = str(value).partition(":")
    try:
        return int(minutes) + int(seconds or 0) / 60.0
    except ValueError:
        return 0.0


def _text(obj: Any) -> str:
    if isinstance(obj, dict):
        return str(obj.get("default", ""))
    return str(obj or "")


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


class NhlApi:
    def __init__(self, client: JsonClient, today: date | None = None) -> None:
        self.client = client
        self.current_season = season_for(today or date.today())
        self._teams: dict[int, tuple[str, str]] | None = None

    # ---------------------------------------------------------------- schedule
    def games_on(self, day: date) -> list[Game]:
        data, _ = self.client.get(f"{WEB}/schedule/{day.isoformat()}", ttl=TTL_SCHEDULE)
        games: list[Game] = []
        for week_day in data.get("gameWeek", []):
            if week_day.get("date") != day.isoformat():
                continue
            for g in week_day.get("games", []):
                game_type = int(g.get("gameType", 0))
                if game_type not in (REGULAR_SEASON, PLAYOFFS):
                    continue
                games.append(
                    Game(
                        game_id=int(g["id"]),
                        game_date=day,
                        start_utc=_parse_utc(g.get("startTimeUTC")),
                        home=g["homeTeam"]["abbrev"],
                        away=g["awayTeam"]["abbrev"],
                        state=str(g.get("gameState", "")),
                        game_type=game_type,
                        season=str(g.get("season") or season_for(day)),
                    )
                )
        return games

    # ------------------------------------------------------------------ roster
    def roster(self, team: str, season: str | None = None) -> list[Skater]:
        path = f"{WEB}/roster/{team}/{season}" if season else f"{WEB}/roster/{team}/current"
        try:
            data, _ = self.client.get(path, ttl=TTL_ROSTER)
        except HttpError as exc:
            if exc.status == 404:
                log.warning("No roster for %s (%s)", team, season or "current")
                return []
            raise
        skaters: list[Skater] = []
        for group, pos in (("forwards", "F"), ("defensemen", "D")):
            for p in data.get(group, []) or []:
                name = f"{_text(p.get('firstName'))} {_text(p.get('lastName'))}".strip()
                skaters.append(
                    Skater(
                        player_id=int(p["id"]),
                        name=name,
                        team=team,
                        position=pos,
                        raw_position=str(p.get("positionCode", pos)),
                    )
                )
        return skaters

    # ---------------------------------------------------------------- game log
    def game_log(self, player_id: int, season: str, game_type: int = REGULAR_SEASON) -> list[LogEntry]:
        ttl = TTL_LOG_PAST if season < self.current_season else TTL_LOG_CURRENT
        try:
            data, _ = self.client.get(f"{WEB}/player/{player_id}/game-log/{season}/{game_type}", ttl=ttl)
        except HttpError as exc:
            if exc.status == 404:
                return []
            raise
        entries: list[LogEntry] = []
        for row in data.get("gameLog", []) or []:
            try:
                entries.append(
                    LogEntry(
                        game_id=int(row["gameId"]),
                        game_date=date.fromisoformat(row["gameDate"]),
                        team=str(row.get("teamAbbrev", "")),
                        opponent=str(row.get("opponentAbbrev", "")),
                        home=row.get("homeRoadFlag") == "H",
                        shots=int(row.get("shots") or 0),
                        toi=parse_toi(row.get("toi")),
                        goals=int(row.get("goals") or 0),
                        assists=int(row.get("assists") or 0),
                        points=int(row.get("points") or 0),
                        pp_goals=int(row.get("powerPlayGoals") or 0),
                        pp_points=int(row.get("powerPlayPoints") or 0),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                log.debug("Skipping malformed game-log row for %s: %s", player_id, exc)
        entries.sort(key=lambda e: (e.game_date, e.game_id))
        return entries

    # ------------------------------------------------------------------- teams
    def teams(self) -> dict[int, tuple[str, str]]:
        """team id -> (tri-code, full name), including relocated/defunct franchises."""
        if self._teams is None:
            data, _ = self.client.get(f"{STATS}/team", ttl=TTL_TEAMS)
            self._teams = {
                int(t["id"]): (str(t["triCode"]), str(t["fullName"]))
                for t in data.get("data", [])
                if t.get("triCode") and t.get("fullName")
            }
        return self._teams

    def abbrev_by_full_name(self) -> dict[str, str]:
        """normalised full team name -> tri-code (used to match sportsbook team names)."""
        return {normalize_name(full): tri for tri, full in self.teams().values()}

    def team_defense(self, season: str, game_type: int = REGULAR_SEASON) -> dict[str, TeamDefense]:
        data, _ = self.client.get(
            f"{STATS}/team/summary",
            {"cayenneExp": f"seasonId={season} and gameTypeId={game_type}"},
            ttl=TTL_TEAM_STATS,
        )
        teams = self.teams()
        result: dict[str, TeamDefense] = {}
        for row in data.get("data", []):
            team = teams.get(int(row.get("teamId", 0)))
            gp = int(row.get("gamesPlayed") or 0)
            sa = row.get("shotsAgainstPerGame")
            if not team or gp <= 0 or sa is None:
                continue
            result[team[0]] = TeamDefense(abbrev=team[0], games_played=gp, shots_against_per_game=float(sa))
        return result


def league_average_shots_against(defense: dict[str, TeamDefense]) -> float | None:
    total_gp = sum(t.games_played for t in defense.values())
    if total_gp <= 0:
        return None
    return sum(t.shots_against_per_game * t.games_played for t in defense.values()) / total_gp
