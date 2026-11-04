"""SQLite store: line snapshots (odds high, sharp movement) and a full leg log for validation.

The leg log keeps, for every player/line/side the bot evaluated, the first observation,
the observation with the largest edge, the last pre-match observation (the close) and
the result. That gives thousands of graded data points per week, independent of how
many bets are actually placed.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .engine import Leg


@dataclass(frozen=True)
class LegHistory:
    first_seen: float | None
    max_odds: float | None
    first_sharp_p: float | None
    first_sharp_ts: float | None


LEG_COLUMNS = (
    "key TEXT PRIMARY KEY, game_id INTEGER, player_id INTEGER, player TEXT, team TEXT, line REAL, side TEXT,"
    " start TEXT, us_date TEXT,"
    " first_ts REAL, first_odds REAL, first_book TEXT, first_p_fair REAL, first_p_market REAL, first_p_model REAL,"
    " first_edge REAL,"
    " max_edge REAL, max_edge_ts REAL, max_edge_odds REAL, max_edge_book TEXT, max_edge_p_fair REAL,"
    " max_edge_passed INTEGER,"
    " last_ts REAL, close_odds REAL, close_p_fair REAL, close_p_market REAL, close_p_model REAL,"
    " close_p_kambi REAL, close_groups INTEGER,"
    " result_sog INTEGER, outcome TEXT"
)


class LineHistory:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS snapshots ("
            " leg TEXT NOT NULL, ts REAL NOT NULL, best_odds REAL, p_market REAL, p_sharp REAL)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_leg ON snapshots(leg, ts)")
        self.db.execute(f"CREATE TABLE IF NOT EXISTS legs ({LEG_COLUMNS})")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_legs_game ON legs(game_id)")
        self.db.commit()

    # ------------------------------------------------------------ snapshots
    def get(self, leg: str) -> LegHistory:
        with self._lock:
            first_seen, max_odds = self.db.execute(
                "SELECT MIN(ts), MAX(best_odds) FROM snapshots WHERE leg = ?", (leg,)
            ).fetchone()
            row = self.db.execute(
                "SELECT p_sharp, ts FROM snapshots WHERE leg = ? AND p_sharp IS NOT NULL ORDER BY ts LIMIT 1", (leg,)
            ).fetchone()
        return LegHistory(first_seen, max_odds, row[0] if row else None, row[1] if row else None)

    def record(self, leg: str, best_odds: float | None, p_market: float | None, p_sharp: float | None,
               ts: float | None = None) -> None:
        """Store a snapshot only when something changed (keeps the database small)."""
        r = lambda x: None if x is None else round(x, 4)  # noqa: E731
        with self._lock:
            last = self.db.execute(
                "SELECT best_odds, p_market, p_sharp FROM snapshots WHERE leg = ? ORDER BY ts DESC LIMIT 1", (leg,)
            ).fetchone()
            if last is not None and tuple(map(r, last)) == (r(best_odds), r(p_market), r(p_sharp)):
                return
            self.db.execute(
                "INSERT INTO snapshots (leg, ts, best_odds, p_market, p_sharp) VALUES (?, ?, ?, ?, ?)",
                (leg, ts or time.time(), best_odds, p_market, p_sharp),
            )
            self.db.commit()

    def prune(self, older_than_days: float = 4.0) -> None:
        with self._lock:
            cur = self.db.execute("DELETE FROM snapshots WHERE ts < ?", (time.time() - older_than_days * 86400,))
            self.db.commit()
            if cur.rowcount > 1000:
                self.db.execute("VACUUM")

    # ------------------------------------------------------------ leg log
    def log_leg(self, leg: "Leg", ts: float) -> None:
        p = leg.projection
        passed = int(not leg.blocks)
        with self._lock:
            row = self.db.execute("SELECT max_edge FROM legs WHERE key = ?", (leg.key,)).fetchone()
            if row is None:
                self.db.execute(
                    "INSERT INTO legs (key, game_id, player_id, player, team, line, side, start, us_date,"
                    " first_ts, first_odds, first_book, first_p_fair, first_p_market, first_p_model, first_edge,"
                    " max_edge, max_edge_ts, max_edge_odds, max_edge_book, max_edge_p_fair, max_edge_passed)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (leg.key, leg.game.game_id, p.skater.player_id, p.skater.name, p.skater.team, leg.line, leg.side,
                     leg.game.start_utc.isoformat() if leg.game.start_utc else None, leg.game.game_date.isoformat(),
                     ts, leg.odds, leg.book, leg.p_fair, leg.p_market, leg.p_model, leg.edge,
                     leg.edge, ts, leg.odds, leg.book, leg.p_fair, passed),
                )
            elif leg.edge is not None and (row["max_edge"] is None or leg.edge > row["max_edge"]):
                self.db.execute(
                    "UPDATE legs SET max_edge=?, max_edge_ts=?, max_edge_odds=?, max_edge_book=?, max_edge_p_fair=?,"
                    " max_edge_passed=? WHERE key=?",
                    (leg.edge, ts, leg.odds, leg.book, leg.p_fair, passed, leg.key),
                )
            self.db.execute(
                "UPDATE legs SET last_ts=?, close_odds=?, close_p_fair=?, close_p_market=?, close_p_model=?,"
                " close_p_kambi=?, close_groups=? WHERE key=?",
                (ts, leg.odds, leg.p_fair, leg.p_market, leg.p_model, leg.p_kambi, leg.groups, leg.key),
            )
            self.db.commit()

    def unsettled_games(self, before_iso: str) -> list[int]:
        with self._lock:
            rows = self.db.execute(
                "SELECT DISTINCT game_id FROM legs WHERE outcome IS NULL AND start IS NOT NULL AND start <= ?",
                (before_iso,),
            ).fetchall()
        return [r[0] for r in rows]

    def settle_game(self, game_id: int, sog: dict[int, int]) -> int:
        n = 0
        with self._lock:
            rows = self.db.execute(
                "SELECT key, player_id, line, side FROM legs WHERE game_id = ? AND outcome IS NULL", (game_id,)
            ).fetchall()
            for r in rows:
                shots = sog.get(r["player_id"])
                if shots is None:
                    outcome = "void"
                elif shots == r["line"]:
                    outcome = "push"
                else:
                    over = shots > r["line"]
                    outcome = "won" if (over if r["side"] == "over" else not over) else "lost"
                self.db.execute("UPDATE legs SET result_sog=?, outcome=? WHERE key=?", (shots, outcome, r["key"]))
                n += 1
            self.db.commit()
        return n

    def settled_legs(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM legs WHERE outcome IN ('won','lost')").fetchall()
        return [dict(r) for r in rows]

    def leg_counts(self) -> dict[str, int]:
        with self._lock:
            rows = self.db.execute("SELECT COALESCE(outcome,'open'), COUNT(*) FROM legs GROUP BY 1").fetchall()
        return {r[0]: r[1] for r in rows}

    def close(self) -> None:
        self.db.close()
