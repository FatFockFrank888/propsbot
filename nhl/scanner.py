"""One scan cycle and the watch loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from .bot_settings import BotSettings
from .config import Settings
from .engine import Leg, best_per_player, evaluate_game, stake_units
from .history import LineHistory
from .http import HttpError, JsonClient
from .ledger import bet_from_leg, boxscore_sog, open_ledgers
from .market import Quote
from .nhl_api import WEB, Game, NhlApi
from .notify import PlayerGuard, format_live_bet, format_recap, send
from .odds import OddsEvent, match_events
from .slate import Projection, build_slate
from .sources.bovada import BovadaClient
from .sources.kambi import KambiClient, KambiEvent
from .state import BotState
from .sources.pinnacle import PinnacleClient
from .sources.us_books import Budget, UsBooks

log = logging.getLogger(__name__)

SETTLE_AFTER = timedelta(hours=2, minutes=30)


@dataclass
class ScanReport:
    started: datetime
    kambi_events: int = 0
    games: int = 0
    games_with_props: int = 0
    playable_quotes: int = 0
    reference_quotes: int = 0
    legs: int = 0
    us_fetched: list[str] = field(default_factory=list)
    live_new: list[dict] = field(default_factory=list)
    pushed: int = 0
    test_new: int = 0
    test_settled: int = 0
    data_new: int = 0
    shadow_new: int = 0
    model_new: int = 0
    settled: int = 0
    legs_settled: int = 0
    bovada_games: int = 0
    pinnacle_games: int = 0
    unmatched: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
    top_legs: list[Leg] = field(default_factory=list)
    all_legs: list[Leg] = field(default_factory=list)


def _as_event(e: KambiEvent) -> OddsEvent:
    return OddsEvent(str(e.event_id), e.home, e.away, e.start)


class Scanner:
    def __init__(self, s: BotSettings, cfg: Settings, *, diagnose: bool = False, notify: bool = True) -> None:
        self.s = s
        self.cfg = cfg
        self.notify = notify
        self.client = JsonClient(cfg.cache_dir)
        self.nhl = NhlApi(self.client)
        self.kambi = KambiClient(self.client, s.kambi_market, s.data_path / "diagnos" if diagnose else None)
        self.pinnacle = (
            PinnacleClient(self.client, s.pinnacle_api_key, s.pinnacle_league_id, s.data_path / "diagnos")
            if s.use_pinnacle else None
        )
        self.us: UsBooks | None = None
        if cfg.odds_api_key:
            budget = Budget(s.data_path / "odds_api_budget.json", s.odds_api_monthly_credits, s.odds_api_share, s.odds_api_reserve)
            self.us = UsBooks(self.client, cfg.odds_api_key, s.us_books, s.data_path / "us_quotes", budget)
        self.bovada = BovadaClient(self.client, s.bovada_ttl_s, cfg.dispersion) if s.use_bovada else None
        self.history = LineHistory(s.data_path / "line_history.sqlite")
        self.ledgers = open_ledgers(s)
        self.state = BotState(s.data_path / "state.json")
        from .test_markets import TestMarkets
        self.tests = TestMarkets(s.data_path, s) if s.test_markets else None

    # ================================================================ scan
    def run_once(self) -> ScanReport:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.timestamp()
        rep = ScanReport(started=now_dt)
        self._pp_ctx = None   # fresh power-play context (DailyFaceoff units) each scan

        self._settle(now_dt, rep)

        playable = {b.lower() for b in self.s.playable_books}
        offerings = list(self.s.kambi_offerings.items())
        events_by_off: dict[str, list[KambiEvent]] = {}
        for off, _ in offerings:
            try:
                events_by_off[off] = [
                    e for e in self.kambi.events(off)
                    if e.state == "NOT_STARTED"
                    and now < e.start.timestamp() - self.s.pre_match_cutoff_min * 60
                    and e.start.timestamp() < now + self.s.hours_ahead * 3600
                ]
            except HttpError as exc:
                rep.errors.append(f"kambi {off}: {exc}")
        main = max(events_by_off.values(), key=len, default=[])
        main = sorted(main, key=lambda e: e.start)[: self.s.max_events]
        rep.kambi_events = len(main)
        if not main:
            self._finish(rep, {})
            return rep

        games = self._nhl_games({(e.start - timedelta(hours=5)).date() for e in main})
        names = self.nhl.abbrev_by_full_name()
        main_map = match_events(games.values(), [_as_event(e) for e in main], names)
        wanted = {gid: games[gid] for gid in main_map}
        rep.games = len(wanted)
        off_maps = {off: match_events(wanted.values(), [_as_event(e) for e in evs], names) for off, evs in events_by_off.items()}

        projections = self._projections(wanted.values(), rep)

        us_events: dict[int, str] = {}
        if self.us and any(self._in_us_window(g, now_dt) for g in wanted.values()):
            try:
                us_events = match_events(wanted.values(), self.us.events(), names)
            except HttpError as exc:
                rep.errors.append(f"odds api events: {exc}")
        pin_events: dict[int, str] = {}
        if self.pinnacle:
            try:
                pin_games = self.pinnacle.games()
                pin_events = match_events(
                    wanted.values(), [OddsEvent(str(g.matchup_id), g.home, g.away, g.start) for g in pin_games], names
                )
            except HttpError as exc:
                rep.errors.append(f"pinnacle: {exc}")
            rep.pinnacle_games = len(pin_events)

        bov_events: dict[int, str] = {}
        bov_links: dict[str, str] = {}
        if self.bovada:
            try:
                bevs = self.bovada.events()
                bov_links = {e.event_id: e.link for e in bevs}
                bov_events = match_events(
                    wanted.values(), [OddsEvent(e.event_id, e.home, e.away, e.start) for e in bevs], names
                )
            except HttpError as exc:
                rep.errors.append(f"bovada: {exc}")
            rep.bovada_games = len(bov_events)

        all_legs: list[Leg] = []
        for gid, game in wanted.items():
            quotes: list[Quote] = []
            for off, book in offerings:
                eid = off_maps.get(off, {}).get(gid)
                if eid is None:
                    continue
                try:
                    qs, _ = self.kambi.sog_quotes(off, book, int(eid), playable=book.lower() in playable)
                    quotes += qs
                except HttpError as exc:
                    rep.errors.append(f"kambi {off} {game.away}@{game.home}: {exc}")
            n_playable = sum(q.playable for q in quotes)
            if self.tests is not None:
                self._test_markets(game, gid, off_maps, projections.get(gid, []), playable, now, rep)
            if not n_playable:
                continue
            rep.games_with_props += 1
            rep.playable_quotes += n_playable

            if self.bovada and gid in bov_events:
                try:
                    quotes += self.bovada.sog_quotes(bov_links[bov_events[gid]])
                except HttpError as exc:
                    rep.errors.append(f"bovada {game.away}@{game.home}: {exc}")
            if self.pinnacle and gid in pin_events:
                try:
                    quotes += self.pinnacle.sog_quotes(int(pin_events[gid]))
                except HttpError as exc:
                    rep.errors.append(f"pinnacle {game.away}@{game.home}: {exc}")
            if self.us:
                cached = self.us.cached(gid)
                if (cached is None and gid in us_events and self._in_us_window(game, now_dt)
                        and self._worth_a_credit(game, projections.get(gid, []), quotes, now)):
                    try:
                        cached = self.us.fetch(gid, us_events[gid], now_dt)
                        if cached is not None:
                            rep.us_fetched.append(f"{game.away}@{game.home}")
                    except HttpError as exc:
                        rep.errors.append(f"odds api {game.away}@{game.home}: {exc}")
                quotes += cached or []
            rep.reference_quotes += sum(not q.playable and q.group != "kambi" for q in quotes)

            legs, unmatched = evaluate_game(
                game, projections.get(gid, []), quotes, self.history, self.s, self.cfg.dispersion, now
            )
            rep.unmatched.update(unmatched)
            for leg in legs:
                self.history.log_leg(leg, now)
            all_legs += legs

        rep.legs = len(all_legs)
        rep.all_legs = all_legs
        self._book(all_legs, rep)
        self._finish(rep, {leg.key: leg for leg in all_legs})
        ctx = getattr(self, "_pp_ctx", None)
        if ctx is not None:
            n_dfo = sum(1 for v in ctx._dfo.values() if v)
            print(f"  Power play: DailyFaceoff-enheter för {n_dfo}/{len(ctx._dfo)} lag"
                  + (f"; fel: {'; '.join(ctx.errors[:3])}" if ctx.errors else ""), flush=True)
        return rep

    # ============================================================= helpers
    def _nhl_games(self, days: Iterable[date]) -> dict[int, Game]:
        games: dict[int, Game] = {}
        for d in sorted(set(days) | {d + timedelta(days=1) for d in days}):
            for g in self.nhl.games_on(d):
                games[g.game_id] = g
        return games

    def _projections(self, games: Iterable[Game], rep: ScanReport) -> dict[int, list[Projection]]:
        wanted = {g.game_id for g in games}
        out: dict[int, list[Projection]] = {}
        for d in sorted({g.game_date for g in games}):
            try:
                for p in build_slate(self.nhl, self.cfg, d):
                    if p.game.game_id in wanted:
                        out.setdefault(p.game.game_id, []).append(p)
            except HttpError as exc:
                rep.errors.append(f"nhl model {d}: {exc}")
        return out

    def _worth_a_credit(self, game: Game, projections: list[Projection], quotes: list[Quote], now: float) -> bool:
        """Spend Odds API credits only on games where Kambi already looks off vs Bovada/model."""
        legs, _ = evaluate_game(game, projections, quotes, self.history, self.s, self.cfg.dispersion, now, record=False)
        return any(
            (l.edge is not None and l.edge >= self.s.shadow_min_edge) or l.model_edge >= self.s.min_edge_all
            for l in legs
            if self.s.odds_min_all <= l.odds <= self.s.odds_max_all
        )

    def _in_us_window(self, game: Game, now_dt: datetime) -> bool:
        if game.start_utc is None:
            return False
        minutes = (game.start_utc - now_dt).total_seconds() / 60
        lo, hi = self.s.us_fetch_window_min
        return lo <= minutes <= hi

    def _book(self, legs: list[Leg], rep: ScanReport) -> None:
        s = self.s
        L = self.ledgers

        # ---- LIVE (notified) ------------------------------------------------
        live = L["live"]
        per_match_units_cap = int(round(s.max_stake_per_match_pct / s.unit_pct))
        for leg in best_per_player((l for l in legs if not l.blocks and not l.live_blocks), lambda l: l.edge):
            if live.for_player(leg.game.game_id, leg.player_id):
                continue  # one live bet per player per game; first notified stands
            gid, day = leg.game.game_id, leg.game.game_date.isoformat()
            units = min(leg.units, s.live_max_units)
            cap_reason = None
            if live.count(lambda b: b["game_id"] == gid) >= s.live_max_per_match:
                cap_reason = f"live max {s.live_max_per_match} per match"
            elif live.count(lambda b: b["us_date"] == day) >= s.live_max_per_day:
                cap_reason = f"live max {s.live_max_per_day} per day"
            elif live.units(lambda b: b["us_date"] == day) + units > s.live_max_units_day:
                cap_reason = f"live max {s.live_max_units_day}u per day"
            elif live.units(lambda b: b["game_id"] == gid) + units > per_match_units_cap:
                cap_reason = f"max {s.max_stake_per_match_pct:.0%} per match"
            if cap_reason:
                leg.live_blocks.append(cap_reason)
                continue
            bet = bet_from_leg(leg, "live", s, units)
            bet["notified"] = False
            live.add(bet)
            rep.live_new.append(bet)
        self._push_live(rep)

        # ---- Data ledger: everything that passes the shared rules ------------
        for leg in best_per_player((l for l in legs if not l.blocks), lambda l: l.edge):
            if L["bokforing"].upsert_best(bet_from_leg(leg, "bokforing", s, leg.units)):
                rep.data_new += 1

        # ---- Shadow: decent edge stopped by a rule -----------------------------
        shadow = [l for l in legs if l.blocks and l.edge is not None and l.edge >= s.shadow_min_edge]
        for leg in best_per_player(shadow, lambda l: l.edge):
            if L["skugga"].upsert_best(bet_from_leg(leg, "skugga", s, leg.units, reasons=leg.blocks)):
                rep.shadow_new += 1

        # ---- Model test: the player model on its own ---------------------------
        model = [
            l for l in legs
            if l.model_ok and l.projection.active
            and s.odds_min_all <= l.odds <= s.odds_max_all
            and s.min_edge_all <= l.model_edge <= s.max_plausible_edge
        ]
        for leg in best_per_player(model, lambda l: l.model_edge):
            units = stake_units(leg.p_model, leg.odds, s, s.max_units_per_bet)
            if L["modelltest"].upsert_best(bet_from_leg(leg, "modelltest", s, units, edge_field="model_edge"), "model_edge"):
                rep.model_new += 1

        rep.top_legs = sorted((l for l in legs if l.edge is not None), key=lambda l: l.edge, reverse=True)[:15]

    def _push_live(self, rep: ScanReport) -> None:
        """Push every LIVE bet exactly once. A failed send is retried on the next scan until puck drop.
        The shared player guard (one bet per player per game, across every market and run) is checked last."""
        s = self.s
        if not (self.notify and s.ntfy_topic):
            return
        guard = PlayerGuard.shared()
        now_dt = datetime.now(timezone.utc)
        for bet in self.ledgers["live"].bets:
            if bet.get("notified", True) or bet.get("status") != "open":
                continue
            if bet.get("start") and datetime.fromisoformat(bet["start"]) <= now_dt:
                continue
            spel = f"{bet['player_id']}|sog|{bet['line']}|{bet['side']}"
            if not guard.allows("nhl", bet["game_id"], bet["player"], spel):
                bet["notified"] = None  # another bet on this player is already out
                continue
            title, msg = format_live_bet(bet, s.currency)
            if send(s.ntfy_topic, title, msg):
                bet["notified"] = True
                guard.mark("nhl", bet["game_id"], bet["player"], spel)
                rep.pushed += 1
            self.ledgers["live"].dirty = True
        guard.save()

    def _test_markets(self, game: Game, gid: int, off_maps: dict, projections: list, playable: set[str],
                      now: float, rep: ScanReport) -> None:
        """Points/assists/goals at Kambi vs our own model (data only, never notified)."""
        from .config import previous_season
        from .test_markets import parse_kambi
        try:
            tq = []
            for off, book in self.s.kambi_offerings.items():
                eid = off_maps.get(off, {}).get(gid)
                raw = self.kambi.last_raw.get((off, int(eid))) if eid is not None else None
                if raw:
                    tq += parse_kambi(raw, book)
            if tq:
                rep.test_new += self.tests.evaluate(
                    game, projections, tq, lambda p: self._scoring_history(p), playable, now,
                    pp_model=lambda p: self._pp().expected(p, p.game, previous_season(p.game.season)))
        except Exception as exc:  # noqa: BLE001 - test markets must never stop the scan
            rep.errors.append(f"test markets {game.away}@{game.home}: {exc}")

    def _pp(self):
        """Power-play context (DailyFaceoff units + NHL PP/PK stats), one per scan."""
        if getattr(self, "_pp_ctx", None) is None:
            from .pp_model import PPContext
            self._pp_ctx = PPContext(self.client, self.nhl, self.client.cache_dir / "pp")
        return self._pp_ctx

    def _scoring_history(self, p) -> list:
        """Current + previous regular season before game day (scoring rates need a long window)."""
        from .config import previous_season
        from .nhl_api import REGULAR_SEASON
        logs = self.nhl.game_log(p.skater.player_id, p.game.season, REGULAR_SEASON) +             self.nhl.game_log(p.skater.player_id, previous_season(p.game.season), REGULAR_SEASON)
        return [e for e in logs if e.game_date < p.game.game_date]

    def _settle(self, now_dt: datetime, rep: ScanReport) -> None:
        if self.tests is not None:
            def box(gid: int) -> dict:
                data, _ = self.client.get(f"{WEB}/gamecenter/{gid}/boxscore", ttl=0)
                return data
            def pp(pid: int, gid: int) -> dict | None:
                season = f"{gid // 1000000}{gid // 1000000 + 1}"
                data, _ = self.client.get(f"{WEB}/player/{pid}/game-log/{season}/{(gid // 10000) % 100}", ttl=0)
                for row in data.get("gameLog", []) or []:
                    if int(row.get("gameId", 0)) == gid:
                        return {"pp_points": int(row.get("powerPlayPoints") or 0),
                                "pp_goals": int(row.get("powerPlayGoals") or 0)}
                return None
            rep.test_settled = self.tests.settle(box, now_dt.timestamp(), pp)
        due: set[int] = set(self.history.unsettled_games((now_dt - SETTLE_AFTER).isoformat()))
        for ledger in self.ledgers.values():
            for b in ledger.open_bets():
                start = datetime.fromisoformat(b["start"]) if b.get("start") else None
                if start is None or now_dt - start >= SETTLE_AFTER:
                    due.add(b["game_id"])
        if not due:
            return
        results: dict[int, dict[int, int] | None] = {}
        for gid in due:
            try:
                data, _ = self.client.get(f"{WEB}/gamecenter/{gid}/boxscore", ttl=0)
                results[gid] = boxscore_sog(data)
            except HttpError as exc:
                rep.errors.append(f"settle {gid}: {exc}")
        for gid, sog in results.items():
            if sog is not None:
                rep.legs_settled += self.history.settle_game(gid, sog)
        for ledger in self.ledgers.values():
            rep.settled += ledger.settle(results)

    # ============================================================ notifications
    def maybe_daily_recap(self, now_dt: datetime | None = None) -> bool:
        """Once a day after recap_hour_local: yesterday's live results + running totals + bot heartbeat."""
        s = self.s
        local = (now_dt or datetime.now(timezone.utc)).astimezone()
        today = local.date().isoformat()
        if not (s.daily_recap and s.ntfy_topic and self.notify) or local.hour < s.recap_hour_local:
            return False
        if self.state.get("last_recap") == today:
            return False
        yesterday = (local.date() - timedelta(days=1)).isoformat()
        live = self.ledgers["live"]
        title, msg = format_recap(yesterday, live, self.ledgers, self.history, s)
        send(s.ntfy_topic, title, msg, priority=2, tags="bar_chart")
        self.state.set("last_recap", today)
        return True

    def record_health(self, ok: bool, problem: str = "") -> None:
        fails = 0 if ok else int(self.state.get("consecutive_failures", 0)) + 1
        self.state.set("consecutive_failures", fails)
        if fails == self.s.health_alert_after_failures and self.s.ntfy_topic and self.notify:
            send(self.s.ntfy_topic, "NHL: skanningen misslyckas",
                 f"{fails} skanningar i rad misslyckades. Senaste problem: {problem[:300]}", priority=4, tags="warning")

    def _finish(self, rep: ScanReport, legs_by_key: dict[str, Leg]) -> None:
        if self.tests is not None:
            self.tests.save()
        for ledger in self.ledgers.values():
            if legs_by_key:
                ledger.update_close(legs_by_key)
            ledger.save()
        self.state.set("last_scan", {
            "time": rep.started.isoformat(timespec="seconds"),
            "games": rep.games,
            "games_with_props": rep.games_with_props,
            "legs": rep.legs,
            "live_new": len(rep.live_new),
            "errors": rep.errors[:5],
        })
        if rep.started.minute < 10:
            self.history.prune()

    def close(self) -> None:
        for ledger in self.ledgers.values():
            ledger.save()
        self.history.close()


def next_interval_minutes(s: BotSettings, now_dt: datetime | None = None) -> float:
    now_dt = now_dt or datetime.now(timezone.utc)
    start, end = (s.quiet_hours_utc + [0, 0])[:2]
    if start <= now_dt.hour < end:
        return s.quiet_interval_min
    return s.scan_interval_min
