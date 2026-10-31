"""Linjejustering: Kambis spelarodds räknas om med Pinnacles matchlinjer.

Idé: Kambi prissätter spelarprops utifrån sin egen matchmodell. Om Pinnacle
(skarpast på matchlinjer) väntar sig fler mål i matchen än Kambi är Kambis
spelarodds för höga, och tvärtom.

För varje Kambi-linje:
1. Kambis rättvisa sannolikhet p_k (tvåsidigt pris -> exakt, annars ensidig marginal).
2. Översätt till en Poisson-takt μ så att P(X > linje) = p_k.
3. Skala μ med (Pinnacles totala väntade mål / Kambis)^elasticitet.
   Elasticitet: mål/assist 1.0, skott på mål 0.6, skott 0.5 (skottvolym ändras
   mindre än målförväntan).
4. p_justerad = P(X > linje | μ_justerad).

Edge räknas mot bästa spelbara Kambi-pris. Samma spärrar som tidigare gäller.
"""
from __future__ import annotations

import dataclasses
import math
from collections import defaultdict
from datetime import datetime, timezone
from statistics import median

from .config import Config
from .decision import Candidate, apply_portfolio_limits, evaluate
from .market import devig_power, fair_prob_one_sided, team_lambdas_from_pinnacle
from .models import OddsQuote
from .pipeline import Row
from .scan import ScanRow

ELASTICITY = {"goal": 1.0, "assist": 1.0, "shots_on_target": 0.6, "shots": 0.5}


def poisson_over(mu: float, line: float) -> float:
    k_max = int(math.floor(line))
    cdf = sum(math.exp(-mu) * mu ** k / math.factorial(k) for k in range(k_max + 1))
    return max(0.0, min(1.0, 1.0 - cdf))


def rate_for_prob(p: float, line: float) -> float:
    lo, hi = 1e-4, 30.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if poisson_over(mid, line) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def adjust_prob(p_k: float, line: float, ratio: float, market: str) -> float:
    mu = rate_for_prob(min(max(p_k, 1e-4), 0.999), line)
    return poisson_over(mu * ratio ** ELASTICITY.get(market, 1.0), line)


def kambi_fair(qs: list[OddsQuote], market: str, cfg: Config) -> tuple[float, bool] | None:
    """Median över Kambi-bolagen av rättvis sannolikhet; True om tvåsidigt."""
    by_book: dict[str, dict[str, float]] = defaultdict(dict)
    for q in qs:
        by_book[q.book][q.side] = q.odds
    two = [devig_power((d["over"], d["under"]))[0] for d in by_book.values()
           if "over" in d and "under" in d]
    if two:
        return median(two), True
    overs = [d["over"] for d in by_book.values() if "over" in d]
    if not overs:
        return None
    return fair_prob_one_sided(market, median(overs), cfg.market), False


@dataclasses.dataclass
class Lines:
    odds_1x2: tuple[float, float, float]
    total_line: float
    odds_total: tuple[float, float]

    def lambdas(self) -> tuple[float, float]:
        return team_lambdas_from_pinnacle(self.odds_1x2, self.odds_total, self.total_line)


