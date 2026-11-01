"""CLV-signal: förutse när vi kommer att slå stängningsoddset.

Kambi följer Pinnacle med fördröjning. Boten sparar den "rätta" sannolikheten
(Pinnacle-baserad) för varje linje över tid. Har den rört sig åt vårt håll
(momentum) medan Kambis pris står still, väntas Kambi korta in priset före
avspark – då slår vi CLV.

Förväntad CLV (procentenheter) = (rätt sannolikhet nu − Kambis implicita sannolikhet)
                                 + 0,5 × Pinnacle-rörelsen sedan första observationen.

Regel: ett ben som BARA stoppades av edgekravet släpps igenom om edge ≥ 1 %,
förväntad CLV ≥ 2,0 procentenheter och Pinnacle har rört sig minst 1,5 enheter åt vårt håll.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .decision import kelly_stake


def line_key(c) -> str:
    side = "|under" if c.best.side == "under" else ""
    return f"{c.match_id}|{c.player_id}|{c.market}|{c.line}{side}"


class History:
    def __init__(self, path: Path):
        self.path = path
        self.d: dict[str, list] = {}
        if path.exists():
            try:
                self.d = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.d = {}

    def update(self, rows, now: float) -> None:
        for r in rows:
            c = r.row.decision.cand
            k = line_key(c)
            if k not in self.d:
                self.d[k] = [c.p, now, c.p, now]
            else:
                self.d[k][2], self.d[k][3] = c.p, now

    def momentum_pp(self, c, min_age_s: float = 1800) -> float:
        h = self.d.get(line_key(c))
        if not h or h[3] - h[1] < min_age_s:
            return 0.0
        return (h[2] - h[0]) * 100

    def save(self, now: float) -> None:
        self.d = {k: v for k, v in self.d.items() if now - v[3] < 2 * 86400}
        self.path.write_text(json.dumps(self.d), encoding="utf-8")


def expected_clv_pp(c, momentum: float) -> float:
    return (c.p - 1.0 / c.best.odds) * 100 + 0.5 * momentum


def apply(rows, hist: History, settings: dict) -> int:
    """Släpp igenom ben med CLV-signal. Returnerar antal."""
    min_edge = settings.get("clv_min_edge", 0.01)
    min_clv = settings.get("clv_min_expected_pp", 2.0)
    min_mom = settings.get("clv_min_momentum_pp", 1.5)
    n = 0
    for r in rows:
        d = r.row.decision
        c = d.cand
        mom = hist.momentum_pp(c)
        r.clv_pp = expected_clv_pp(c, mom)
        r.momentum_pp = mom
        if d.playable or not d.show or c.edge < min_edge:
            continue
        # Bara ben som enbart stoppades av edgekravet (inga andra spärrar).
        if not d.reasons or not all(x.startswith("edge ") or x.startswith("linjejusterat")
                                    or x.startswith("modell ") for x in d.reasons):
            continue
        if r.clv_pp >= min_clv and mom >= min_mom:
            d.playable = True
            d.stake = kelly_stake(c.p, c.best.odds, 0.25, 0.02)
            d.reasons.append(f"CLV-signal: Pinnacle +{mom:.1f} enheter, förväntad CLV +{r.clv_pp:.1f}")
            n += 1
    return n


def units(stake_frac: float) -> int:
    """Insats som units 1–10 (1 unit = 0,2 % av bankrullen, 10 = taket 2 %)."""
    if not stake_frac or stake_frac <= 0:
        return 0
    return max(1, min(10, round(stake_frac / 0.002)))
