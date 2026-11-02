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
            o = c.best.odds
            if k not in self.d:
                self.d[k] = [c.p, now, c.p, now, o]
            else:
                h = self.d[k]
                h[2], h[3] = c.p, now
                if len(h) < 5:
                    h.append(o)          # äldre poster saknar oddshistorik: börja mäta nu
                else:
                    h[4] = max(h[4] or 0.0, o)

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


def pause_live(rows, settings: dict) -> int:
    """När live är pausat blir alla spelbara ben skuggspel (bokförs och rättas, ingen notis)."""
    if settings.get("live_enabled", True):
        return 0
    n = 0
    for r in rows:
        d = r.row.decision
        if d.playable:
            d.playable = False
            d.reasons.append("live pausat – skuggspel")
            n += 1
    return n


# ---------------------------------------------------------------- gemensamma spelregler (2/11)
def _block(d, reason: str) -> None:
    d.playable = False
    d.stake = 0.0
    d.reasons.append(reason)


def odds_drop(hist: "History | None", c) -> float:
    """Hur mycket bästa oddset har fallit från det högsta vi sett (andel, 0 = inget fall)."""
    if hist is None:
        return 0.0
    h = hist.d.get(line_key(c))
    if not h or len(h) < 5 or not h[4]:
        return 0.0
    return max(0.0, 1.0 - c.best.odds / h[4])


def final_rules(rows, settings: dict, hist: "History | None" = None, sport: str = "",
                taken: dict | None = None) -> dict:
    """Sista spärrarna, efter alla andra regler (även CLV-signalen):
    1. minst min_edge_all (5 %) edge, alla marknader och sporter
    2. ett enda spel per spelare och match (störst edge vinner) – ingen dubbel/trippel på samma spelare
       (taken = redan bokförda spel {(match_id, spelare_id): nyckel} – även från tidigare körningar)
    3. inget spel om bästa oddset fallit mer än max_odds_drop (3 %) från det högsta vi sett
    4. fotboll i skuggläge: bara spel med skarp spelarreferens och odds inom football_odds_window
    """
    min_edge = settings.get("min_edge_all", 0.05)
    max_drop = settings.get("max_odds_drop", 0.03)
    n = {"edge": 0, "spelare": 0, "oddsfall": 0, "fotboll": 0}
    for r in rows:
        d = r.row.decision
        if not d.playable:
            continue
        c = d.cand
        if c.edge < min_edge:
            _block(d, f"edge {c.edge:.1%} < {min_edge:.0%} (gemensamt krav)")
            n["edge"] += 1
            continue
        drop = odds_drop(hist, c)
        if drop > max_drop:
            _block(d, f"oddset har fallit {drop:.1%} från {c.best.odds / (1 - drop):.2f} – för sent")
            n["oddsfall"] += 1
            continue
        if sport == "fotboll" and settings.get("football_shadow", True):
            lo, hi = settings.get("football_odds_window", [1.60, 2.50])
            sharp = getattr(r, "sharp_ref", False)
            if not (sharp and lo <= c.best.odds <= hi):
                _block(d, "fotboll i skuggläge – skuggspel")
                n["fotboll"] += 1
                continue
    best: dict = {}
    for r in rows:
        d = r.row.decision
        if d.playable:
            k = (d.cand.match_id, d.cand.player_id)
            if k not in best or d.cand.edge > best[k].row.decision.cand.edge:
                best[k] = r
    keep = {id(x) for x in best.values()}
    if taken:
        from .ledger import bet_key
        for k, r in best.items():
            if k in taken and taken[k] != bet_key(r):
                keep.discard(id(r))
    for r in rows:
        d = r.row.decision
        if d.playable and id(r) not in keep:
            _block(d, "redan ett spel på samma spelare i matchen (störst edge vinner)")
            n["spelare"] += 1
    return n


def taken_players(*ledgers) -> dict:
    """{(match_id, spelare_id): nyckel} för alla spel som redan är bokförda."""
    out = {}
    for lg in ledgers:
        for x in getattr(lg, "bets", []):
            if x.get("match_id") and x.get("spelare_id"):
                out.setdefault((x["match_id"], x["spelare_id"]), x["key"])
    return out
