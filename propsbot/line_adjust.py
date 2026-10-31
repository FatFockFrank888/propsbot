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


def _power_k(prices: list[float], target: float) -> float | None:
    """k så att Σ -ln(1 - (1/o)^k) = target (Poisson: summan av spelarnas takt = lagens väntade antal).
    Power-metoden lägger mer marginal på långa odds, vilket stämmer med hur bolag prissätter."""
    if len(prices) < 12 or target <= 0:
        return None
    def total(k):
        return sum(-math.log(max(1e-9, 1 - (1 / o) ** k)) for o in prices)
    lo, hi = 1.0, 6.0
    if total(lo) < target:          # redan under målet utan marginal – orimligt, avstå
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if total(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _ladder_k(ladder: dict[float, float], market: str) -> float | None:
    """Power-k som gör spelarens stege inre konsistent (samma μ på alla linjer)."""
    from .player_model import NB_SHAPE, nb_over
    shape = NB_SHAPE.get(market, 8.0)

    def mu_for(p: float, line: float) -> float:
        lo, hi = 1e-3, 25.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if nb_over(mid, line, shape) < p:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    best, best_k = None, None
    k = 1.0
    while k <= 3.0001:
        mus = [mu_for(min((1 / o) ** k, 0.999), ln) for ln, o in ladder.items()]
        lm = [math.log(m) for m in mus]
        mean = sum(lm) / len(lm)
        var = sum((x - mean) ** 2 for x in lm)
        if best is None or var < best:
            best, best_k = var, k
        k += 0.02
    return best_k if best_k and 1.0 < best_k < 2.99 else None


@dataclasses.dataclass
class MarginModel:
    """Uppmätt marginal för en match: power-k per bolag för målskytt/assist och
    marginalkurva m(odds) per marknad för skott (från tvåsidiga linjer)."""
    power: dict = dataclasses.field(default_factory=dict)      # (bolag, marknad) -> k
    curve: dict = dataclasses.field(default_factory=dict)      # marknad -> (bas, lutning)
    info: str = ""


def measure_margins(quotes: list[OddsQuote], total_goals: float, cfg: Config) -> MarginModel:
    from .market import estimate_one_sided_margin
    mm = MarginModel()
    parts = []
    targets = {"goal": total_goals * 0.97, "assist": total_goals * 0.97 * 0.72}
    by: dict[tuple[str, str], list[float]] = defaultdict(list)
    for q in quotes:
        if q.provider == "kambi" and q.market in targets and q.line == 0.5 and q.side == "over" \
                and q.variant in ("to score", "to give an assist (settled using opta data)",
                                  "to give an assist"):
            by[(q.book, q.market)].append(q.odds)
    for (book, market), prices in by.items():
        k = _power_k(prices, targets[market])
        if k:
            mm.power[(book, market)] = k
    for market in ("goal", "assist"):
        ks = [k for (b, m), k in mm.power.items() if m == market]
        if ks:
            parts.append(f"{market} k={median(ks):.2f}")
    # Stege: samma spelare har ensidiga över-priser på flera linjer (0,5 / 1,5 / 2,5 …).
    # Med rätt marginal (power k) ska alla linjer ge samma väntade antal μ.
    for market in ("shots", "shots_on_target"):
        ladders: dict[tuple, dict[float, float]] = defaultdict(dict)
        for q in quotes:
            if q.provider == "kambi" and q.market == market and q.side == "over":
                ladders[(q.book, q.player_id, q.variant)][q.line] = q.odds
        ks_by_book: dict[str, list[float]] = defaultdict(list)
        for (book, _pid, _v), lad in ladders.items():
            if len(lad) >= 3:
                k = _ladder_k(lad, market)
                if k:
                    ks_by_book[book].append(k)
        for book, ks in ks_by_book.items():
            if len(ks) >= 5:
                mm.power[(book, market)] = median(ks)
        allk = [k for ks in ks_by_book.values() for k in ks]
        if len(allk) >= 5:
            kk = median(allk)
            parts.append(f"{market} stege k={kk:.2f} ({len(allk)} spelare; marginal vid 3,00 ≈ "
                         f"{1 / (3.0 * (1 / 3.0) ** kk) - 1:.0%})")
    for market in ("shots", "shots_on_target"):
        pairs_by: dict[tuple, dict] = defaultdict(dict)
        for q in quotes:
            if q.provider == "kambi" and q.market == market:
                pairs_by[(q.book, q.player_id, q.line, q.variant)][q.side] = q.odds
        pairs = [(d["over"], devig_power((d["over"], d["under"]))[0])
                 for d in pairs_by.values() if "over" in d and "under" in d]
        if len(pairs) >= 20:
            mm.curve[market] = estimate_one_sided_margin(
                pairs, cfg.market.one_sided_margin.get(market, (0.08, 0.015)), prior_n=20)
            b, sl = mm.curve[market]
            parts.append(f"{market} m(2,0)={b:.0%} m(4,0)={b + 2 * sl:.0%}")
    mm.info = "uppmätt marginal: " + (", ".join(parts) or "otillräckligt underlag")
    return mm


def kambi_fair(qs: list[OddsQuote], market: str, cfg: Config,
               mm: MarginModel | None = None) -> tuple[float, bool] | None:
    """Median över Kambi-bolagen av rättvis sannolikhet; True om tvåsidigt eller uppmätt."""
    by_book: dict[str, dict[str, float]] = defaultdict(dict)
    for q in qs:
        by_book[q.book][q.side] = q.odds
    two = [devig_power((d["over"], d["under"]))[0] for d in by_book.values()
           if "over" in d and "under" in d]
    if two:
        return median(two), True
    if mm is not None:
        measured = []
        for book, d in by_book.items():
            if "over" not in d:
                continue
            k = mm.power.get((book, market))
            if k and (qs[0].line == 0.5 or market in ("shots", "shots_on_target")):
                measured.append((1 / d["over"]) ** k)
            elif market in mm.curve:
                b, sl = mm.curve[market]
                m = min(max(b + sl * (d["over"] - 2.0), 0.0), 2.0)
                measured.append(1.0 / (d["over"] * (1 + m)))
        if measured:
            return median(measured), True
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
                           pin_lines: Lines, kambi_lines: Lines,
                           model: dict | None = None, model_offset: dict | None = None,
                           gaps_out: list | None = None) -> tuple[list[ScanRow], str]:
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

    mm = measure_margins(quotes, lh_p + la_p, cfg) if settings.get("measure_margins", True) else None
    if mm:
        info += f"; {mm.info}"
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
        fk = kambi_fair(qs, market, cfg, mm)
        if not fk:
            continue
        p_k, two_sided = fk
        # Målskytt/assist som normaliserats mot Pinnacles mål behöver ingen extra kvotjustering.
        normalized = mm is not None and line == 0.5 and market in ("goal", "assist") and any(
            (q.book, market) in mm.power for q in qs)
        p_adj = p_k if normalized else adjust_prob(p_k, line, ratio, market)
        p, p_mod, note = p_adj, float("nan"), ""
        if model:
            from .market import inv_logit, logit
            from .player_model import match_player, prob_over
            mk = match_player(model, pid)
            if mk and (mk, market) in model:
                mu, pr = model[(mk, market)]
                p_raw = min(max(prob_over(market, mu, line), 0.005), 0.995)
                if gaps_out is not None:
                    if 0.15 <= p_adj <= 0.85:
                        gaps_out.append((market, logit(p_raw) - logit(p_adj)))
                # Nivån tas från marknaden: modellens snittavvikelse per marknad dras bort,
                # så att modellen bara bidrar med skillnader mellan spelare.
                off = (model_offset or {}).get(market, 0.0)
                p_mod = inv_logit(logit(p_raw) - off)
                w = settings.get("model_weight", 0.25) * \
                    settings.get("model_market_mult", {}).get(market, 1.0)
                if abs(logit(p_mod) - logit(p_adj)) > 1.0:
                    w *= 0.5   # stor oenighet: modellen saknar troligen info (roll, skada)
                p = inv_logit(w * logit(p_mod) + (1 - w) * logit(p_adj))
                note = (f"modell {p_mod:.0%} (rå {p_raw:.0%}, väntat {mu:.2f}, {pr.n_matches} matcher, "
                        f"{pr.starts} starter), marknad {p_adj:.0%}, modellvikt {w:.2f}")
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
        if note:
            d.reasons.append(note)
        if not two_sided:
            d.reasons.append("ensidigt pris med gissad marginal – högre edgekrav")
        if d.cand.edge > settings["max_plausible_edge"]:
            d.playable, d.stake = False, 0.0
            d.reasons.append(f"edge över {settings['max_plausible_edge']:.0%} – orimligt, kontrollera")
        out.append(ScanRow("fotboll", title, kickoff, Row(d, p_mod, p_k, 0.0), 1))
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
