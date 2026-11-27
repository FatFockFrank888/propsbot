"""Fas 6: ¼ Kelly med tak per spel, ett ben per spelare och familj, korrelationsavdrag och tak per match.

Används i skugga (kelly_u bredvid tiers units). Samma formel som decision.kelly_stake.
"""
from __future__ import annotations

import math
from collections import defaultdict

FAMILY = {"shots_on_target": "shots"}        # skott + skott på mål = samma familj (som decision.MARKET_FAMILY)
MANUAL_REVIEW = "MANUAL_REVIEW"


def stake(p: float, odds: float, frac: float = 0.25, cap: float = 0.02) -> float:
    if p is None or odds is None or not (0.0 < p < 1.0) or not math.isfinite(odds) or odds <= 1.0:
        return 0.0
    b = odds - 1.0
    f = (p * b - (1.0 - p)) / b
    return max(0.0, min(cap, f * frac))


def ev(p: float, odds: float) -> float:
    return p * odds - 1.0


def units(st: float, unit: float = 0.01, max_u: int = 2) -> int:
    """Insats -> hela units (avrundat), högst max_u. 0 om insatsen < halv unit."""
    return int(min(max_u, math.floor(st / unit + 0.5)))


def portfolio(bets: list[dict], frac: float = 0.25, cap: float = 0.02, per_match_cap: float = 0.035,
              corr_mult: float = 0.65, max_p_gap: float | None = 0.14) -> list[dict]:
    """bets: {match_id, player_id, market, p, odds, [p_market], [min_ev], [kelly_mult], [playable]}.
    Returnerar nya dictar med stake och status (OK / UNDER_EV / SAMMA_SPELARE / MANUAL_REVIEW / EJ_SPELBAR)."""
    out = []
    for b in bets:
        d = dict(b)
        d["ev"] = ev(b["p"], b["odds"])
        d["stake"], d["status"] = 0.0, "OK"
        if not b.get("playable", True):
            d["status"] = "EJ_SPELBAR"
        elif max_p_gap is not None and b.get("p_market") is not None and b["p"] - b["p_market"] > max_p_gap:
            d["status"] = MANUAL_REVIEW
        elif d["ev"] < b.get("min_ev", 0.0) or d["ev"] <= 0:
            d["status"] = "UNDER_EV"
        else:
            d["stake"] = stake(b["p"], b["odds"], frac * b.get("kelly_mult", 1.0), cap)
        out.append(d)
    best: dict = {}
    for d in out:
        if d["stake"] <= 0:
            continue
        k = (d["match_id"], d["player_id"], FAMILY.get(d["market"], d["market"]))
        if k not in best or d["ev"] > best[k]["ev"]:
            best[k] = d
    keep = {id(d) for d in best.values()}
    for d in out:
        if d["stake"] > 0 and id(d) not in keep:
            d["stake"], d["status"] = 0.0, "SAMMA_SPELARE"
    per: dict = defaultdict(list)
    for d in out:
        if d["stake"] > 0:
            per[d["match_id"]].append(d)
    for ds in per.values():
        ds.sort(key=lambda x: -x["ev"])
        for i, d in enumerate(ds):
            d["stake"] *= corr_mult ** min(i, 1)
        tot = sum(d["stake"] for d in ds)
        if tot > per_match_cap:
            for d in ds:
                d["stake"] *= per_match_cap / tot
    return out
