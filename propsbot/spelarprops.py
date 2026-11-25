"""Spelarprops-testet (25/11): fotbollens spelarprops med hybridmodellen, egen bokföring och egen flik.

Hybridmodell = elasticiteter mitt emellan vår och brorsens (player_model.ELASTICITY_HYB). Varje ben med minst
MIN_EDGE edge (bara startande spelare, odds inom ramen) bokförs i bokforing_spelarprops_test.json med råa
sannolikheter för alla tre varianter (p_raw_cur / p_raw_alt / p_raw_hyb), så att kalibreringen kan jämföras
(`python -m propsbot.alt_elasticitet`). Inga notiser, inga insatser, ingår inte i A/B/C Tier eller "Alla".
Fliken visar vilken nivå varje spel HADE fått enligt våra tier-regler (hade_blivit) och varför inte högre.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

LEDGER = "bokforing_spelarprops_test.json"
MIN_EDGE = 0.02


def record_hyb(root: Path, hyb_rows: list, cur_rows: list, evd_by_id: dict, data: list, settings: dict, diag,
               skarp=None) -> int:
    from .ledger import Ledger
    from .results import settle_open
    from .sources.http import JsonClient
    allowed = set(settings.get("football_markets", ["shots_on_target"]))
    lo, hi = settings.get("odds_window_all", [1.40, 6.0])
    cap = settings.get("max_plausible_edge", 0.25)
    rows = [r for r in hyb_rows if r.row.decision.cand.market in allowed]
    for r in rows:
        d, c = r.row.decision, r.row.decision.cand
        d.playable = bool(MIN_EDGE <= c.edge <= cap and lo <= c.best.odds <= hi)
        d.show = True
    try:   # bara bekräftade startande spelare (annars skulle bänkade spelare dra ner träffen)
        from .free_scan import apply_lineups
        diag.log(f"Spelarprops-test startelvor: {apply_lineups(root, rows, data, settings)}")
    except Exception as e:  # noqa: BLE001
        diag.log(f"Spelarprops-test startelvor: FEL {type(e).__name__}: {e}")
        for r in rows:
            r.row.decision.playable = False
    led = Ledger(root / LEDGER)
    new = led.record(rows, evd_by_id, predicate=lambda r: r.row.decision.playable)
    led.update_closing(rows, time.time())
    try:
        settle_open(led, JsonClient(root / ".cache_odds", ttl_s=900))
    except Exception as e:  # noqa: BLE001
        diag.log(f"Rättning (spelarprops-test): {type(e).__name__}: {e}")
    if skarp:
        skarp(led)
    led.save()
    n_edge = sum(1 for r in rows if r.row.decision.cand.edge >= MIN_EDGE)
    diag.log(f"Spelarprops-test: {len(rows)} ben med hybridmodell, {n_edge} med minst {MIN_EDGE:.0%} edge, "
             f"{len(new)} nya bokförda, {len(led.bets)} totalt")
    try:
        export(root, settings)
    except Exception as e:  # noqa: BLE001
        diag.log(f"Spelarprops-export: FEL {type(e).__name__}: {e}")
    return len(new)


def annotate(b: dict, c: dict) -> dict:
    """Spelet + vilken nivå det hade fått enligt våra tier-regler (aldrig högre än C utan skarp referens)."""
    from . import tiers
    tier, why = tiers.classify(b, "skugga", "fotboll", c)
    out = dict(b)
    out["hade_blivit"] = tier or "–"
    out["varfor_inte_hogre"] = why
    if tier:
        out.update(tier=tier, kalla="skugga", sport="fotboll")
        tiers.annotate(out, b, c)
    from .msg import build_motiv
    out["motiv"] = build_motiv(out)
    return out


CSV_COLS = ["Bokförd", "Avspark", "Match", "Spelare", "Marknad", "Linje", "Bolag", "Odds", "Stängning", "CLV (%)",
            "Edge", "Sannolikhet", "Fair odds", "Hade blivit", "Varför inte högre", "p nuvarande", "p brorsens",
            "p hybrid", "Status", "Utfall", "Resultat (u)"]


def export(root: Path, settings: dict) -> int:
    import csv
    from datetime import datetime, timezone
    from . import tiers
    try:
        bets = json.loads((root / LEDGER).read_text(encoding="utf-8")).get("bets", [])
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        bets = []
    c = tiers.cfg(settings)
    ann = [annotate(b, c) for b in bets if not b.get("dubblett")]
    ann.sort(key=lambda b: b.get("bokford") or 0, reverse=True)
    site = root / "site"
    (site / "csv").mkdir(parents=True, exist_ok=True)
    from .ledger import rensa_nan
    (site / "spelarprops.json").write_text(json.dumps(rensa_nan({"uppdaterad_ts": time.time(), "bets": ann}),
                                                      ensure_ascii=False, allow_nan=False), encoding="utf-8")
    f = lambda ts: datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else ""
    n = lambda x, k=3: "" if x is None else round(x, k)
    with open(site / "csv" / "spelarprops.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for b in ann:
            u = b.get("insats_pct") and b["insats_pct"] / 0.01
            res = b.get("resultat_enheter")
            clv = None if not (b.get("odds") and b.get("stangning")) else (b["odds"] / b["stangning"] - 1) * 100
            w.writerow([f(b.get("bokford")), f(b.get("avspark")), b.get("match"), b.get("spelare"), b.get("marknad"),
                        b.get("linje"), b.get("bolag"), n(b.get("odds"), 2), n(b.get("stangning"), 2), n(clv, 2),
                        n(b.get("edge")), n(b.get("sannolikhet")), n(b["motiv"].get("fair_odds"), 2), b["hade_blivit"],
                        "; ".join(b["varfor_inte_hogre"]), n(b.get("p_raw_cur")), n(b.get("p_raw_alt")),
                        n(b.get("p_raw_hyb")), b.get("status"), b.get("utfall"),
                        n(None if res is None or not u else res / 0.01, 2)])
    return len(ann)
