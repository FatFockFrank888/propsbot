"""JSON ledgers (live, bokforing, skugga, modelltest), CLV tracking and auto-settlement."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .bot_settings import BotSettings
from .engine import Leg, play_down_to

log = logging.getLogger(__name__)

LEDGERS = {
    "live": "nhl_live.json",  # real bets, notified
    "bokforing": "nhl_bokforing.json",  # passes all shared rules
    "skugga": "nhl_skugga.json",  # >= shadow edge but stopped by a rule
    "modelltest": "nhl_modelltest.json",  # the player model's own picks
}
OPEN = "open"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def bet_from_leg(leg: Leg, ledger: str, s: BotSettings, units: int, reasons: list[str] | None = None,
                 edge_field: str = "edge") -> dict[str, Any]:
    p = leg.projection
    edge = leg.model_edge if edge_field == "model_edge" else leg.edge
    return {
        "id": uuid.uuid4().hex[:12],
        "ledger": ledger,
        "created": _iso(datetime.now(timezone.utc)),
        "game_id": leg.game.game_id,
        "game": f"{leg.game.away}@{leg.game.home}",
        "start": _iso(leg.game.start_utc) if leg.game.start_utc else None,
        "us_date": leg.game.game_date.isoformat(),
        "player": p.skater.name,
        "player_id": p.skater.player_id,
        "team": p.skater.team,
        "line": leg.line,
        "side": leg.side,
        "book": leg.book,
        "odds": round(leg.odds, 3),
        "units": units,
        "stake": round(units * s.unit_value(), 2),
        "p_fair": None if leg.p_fair is None else round(leg.p_fair, 4),
        "p_market": None if leg.p_market is None else round(leg.p_market, 4),
        "p_model": round(leg.p_model, 4),
        "proj_sog": round(p.mu, 3),
        "edge": None if edge is None else round(edge, 4),
        "model_edge": round(leg.model_edge, 4),
        "play_down_to": play_down_to(leg.p_fair, s.live_min_edge if ledger == "live" else s.min_edge_all),
        "alt_prices": {b: round(o, 3) for b, o in sorted(leg.playable_prices.items(), key=lambda kv: -kv[1])},
        "p_kambi": None if leg.p_kambi is None else round(leg.p_kambi, 4),
        "groups": [f.group for f in leg.refs],
        "sharp": leg.has_sharp,
        "two_sided": leg.has_two_sided,
        "tags": list(leg.tags),
        "reasons": reasons or [],
        "close_odds": None,
        "close_p": None,
        "clv": None,
        "close_p_kambi": None,
        "kambi_clv": None,
        "price_clv": None,
        "status": OPEN,
        "result_sog": None,
        "profit_units": None,
        "settled_at": None,
    }


class Ledger:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        self.bets: list[dict[str, Any]] = self._load()
        self.dirty = False

    def _load(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as exc:
            raise ValueError(f"{self.path} is corrupt: {exc}") from None
        return data if isinstance(data, list) else data.get("bets", [])

    def save(self) -> None:
        if not self.dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(self.bets, fh, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)
        self.dirty = False

    # ------------------------------------------------------------------ queries
    def for_player(self, game_id: int, player_id: int) -> dict[str, Any] | None:
        for b in self.bets:
            if b["game_id"] == game_id and b["player_id"] == player_id:
                return b
        return None

    def open_bets(self) -> list[dict[str, Any]]:
        return [b for b in self.bets if b["status"] == OPEN]

    def count(self, pred: Callable[[dict[str, Any]], bool]) -> int:
        return sum(1 for b in self.bets if pred(b))

    def units(self, pred: Callable[[dict[str, Any]], bool]) -> int:
        return sum(int(b["units"]) for b in self.bets if pred(b))

    # ------------------------------------------------------------------ updates
    def add(self, bet: dict[str, Any]) -> None:
        self.bets.append(bet)
        self.dirty = True

    def upsert_best(self, bet: dict[str, Any], score_field: str = "edge") -> bool:
        """One bet per player per game; a larger edge replaces an open, not-yet-started bet."""
        existing = self.for_player(bet["game_id"], bet["player_id"])
        if existing is None:
            self.add(bet)
            return True
        if existing["status"] != OPEN:
            return False
        if (bet.get(score_field) or 0) > (existing.get(score_field) or 0) + 1e-9:
            self.bets[self.bets.index(existing)] = bet
            self.dirty = True
            return True
        return False

    def update_close(self, legs_by_key: dict[str, Leg]) -> None:
        """Track the last pre-match price/fair probability for CLV."""
        for b in self.open_bets():
            leg = legs_by_key.get(f"{b['game_id']}|{b['player_id']}|{b['line']:g}|{b['side']}")
            if leg is None:
                continue
            close_odds = leg.playable_prices.get(b["book"], leg.odds)
            b["close_odds"] = round(close_odds, 3)
            b["price_clv"] = round(b["odds"] / close_odds - 1, 4)
            if leg.p_market is not None:
                b["close_p"] = round(leg.p_market, 4)
                b["clv"] = round(b["odds"] * leg.p_market - 1, 4)
            if leg.p_kambi is not None:
                b["close_p_kambi"] = round(leg.p_kambi, 4)
                b["kambi_clv"] = round(b["odds"] * leg.p_kambi - 1, 4)
            self.dirty = True

    def settle(self, results: dict[int, dict[int, int] | None]) -> int:
        """results: game_id -> {player_id: sog} for finished games (None = not final yet)."""
        settled = 0
        for b in self.open_bets():
            final = results.get(b["game_id"])
            if final is None:
                continue
            sog = final.get(b["player_id"])
            if sog is None:
                status, profit = "void", 0.0
            else:
                over_wins = sog > b["line"]
                push = sog == b["line"]
                won = over_wins if b["side"] == "over" else (sog < b["line"])
                status = "push" if push else ("won" if won else "lost")
                profit = b["units"] * (b["odds"] - 1) if status == "won" else (-b["units"] if status == "lost" else 0.0)
            b.update(status=status, result_sog=sog, profit_units=round(profit, 3),
                     settled_at=_iso(datetime.now(timezone.utc)))
            settled += 1
            self.dirty = True
        return settled

    def stats(self) -> dict[str, Any]:
        done = [b for b in self.bets if b["status"] in ("won", "lost", "push")]
        staked = sum(b["units"] for b in done)
        profit = sum(b["profit_units"] or 0 for b in done)
        clvs = [b["clv"] for b in self.bets if b.get("clv") is not None]
        return {
            "ledger": self.name,
            "bets": len(self.bets),
            "open": len(self.open_bets()),
            "settled": len(done),
            "won": sum(b["status"] == "won" for b in done),
            "lost": sum(b["status"] == "lost" for b in done),
            "push": sum(b["status"] == "push" for b in done),
            "void": sum(b["status"] == "void" for b in self.bets),
            "units_staked": staked,
            "profit_units": round(profit, 2),
            "roi": (profit / staked) if staked else None,
            "avg_clv": (sum(clvs) / len(clvs)) if clvs else None,
            "beat_close": (sum(c > 0 for c in clvs) / len(clvs)) if clvs else None,
        }


def open_ledgers(s: BotSettings) -> dict[str, Ledger]:
    return {name: Ledger(name, s.data_path / fname) for name, fname in LEDGERS.items()}


def boxscore_sog(data: dict) -> dict[int, int] | None:
    """player_id -> shots on goal from an NHL boxscore, or None if the game is not final."""
    if data.get("gameState") not in ("OFF", "FINAL"):
        return None
    out: dict[int, int] = {}
    stats = data.get("playerByGameStats", {}) or {}
    for side in ("homeTeam", "awayTeam"):
        for group in ("forwards", "defense"):
            for p in (stats.get(side, {}) or {}).get(group, []) or []:
                if "playerId" in p and p.get("sog") is not None:
                    out[int(p["playerId"])] = int(p["sog"])
    return out
