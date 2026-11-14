"""Automatisk uppgradering när en marknad har bevisat sig mot stängningen (CLV).

En marknad som samlar data (sides/totals) eller spelas i halv storlek (fotbollsprops) går över till
samma villkor som NBA LIVE – insats 1–10u efter styrkan, notiser – när underlaget räcker:

  * minst graduation_min_bets (50) spel vars match har startat (stängningen är känd), och
  * snitt-CLV > 0 med t-värde över en gräns som tål att den prövas vid VARJE skanning.

Varför gränsen inte är ett fast t: prövar man "t ≥ 1" om och om igen när nya spel kommer in, blir en
marknad utan verklig CLV till slut uppgraderad av ren slump (t ≥ 1 är p ≈ 0,16 per prövning). Gränsen är
därför en tidsoberoende (always-valid) gräns, Robbins normalblandning:

    t_krav(n) = sqrt((n + ρ)/n · (ln((n + ρ)/ρ) + 2 ln(K/α)))

med ρ = graduation_min_bets, α = graduation_alpha (0,10) och K = antal marknader som prövas (Bonferroni).
Sannolikheten att en marknad med CLV ≤ 0 NÅGON gång passerar är då högst α/K, hur ofta vi än tittar.
Exempel (α 0,10, K 2): n = 50 -> t ≥ 3,7, n = 150 -> 3,1, n = 500 -> 3,0. graduation_min_t är ett golv.

Det prövas vid varje skanning. Vänder CLV till negativt (snitt < 0 över minst 30 spel) går marknaden
tillbaka till försiktigt läge. Varje byte skickar EN notis och sparas i graduering.json.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path


def clv_stats(values: list[float]) -> dict:
    n = len(values)
    if not n:
        return {"n": 0, "mean": None, "t": None}
    m = sum(values) / n
    if n < 2:
        return {"n": n, "mean": m, "t": None}
    sd = math.sqrt(sum((x - m) ** 2 for x in values) / (n - 1))
    return {"n": n, "mean": m, "t": (m / (sd / math.sqrt(n))) if sd > 0 else None}


GRADUATION_KEYS = 2      # sides + fotbollsprops prövas parallellt


def required_t(n: int, rho: float, alpha: float, k: int = GRADUATION_KEYS) -> float:
    """Always-valid t-gräns (Robbins normalblandning) för n observationer."""
    if n <= 0:
        return float("inf")
    return math.sqrt((n + rho) / n * (math.log((n + rho) / rho) + 2 * math.log(k / alpha)))


def check(root: Path, key: str, values: list[float], settings: dict, label: str, notify: bool, log=print) -> bool:
    """values = CLV i procentenheter per spel med känd stängning. Returnerar True om marknaden är uppgraderad."""
    path = root / "graduering.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    st = clv_stats(values)
    was = bool(state.get(key, {}).get("uppgraderad"))
    min_n = settings.get("graduation_min_bets", 50)
    t_req = max(settings.get("graduation_min_t", 1.0),
                required_t(st["n"], min_n, settings.get("graduation_alpha", 0.10)))
    if not was:
        now = st["n"] >= min_n and (st["mean"] or 0) > 0 and (st["t"] or 0) >= t_req
    else:
        now = not (st["n"] >= 30 and (st["mean"] or 0) < 0)
    state[key] = {"uppgraderad": now, "n": st["n"], "clv_pp": st["mean"], "t": st["t"],
                  "t_krav": round(t_req, 2), "andrad": state.get(key, {}).get("andrad") if now == was else time.time()}
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    if now != was:
        txt = (f"{label}: {st['n']} spel med stängning, snitt-CLV {st['mean']:+.2f} pe (t = {st['t'] or 0:.1f}). "
               + ("Uppgraderad: full insats (1–10u efter styrkan) och notiser som NBA."
                  if now else "CLV har vänt till negativt – tillbaka till försiktigt läge."))
        log(f"UPPGRADERING: {txt}")
        if notify and settings.get("ntfy_topic"):
            from .notify import send
            send(settings["ntfy_topic"], f"{label}: {'uppgraderad' if now else 'nedgraderad'}", txt,
                 priority=4, tags="rocket" if now else "warning")
    return now
