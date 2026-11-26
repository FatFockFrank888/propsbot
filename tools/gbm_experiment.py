"""Fas 9 (docs/PLAN.md): LightGBM-residual mot linjär residual och marknad på NBA:s kalibreringslogg.

Walk-forward per match (quant.walk_forward), features ur loggen: modellens, faktormodellens och betygsmodellens
avvikelse mot marknaden i logit, dq, linje och marknad. Kräver lightgbm (ingår inte i botens krav).

    python tools/gbm_experiment.py --kalib nba_kalibrering.json.gz
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from propsbot.quant import evaluate, residual, residual_gbm  # noqa: E402
from propsbot.quant.devig import base_logit  # noqa: E402
from propsbot.quant.walk_forward import assert_no_leak, splits  # noqa: E402

MARKETS = ("points", "rebounds", "assists", "threes", "pr", "pra", "ra", "pa", "steals", "blocks")


def rows_from(kal: list[dict]) -> list[dict]:
    out = []
    for r in kal:
        if r.get("y") not in (0, 1) or r.get("pk") is None or r.get("avspark") is None:
            continue
        if (r.get("t0") or 0) > r["avspark"]:
            continue
        lk = base_logit(r["pk"])
        f = [base_logit(r["pm"]) - lk if r.get("pm") is not None else math.nan,
             base_logit(r["pf"]) - lk if r.get("pf") is not None else math.nan,
             base_logit(r["pb"]) - lk if r.get("pb") is not None else math.nan,
             r.get("dq") if r.get("dq") is not None else math.nan, r.get("linje") or math.nan, lk]
        f += [1.0 if r.get("marknad") == m else 0.0 for m in MARKETS]
        out.append({"ts": r["avspark"], "prognos_ts": r.get("t0"), "match_id": r["match_id"], "y": r["y"],
                    "pk": r["pk"], "x": f})
    return out


def run(rows: list[dict], n_folds: int = 4) -> dict:
    folds = splits(rows, n_folds=n_folds, embargo_s=6 * 3600)
    res = {"marknad": [], "linjär residual": [], "LightGBM": []}
    diffs = {"linjär residual": [], "LightGBM": []}
    trees = []
    for f in folds:
        assert_no_leak(rows, f)
        tr, va, te = ([rows[i] for i in ix] for ix in (f.train, f.val, f.test))
        X = lambda R: np.array([r["x"] for r in R], float)
        y = lambda R: np.array([r["y"] for r in R], float)
        p = lambda R: np.array([r["pk"] for r in R], float)
        lin = residual.fit(X(tr + va)[:, :4], y(tr + va), p(tr + va), l2=200.0)
        gbm = residual_gbm.fit(X(tr), y(tr), p(tr), X(va), y(va), p(va))
        trees.append(gbm.best_iteration or gbm.num_trees())
        preds = {"marknad": p(te), "linjär residual": residual.predict(lin, X(te)[:, :4], p(te)),
                 "LightGBM": residual_gbm.predict(gbm, X(te), p(te))}
        for k, v in preds.items():
            res[k].append((len(te), evaluate.logloss(v, y(te)), evaluate.brier(v, y(te))))
        for k in diffs:
            yy = y(te)
            ll = lambda q: -(yy * np.log(np.clip(q, 1e-6, 1 - 1e-6)) + (1 - yy) * np.log(1 - np.clip(q, 1e-6, 1 - 1e-6)))
            diffs[k] += list(zip((ll(preds[k]) - ll(preds["marknad"])).tolist(), [r["match_id"] for r in te]))
    ci = {k: evaluate.boot_ci([d for d, _ in v], [g for _, g in v]) for k, v in diffs.items() if v}
    return {"folds": len(folds), "res": res, "ci": ci, "trees": trees}


def report(rows: list[dict], out: dict) -> str:
    L = ["# Fas 9: LightGBM-residual (NBA kalibreringslogg)", "",
         f"{len(rows)} avgjorda ben, {len({r['match_id'] for r in rows})} matcher, {out['folds']} veck (per match, 6 h embargo).",
         f"Träd per veck (tidigt stopp): {out['trees']}.", "",
         "| Modell | log-loss per veck | poolad Δ mot marknad | 95 % CI (per match) |", "|---|---|---|---|"]
    base = out["res"]["marknad"]
    for k, v in out["res"].items():
        n = sum(a for a, _, _ in v)
        pooled = sum(a * b for a, b, _ in v) / n - sum(a * b for a, b, _ in base) / n
        ci = out["ci"].get(k)
        L.append(f"| {k} | " + ", ".join(f"{b:.4f}" for _, b, _ in v) + f" | {pooled:+.4f} | "
                 + (f"{ci[0]:+.4f} … {ci[1]:+.4f}" if ci else "–") + " |")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kalib", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    op = gzip.open if str(a.kalib).endswith(".gz") else open
    with op(a.kalib, "rt", encoding="utf-8") as fh:
        d = json.load(fh)
    rows = rows_from(d.get("rader", d) if isinstance(d, dict) else d)
    txt = report(rows, run(rows))
    if a.out:
        a.out.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
