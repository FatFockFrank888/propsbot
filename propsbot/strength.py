"""Styrka och insats 1–10u (14/11).

Styrka = edge (högst 15, över 15 dras ner) + MODEL_W × modellens edge (±15) + sharp money (+1 / −2) + 1 för LIVE.
MODEL_W = 0 sedan 15/11: modellen slog inte den skarpa stängningen (modelltest CLV ≈ 0, Brier sämre än
marknaden), medan edgen mot Pinnacle/DK förutsade skarp CLV tydligt (2–4 %: +0,5 pe … 8–12 %: +3,1 pe).
Samma tal som rankar fliken Topp 5. Insatsen följer styrkan över hela skalan 1–10u
(1u = 0,2 % av bankrullen), så 10u betyder ett av de starkaste spelen:

    styrka   ≤ 7    8    10    12    14   ≥ 16        (skala från 15/11: S0 6, steg 1)
    units      1    2     4     6     8     10
    LIVE-exempel: edge 7 % -> 2u, 10 % -> 5u, 13 % -> 8u, 15 % -> 10u (+1u om sharp money med oss)

Tidigare var LIVE-insatsen ¼ Kelly med tak 5u, och nästan alla spel hamnade på taket.
Inga dags- eller matchtak sedan 18/11 (live_max_* = None).
"""
from __future__ import annotations

import math
import re

U = 0.002            # 1 unit = 0,2 % av bankrullen
S0, STEP = 6.0, 1.0  # styrka S0 + STEP·u ger u units (var 5,0 / 1,5 med modellen)
MODEL_W = 0.0        # var 0,5 till 15/11


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
    mp = 0.0 if model_edge is None else MODEL_W * max(-15.0, min(15.0, model_edge * 100))
    return ec + mp + sharp + (1 if live else 0)


def units_for(s: float, cap: int = 10) -> int:
    """Styrka -> units 1..cap."""
    return max(1, min(cap, 10, math.floor((s - S0) / STEP + 0.5)))   # som Math.round i webbsidan


def units_from(edge, model_edge=None, sharp: int = 0, live: bool = True, cap: int = 10) -> int:
    return units_for(score(edge, model_edge, sharp, live), cap)


def stake_text(u: int) -> str:
    """Insatsraden i notisen: 10u = maxinsats, ett av de starkaste spelen."""
    return f"{u}/10 units" + (" – MAX, starkt spel 💪" if u >= 10 else "")
