"""Backtest F1–F2: per framträdande (M0, som player_model i dag) mot per 90 med Empirical Bayes (M1).

Indata: en mapp med små matchutdrag (en JSON per match: lg, id, date, teams{tid: [{id, n, s, min, pos, shots,
sot, fouls}]}), t.ex. hämtade ur ESPN:s summary. Allt räknas i tidsordning: varje prognos använder bara
matcher före avspark (rullande tillstånd, uppdateras efter matchen).

Bara startande utespelare prognostiseras (som i produktionen: bekräftad elva). Båda modellerna använder samma
NB-form och ingen matchkontext (lagets väntade mål), så skillnaden är takten och minuterna.
Utvärdering: log-loss och Brier rå samt efter Platt (a + b·logit p) skattad på valideringsperioden,
parad skillnad med bootstrap per match.

    python tools/backtest_per90.py --dir utdrag/ --val 2026-09-15 --test 2026-10-16 --out rapport.md
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from propsbot.player_model import nb_over  # noqa: E402
from propsbot.quant import calibration, evaluate  # noqa: E402
from propsbot.quant.fb_minutes import Status, expected_minutes  # noqa: E402
from propsbot.quant import fb_context as fc  # noqa: E402
from propsbot.quant.fb_rates import M_PRIOR, position_group, shrunk_rate  # noqa: E402

STATS = {"shots": "shots", "sot": "shots_on_target", "fouls": "fouls"}
SHAPE = {"shots": 6.0, "sot": 10.0, "fouls": 8.0}
LINES = {"shots": (0.5, 1.5, 2.5), "sot": (0.5, 1.5), "fouls": (0.5, 1.5)}
# M0 = player_model.PlayerModel: senaste 8 lagmatcher, halveringstid 5, inhopp 0,35, prior 3 framträdanden
M0_N, M0_HL, M0_SUB, M0_PRIOR = 8, 5.0, 0.35, 3.0


def _f(x) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def load(d: str) -> list[dict]:
    ms = [json.load(open(f, encoding="utf-8")) for f in glob.glob(str(Path(d) / "*.json"))]
    return sorted(ms, key=lambda m: (m["date"], str(m["id"])))


class State:
    def __init__(self):
        self.team_hist = defaultdict(list)      # tid -> [match players list] (nyaste sist)
        self.player = defaultdict(list)         # pid -> [{min, s, pos, shots, sot, fouls}] (nyaste sist)
        self.pos_acc = defaultdict(lambda: defaultdict(float))   # (lg, grupp) -> {min, stat...}
        self.conc = defaultdict(list)            # tid -> [{stat: medgivet}] (nyaste sist)
        self.lg_conc = defaultdict(lambda: defaultdict(float))   # lg -> {n, stat...}

    def m0(self, tid: str, name_id: str, stat: str) -> float | None:
        hist = self.team_hist[tid][-M0_N:][::-1]
        if len(hist) < 3:
            return None
        acc = {"apps": 0.0, "x": 0.0}
        tot_team = 0.0
        tot_w = 0.0
        for age, players in enumerate(hist):
            w_age = 0.5 ** (age / M0_HL)
            tot_w += w_age
            for p in players:
                if not (p["s"] or (p.get("min") or 0) > 0):
                    continue
                tot_team += w_age * _f(p.get(stat))
                if p["id"] == name_id:
                    acc["apps"] += w_age * (1.0 if p["s"] else M0_SUB)
                    acc["x"] += w_age * _f(p.get(stat))
        team_rate = tot_team / tot_w / 11.0
        return (acc["x"] + team_rate * M0_PRIOR) / (acc["apps"] + M0_PRIOR)

    def group(self, pid: str, today_pos: str | None) -> str | None:
        g = position_group(today_pos)
        if g:
            return g
        cnt = defaultdict(int)
        for r in self.player[pid]:
            gg = position_group(r.get("pos"))
            if gg:
                cnt[gg] += 1
        return max(cnt, key=cnt.get) if cnt else None

    def prior90(self, lg: str, grp: str | None, stat: str) -> float | None:
        for key in ((lg, grp), (lg, "*")):
            a = self.pos_acc.get(key)
            if a and a["min"] >= 900:
                return a[stat] * 90.0 / a["min"]
        return None

    def m1(self, pid: str, lg: str, grp: str | None, stat: str, m_prior: float) -> float | None:
        prior = self.prior90(lg, grp, stat)
        if prior is None:
            return None
        hist = self.player[pid][::-1]
        rows = [{"min": r.get("min") or 0.0, "n": _f(r.get(stat)), "age": i} for i, r in enumerate(hist)]
        rate, _ = shrunk_rate(rows, prior, m_prior)
        e_min = expected_minutes([(r["s"], r.get("min")) for r in hist], Status.CONFIRMED_XI)
        return rate * e_min / 90.0

    def opp(self, lg: str, opp_tid: str | None, stat: str) -> float:
        a = self.lg_conc.get(lg)
        if not opp_tid or not a or a["n"] < 20:
            return 1.0
        return fc.opp_factor([c[stat] for c in self.conc[opp_tid][-8:][::-1]], a[stat] / a["n"])

    def update(self, m: dict) -> None:
        tids = list(m["teams"])
        if len(tids) == 2:
            for t, o in ((tids[0], tids[1]), (tids[1], tids[0])):
                c = {st: sum(_f(p.get(st)) for p in m["teams"][o]) for st in STATS}
                self.conc[t].append(c)
                a = self.lg_conc[m["lg"]]
                a["n"] += 1
                for st in STATS:
                    a[st] += c[st]
        for tid, ps in m["teams"].items():
            self.team_hist[tid].append(ps)
            for p in ps:
                if (p.get("min") or 0) <= 0:
                    continue
                self.player[p["id"]].append(p)
                g = position_group(p.get("pos")) if p["s"] else None
                g = g or self.group(p["id"], None)
                if g and g != "GK":
                    for key in ((m["lg"], g), (m["lg"], "*")):
                        a = self.pos_acc[key]
                        a["min"] += p["min"]
                        for st in STATS:
                            a[st] += _f(p.get(st))


def _ts(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def predictions(matches: list[dict], start: str, m_prior: dict | None = None, ctx: dict | None = None) -> list[dict]:
    """ctx (valfri): {"home": {match_id: hemmalagets id}, "sched": {lag_id: [ISO-tider, alla tävlingar]}}."""
    mp = m_prior or {s: M_PRIOR[STATS[s]] for s in STATS}
    st = State()
    out = []
    home = (ctx or {}).get("home", {})
    sched = {t: [_ts(x) for x in v] for t, v in ((ctx or {}).get("sched") or {}).items()}
    for m in matches:
        if m["date"] >= start:
            ko = _ts(m["date"])
            tids = list(m["teams"])
            for tid, ps in m["teams"].items():
                opp_tid = next((t for t in tids if t != tid), None)
                is_home = (home[str(m["id"])] == tid) if str(m["id"]) in home else None
                rest = fc.rest_days(sched.get(tid, []), ko)
                for p in ps:
                    if not p["s"] or p.get("min") is None or position_group(p.get("pos")) == "GK":
                        continue
                    grp = st.group(p["id"], p.get("pos"))
                    for s in STATS:
                        mu0 = st.m0(tid, p["id"], s)
                        mu1 = st.m1(p["id"], m["lg"], grp, s, mp[s])
                        if mu0 is None or mu1 is None:
                            continue
                        y = _f(p.get(s))
                        for ln in LINES[s]:
                            out.append({"date": m["date"], "mid": m["id"], "lg": m["lg"], "stat": s, "line": ln,
                                        "grp": grp, "y": 1 if y > ln else 0, "mu1": mu1, "cnt": y,
                                        "f_opp": st.opp(m["lg"], opp_tid, s), "home": is_home, "rest": rest,
                                        "p0": nb_over(max(mu0, 1e-4), ln, SHAPE[s]),
                                        "p1": nb_over(max(mu1, 1e-4), ln, SHAPE[s])})
        st.update(m)
    return out


def evaluate_rows(rows: list[dict], test: str) -> list[tuple]:
    res = []
    keys = sorted({(r["stat"], r["line"]) for r in rows})
    for k in keys:
        val = [r for r in rows if (r["stat"], r["line"]) == k and r["date"] < test]
        te = [r for r in rows if (r["stat"], r["line"]) == k and r["date"] >= test]
        if len(val) < 200 or len(te) < 200:
            continue
        y = [r["y"] for r in te]
        line = [k, len(te), sum(y) / len(y)]
        cal = {}
        for m in ("p0", "p1"):
            pr = calibration.platt_fit([r[m] for r in val], [r["y"] for r in val])
            cal[m] = calibration.platt_apply(pr, [r[m] for r in te])
            line += [evaluate.logloss([r[m] for r in te], y), evaluate.logloss(cal[m], y)]
        ll = lambda p, yy: -(yy * math.log(min(max(p, 1e-6), 1 - 1e-6)) + (1 - yy) * math.log(1 - min(max(p, 1e-6), 1 - 1e-6)))
        diffs = [ll(cal["p1"][i], r["y"]) - ll(cal["p0"][i], r["y"]) for i, r in enumerate(te)]
        ci = evaluate.boot_ci(diffs, [r["mid"] for r in te], n=1000)
        line += [sum(diffs) / len(diffs), ci]
        res.append(tuple(line))
    return res


GRID = {"e_opp": (0.0, 0.25, 0.5, 0.75, 1.0), "h": (0.0, 0.05, 0.1, 0.15), "s": (0.0, 0.03, 0.06, 0.1)}


def _p_ctx(r: dict, e_opp: float, h: float, s_: float) -> float:
    mu = fc.apply(r["mu1"], {"opp": r["f_opp"], "home": fc.home_factor(r["home"], h),
                             "rest": fc.rest_factor(r["rest"], s_)}, {"opp": e_opp, "home": 1.0, "rest": 1.0})
    return nb_over(max(mu, 1e-4), r["line"], SHAPE[r["stat"]])


def context_eval(rows: list[dict], test: str) -> list[tuple]:
    """Per stat: välj (e_opp, h, s) på perioden före test (log-loss), pröva på test mot M1 (båda efter Platt)."""
    import itertools
    out = []
    for stat in STATS:
        val = [r for r in rows if r["stat"] == stat and r["date"] < test]
        te = [r for r in rows if r["stat"] == stat and r["date"] >= test]
        if len(val) < 500 or len(te) < 500:
            continue
        yv = [r["y"] for r in val]
        best = min(itertools.product(*GRID.values()),
                   key=lambda g: evaluate.logloss([_p_ctx(r, *g) for r in val], yv))
        res = [stat, best]
        for ln in LINES[stat]:
            v = [r for r in val if r["line"] == ln]
            t = [r for r in te if r["line"] == ln]
            if len(v) < 200 or len(t) < 200:
                continue
            y = [r["y"] for r in t]
            c1 = calibration.platt_apply(calibration.platt_fit([r["p1"] for r in v], [r["y"] for r in v]), [r["p1"] for r in t])
            pc_v = [_p_ctx(r, *best) for r in v]
            c2 = calibration.platt_apply(calibration.platt_fit(pc_v, [r["y"] for r in v]), [_p_ctx(r, *best) for r in t])
            ll = lambda p, yy: -(yy * math.log(min(max(p, 1e-6), 1 - 1e-6)) + (1 - yy) * math.log(1 - min(max(p, 1e-6), 1 - 1e-6)))
            d = [ll(c2[i], r["y"]) - ll(c1[i], r["y"]) for i, r in enumerate(t)]
            res.append((ln, len(t), evaluate.logloss(c1, y), evaluate.logloss(c2, y), sum(d) / len(d),
                        evaluate.boot_ci(d, [r["mid"] for r in t], n=1000)))
        out.append(tuple(res))
    return out


def context_report(rows: list[dict], test: str) -> str:
    L = ["", "## Matchkontext (F4) ovanpå M1", "",
         "Elasticiteter valda på perioden före test: e_opp (motståndarens medgivna), h (hemma +h / borta 1/(1+h)), "
         "s (avdrag vid ≤ 3,5 dagars vila).", "",
         "| Marknad | vald (e_opp, h, s) | n test | M1 Platt | M1 + kontext Platt | Δ | 95 % CI |", "|---|---|---|---|---|---|---|"]
    for stat, best, *lines in context_eval(rows, test):
        for ln, n, l1, l2, d, ci in lines:
            L.append(f"| {STATS[stat]} > {ln} | {best} | {n} | {l1:.4f} | {l2:.4f} | {d:+.4f} | {ci[0]:+.4f} … {ci[1]:+.4f} |")
    return "\n".join(L)


def report(rows: list[dict], test: str, n_matches: int) -> str:
    L = ["# Backtest per 90 (F1–F2) mot per framträdande", "",
         f"{n_matches} matcher, {len(rows)} prognoser (startande utespelare). Test från {test}; Platt skattad före.", "",
         "| Marknad | n test | utfall | M0 rå | M0 Platt | M1 rå | M1 Platt | Δ (M1−M0, Platt) | 95 % CI |",
         "|---|---|---|---|---|---|---|---|---|"]
    for (st, ln), n, base, l0, c0, l1, c1, d, ci in evaluate_rows(rows, test):
        L.append(f"| {STATS[st]} > {ln} | {n} | {base:.1%} | {l0:.4f} | {c0:.4f} | {l1:.4f} | {c1:.4f} | {d:+.4f} | {ci[0]:+.4f} … {ci[1]:+.4f} |")
    L += ["", "Negativt Δ = per 90-modellen bättre. CI per match (bootstrap)."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--val", default="2026-09-15")
    ap.add_argument("--test", default="2026-10-16")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--context", type=Path, help="JSON med hemmalag och lagens spelscheman (F4)")
    a = ap.parse_args(argv)
    ms = load(a.dir)
    ctx = json.loads(a.context.read_text(encoding="utf-8")) if a.context else None
    rows = predictions(ms, a.val, ctx=ctx)
    txt = report(rows, a.test, len(ms))
    if ctx:
        txt += context_report(rows, a.test)
    if a.out:
        a.out.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
