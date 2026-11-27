"""Fas 2: kronologiska walk-forward-veck utan läckage.

Rader grupperas per match (group_key) så att korrelerade ben (flera linjer/marknader i samma match) alltid hamnar
i samma del. Grupperna sorteras på sin tidigaste tid och delas i n_folds + 2 lika stora block; veck i tränar på
block[:i+1] (expanderande) eller block[i] (rullande), validerar på block[i+1] och testar på block[i+2].
Embargo: träningsgrupper med tid ≥ val_start − embargo släpps (likaså val-grupper nära test_start),
så att t.ex. samma NBA-kväll inte delas mellan träning och validering.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


class LeakageError(AssertionError):
    pass


@dataclass
class Fold:
    train: list[int]
    val: list[int]
    test: list[int]


def _ts(r: dict, key: str) -> float:
    v = r.get(key)
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise ValueError(f"rad saknar {key}")
    return float(v)


def splits(rows: list[dict], n_folds: int = 3, ts_key: str = "ts", group_key: str = "match_id",
           embargo_s: float = 6 * 3600, expanding: bool = True, min_train: int = 1) -> list[Fold]:
    groups: dict = {}
    for i, r in enumerate(rows):
        g = r.get(group_key)
        groups.setdefault(g if g is not None else f"_rad{i}", []).append(i)
    gts = {g: min(_ts(rows[i], ts_key) for i in ix) for g, ix in groups.items()}
    order = sorted(groups, key=lambda g: (gts[g], str(g)))
    nb = n_folds + 2
    if len(order) < nb:
        raise ValueError(f"för få grupper ({len(order)}) för {n_folds} veck")
    bounds = [round(j * len(order) / nb) for j in range(nb + 1)]
    blocks = [order[bounds[j]:bounds[j + 1]] for j in range(nb)]

    def gmax(g):
        return max(_ts(rows[i], ts_key) for i in groups[g])

    folds = []
    for f in range(n_folds):
        tr_g = [g for b in (blocks[:f + 1] if expanding else blocks[f:f + 1]) for g in b]
        va_g, te_g = blocks[f + 1], blocks[f + 2]
        va_start = min(gts[g] for g in va_g)
        te_start = min(gts[g] for g in te_g)
        tr_g = [g for g in tr_g if gmax(g) < va_start - embargo_s]
        va_g = [g for g in va_g if gmax(g) < te_start - embargo_s]
        fold = Fold(sorted(i for g in tr_g for i in groups[g]), sorted(i for g in va_g for i in groups[g]),
                    sorted(i for g in te_g for i in groups[g]))
        if len(fold.train) >= min_train and fold.val:
            folds.append(fold)
    return folds


def assert_no_leak(rows: list[dict], fold: Fold, ts_key: str = "ts", group_key: str = "match_id",
                   feature_ts_key: str | None = "prognos_ts", market_ts_key: str | None = None) -> None:
    """Kastar LeakageError om tidsordning, gruppdisjunkthet eller feature-/marknadstider bryts."""
    parts = {"train": fold.train, "val": fold.val, "test": fold.test}
    ts = {k: [_ts(rows[i], ts_key) for i in v] for k, v in parts.items()}
    if ts["train"] and ts["val"] and not max(ts["train"]) < min(ts["val"]):
        raise LeakageError("träning överlappar validering i tid")
    if ts["val"] and ts["test"] and not max(ts["val"]) < min(ts["test"]):
        raise LeakageError("validering överlappar test i tid")
    seen: dict = {}
    for k, ix in parts.items():
        for i in ix:
            g = rows[i].get(group_key)
            if g is None:
                continue
            if seen.setdefault(g, k) != k:
                raise LeakageError(f"grupp {g} finns i både {seen[g]} och {k}")
    for i in (j for v in parts.values() for j in v):
        r = rows[i]
        for key in (feature_ts_key, market_ts_key):
            v = r.get(key) if key else None
            if v is not None and not (isinstance(v, float) and math.isnan(v)) and float(v) > _ts(r, ts_key):
                raise LeakageError(f"rad {i}: {key} efter {ts_key}")
