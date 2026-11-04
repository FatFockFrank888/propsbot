"""Edge engine: turns quotes + model projections into evaluated legs with rule verdicts.

Definitions
-----------
p_market   de-vigged consensus of independent reference groups (sharp weighted x2), log-odds mean
p_model    NHL player model probability (no-push conditional)
p_fair     log-odds blend: (1 - model_weight) * p_market + model_weight * p_model
edge       p_fair * odds - 1           (expected return per unit at the best playable price)
model_edge p_model * odds - 1
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

from .bot_settings import BotSettings
from .history import LineHistory
from .market import GroupFair, Quote, blend_logit, group_fairs, market_probability, power_devig
from .names import NameMatcher, normalize_name
from .nhl_api import Game
from .pricing import kelly_fraction
from .slate import Projection

log = logging.getLogger(__name__)


@dataclass
class Leg:
    game: Game
    projection: Projection
    line: float
    side: str
    book: str
    odds: float
    odds_ts: float
    playable_prices: dict[str, float]
    refs: list[GroupFair]
    p_market: float | None
    p_model: float
    p_fair: float | None
    edge: float | None
    model_edge: float
    model_ok: bool
    consensus_odds: float | None
    p_sharp: float | None
    units: int
    p_kambi: float | None = None  # Kambi's own de-vigged probability (median of two-way Kambi prices)
    tags: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    live_blocks: list[str] = field(default_factory=list)

    @property
    def player_id(self) -> int:
        return self.projection.skater.player_id

    @property
    def key(self) -> str:
        return leg_key(self.game.game_id, self.player_id, self.line, self.side)

    @property
    def groups(self) -> int:
        return len(self.refs)

    @property
    def has_sharp(self) -> bool:
        return any(f.sharp for f in self.refs)

    @property
    def has_two_sided(self) -> bool:
        return any(f.two_sided for f in self.refs)

    @property
    def label(self) -> str:
        return f"{self.projection.skater.name} {self.side.capitalize()} {self.line:g} SOG"


def leg_key(game_id: int, player_id: int, line: float, side: str) -> str:
    return f"{game_id}|{player_id}|{line:g}|{side}"


def play_down_to(p_fair: float | None, min_edge: float) -> float | None:
    """Lowest odds that still give `min_edge` at this fair probability."""
    if not p_fair or p_fair <= 0:
        return None
    return round((1.0 + min_edge) / p_fair, 2)


def stake_units(p: float, odds: float, s: BotSettings, cap: int) -> int:
    f = kelly_fraction(p, 0.0, odds) * s.kelly_fraction
    if f <= 0:
        return 0
    return max(1, min(cap, round(f / s.unit_pct)))


def match_quotes(
    projections: Sequence[Projection], quotes: Iterable[Quote]
) -> tuple[dict[tuple[int, float], list[Quote]], list[str]]:
    """Group quotes by (player_id, line). Returns (groups, unmatched player names)."""
    ordered = sorted(projections, key=lambda p: not p.active)
    matcher = NameMatcher((p.skater.name, p) for p in ordered)
    cache: dict[str, Projection | None] = {}
    grouped: dict[tuple[int, float], list[Quote]] = {}
    unmatched: set[str] = set()
    for q in quotes:
        key = normalize_name(q.player)
        if key not in cache:
            cache[key] = matcher.match(q.player)
        proj = cache[key]
        if proj is None:
            unmatched.add(q.player)
            continue
        grouped.setdefault((proj.skater.player_id, q.line), []).append(q)
    return grouped, sorted(unmatched)


def evaluate_game(
    game: Game,
    projections: Sequence[Projection],
    quotes: Sequence[Quote],
    history: LineHistory,
    s: BotSettings,
    alpha: float,
    now: float,
    record: bool = True,
) -> tuple[list[Leg], list[str]]:
    by_id = {p.skater.player_id: p for p in projections}
    grouped, unmatched = match_quotes(projections, quotes)
    # Reference quotes are matched per player across all lines so neighbouring lines can be used.
    refs_by_player: dict[int, list[Quote]] = {}
    for (pid, _), qs in grouped.items():
        refs_by_player.setdefault(pid, []).extend(q for q in qs if not q.playable)

    legs: list[Leg] = []
    for (pid, line), qs in grouped.items():
        playable = [q for q in qs if q.playable]
        if not playable:
            continue
        proj = by_id[pid]
        probs = proj.probs(line, alpha)
        decisive = 1.0 - probs.push
        model_ok = proj.estimate.games_used >= s.model_min_games

        for side in ("over", "under"):
            offers = [(q.price(side), q.source, q.ts) for q in playable if q.price(side)]
            if not offers:
                continue
            odds, book, odds_ts = max(offers)
            fairs = group_fairs(refs_by_player.get(pid, []), line, side, alpha, s.one_sided_margin, s.max_interp_distance)
            has_sharp = any(f.sharp for f in fairs)
            has_two = any(f.two_sided for f in fairs)
            if side == "under" and not (has_sharp or has_two):
                continue  # unders need a two-sided or sharp reference

            p_model = probs.side(side) / decisive if decisive > 0 else 0.0
            p_market = market_probability(fairs, s.sharp_weight)
            if p_market is None:
                p_fair = None
            elif model_ok and s.model_weight > 0:
                p_fair = blend_logit([p_market, p_model], [1.0 - s.model_weight, s.model_weight])
            else:
                p_fair = p_market
            edge = p_fair * odds - 1.0 if p_fair is not None else None
            model_edge = p_model * odds - 1.0

            exact_prices = [q.price(side) for q in qs if q.price(side)]
            consensus_odds = statistics.median(exact_prices) if exact_prices else None
            sharp_ps = [f.p for f in fairs if f.sharp]
            p_sharp = statistics.median(sharp_ps) if sharp_ps else None
            kambi_two = [power_devig(q.over, q.under)[0] for q in qs if q.group == "kambi" and q.over and q.under]
            p_kambi = None
            if kambi_two:
                k_over = statistics.median(kambi_two)
                p_kambi = k_over if side == "over" else 1.0 - k_over

            leg = Leg(
                game=game, projection=proj, line=line, side=side, book=book, odds=odds, odds_ts=odds_ts,
                playable_prices={q.source: q.price(side) for q in playable if q.price(side)},
                refs=fairs, p_market=p_market, p_model=p_model, p_fair=p_fair, edge=edge, model_edge=model_edge,
                model_ok=model_ok, consensus_odds=consensus_odds, p_sharp=p_sharp,
                units=stake_units(p_fair, odds, s, s.max_units_per_bet) if p_fair is not None else 0,
                p_kambi=p_kambi,
            )
            _apply_rules(leg, history.get(leg.key), s, now)
            if record:
                history.record(leg.key, odds, p_market, p_sharp, now)
            legs.append(leg)
    return legs, unmatched


def _apply_rules(leg: Leg, hist, s: BotSettings, now: float) -> None:
    b, lb, tags = leg.blocks, leg.live_blocks, leg.tags
    if any(f.interpolated for f in leg.refs):
        tags.append("interpolated ref")
    if not leg.projection.active:
        tags.append("lineup?")

    # ---- shared rules -------------------------------------------------------
    if not (s.odds_min_all <= leg.odds <= s.odds_max_all):
        b.append(f"odds {leg.odds:.2f} outside {s.odds_min_all:.2f}-{s.odds_max_all:.2f}")
    if now - leg.odds_ts > s.max_odds_age_s:
        b.append(f"odds {now - leg.odds_ts:.0f}s old")
    if leg.edge is None:
        b.append("no market reference")
    else:
        required = s.min_edge_all + (0.0 if (leg.has_sharp or leg.has_two_sided) else s.extra_edge_without_sharp)
        if leg.edge < required:
            b.append(f"edge {leg.edge:.1%} < {required:.1%}")
        if leg.edge > s.max_plausible_edge:
            b.append(f"edge {leg.edge:.1%} implausible (> {s.max_plausible_edge:.0%})")
        if not leg.has_sharp and leg.groups < s.min_groups_without_sharp:
            b.append(f"{leg.groups} ref group(s) without sharp (need {s.min_groups_without_sharp})")
    if leg.consensus_odds and leg.odds / leg.consensus_odds - 1 > s.max_dev_from_consensus:
        b.append(f"price {leg.odds / leg.consensus_odds - 1:.0%} above consensus")
    if hist.max_odds and leg.odds < hist.max_odds * (1 - s.max_odds_drop):
        b.append(f"odds dropped {1 - leg.odds / hist.max_odds:.1%} from high {hist.max_odds:.2f}")
    if (
        leg.p_sharp is not None
        and hist.first_sharp_p is not None
        and hist.first_sharp_ts is not None
        and now - hist.first_sharp_ts >= s.sharp_min_age_min * 60
    ):
        move_pp = (leg.p_sharp - hist.first_sharp_p) * 100
        if move_pp <= -s.sharp_against_pp:
            b.append(f"sharp moved {move_pp:+.1f}pp against")
        elif move_pp >= s.sharp_with_pp:
            tags.append("Sharp money with us ⬆")

    # ---- live-only rules -----------------------------------------------------
    if not s.live_on:
        lb.append("live off")
    if leg.edge is not None and leg.edge < s.live_min_edge:
        lb.append(f"edge {leg.edge:.1%} < live {s.live_min_edge:.0%}")
    if not leg.model_ok:
        lb.append(f"model: {leg.projection.estimate.games_used} games (< {s.model_min_games})")
    elif leg.model_edge < s.live_model_min_edge:
        lb.append(f"model edge {leg.model_edge:.1%} < {s.live_model_min_edge:.0%}")
    if leg.groups < s.live_min_groups:
        lb.append(f"{leg.groups} ref group(s) < {s.live_min_groups}")
    if not (s.live_odds_min <= leg.odds <= s.live_odds_max):
        lb.append(f"odds outside live {s.live_odds_min:.2f}-{s.live_odds_max:.2f}")
    if s.live_require_active and not leg.projection.active:
        lb.append("not in last lineup")


def best_per_player(legs: Iterable[Leg], score) -> list[Leg]:
    """One leg per (game, player): the highest score wins."""
    best: dict[tuple[int, int], Leg] = {}
    for leg in legs:
        k = (leg.game.game_id, leg.player_id)
        if k not in best or score(leg) > score(best[k]):
            best[k] = leg
    return sorted(best.values(), key=score, reverse=True)
