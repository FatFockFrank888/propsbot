"""Blandning modell + marknad i log-odds, och nivåkalibrering per marknad."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .config import BlendConfig, CalibrationConfig
from .market import inv_logit, logit


def model_weight(market: str, lineup_confirmed: bool, pinnacle_present: bool,
                 p_model: float, p_market: float, cfg: BlendConfig) -> float:
    w = cfg.w_model_post_lineup if lineup_confirmed else cfg.w_model_pre_lineup
    if pinnacle_present:
        w -= cfg.pinnacle_present_penalty
    w *= cfg.market_weight_mult.get(market, 1.0)
    # Stor oenighet betyder oftare att modellen saknar info än att det finns edge.
    gap = abs(logit(p_model) - logit(p_market))
    if gap > cfg.disagree_start:
        frac = min(1.0, (gap - cfg.disagree_start) / (cfg.disagree_full - cfg.disagree_start))
        w = w - frac * (w - cfg.w_model_min)
    return max(cfg.w_model_min, min(1.0, w))


def blend(p_model: float, p_market: float | None, w: float) -> float:
    if p_market is None:
        return p_model
    return inv_logit(w * logit(p_model) + (1 - w) * logit(p_market))


@dataclass
class SettledLine:
    match_id: str
    market: str
    p: float          # den blandade sannolikheten innan kalibrering
    outcome: int      # 1 = över gick in


@dataclass
class LevelCalibration:
    offset: dict[str, float]          # logit-förskjutning per marknad
    n_lines: dict[str, int]
    n_matches: dict[str, int]

    def apply(self, market: str, p: float) -> float:
        return inv_logit(logit(p) + self.offset.get(market, 0.0))


def fit_level_calibration(lines: Iterable[SettledLine], cfg: CalibrationConfig
                          ) -> LevelCalibration:
    """Nivåkalibrering: en logit-förskjutning per marknad, krympt mot 0.

    offset = Σ(y − p) / (Σ p(1−p) + k · p̄(1−p̄))
    (ett Newtonsteg med en prior som motsvarar k linjer). Lutningen justeras inte.
    Antal unika matcher rapporteras: det är den effektiva urvalsstorleken som
    avgör hur mycket man ska lita på förskjutningen, inte antalet linjer.
    """
    by_m: dict[str, list[SettledLine]] = defaultdict(list)
    for l in lines:
        by_m[l.market].append(l)
    off, n_l, n_m = {}, {}, {}
    for m, ls in by_m.items():
        resid = sum(l.outcome - l.p for l in ls)
        info = sum(l.p * (1 - l.p) for l in ls)
        pbar = sum(l.p for l in ls) / len(ls)
        o = resid / (info + cfg.shrink_k * pbar * (1 - pbar))
        off[m] = max(-cfg.max_abs_offset, min(cfg.max_abs_offset, o))
        n_l[m] = len(ls)
        n_m[m] = len({l.match_id for l in ls})
    return LevelCalibration(off, n_l, n_m)


def cluster_level_bias(lines: Iterable[SettledLine]) -> dict[str, tuple[float, float]]:
    """Medelfel (y − p) per marknad med standardfel klustrat per match.

    Visar om ett nivåfel är verkligt eller brus från att linjerna hänger ihop.
    """
    by_m: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for l in lines:
        by_m[l.market][l.match_id].append(l.outcome - l.p)
    out = {}
    for m, clusters in by_m.items():
        n = sum(len(v) for v in clusters.values())
        mean = sum(sum(v) for v in clusters.values()) / n
        G = len(clusters)
        if G < 2:
            out[m] = (mean, float("nan"))
            continue
        s = sum((sum(v) - len(v) * mean) ** 2 for v in clusters.values())
        se = math.sqrt(G / (G - 1) * s) / n
        out[m] = (mean, se)
    return out