def evaluate_line_adjusted(evd: dict, quotes: list[OddsQuote], names: dict[str, str],
                           settings: dict, cfg: Config, now: float,
                           pin_lines: Lines, kambi_lines: Lines) -> tuple[list[ScanRow], str]:
    lh_p, la_p = pin_lines.lambdas()
    lh_k, la_k = kambi_lines.lambdas()
    ratio = (lh_p + la_p) / (lh_k + la_k)
    info = (f"väntade mål Pinnacle {lh_p + la_p:.2f} mot Kambi {lh_k + la_k:.2f} "
            f"(kvot {ratio:.3f})")
    if abs(ratio - 1) > settings.get("max_line_ratio_dev", 0.10):
        # Så stora skillnader mellan Kambi och Pinnacle är nästan alltid fel matchning,
        # olika regler (t.ex. förlängning i cup) eller gamla linjer – inte en edge.
        return [], info + " – för stor skillnad, hoppas över"
    excluded = set(settings.get("excluded_books", [])) | {settings["sharp_book"]}
    playable = set(settings["playable_books"]) or {q.book for q in quotes if q.book not in excluded}
    mtk = (evd["commence_time"] - now) / 60.0
    title = f"{evd['home_team']} – {evd['away_team']}"
    kickoff = datetime.fromtimestamp(evd["commence_time"], timezone.utc).strftime("%Y-%m-%d %H:%M")

    by_line: dict[tuple, list[OddsQuote]] = defaultdict(list)
    for q in quotes:
        if q.provider == "kambi":
            by_line[(q.player_id, q.market, q.line, q.variant)].append(q)

    out: list[ScanRow] = []
    for (pid, market, line, _variant), qs in by_line.items():
        cands = [q for q in qs if q.side == "over" and q.book in playable]
        if not cands:
            continue
        best = max(cands, key=lambda q: q.odds)
        fk = kambi_fair(qs, market, cfg)
        if not fk:
            continue
        p_k, two_sided = fk
        p = adjust_prob(p_k, line, ratio, market)
        dcfg = dataclasses.replace(cfg.decision,
                                   min_edge_by_market=dict(cfg.decision.min_edge_by_market))
        if not two_sided:
            for k in dcfg.min_edge_by_market:
                dcfg.min_edge_by_market[k] += settings["extra_edge_without_sharp"]
        cand = Candidate(evd["id"], pid, names.get(pid, pid), market, line, p,
                         dataclasses.replace(best, ts=now), consensus_odds=1.0 / p, now=now,
                         lineup_confirmed=True, minutes_to_kickoff=mtk)
        d = evaluate(cand, dcfg)
        d.reasons.append(f"linjejusterat: {info}")
        if not two_sided:
            d.reasons.append("ensidigt pris – högre edgekrav")
        if d.cand.edge > settings["max_plausible_edge"]:
            d.playable, d.stake = False, 0.0
            d.reasons.append(f"edge över {settings['max_plausible_edge']:.0%} – orimligt, kontrollera")
        out.append(ScanRow("fotboll", title, kickoff, Row(d, float("nan"), p_k, 0.0), 1))
    apply_portfolio_limits([r.row.decision for r in out], cfg.decision)
    return out, info


# ------------------------------------------------------------ matchlinjer
def _is_half_line(x: float) -> bool:
    """Bara x.5-linjer. Asiatiska linjer (2.25, 2.75, 3.0) har halva vinster/push
    och kan inte tolkas som P(mål > linje)."""
    return abs((x % 1) - 0.5) < 1e-6


def kambi_match_lines(raw: dict) -> Lines | None:
    """1X2 och total ur Kambis betoffer-svar för en match."""
    x12 = None
    totals: dict[float, dict[str, float]] = {}
    for bo in raw.get("betOffers", []):
        lab = (bo.get("criterion", {}).get("englishLabel") or "").strip().lower()
        if lab in ("full time", "match odds", "1x2", "match result", "full time result"):
            t = {o.get("type"): o.get("odds") for o in bo.get("outcomes", [])}
            if t.get("OT_ONE") and t.get("OT_CROSS") and t.get("OT_TWO"):
                x12 = (t["OT_ONE"] / 1000, t["OT_CROSS"] / 1000, t["OT_TWO"] / 1000)
        elif lab in ("total goals", "total goals - full time"):
            for o in bo.get("outcomes", []):
                if o.get("line") is None or not o.get("odds"):
                    continue
                side = "over" if o.get("type") == "OT_OVER" or \
                    (o.get("englishLabel") or "").lower() == "over" else "under"
                totals.setdefault(o["line"] / 1000, {})[side] = o["odds"] / 1000
    full = {k: v for k, v in totals.items()
            if "over" in v and "under" in v and _is_half_line(k)}
    if not x12 or not full:
        return None
    ln = min(full, key=lambda k: abs(full[k]["over"] - full[k]["under"]))
    return Lines(x12, ln, (full[ln]["over"], full[ln]["under"]))


def pinnacle_match_lines(markets: list, matchup_id: int) -> Lines | None:
    from .sources.pinnacle_public import american_to_decimal
    x12 = None
    totals: dict[float, dict[str, float]] = {}
    for m in markets:
        if m.get("matchupId") != matchup_id or m.get("period", 0) != 0:
            continue
        if m.get("type") == "moneyline":
            d = {p.get("designation"): p.get("price") for p in m.get("prices", [])}
            if all(d.get(k) is not None for k in ("home", "draw", "away")):
                x12 = tuple(american_to_decimal(float(d[k])) for k in ("home", "draw", "away"))
        elif m.get("type") == "total":
            for p in m.get("prices", []):
                if p.get("points") is None or p.get("price") is None:
                    continue
                totals.setdefault(float(p["points"]), {})[p.get("designation")] = \
                    american_to_decimal(float(p["price"]))
    full = {k: v for k, v in totals.items()
            if "over" in v and "under" in v and _is_half_line(k)}
    if not x12 or not full:
        return None
    ln = min(full, key=lambda k: abs(full[k]["over"] - full[k]["under"]))
    return Lines(x12, ln, (full[ln]["over"], full[ln]["under"]))
