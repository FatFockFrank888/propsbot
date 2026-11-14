"""Styrka och insats 1–10u (14/11).

Styrka = edge (högst 15, över 15 dras ner) + halva modellens edge (±15) + sharp money (+1 / −2) + 1 för LIVE.
Samma tal som rankar fliken Topp 5. Insatsen följer styrkan över hela skalan 1–10u
(1u = 0,2 % av bankrullen), så 10u betyder ett av de starkaste spelen:

    styrka   ≤ 7   9,5   11   14   17   ≥ 20
    units      1    3     4    6    8     10

Tidigare var LIVE-insatsen ¼ Kelly med tak 5u, och nästan alla spel hamnade på taket.
Dagstaket (live_max_units_day) gäller som förut.
"""
from __future__ import annotations

import math
import re

U = 0.002            # 1 unit = 0,2 % av bankrullen
S0, STEP = 5.0, 1.5  # styrka S0 + STEP·u ger u units


def sharp_signal(text: str | None) -> int:
    k = (text or "").lower()
    if re.search(r"sharp money (with|med) (us|oss)", k):
        return 1
    if re.search(r"sharp (money mot oss|moved .* against)", k):
        return -2
    return 0


def score(edge: float | None, model_edge: float | None = None, sharp: int = 0, live: bool = True) -> float:
    """edge och model_edge som andelar (0,08 = 8 %)."""
    e = (edge or 0) * 100
    ec = min(e, 15) - max(0.0, e - 15) * 0.5
    mp = 0.0 if model_edge is None else 0.5 * max(-15.0, min(15.0, model_edge * 100))
    return ec + mp + sharp + (1 if live else 0)


def units_for(s: float, cap: int = 10) -> int:
    """Styrka -> units 1..cap."""
    return max(1, min(cap, 10, math.floor((s - S0) / STEP + 0.5)))   # som Math.round i webbsidan


def units_from(edge, model_edge=None, sharp: int = 0, live: bool = True, cap: int = 10) -> int:
    return units_for(score(edge, model_edge, sharp, live), cap)


def stake_text(u: int) -> str:
    """Insatsraden i notisen: 10u = maxinsats, ett av de starkaste spelen."""
    return f"{u}/10 units" + (" – MAX, starkt spel 💪" if u >= 10 else "")
