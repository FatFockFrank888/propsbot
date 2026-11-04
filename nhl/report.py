"""Console tables and CSV/JSON exports."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from .config import Settings
from .edges import Evaluation
from .pricing import fair_odds
from .slate import Projection


def format_table(headers: Sequence[str], rows: Sequence[Sequence[object]], right_align: set[int] | None = None) -> str:
    right_align = right_align or set()
    cells = [[str(h) for h in headers]] + [["" if c is None else str(c) for c in row] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(headers))]

    def fmt(row: list[str]) -> str:
        return "  ".join(c.rjust(w) if i in right_align else c.ljust(w) for i, (c, w) in enumerate(zip(row, widths)))

    sep = "  ".join("-" * w for w in widths)
    return "\n".join([fmt(cells[0]), sep] + [fmt(r) for r in cells[1:]])


def _pct(x: float | None) -> str:
    return "" if x is None else f"{x * 100:.1f}%"


def _odds(x: float | None) -> str:
    return "" if x is None else f"{x:.2f}"


def _num(x: float | None, digits: int = 2) -> str:
    return "" if x is None else f"{x:.{digits}f}"


def projection_rows(projs: Sequence[Projection], lines: Sequence[float], alpha: float) -> tuple[list[str], list[list[object]]]:
    headers = ["Player", "Team", "Opp", "Pos", "GP", "TOI", "SOG/60", "L5", "L10", "Opp×", "Proj"]
    for ln in lines:
        headers += [f"O{ln:g}%", f"O{ln:g} fair"]
    rows: list[list[object]] = []
    for p in projs:
        row: list[object] = [
            p.skater.name + ("" if p.active else " *"),
            p.skater.team,
            ("vs " if p.home else "@ ") + p.opponent,
            p.skater.position,
            p.season_gp,
            _num(p.estimate.proj_toi, 1),
            _num(p.estimate.rate_per_min * 60, 1),
            _num(p.avg_last(5), 1),
            _num(p.avg_last(10), 1),
            _num(p.opp_factor, 2),
            _num(p.mu, 2),
        ]
        for ln in lines:
            pr = p.probs(ln, alpha)
            row += [_pct(pr.over), _odds(fair_odds(pr.over))]
        rows.append(row)
    return headers, rows


def print_projections(projs: Sequence[Projection], lines: Sequence[float], alpha: float, top: int | None) -> None:
    ordered = sorted(projs, key=lambda p: (-p.active, -p.mu))
    if top:
        ordered = ordered[:top]
    headers, rows = projection_rows(ordered, lines, alpha)
    print(format_table(headers, rows, right_align=set(range(4, len(headers)))))
    if any(not p.active for p in ordered):
        print("* did not play in the team's most recent game (scratched/injured/call-up) - verify the lineup")


def evaluation_rows(evals: Sequence[Evaluation], s: Settings) -> tuple[list[str], list[list[object]]]:
    headers = ["Player", "Team", "Game", "Bet", "Book", "Odds", "Model%", "Market%", "Edge", "EV", f"Stake {s.currency}", "Proj", "L10 hit", "Note"]
    rows: list[list[object]] = []
    for e in evals:
        p = e.projection
        rows.append([
            p.skater.name,
            p.skater.team,
            f"{p.game.away}@{p.game.home}",
            f"{e.side.capitalize()} {e.line:g}",
            e.book,
            _odds(e.odds),
            _pct(e.model_prob),
            _pct(e.market_prob),
            _pct(e.edge),
            _pct(e.ev),
            f"{e.stake:.0f}" if e.is_pick else "",
            _num(p.mu, 2),
            _pct(p.hit_rate(e.line, e.side)),
            e.reject_reason or (f"market: {e.market_source}" if e.market_source != "reference" else ""),
        ])
    return headers, rows


def print_evaluations(evals: Sequence[Evaluation], s: Settings, title: str) -> None:
    print(f"\n{title}")
    if not evals:
        print("  (none)")
        return
    headers, rows = evaluation_rows(evals, s)
    print(format_table(headers, rows, right_align={5, 6, 7, 8, 9, 10, 11, 12}))


def write_csv(path: Path, headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


def write_picks_json(path: Path, picks: Sequence[Evaluation], s: Settings, day: date) -> None:
    payload = {
        "date": day.isoformat(),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "currency": s.currency,
        "bankroll": s.bankroll,
        "picks": [
            {
                "player": e.projection.skater.name,
                "player_id": e.projection.skater.player_id,
                "team": e.projection.skater.team,
                "opponent": e.projection.opponent,
                "game_id": e.projection.game.game_id,
                "market": "shots_on_goal",
                "side": e.side,
                "line": e.line,
                "book": e.book,
                "odds": round(e.odds, 3),
                "projection": round(e.projection.mu, 3),
                "model_prob": round(e.model_prob, 4),
                "market_prob": None if e.market_prob is None else round(e.market_prob, 4),
                "edge": round(e.edge, 4),
                "ev": round(e.ev, 4),
                "stake": e.stake,
            }
            for e in picks
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
