"""Walk-forward backtest of the projection model on a completed season.

Each game is predicted using only games played before it. The opponent factor is
held at 1.0 because season-end team stats would leak future information.
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Sequence

from .config import Settings, previous_season
from .model import line_probs
from .nhl_api import NhlApi, Skater
from .projections import estimate_mean, venue_factor

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Record:
    mu: float
    baseline: float  # naive: average of last 10 games
    actual: int


def collect_records(
    nhl: NhlApi, s: Settings, season: str, teams: Iterable[str] | None = None, min_history: int = 10
) -> list[Record]:
    team_list = sorted({t.upper() for t in teams} if teams else nhl.team_defense(season).keys())
    if not team_list:
        raise ValueError(f"No teams found for season {season}")
    skaters: dict[int, Skater] = {}
    for team in team_list:
        for sk in nhl.roster(team, season):
            skaters.setdefault(sk.player_id, sk)
    log.info("Backtesting %d skaters from %d teams", len(skaters), len(team_list))

    prev_season = previous_season(season)

    def logs(sk: Skater):
        return nhl.game_log(sk.player_id, prev_season), nhl.game_log(sk.player_id, season)

    players = list(skaters.values())
    with ThreadPoolExecutor(max_workers=s.http_workers) as pool:
        all_logs = list(pool.map(logs, players))

    records: list[Record] = []
    for sk, (prev, cur) in zip(players, all_logs):
        prev_played = [e for e in prev if e.toi > 0]
        cur_played = [e for e in cur if e.toi > 0]
        for i, game in enumerate(cur_played):
            history = prev_played + cur_played[:i]
            if len(history) < min_history:
                continue
            est = estimate_mean(history, sk.position, s)
            last10 = history[-10:]
            records.append(
                Record(
                    mu=est.base_mu * venue_factor(game.home, s),
                    baseline=sum(e.shots for e in last10) / len(last10),
                    actual=game.shots,
                )
            )
    return records


def _log_loss(p: float, hit: bool) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if hit else 1 - p)


def fit_dispersion(records: Sequence[Record]) -> float:
    """Method-of-moments NB alpha: E[(x-mu)^2] = mu + alpha * mu^2."""
    num = sum((r.actual - r.mu) ** 2 - r.mu for r in records)
    den = sum(r.mu ** 2 for r in records)
    return max(0.0, num / den) if den > 0 else 0.0


def summarize(records: Sequence[Record], lines: Sequence[float], alpha: float) -> dict:
    n = len(records)
    if n == 0:
        return {"n": 0}
    out: dict = {
        "n": n,
        "mean_actual": sum(r.actual for r in records) / n,
        "mean_model": sum(r.mu for r in records) / n,
        "mean_baseline": sum(r.baseline for r in records) / n,
        "mae_model": sum(abs(r.actual - r.mu) for r in records) / n,
        "mae_baseline": sum(abs(r.actual - r.baseline) for r in records) / n,
        "fitted_alpha": fit_dispersion(records),
        "lines": {},
    }
    for line in lines:
        brier_m = brier_b = ll_m = ll_b = 0.0
        bins: list[list[float]] = [[0, 0.0, 0] for _ in range(10)]  # count, sum_pred, hits
        for r in records:
            hit = r.actual > line
            pm = line_probs(line, r.mu, alpha).over
            pb = line_probs(line, r.baseline, 0.0).over
            brier_m += (pm - hit) ** 2
            brier_b += (pb - hit) ** 2
            ll_m += _log_loss(pm, hit)
            ll_b += _log_loss(pb, hit)
            b = bins[min(9, int(pm * 10))]
            b[0] += 1
            b[1] += pm
            b[2] += hit
        out["lines"][line] = {
            "hit_rate": sum(r.actual > line for r in records) / n,
            "brier_model": brier_m / n,
            "brier_baseline": brier_b / n,
            "logloss_model": ll_m / n,
            "logloss_baseline": ll_b / n,
            "calibration": [
                {"bucket": f"{i * 10}-{i * 10 + 10}%", "n": int(c), "predicted": sp / c, "actual": h / c}
                for i, (c, sp, h) in enumerate(bins)
                if c > 0
            ],
        }
    return out


def print_summary(summary: dict, season: str, alpha: float) -> None:
    from .report import format_table

    if not summary.get("n"):
        print("No backtest records (not enough games).")
        return
    print(f"Backtest {season}: {summary['n']:,} player-games  (dispersion alpha used = {alpha:.3f})")
    print(f"  Mean SOG  actual {summary['mean_actual']:.3f} | model {summary['mean_model']:.3f} | naive L10 {summary['mean_baseline']:.3f}")
    print(f"  MAE       model {summary['mae_model']:.3f} | naive L10 {summary['mae_baseline']:.3f}")
    print(f"  Fitted dispersion alpha = {summary['fitted_alpha']:.3f}  (set DISPERSION in .env)")
    rows = []
    for line, m in summary["lines"].items():
        rows.append([
            f"O{line:g}", f"{m['hit_rate'] * 100:.1f}%",
            f"{m['brier_model']:.4f}", f"{m['brier_baseline']:.4f}",
            f"{m['logloss_model']:.4f}", f"{m['logloss_baseline']:.4f}",
        ])
    print()
    print(format_table(["Line", "Hit rate", "Brier model", "Brier naive", "LogLoss model", "LogLoss naive"], rows, set(range(1, 6))))
    for line, m in summary["lines"].items():
        print(f"\nCalibration, over {line:g}")
        cal = [[c["bucket"], c["n"], f"{c['predicted'] * 100:.1f}%", f"{c['actual'] * 100:.1f}%"] for c in m["calibration"]]
        print(format_table(["Model prob", "N", "Predicted", "Actual"], cal, {1, 2, 3}))
