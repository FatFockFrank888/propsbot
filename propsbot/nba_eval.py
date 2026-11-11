"""Utvärdering av NBA-kedjan på framåtriktad (osedd) data – bara det som faktiskt bokfördes vid spelets tid.

    python -m propsbot.nba_eval <lägesmapp>          # t.ex. state/ från data-grenen

Läser bokföringarna (nba_live.json, nba_bokforing_v2.json, nba_skugga_v2.json, nba_modelltest.json) och skriver
nba_utvardering.json + nba_utvardering.md i samma mapp. Ingenting räknas om retroaktivt: varje rad är en
prognos som gjordes före matchen, med de odds och sannolikheter som gällde då.

Begrepp
  * EV (edge i boten)  = p × odds − 1            (halvlinjer; heltalslinjer används inte – se GRANSKNING_NBA.md)
  * CLV (pe)           = 1/stängning − 1/odds    (samma bolag, samma linje; ett riktmärke, inte bevis för EV)
  * Brier / log loss   = modellens resp. marknadens sannolikhet för vår sida mot utfallet, på SAMMA spel
Oberoende: samma spelare, match och marknad räknas som EN prestation (linjer och bolag avdupliceras), och
konfidensintervall tas med block-bootstrap över speldagar (amerikansk tid) med fast seed.

Status per marknad (dokumenterade kriterier – konventioner, inte garantier):
  * insufficient_data : färre än MIN_OBS avgjorda unika prestationer med både modell- och marknadssannolikhet
  * degraded          : modellens Brier är signifikant sämre än marknadens (95 %-intervallet för skillnaden > 0)
                        eller CLV signifikant negativ
  * validated         : modellens Brier signifikant bättre än marknadens OCH CLV signifikant positiv
  * shadow            : övrigt – prognoser visas och bokförs, men räknas inte som bevisat
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGERS = {"live": "nba_live.json", "spel": "nba_bokforing_v2.json", "skugga": "nba_skugga_v2.json",
           "modelltest": "nba_modelltest.json"}
MIN_OBS = 30
SEED = 20261111
B = 2000


def _us_day(ts: float) -> str:
    return (datetime.fromtimestamp(ts, timezone.utc) - timedelta(hours=10)).strftime("%Y-%m-%d")


def load(root: Path) -> dict[str, list[dict]]:
    out = {}
    for k, f in LEDGERS.items():
        try:
            out[k] = [b for b in json.loads((root / f).read_text(encoding="utf-8")) if not b.get("dubblett")]
        except (FileNotFoundError, json.JSONDecodeError):
            out[k] = []
    return out


def prestation(b: dict) -> tuple:
    return (b.get("match_id"), b.get("spelare_id") or b.get("spelare"), b.get("marknad"))


def dedup(bets: list[dict]) -> list[dict]:
    """En rad per prestation (spelare, match, marknad): första bokförda prognosen räknas."""
    seen, out = set(), []
    for b in sorted(bets, key=lambda x: x.get("bokford") or 0):
        k = prestation(b)
        if k not in seen:
            seen.add(k)
            out.append(b)
    return out


def _boot(values_by_day: dict[str, list[float]], stat, rnd: random.Random) -> tuple[float, float] | None:
    days = list(values_by_day)
    if len(days) < 3:
        return None
    res = []
    for _ in range(B):
        xs = [v for d in (rnd.choice(days) for _ in days) for v in values_by_day[d]]
        if xs:
            res.append(stat(xs))
    res.sort()
    return res[int(0.025 * len(res))], res[int(0.975 * len(res)) - 1]


def _ll(p: float, y: int) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def summarize(bets: list[dict], rnd: random.Random) -> dict:
    settled = [b for b in bets if b.get("status") in ("vunnen", "förlorad", "push")]
    won = [b for b in settled if b["status"] == "vunnen"]
    flat = [((b["odds"] - 1) if b["status"] == "vunnen" else 0.0 if b["status"] == "push" else -1.0) for b in settled]
    model_u = [(b.get("resultat_enheter") or 0) / 0.002 for b in settled]
    stake_u = sum((b.get("insats_pct") or 0) / 0.002 for b in settled)
    # drawdown (flat 1u, i tidsordning)
    eq, peak, dd = 0.0, 0.0, 0.0
    for b, r in sorted(zip(settled, flat), key=lambda t: t[0].get("avspark") or 0):
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    started = [b for b in bets if b.get("avspark") and b.get("stangning") and b.get("odds")
               and b["avspark"] < datetime.now(timezone.utc).timestamp()]
    clv_day = defaultdict(list)
    for b in started:
        clv_day[_us_day(b["avspark"])].append((1 / b["stangning"] - 1 / b["odds"]) * 100)
    clv_all = [v for vs in clv_day.values() for v in vs]
    # Verifierad stängning = ett senare odds på samma bolag och linje har setts (stangning_ts, från 2026-11-11).
    # Utan tidsstämpel kan "stängningen" vara spelets eget odds (CLV 0) – räknas som legacy, inte som täckt.
    ver = [b for b in started if b.get("stangning_ts")]
    clv_ver_day = defaultdict(list)
    for b in ver:
        clv_ver_day[_us_day(b["avspark"])].append((1 / b["stangning"] - 1 / b["odds"]) * 100)
    clv_ver = [v for vs in clv_ver_day.values() for v in vs]
    ages = [(b["avspark"] - b["stangning_ts"]) / 60 for b in ver]
    # Brier / log loss på samma spel (modell vs marknad), unika prestationer
    br_day = defaultdict(list)
    pairs = []
    for b in dedup(settled):
        pm, pk = b.get("p_modell"), b.get("p_marknad")
        if pm is None or pk is None or b["status"] == "push":
            continue
        y = 1 if b["status"] == "vunnen" else 0
        pairs.append((pm, pk, y))
        br_day[_us_day(b["avspark"])].append((pm - y) ** 2 - (pk - y) ** 2)
    brier = None
    if pairs:
        n = len(pairs)
        brier = {"n": n, "modell": sum((p - y) ** 2 for p, _, y in pairs) / n,
                 "marknad": sum((q - y) ** 2 for _, q, y in pairs) / n,
                 "logloss_modell": sum(_ll(p, y) for p, _, y in pairs) / n,
                 "logloss_marknad": sum(_ll(q, y) for _, q, y in pairs) / n,
                 "diff_ci95": _boot(br_day, lambda xs: sum(xs) / len(xs), rnd)}
    return {
        "rader": len(bets), "prestationer": len({prestation(b) for b in bets}),
        "matcher": len({b.get("match_id") for b in bets}), "dagar": len({_us_day(b["avspark"]) for b in bets if b.get("avspark")}),
        "avgjorda": len(settled), "vunna": len(won),
        "roi_flat": (sum(flat) / len(flat)) if flat else None,
        "roi_modell": (sum(model_u) / stake_u) if stake_u else None,
        "omsattning_u": stake_u, "resultat_u": sum(model_u), "max_drawdown_flat_u": dd,
        "clv_pp": (sum(clv_all) / len(clv_all)) if clv_all else None,
        "clv_ci95": _boot(clv_day, lambda xs: sum(xs) / len(xs), rnd),
        "clv_verifierad_pp": (sum(clv_ver) / len(clv_ver)) if clv_ver else None,
        "clv_verifierad_ci95": _boot(clv_ver_day, lambda xs: sum(xs) / len(xs), rnd),
        "clv_tackning": (len(ver) / max(1, len([b for b in bets if b.get("avspark") and b["avspark"] < datetime.now(timezone.utc).timestamp()]))) if bets else None,
        "stangning_min_fore_start_median": sorted(ages)[len(ages) // 2] if ages else None,
        "brier": brier,
    }


def status(s: dict) -> str:
    br = s.get("brier")
    if not br or br["n"] < MIN_OBS:
        return "insufficient_data"
    d = br.get("diff_ci95")
    c = s.get("clv_verifierad_ci95") or s.get("clv_ci95")     # verifierad stängning går före legacy
    if (d and d[0] > 0) or (c and c[1] < 0):
        return "degraded"
    if d and d[1] < 0 and c and c[0] > 0:
        return "validated"
    return "shadow"


def odds_band(o: float) -> str:
    for lo, hi in ((1.0, 1.6), (1.6, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 99)):
        if lo <= o < hi:
            return f"{lo:.2f}–{hi:.2f}" if hi < 99 else "3,00+"
    return "?"


def evaluate(root: Path) -> dict:
    rnd = random.Random(SEED)
    data = load(root)
    out = {"skapad": datetime.now(timezone.utc).isoformat(timespec="seconds"), "per_bokforing": {}, "per_marknad": {},
           "per_oddsintervall": {}, "status": {}}
    for k, bets in data.items():
        out["per_bokforing"][k] = summarize(bets, rnd)
    # per marknad: modelltest (störst framåtriktat urval med både modell och marknad) + LIVE
    mt = data["modelltest"]
    for mk in sorted({b.get("marknad") for b in mt + data["live"]}):
        s = summarize([b for b in mt if b.get("marknad") == mk], rnd)
        s_live = summarize([b for b in data["live"] if b.get("marknad") == mk], rnd)
        out["per_marknad"][mk] = {"modelltest": s, "live": s_live}
        out["status"][mk] = status(s)
    for band in sorted({odds_band(b["odds"]) for b in data["live"] if b.get("odds")}):
        out["per_oddsintervall"][band] = summarize([b for b in data["live"] if b.get("odds") and odds_band(b["odds"]) == band], rnd)
    return out


def _f(x, d=3, pct=False):
    if x is None:
        return "–"
    return f"{x * 100:+.1f} %" if pct else f"{x:.{d}f}"


def markdown(r: dict) -> str:
    L = [f"# NBA – utvärdering på framåtriktad data ({r['skapad']})", "",
         "Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.", "",
         "| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in r["per_bokforing"].items():
        br = s["brier"]
        ci = s["clv_ci95"]
        L.append(f"| {k} | {s['rader']} | {s['prestationer']} | {s['matcher']} | {s['dagar']} | {s['avgjorda']} | "
                 f"{_f(s['roi_flat'], pct=True)} | {_f(s['roi_modell'], pct=True)} | {_f(s['max_drawdown_flat_u'], 1)} | "
                 f"{_f(s['clv_pp'], 2)} ({'–' if not ci else f'{ci[0]:+.2f}…{ci[1]:+.2f}'}) | {_f(s['clv_verifierad_pp'], 2)} | {_f(s['clv_tackning'], 2)} | "
                 + ("–" if not br else f"{br['modell']:.4f} / {br['marknad']:.4f} ({br['n']})") + " |")
    L += ["", "## Status per marknad", "", "| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |",
          "|---|---|---|---|---|---|---|"]
    for mk, d in r["per_marknad"].items():
        s, sl = d["modelltest"], d["live"]
        br = s["brier"]
        ci, dci = s["clv_ci95"], (br or {}).get("diff_ci95")
        L.append(f"| {mk} | **{r['status'][mk]}** | " + ("–" if not br else f"{br['modell']:.4f} / {br['marknad']:.4f} ({br['n']})")
                 + f" | {'–' if not dci else f'{dci[0]:+.4f}…{dci[1]:+.4f}'} | {_f(s['clv_pp'], 2)} ({'–' if not ci else f'{ci[0]:+.2f}…{ci[1]:+.2f}'}) | "
                 f"{sl['avgjorda']} | {_f(sl['roi_flat'], pct=True)} |")
    L += ["", "## LIVE per oddsintervall", "", "| Odds | Avgjorda | ROI flat | CLV pe |", "|---|---|---|---|"]
    for band, s in r["per_oddsintervall"].items():
        L.append(f"| {band} | {s['avgjorda']} | {_f(s['roi_flat'], pct=True)} | {_f(s['clv_pp'], 2)} |")
    L += ["", "Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md."]
    return "\n".join(L) + "\n"


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    r = evaluate(root)
    (root / "nba_utvardering.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    (root / "nba_utvardering.md").write_text(markdown(r), encoding="utf-8")
    print(markdown(r))


if __name__ == "__main__":
    main()
