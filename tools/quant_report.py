"""Kvantrapport (docs/PLAN.md fas 7): walk-forward-utvärdering av marknad, modell, kalibrering och residual,
NB-spridning per marknad och tiers insats mot ¼ Kelly. Läser bara filer, skriver en markdown-sammanfattning.

    python tools/quant_report.py --ledger nba_modelltest.json --tiers tiers.json --out rapport.md
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from propsbot.quant import calibration, dataset, evaluate, kelly, residual  # noqa: E402
from propsbot.quant.devig import base_logit  # noqa: E402
from propsbot.quant.dispersion import fit_nb_r  # noqa: E402
from propsbot.quant.walk_forward import assert_no_leak, splits  # noqa: E402

FEATS = ["d_modell", "f_b2b", "f_minuter_bas", "f_mot", "f_tempo", "f_anv", "traff_l10", "traff_sasong"]
L2_GRID = (10.0, 50.0, 200.0, 1000.0)


def _prep_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if math.isnan(r["p_market"]):
            continue
        f = r["features"]
        pm = r["p_model"]
        f["d_modell"] = base_logit(pm) - base_logit(r["p_market"]) if not math.isnan(pm) else float("nan")
        out.append(r)
    return out


def _X(rows, names):
    return np.array(dataset.matrix(rows, names), float).reshape(len(rows), len(names))


def walk_forward(rows: list[dict], n_folds: int = 3) -> dict:
    folds = splits(rows, n_folds=n_folds, embargo_s=6 * 3600)
    res = defaultdict(list)          # namn -> [(n, logloss, brier)] per veck
    pooled = defaultdict(lambda: ([], []))
    chosen = []
    for f in folds:
        assert_no_leak(rows, f)
        tr, va, te = ([rows[i] for i in ix] for ix in (f.train, f.val, f.test))
        y_te = np.array([r["y"] for r in te], float)
        preds = {"marknad": np.array([r["p_market"] for r in te])}
        pmod = np.array([r["p_model"] for r in te])
        if not np.isnan(pmod).any():
            preds["modell (rå)"] = pmod
        pf = np.array([r["p_final"] for r in te])
        if not np.isnan(pf).any():
            preds["slutlig p (bokförd)"] = pf
        # Platt på marknaden (nivåfel), prior mot identitet värd 100 obs
        trva = tr + va
        pl = calibration.platt_fit([r["p_market"] for r in trva], [r["y"] for r in trva], prior_n=100)
        preds["marknad + Platt"] = calibration.platt_apply(pl, preds["marknad"])
        # residual: l2 väljs på val, sedan omträning på train+val
        best = None
        for l2 in L2_GRID:
            m = residual.fit(_X(tr, FEATS), [r["y"] for r in tr], [r["p_market"] for r in tr], l2=l2)
            ll = evaluate.logloss(residual.predict(m, _X(va, FEATS), [r["p_market"] for r in va]), [r["y"] for r in va])
            if best is None or ll < best[0]:
                best = (ll, l2)
        chosen.append(best[1])
        m = residual.fit(_X(trva, FEATS), [r["y"] for r in trva], [r["p_market"] for r in trva], l2=best[1])
        preds["residual (utfall)"] = residual.predict(m, _X(te, FEATS), [r["p_market"] for r in te])
        cl = [r for r in trva if not math.isnan(r["p_close"])]
        if len(cl) > 50:
            mc = residual.fit(_X(cl, FEATS), None, [r["p_market"] for r in cl], l2=50.0, target="close",
                              p_close=[r["p_close"] for r in cl])
            preds["residual (mål: stängning)"] = residual.predict(mc, _X(te, FEATS), [r["p_market"] for r in te])
        for k, p in preds.items():
            res[k].append((len(te), evaluate.logloss(p, y_te), evaluate.brier(p, y_te)))
            pooled[k][0].extend(p.tolist())
            pooled[k][1].extend(y_te.tolist())
    return {"folds": folds, "res": res, "pooled": pooled, "l2": chosen}


def clv_block(rows: list[dict]) -> dict:
    v = [(evaluate.clv_pp(r["p_close"], r["odds"]), r["match_id"]) for r in rows if not math.isnan(r["p_close"])]
    v = [(x, g) for x, g in v if x is not None]
    if not v:
        return {}
    xs, gs = zip(*v)
    return {"n": len(xs), "mean": st.mean(xs), "ci": evaluate.boot_ci(xs, gs)}


def market_drift(rows: list[dict]) -> dict:
    """Hur mycket av rörelsen mot stängning förutsäger modellens avvikelse? (korrelation d_modell ~ Δlogit)."""
    pts = [(r["features"]["d_modell"], base_logit(r["p_close"]) - base_logit(r["p_market"])) for r in rows
           if not math.isnan(r["p_close"]) and not math.isnan(r["features"]["d_modell"])]
    if len(pts) < 30:
        return {}
    a, b = np.array(pts).T
    if a.std() < 1e-12 or b.std() < 1e-12:
        return {}
    return {"n": len(pts), "corr": float(np.corrcoef(a, b)[0, 1]), "slope": float(np.polyfit(a, b, 1)[0])}


def dispersion(bets: list[dict]) -> dict:
    by = defaultdict(lambda: ([], []))
    for b in bets:
        mu, y = b.get("vantat_faktorer"), b.get("utfall")
        if isinstance(mu, (int, float)) and isinstance(y, (int, float)) and mu > 0 and b.get("status") != "struken":
            by[b.get("marknad")][0].append(mu)
            by[b.get("marknad")][1].append(y)
    # unika prestationer: ett utfall per spelare/match/marknad
    return {m: (len(mu), fit_nb_r(mu, y, prior_r=10, prior_n=0)) for m, (mu, y) in by.items() if len(mu) >= 30}


def tiers_vs_kelly(tb: list[dict]) -> dict:
    rows = []
    for b in tb:
        p, o, u = b.get("sannolikhet"), b.get("odds"), b.get("units")
        if p and o and u:
            rows.append((b, u * (b.get("unit_pct") or 0.01), kelly.stake(p, o)))
    out = {"n": len(rows), "bands": []}
    for lo, hi in ((1.4, 2.0), (2.0, 3.0), (3.0, 6.6)):
        g = [(s, k) for b, s, k in rows if lo <= b["odds"] < hi]
        if g:
            out["bands"].append((lo, hi, len(g), st.mean(s for s, _ in g) * 100, st.mean(k for _, k in g) * 100,
                                 sum(1 for s, k in g if s > k) / len(g)))
    per = defaultdict(float)
    for b, s, _ in rows:
        per[(b.get("sport"), b.get("match_id"), (b.get("bokford") or 0) // 86400)] += s
    ex = sorted(per.values())
    out["match_exposure"] = {"matcher": len(ex), "median_pct": st.median(ex) * 100 if ex else None,
                             "max_pct": max(ex) * 100 if ex else None,
                             "andel_over_3_5": sum(1 for x in ex if x > 0.035) / len(ex) if ex else None}
    kel_u = Counter(kelly.units(k) for _, _, k in rows)
    out["kelly_units"] = dict(sorted(kel_u.items()))
    out["tier_units"] = dict(sorted(Counter(b["units"] for b, _, _ in rows).items()))
    return out


W_GRID = (0.0, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3)


def blend_p(r: dict, w0: float, key: str = "pm") -> float:
    """Samma regel som nba.coherent_blend: w = w0·dq, halverad när modellen avviker > 1 i logit."""
    pm = r.get(key)
    if pm is None:
        return r["pk"]
    lm, lk = base_logit(pm), base_logit(r["pk"])
    w = w0 * (r.get("dq") or 1.0) * (0.5 if abs(lm - lk) > 1.0 else 1.0)
    return 1 / (1 + math.exp(-(w * lm + (1 - w) * lk)))


def weight_grid(kal_rows: list[dict], key: str = "pm", n_folds: int = 4) -> dict:
    """Walk-forward över modellvikten w0 på kalibreringsloggen (alla ben, över-orienterade pm/pk/y)."""
    rows = [{"ts": r["avspark"], "prognos_ts": r.get("t0"), **r} for r in kal_rows
            if r.get("y") in (0, 1) and r.get("pk") is not None and r.get(key) is not None
            and r.get("avspark") is not None and (r.get("t0") or 0) <= r["avspark"]]
    if len({r.get("match_id") for r in rows}) < n_folds + 2:
        return {"n": len(rows), "folds": 0, "chosen": [], "logloss": {}, "vald_ci": (math.nan, math.nan)}
    folds = splits(rows, n_folds=n_folds, embargo_s=6 * 3600)
    tot = {w: [0.0, 0] for w in W_GRID}
    chosen, diffs = [], []
    for f in folds:
        assert_no_leak(rows, f)
        fit = [rows[i] for i in f.train + f.val]
        te = [rows[i] for i in f.test]
        best = min(W_GRID, key=lambda w: evaluate.logloss([blend_p(r, w, key) for r in fit], [r["y"] for r in fit]))
        chosen.append(best)
        y = [r["y"] for r in te]
        for w in W_GRID:
            tot[w][0] += evaluate.logloss([blend_p(r, w, key) for r in te], y) * len(te)
            tot[w][1] += len(te)
        for r in te:
            ll = lambda p: -(r["y"] * math.log(p) + (1 - r["y"]) * math.log(1 - p))
            diffs.append((ll(blend_p(r, best, key)) - ll(min(max(r["pk"], 1e-4), 1 - 1e-4)), r["match_id"]))
    ll = {w: s / n for w, (s, n) in tot.items() if n}
    xs, gs = zip(*diffs) if diffs else ((), ())
    return {"n": len(rows), "folds": len(folds), "chosen": chosen, "logloss": ll,
            "vald_ci": evaluate.boot_ci(xs, gs) if xs else (math.nan, math.nan)}


def report(ledger: Path | None, tiers: Path | None, sport: str = "nba", kalib: Path | None = None) -> str:
    L = [f"# Kvantrapport ({sport})", "", "Walk-forward (3 veck, grupperat per match, 6 h embargo). Test = osedd data i varje veck.", ""]
    if ledger:
        bets = json.loads(Path(ledger).read_text(encoding="utf-8"))
        bets = bets.get("bets", bets) if isinstance(bets, dict) else bets
        rows = _prep_rows(dataset.build(bets, sport))
        L += [f"Avgjorda unika ben med marknadens p: **{len(rows)}** (av {len(bets)} rader).", ""]
        if len(rows) >= 60:
            wf = walk_forward(rows)
            base = {i: v[1] for i, v in enumerate(wf["res"]["marknad"])}
            L += ["| Modell | n test | log-loss (poolad) | Brier | Δ log-loss mot marknad per veck |", "|---|---|---|---|---|"]
            for k, v in wf["res"].items():
                p, y = wf["pooled"][k]
                d = ", ".join(f"{x[1] - base[i]:+.4f}" for i, x in enumerate(v))
                L.append(f"| {k} | {len(y)} | {evaluate.logloss(p, y):.4f} | {evaluate.brier(p, y):.4f} | {d} |")
            L += ["", f"Vald ridge (l2) per veck: {wf['l2']}. Negativt Δ = bättre än marknaden.", ""]
        c = clv_block(rows)
        if c:
            L += [f"CLV mot skarp stängning: {c['mean']:+.2f} pe (95 % CI {c['ci'][0]:+.2f} … {c['ci'][1]:+.2f}, n = {c['n']}).", ""]
        md = market_drift(rows)
        if md:
            L += [f"Modellens avvikelse mot marknaden förutsäger stängningens rörelse: korrelation {md['corr']:+.3f}, "
                  f"lutning {md['slope']:+.3f} (n = {md['n']}). Lutning 0 = ingen information, 1 = marknaden går hela vägen till modellen.", ""]
        ds = dispersion(bets)
        if ds:
            L += ["NB-form r skattad ur (väntat, utfall), momentmetod:", "", "| Marknad | n | r̂ |", "|---|---|---|"]
            L += [f"| {m} | {n} | {r:.1f} |" for m, (n, r) in sorted(ds.items(), key=lambda x: -x[1][0])]
            L.append("")
    if kalib:
        import gzip
        op = gzip.open if str(kalib).endswith(".gz") else open
        with op(kalib, "rt", encoding="utf-8") as fh:
            kd = json.load(fh)
        kr = kd.get("rader", kd) if isinstance(kd, dict) else kd
        L += ["## Modellvikt (w0) walk-forward på kalibreringsloggen", "",
              "| Modell | n | veck | vald w0 per veck | Δ log-loss mot marknad: " + " · ".join(f"{w:g}" for w in W_GRID) + " | vald vs marknad, 95 % CI |",
              "|---|---|---|---|---|---|"]
        for key, name in (("pm", "spelarmodell"), ("pf", "faktormodell"), ("pb", "betygsmodell")):
            g = weight_grid(kr, key)
            if not g["logloss"]:
                continue
            b = g["logloss"][0.0]
            L.append(f"| {name} | {g['n']} | {g['folds']} | {g['chosen']} | "
                     + " · ".join(f"{g['logloss'][w] - b:+.4f}" for w in W_GRID)
                     + f" | {g['vald_ci'][0]:+.4f} … {g['vald_ci'][1]:+.4f} |")
        L.append("")
    if tiers:
        d = json.loads(Path(tiers).read_text(encoding="utf-8"))
        t = tiers_vs_kelly(d.get("bets", d) if isinstance(d, dict) else d)
        L += ["## Tiers insats mot ¼ Kelly (tak 2 %)", "", "| Odds | n | medel tier-insats % | medel ¼ Kelly % | andel över Kelly |",
              "|---|---|---|---|---|"]
        L += [f"| {lo:.1f}–{hi:.1f} | {n} | {s:.2f} | {k:.2f} | {a:.0%} |" for lo, hi, n, s, k, a in t["bands"]]
        me = t["match_exposure"]
        L += ["", f"Exponering per match och dag: median {me['median_pct']:.1f} %, max {me['max_pct']:.1f} %, "
              f"andel över 3,5 %: {me['andel_over_3_5']:.0%} ({me['matcher']} matcher).",
              f"Units i dag: {t['tier_units']}. Med ¼ Kelly (1u = 1 %, tak 2u): {t['kelly_units']}.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path)
    ap.add_argument("--tiers", type=Path)
    ap.add_argument("--sport", default="nba")
    ap.add_argument("--kalib", type=Path, help="nba_kalibrering.json(.gz) för viktanalysen")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    if not a.ledger and not a.tiers and not a.kalib:
        ap.error("ange --ledger, --tiers och/eller --kalib")
    txt = report(a.ledger, a.tiers, a.sport, a.kalib)
    if a.out:
        a.out.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
