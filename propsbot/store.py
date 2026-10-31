"""Loggning i SQLite: varje beräkning, stängningspriser och utfall.

Ger underlaget för CLV, kalibrering och backtest.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .blend import SettledLine

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    ts REAL, match_id TEXT, player_id TEXT, player_name TEXT, market TEXT, line REAL,
    p_model REAL, p_market REAL, p_final REAL, w_model REAL, lineup_confirmed INTEGER,
    best_book TEXT, best_odds REAL, edge REAL, play_from REAL,
    playable INTEGER, shown INTEGER, stake REAL, reasons TEXT
);
CREATE TABLE IF NOT EXISTS closing (
    match_id TEXT, player_id TEXT, market TEXT, line REAL,
    p_close REAL,              -- Pinnacles marginalfria stängning (eller konsensus)
    PRIMARY KEY (match_id, player_id, market, line)
);
CREATE TABLE IF NOT EXISTS results (
    match_id TEXT, player_id TEXT, market TEXT, count INTEGER, played INTEGER,
    PRIMARY KEY (match_id, player_id, market)
);
"""


class Store:
    def __init__(self, path: str | Path = "propsbot.sqlite"):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def log_prediction(self, row: dict) -> None:
        cols = ",".join(row)
        q = ",".join("?" * len(row))
        self.conn.execute(f"INSERT INTO predictions ({cols}) VALUES ({q})", list(row.values()))
        self.conn.commit()

    def record_closing(self, match_id: str, player_id: str, market: str, line: float,
                       p_close: float) -> None:
        self.conn.execute("INSERT OR REPLACE INTO closing VALUES (?,?,?,?,?)",
                          (match_id, player_id, market, line, p_close))
        self.conn.commit()

    def record_result(self, match_id: str, player_id: str, market: str, count: int,
                      played: bool) -> None:
        self.conn.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)",
                          (match_id, player_id, market, count, int(played)))
        self.conn.commit()

    def clv_report(self) -> list[tuple]:
        """CLV per marknad för spelade ben: snitt av p_close × odds − 1."""
        return self.conn.execute("""
            WITH last AS (
                SELECT p.*, ROW_NUMBER() OVER (PARTITION BY match_id, player_id, market, line
                                              ORDER BY ts DESC) AS rn
                FROM predictions p WHERE playable = 1)
            SELECT l.market, COUNT(*), AVG(c.p_close * l.best_odds - 1.0), AVG(l.edge)
            FROM last l JOIN closing c USING (match_id, player_id, market, line)
            WHERE l.rn = 1 GROUP BY l.market
        """).fetchall()

    def settled_lines(self) -> list[SettledLine]:
        """Senaste förhandsberäkningen per linje + utfall (bara där spelaren spelade)."""
        rows = self.conn.execute("""
            WITH last AS (
                SELECT p.*, ROW_NUMBER() OVER (PARTITION BY match_id, player_id, market, line
                                              ORDER BY ts DESC) AS rn
                FROM predictions p)
            SELECT l.match_id, l.market, l.p_final, r.count, l.line
            FROM last l JOIN results r USING (match_id, player_id, market)
            WHERE l.rn = 1 AND r.played = 1
        """).fetchall()
        return [SettledLine(m, mk, p, int(cnt > line)) for m, mk, p, cnt, line in rows]
