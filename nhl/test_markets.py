"""NHL test markets: points, assists, goals and power-play points/goals at the Kambi books – data only.

Kambi posts, per game, "Player to score at least N points" (yes/no, N = 1-3), "Player to record at
least 1 assists" (yes/no), "To score" and "To score at least N goals" (yes only). No sharp book prices
these for the Swedish market, so the edge can only come from our own model.
Power play (added 2026-11-05): "Player To score at least N Power Play Points" (yes/no, N = 1-2), and
player power-play goals if a book posts them. Same model on the player's power-play points/goals per game
(PP1 role shows up in the rate); settled from the player's NHL game log (the boxscore has no PP points):

  rate  = weighted goals/assists/points per game over the last 82 games incl. last season (half-life 25),
          shrunk toward a position prior worth 5 games (F: 0.22 / 0.32 / 0.54, D: 0.06 / 0.24 / 0.30)
  p     = Poisson P(X >= N) at that rate
  edge  = p x best playable odds - 1   (both yes and no are tried; the side with EV+ is the one we log)

Logged to <data>/nhl_test_marknader.json in the same (Swedish) format as football and NBA, with the
shared rules (edge >= min_edge_all, odds window, implausible edge, one bet per player per game) and
settled from the NHL boxscore. The Kambi de-vigged price is stored too, so the model can be judged
against the market (CLV) long before the results are meaningful.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .names import normalize_name

log = logging.getLogger(__name__)

PRIOR = {"F": {"nhl_goals": 0.22, "nhl_assists": 0.32, "nhl_points": 0.54, "nhl_pp_points": 0.13, "nhl_pp_goals": 0.05},
         "D": {"nhl_goals": 0.06, "nhl_assists": 0.24, "nhl_points": 0.30, "nhl_pp_points": 0.08, "nhl_pp_goals": 0.015}}
STAT = {"nhl_goals": "goals", "nhl_assists": "assists", "nhl_points": "points",
        "nhl_pp_points": "pp_points", "nhl_pp_goals": "pp_goals"}
PP_MARKETS = ("nhl_pp_points", "nhl_pp_goals")
FILE = "nhl_test_marknader.json"
_AT_LEAST = re.compile(r"at least (\d+)", re.I)


@dataclass
class TestQuote:
    player: str
    market: str
    line: float
    side: str
    odds: float
    book: str


def market_of(label: str) -> tuple[str, float | None] | None:
    s = label.lower()
    if "first" in s or "period" in s or "shots" in s or "shorthanded" in s:
        return None
    m = _AT_LEAST.search(s)
    n = int(m.group(1)) if m else 1
    if "power play" in s:
        if "total" in s or " by " in s:            # team/match totals, not a player market
            return None
        if "point" in s:
            return "nhl_pp_points", n - 0.5
        if "goal" in s or s.startswith("to score"):
            return "nhl_pp_goals", n - 0.5
        return None
    if "point" in s:
        return "nhl_points", n - 0.5
    if "assist" in s:
        return "nhl_assists", n - 0.5
    if s.startswith("to score"):
        return "nhl_goals", n - 0.5
    return None


def parse_kambi(raw: dict, book: str) -> list[TestQuote]:
    out = []
    for bo in raw.get("betOffers", []) or []:
        crit = bo.get("criterion", {}) or {}
        mk = market_of(crit.get("englishLabel") or crit.get("label") or "")
        if not mk:
            continue
        market, line = mk
        for o in bo.get("outcomes", []) or []:
            if o.get("status", "OPEN") != "OPEN" or not o.get("odds") or not o.get("participant"):
                continue
            lab = (o.get("englishLabel") or o.get("label") or "").lower()
            typ = (o.get("type") or "").upper()
            side = "under" if lab in ("no", "under") or typ in ("OT_NO", "OT_UNDER") else "over"
            ln = o["line"] / 1000 - 0.5 if o.get("line") is not None else line
            odds = o["odds"] / 1000
            if odds > 1.0 and ln is not None:
                out.append(TestQuote(o["participant"], market, ln, side, odds, book))
    return out


def poisson_at_least(k: int, mu: float) -> float:
    return 1.0 - sum(math.exp(-mu) * mu ** i / math.factorial(i) for i in range(k))


def player_rates(logs: list, position: str, n: int = 82, half_life: float = 25.0, prior_games: float = 5.0) -> dict[str, float]:
    recent = sorted(logs, key=lambda e: (e.game_date, e.game_id), reverse=True)[:n]
    prior = PRIOR.get(position, PRIOR["F"])
    out = {}
    for mk, stat in STAT.items():
        w = [0.5 ** (i / half_life) for i in range(len(recent))]
        num = sum(wi * getattr(e, stat) for wi, e in zip(w, recent))
        out[mk] = (num + prior[mk] * prior_games) / (sum(w) + prior_games)
    return out


def _kambi_fair(quotes: list[TestQuote], market: str, line: float, player: str) -> float | None:
    """Median de-vigged P(over) over the books that price both yes and no."""
    by_book: dict[str, dict[str, float]] = {}
    for q in quotes:
        if q.market == market and q.line == line and q.player == player:
            by_book.setdefault(q.book, {})[q.side] = q.odds
    ps = sorted((1 / d["over"]) / (1 / d["over"] + 1 / d["under"]) for d in by_book.values() if "over" in d and "under" in d)
    return ps[len(ps) // 2] if ps else None


class TestMarkets:
    def __init__(self, data_path: Path, s) -> None:
        self.path = data_path / FILE
        self.s = s
        try:
            self.bets: list[dict[str, Any]] = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.bets = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.bets, ensure_ascii=False, indent=1), encoding="utf-8")

    def evaluate(self, game, projections: list, quotes: list[TestQuote], history_for, playable: set[str], now: float) -> int:
        """Log the best EV+ line per player for one game. Returns the number of new bets."""
        s = self.s
        by_name = {normalize_name(p.skater.name): p for p in projections}
        start = game.start_utc.timestamp() if game.start_utc else None
        best: dict[int, tuple[float, dict]] = {}
        seen = {(q.player, q.market, q.line, q.side) for q in quotes}
        for player, market, line, side in seen:
            proj = by_name.get(normalize_name(player))
            if proj is None or not proj.active:
                continue
            cands = [q for q in quotes if (q.player, q.market, q.line, q.side) == (player, market, line, side)
                     and q.book.lower() in playable]
            if not cands:
                continue
            q = max(cands, key=lambda x: x.odds)
            rate = player_rates(history_for(proj), proj.skater.position)[market]
            p_over = poisson_at_least(int(line + 0.5), rate)
            p = p_over if side == "over" else 1 - p_over
            edge = p * q.odds - 1
            if not (s.odds_min_all <= q.odds <= s.odds_max_all) or not (s.min_edge_all <= edge <= s.max_plausible_edge):
                continue
            fair = _kambi_fair(quotes, market, line, player)
            fair_side = None if fair is None else (fair if side == "over" else 1 - fair)
            pid = proj.skater.player_id
            if pid not in best or edge > best[pid][0]:
                units = max(1, min(s.max_units_per_bet, round(s.kelly_fraction * edge / (q.odds - 1) / s.unit_pct)))
                best[pid] = (edge, {
                    "key": f"nhl|{game.game_id}|{pid}|{market}|{line}|{side}", "id": len(self.bets) + 1,
                    "bokford": now, "match_id": f"nhl{game.game_id}", "game_id": game.game_id,
                    "match": f"{game.away} – {game.home}", "hemma": game.home, "borta": game.away, "liga": "NHL",
                    "avspark": start, "spelare": proj.skater.name, "spelare_id": pid, "marknad": market,
                    "linje": line, "sida": side, "bolag": q.book, "odds": round(q.odds, 3), "sannolikhet": round(p, 4),
                    "ratt_odds": round(1 / p, 3), "edge": round(edge, 4), "prognos": round(rate, 3),
                    "p_kambi": None if fair_side is None else round(fair_side, 4),
                    "spela_fran": round((1 + s.min_edge_all) / p, 3), "insats_pct": units * s.unit_pct,
                    "stangning": round(q.odds, 3), "status": "öppen",
                    "stopp": f"modell {rate:.2f}/match" + ("" if fair_side is None else f", Kambi rättvis {fair_side:.0%}"),
                    "clv_signal": False, "forv_clv_pp": None, "utfall": None, "resultat_enheter": None,
                })
        taken = {(b["game_id"], b["spelare_id"]) for b in self.bets}
        new = 0
        for pid, (_, bet) in best.items():
            if (game.game_id, pid) in taken:   # one bet per player per game, first one stands
                continue
            self.bets.append(bet)
            new += 1
        # closing price: the latest price at the same book, until the game starts
        if start and now < start:
            price = {(q.player, q.market, q.line, q.side, q.book): q.odds for q in quotes}
            for b in self.bets:
                if b["game_id"] == game.game_id and b["status"] == "öppen":
                    for k, o in price.items():
                        if (normalize_name(k[0]), k[1], k[2], k[3], k[4]) == (
                                normalize_name(b["spelare"]), b["marknad"], b["linje"], b["sida"], b["bolag"]):
                            b["stangning"] = round(o, 3)
        return new

    def settle(self, fetch_boxscore, now: float, fetch_pp=None) -> int:
        """fetch_pp(player_id, game_id) -> {"pp_points": n, "pp_goals": n} from the game log, or None
        while the log has not caught up (the bet then stays open until a later scan)."""
        due = {b["game_id"] for b in self.bets
               if b["status"] == "öppen" and b.get("avspark") and now > b["avspark"] + 2.5 * 3600}
        n = 0
        for gid in due:
            try:
                stats = boxscore_scoring(fetch_boxscore(gid))
            except Exception as exc:  # noqa: BLE001 - test markets must never stop the scan
                log.warning("NHL test markets: boxscore %s: %s", gid, exc)
                continue
            if stats is None:
                continue
            for b in self.bets:
                if b["game_id"] != gid or b["status"] != "öppen":
                    continue
                st = stats.get(int(b["spelare_id"]))
                if st is None:
                    b["status"], b["resultat_enheter"] = "struken", 0.0
                else:
                    if b["marknad"] in PP_MARKETS:
                        pp = None
                        if fetch_pp is not None:
                            try:
                                pp = fetch_pp(int(b["spelare_id"]), gid)
                            except Exception as exc:  # noqa: BLE001
                                log.warning("NHL test markets: game log %s: %s", b["spelare_id"], exc)
                        if pp is None:
                            continue
                        st = dict(st, **pp)
                    val = st[STAT[b["marknad"]]]
                    won = val > b["linje"] if b["sida"] == "over" else val < b["linje"]
                    b["utfall"] = val
                    b["status"] = "vunnen" if won else "förlorad"
                    b["resultat_enheter"] = b["insats_pct"] * ((b["odds"] - 1) if won else -1)
                n += 1
        return n


def boxscore_scoring(data: dict) -> dict[int, dict[str, int]] | None:
    """player_id -> goals/assists/points from an NHL boxscore, or None if the game is not final."""
    if data.get("gameState") not in ("OFF", "FINAL"):
        return None
    out = {}
    stats = data.get("playerByGameStats", {}) or {}
    for side in ("homeTeam", "awayTeam"):
        for group in ("forwards", "defense"):
            for p in (stats.get(side, {}) or {}).get(group, []) or []:
                if "playerId" in p:
                    g, a = int(p.get("goals") or 0), int(p.get("assists") or 0)
                    out[int(p["playerId"])] = {"goals": g, "assists": a, "points": int(p.get("points", g + a) or 0),
                                               "pp_goals": int(p.get("powerPlayGoals") or 0)}
    return out
