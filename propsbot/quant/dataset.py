"""Fas 3: enhetliga träningsrader ur befintliga bokföringar (bara läsning, sökväg/lista som indata).

En rad = ett ben för VÅR sida:
  ts (avspark), match_id, key (ben), sport, marknad, linje, sida, odds,
  p_market (marknaden vid prognos, aldrig stängningen), p_model, p_close (skarp stängning), y (1/0, None om ej avgjort),
  prognos_ts, utfall (antal), features {namn: float|nan}
"""
from __future__ import annotations

import json
import math
from pathlib import Path

NAN = float("nan")
WON, LOST = ("vunnen", "vinst", "won"), ("förlorad", "förlust", "lost")
# numeriska fält som får bli features (saknas -> NaN). p_* = andra modellers sannolikhet för vår sida.
FEATURE_KEYS = ("p_modell", "p_stack", "p_modell_min", "p_faktorer", "p_faktorer_ra", "p_betyg", "p_betyg_ra",
                "minuter", "minuter_sd", "f_anv", "f_miljo", "f_tempo", "f_pos", "f_mot", "f_minuter_bas",
                "f_b2b", "f_tre_pa_fyra", "f_minutbegransning", "f_tillbaka", "f_lag_poang",
                "traff_l5", "traff_l10", "traff_sasong", "traff_mot", "traff_hemmaborta", "forv_clv_pp")


def _f(v) -> float:
    if v is None or isinstance(v, str):
        return NAN
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        x = float(v)
    except (TypeError, ValueError):
        return NAN
    return x if math.isfinite(x) else NAN


def _p(v) -> float:
    x = _f(v)
    return x if 0.0 < x < 1.0 else NAN


def outcome(b: dict) -> int | None:
    st = b.get("status")
    return 1 if st in WON else 0 if st in LOST else None


def row(b: dict, sport: str = "") -> dict | None:
    ts, odds = _f(b.get("avspark")), _f(b.get("odds"))
    if math.isnan(ts) or math.isnan(odds) or odds <= 1.0:
        return None
    key = b.get("key") or f"{b.get('match_id')}|{b.get('spelare_id')}|{b.get('marknad')}|{b.get('linje')}|{b.get('sida')}"
    return {
        "ts": ts, "match_id": b.get("match_id"), "key": key, "sport": b.get("sport") or sport,
        "marknad": b.get("marknad"), "linje": _f(b.get("linje")), "sida": b.get("sida") or "over", "odds": odds,
        "p_market": _p(b.get("p_marknad")), "p_model": _p(b.get("p_modell")), "p_final": _p(b.get("sannolikhet")),
        "p_close": _p(b.get("skarp_stang_p")), "y": outcome(b),
        "prognos_ts": _f(b.get("prognos_ts") if b.get("prognos_ts") is not None else b.get("bokford")),
        "utfall": _f(b.get("utfall")), "vantat": _f(b.get("vantat_faktorer")),
        "features": {k: _f(b.get(k)) for k in FEATURE_KEYS},
    }


def build(bets: list[dict], sport: str = "", settled_only: bool = True, dedup: bool = True) -> list[dict]:
    """Rader sorterade på tid. dedup: ett ben (key) räknas en gång (första bokningen)."""
    out, seen = [], set()
    for b in sorted(bets, key=lambda x: (_f(x.get("bokford")) if x.get("bokford") is not None else 0.0)):
        r = row(b, sport)
        if r is None or (settled_only and r["y"] is None):
            continue
        if dedup:
            if r["key"] in seen:
                continue
            seen.add(r["key"])
        out.append(r)
    return sorted(out, key=lambda r: (r["ts"], str(r["key"])))


def load(path: Path, sport: str = "", **kw) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    bets = d.get("bets", d) if isinstance(d, dict) else d
    return build(bets, sport, **kw)


def matrix(rows: list[dict], names: list[str]):
    """(n × k)-lista med NaN för saknade värden."""
    return [[r["features"].get(n, NAN) for n in names] for r in rows]
