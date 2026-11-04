"""Is the bot actually finding +EV? Statistics with confidence intervals.

Three levels of evidence, from fastest to slowest:

1. CLV (closing line value) of bets: did the market move toward our price before puck
   drop? Per-bet CLV has a standard deviation of only a few percent, so a real edge
   shows up after roughly 50-150 bets. This is the primary verdict.
2. Calibration of the whole leg log: every player/line the bot evaluated is graded
   (hundreds per night), comparing the model, the market consensus and the blend by
   log loss. This says whether the model adds information, within days.
3. ROI: the profit itself. Each bet at ~2.00 odds has a standard deviation of ~1 unit,
   so a 5% edge needs ~1,500 bets to be statistically visible. It is reported with its
   confidence interval, but it is the slowest and noisiest signal.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

Z = 1.96


def mean_se(xs: Sequence[float]) -> tuple[float | None, float | None, int]:
    n = len(xs)
    if n == 0:
        return None, None, 0
    m = sum(xs) / n
    if n < 2:
        return m, None, n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var / n), n


def needed_n(mean: float | None, se: float | None, n: int) -> int | None:
    """Sample size at which `mean` would be ~2 standard errors from zero."""
    if not mean or not se or n < 2 or mean <= 0:
        return None
    sd = se * math.sqrt(n)
    return math.ceil((Z * sd / mean) ** 2)


def _summary(xs: Sequence[float]) -> dict[str, Any]:
    m, se, n = mean_se(xs)
    return {
        "n": n,
        "mean": m,
        "se": se,
        "t": (m / se) if (m is not None and se) else None,
        "lo": (m - Z * se) if (m is not None and se) else None,
        "hi": (m + Z * se) if (m is not None and se) else None,
        "needed": needed_n(m, se, n),
    }


def bet_validation(bets: Iterable[dict[str, Any]]) -> dict[str, Any]:
    bets = list(bets)
    settled = [b for b in bets if b["status"] in ("won", "lost", "push")]
    returns = [(b["profit_units"] or 0) / b["units"] for b in settled if b["units"]]
    staked = sum(b["units"] for b in settled)
    profit = sum(b["profit_units"] or 0 for b in settled)
    return {
        "bets": len(bets),
        "settled": len(settled),
        "units_staked": staked,
        "profit_units": profit,
        "roi_weighted": profit / staked if staked else None,
        "roi": _summary(returns),
        "expected_roi": _summary([b["edge"] for b in settled if b.get("edge") is not None]),
        "clv": _summary([b["clv"] for b in bets if b.get("clv") is not None]),
        "kambi_clv": _summary([b["kambi_clv"] for b in bets if b.get("kambi_clv") is not None]),
        "price_clv": _summary([b["price_clv"] for b in bets if b.get("price_clv") is not None]),
    }


def edge_buckets(bets: Iterable[dict[str, Any]], edges=(0.05, 0.08, 0.12)) -> list[dict[str, Any]]:
    """Do bigger edges produce bigger CLV/ROI? (They should, if the edges are real.)"""
    bounds = list(edges) + [float("inf")]
    rows = []
    bets = [b for b in bets if b.get("edge") is not None]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        grp = [b for b in bets if lo <= b["edge"] < hi]
        settled = [b for b in grp if b["status"] in ("won", "lost", "push") and b["units"]]
        clv = [b["clv"] for b in grp if b.get("clv") is not None]
        rows.append({
            "bucket": f"{lo:.0%}-{hi:.0%}" if hi != float("inf") else f"{lo:.0%}+",
            "n": len(grp),
            "avg_edge": sum(b["edge"] for b in grp) / len(grp) if grp else None,
            "avg_clv": sum(clv) / len(clv) if clv else None,
            "roi": (sum(b["profit_units"] or 0 for b in settled) / sum(b["units"] for b in settled)) if settled else None,
            "settled": len(settled),
        })
    return rows


def _log_loss(p: float, y: int) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def leg_validation(legs: Iterable[dict[str, Any]], min_edge: float) -> dict[str, Any]:
    """Grade every evaluated leg (one side per player/line to avoid double counting)."""
    by_line: dict[tuple[int, int, float], dict[str, Any]] = {}
    for r in legs:
        k = (r["game_id"], r["player_id"], r["line"])
        if k not in by_line or r["side"] == "over":
            by_line[k] = r
    rows = list(by_line.values())

    sources = ("close_p_model", "close_p_market", "close_p_fair", "close_p_kambi")
    common = [r for r in rows if all(r.get(c) is not None for c in sources)]
    scores = {}
    for c in sources:
        if common:
            scores[c] = {
                "log_loss": sum(_log_loss(r[c], r["outcome"] == "won") for r in common) / len(common),
                "brier": sum((r[c] - (r["outcome"] == "won")) ** 2 for r in common) / len(common),
            }

    calib = []
    fair_rows = [r for r in rows if r.get("close_p_fair") is not None]
    for i in range(10):
        lo, hi = i / 10, (i + 1) / 10
        grp = [r for r in fair_rows if lo <= r["close_p_fair"] < hi or (i == 9 and r["close_p_fair"] == 1.0)]
        if grp:
            calib.append({"bucket": f"{i * 10}-{i * 10 + 10}%", "n": len(grp),
                          "predicted": sum(r["close_p_fair"] for r in grp) / len(grp),
                          "actual": sum(r["outcome"] == "won" for r in grp) / len(grp)})

    # Every leg that showed >= min_edge at some scan and passed the shared rules ("would have bet").
    flagged = [r for r in legs if r.get("max_edge_passed") and (r.get("max_edge") or 0) >= min_edge]
    flag_clv = [r["max_edge_odds"] * r["close_p_market"] - 1 for r in flagged if r.get("close_p_market") is not None]
    flag_ret = [(r["max_edge_odds"] - 1) if r["outcome"] == "won" else -1.0 for r in flagged]
    return {
        "graded_lines": len(rows),
        "compared": len(common),
        "scores": scores,
        "calibration": calib,
        "flagged_clv": _summary(flag_clv),
        "flagged_roi": _summary(flag_ret),
    }


def verdict(bets: dict[str, Any], legs: dict[str, Any] | None, min_bets: int = 30) -> list[str]:
    out = []
    clv = bets["clv"]
    if clv["n"] < min_bets:
        out.append(f"⏳ CLV: {clv['n']} bet(s) with a closing price; a verdict needs at least {min_bets}.")
    elif clv["t"] is not None and clv["t"] >= 2:
        out.append(f"✅ Beating the closing line: avg CLV {clv['mean']:+.1%} (95% CI {clv['lo']:+.1%} to "
                   f"{clv['hi']:+.1%}, t={clv['t']:.1f}). The bot is finding real edge.")
    elif clv["t"] is not None and clv["t"] <= -2:
        out.append(f"❌ Losing to the closing line: avg CLV {clv['mean']:+.1%} (t={clv['t']:.1f}). "
                   "The edges are not real; pause live betting and retune.")
    else:
        need = f"; at this rate ~{clv['needed']} bets are needed" if clv["needed"] else ""
        mean = f"{clv['mean']:+.1%}" if clv["mean"] is not None else "n/a"
        out.append(f"⏳ CLV not yet conclusive: avg {mean} over {clv['n']} bets{need}.")
    roi = bets["roi"]
    if roi["n"]:
        rng = f" (95% CI {roi['lo']:+.1%} to {roi['hi']:+.1%})" if roi["lo"] is not None else ""
        exp = bets["expected_roi"]["mean"]
        exp_txt = f", expected {exp:+.1%}" if exp is not None else ""
        out.append(f"   ROI {roi['mean']:+.1%}{rng} over {roi['n']} settled bets{exp_txt}. "
                   f"ROI is noisy: ~{roi['needed'] or 1500}+ bets before it is significant on its own.")
    if legs and legs["scores"]:
        sc = legs["scores"]
        m, k, f = sc["close_p_model"]["log_loss"], sc["close_p_market"]["log_loss"], sc["close_p_fair"]["log_loss"]
        out.append(f"   Over {legs['compared']} graded lines, log loss: model {m:.4f} | references {k:.4f} | "
                   f"blend {f:.4f} | Kambi {sc['close_p_kambi']['log_loss']:.4f} (lower is better).")
        if f < k:
            out.append("   ✅ Blending the model improves on the market references: the model adds information.")
        else:
            out.append("   ⚠ The blend is not beating the references: consider lowering model_weight.")
    return out
