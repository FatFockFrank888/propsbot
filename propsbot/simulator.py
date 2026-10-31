"""Matchsimulator: spelar matchen minut för minut N gånger.

Ger sammanhängande sannolikheter för skott, skott på mål, mål och assist för alla
spelare, *givet att spelaren spelar* (annars stryks spelet). Ställning påverkar
tempo och skottmix, byten styr vem som kan skjuta, och lagens simulerade mål
kalibreras mot Pinnacles linjer.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import ASSIST_RATE, SHOT_TYPES, Config
from .models import MatchContext, PlayerProfile, TeamContext
from .volume import team_type_rates, weather_multipliers

MARKETS = ("shots", "shots_on_target", "goal", "assist")
_EPS = 1e-9


@dataclass
class SimResult:
    player_ids: list[str]
    team_of: np.ndarray            # 0 = hemma, 1 = borta
    played: np.ndarray             # (N, P) bool
    counts: dict[str, np.ndarray]  # market -> (N, P) int
    goals_home: np.ndarray
    goals_away: np.ndarray

    def _idx(self, player_id: str) -> int:
        return self.player_ids.index(player_id)

    def n_played(self, player_id: str) -> int:
        return int(self.played[:, self._idx(player_id)].sum())

    def prob_over(self, player_id: str, market: str, line: float) -> float:
        """P(antal > line | spelaren spelar)."""
        i = self._idx(player_id)
        mask = self.played[:, i]
        n = mask.sum()
        if n == 0:
            return float("nan")
        c = self.counts[market][mask, i]
        # Laplace-liknande utjämning så att 0/1 aldrig blir exakt 0 eller 1.
        return float(((c > line).sum() + 0.5) / (n + 1.0))

    def mean(self, player_id: str, market: str) -> float:
        i = self._idx(player_id)
        mask = self.played[:, i]
        return float(self.counts[market][mask, i].mean()) if mask.any() else float("nan")


class MatchSimulator:
    def __init__(self, match: MatchContext, cfg: Config | None = None):
        self.match = match
        self.cfg = cfg or Config()
        self.players: list[PlayerProfile] = match.home.players + match.away.players
        self.team_of = np.array([0] * len(match.home.players) + [1] * len(match.away.players))
        self.teams: tuple[TeamContext, TeamContext] = (match.home, match.away)
        added = match.referee.added_time
        self.total_minutes = int(round(self.cfg.sim.regulation_minutes +
                                       (added if added is not None else self.cfg.sim.default_added_time)))
        self.rates = [team_type_rates(match, t, self.cfg.matchup) for t in self.teams]
        _, self.acc_mult = weather_multipliers(match)
        self._build_player_arrays()

    # ------------------------------------------------------------------ setup
    def _build_player_arrays(self) -> None:
        P, T = len(self.players), len(SHOT_TYPES)
        self.share = np.zeros((P, T))
        self.ot = np.zeros((P, T))
        self.xg = np.zeros((P, T))
        self.xa = np.zeros(P)
        pen_col = SHOT_TYPES.index("penalty")
        for i, p in enumerate(self.players):
            outfield = p.position != "GK"
            for j, t in enumerate(SHOT_TYPES):
                self.share[i, j] = max(p.share.get(t, 0.0), 1e-6 if outfield else 0.0)
                self.ot[i, j] = min(0.98, max(0.01, p.on_target.get(t, 0.33)))
                self.xg[i, j] = min(0.97, max(0.001, p.xg_per_shot.get(t, 0.08)))
            # Straff: rangordning styr; ingen rang = nästan aldrig.
            if p.pen_order is not None:
                self.share[i, pen_col] = 10.0 ** (-3 * (p.pen_order - 1))
            else:
                self.share[i, pen_col] = 1e-9 if outfield else 0.0
            self.xa[i] = max(p.xa_share, 1e-6 if outfield else 1e-9)
        # Motståndarens målvakt (team.opponent beskriver laget man möter) sänker
        # eller höjer målchansen per skott på mål. Påverkar inte skott på mål.
        self.keeper_mult = np.array([
            float(np.clip(1.0 - 0.5 * self.teams[k].opponent.keeper_save_skill, 0.7, 1.3))
            for k in (0, 1)
        ])

    def _sample_minutes(self, rng: np.random.Generator, N: int) -> tuple[np.ndarray, np.ndarray]:
        P, Tm = len(self.players), self.total_minutes
        on = np.full((N, P), Tm + 1.0)
        off = np.full((N, P), float(Tm))
        for i, p in enumerate(self.players):
            mm = p.minutes
            starts = rng.random(N) < mm.p_start
            full = rng.random(N) < mm.p_full_if_start
            off_min = np.clip(rng.normal(mm.sub_off_mean, mm.sub_off_sd, N), 15, Tm - 1)
            red = rng.random(N) < mm.p_red_card
            red_min = rng.uniform(1, Tm, N)
            sub_on = rng.random(N) < mm.p_sub_on_if_bench
            on_min = np.clip(rng.normal(mm.sub_on_mean, mm.sub_on_sd, N), 30, Tm - 2)

            on[starts, i] = 0.0
            off[starts & ~full, i] = off_min[starts & ~full]
            bench_on = ~starts & sub_on
            on[bench_on, i] = on_min[bench_on]
            off[red, i] = np.minimum(off[red, i], np.maximum(red_min[red], on[red, i] + 1))
        return on, off

    # --------------------------------------------------------------- simulate
    def _run(self, N: int, rng: np.random.Generator, scale: np.ndarray) -> SimResult:
        cfg = self.cfg.sim
        P, Tm, nT = len(self.players), self.total_minutes, len(SHOT_TYPES)
        on, off = self._sample_minutes(rng, N)
        played = off > on

        team_vol = rng.gamma(cfg.team_volume_shape, 1.0 / cfg.team_volume_shape, (N, 2))
        player_mult = rng.gamma(cfg.player_share_shape, 1.0 / cfg.player_share_shape, (N, P))

        counts = {m: np.zeros((N, P), dtype=np.int32) for m in MARKETS}
        goals = np.zeros((N, 2), dtype=np.int32)
        base = np.array([[self.rates[k][t] / Tm for t in SHOT_TYPES] for k in (0, 1)])
        base[:, :-1] *= scale[:, None]  # kalibrera öppet spel, inte straff

        ti = {t: j for j, t in enumerate(SHOT_TYPES)}
        idx_team = [np.where(self.team_of == k)[0] for k in (0, 1)]

        for minute in range(Tm):
            on_pitch = (on <= minute) & (off > minute)  # (N, P)
            for k in (0, 1):
                diff = goals[:, k] - goals[:, 1 - k]
                lead, trail = diff > 0, diff < 0
                vol = np.where(lead, cfg.leading_volume_mult,
                               np.where(trail, cfg.trailing_volume_mult, 1.0)) * team_vol[:, k]
                players_k = idx_team[k]
                for t in SHOT_TYPES:
                    j = ti[t]
                    lam = base[k, j] * vol
                    if t == "distance":
                        lam = lam * np.where(trail, cfg.trailing_distance_mult, 1.0)
                    elif t == "header":
                        lam = lam * np.where(trail, cfg.trailing_header_mult, 1.0)
                    elif t == "counter":
                        lam = lam * np.where(lead, cfg.leading_counter_mult, 1.0)
                    n_shots = rng.poisson(lam)
                    if not n_shots.any():
                        continue
                    for rep in range(int(n_shots.max())):
                        sims = np.nonzero(n_shots > rep)[0]
                        w = (self.share[players_k, j][None, :] * player_mult[np.ix_(sims, players_k)]
                             * on_pitch[np.ix_(sims, players_k)])
                        tot = w.sum(1)
                        ok = tot > 0
                        sims, w, tot = sims[ok], w[ok], tot[ok]
                        if sims.size == 0:
                            continue
                        cum = np.cumsum(w, axis=1)
                        u = rng.random(sims.size) * tot
                        local = np.minimum((cum < u[:, None]).sum(1), len(players_k) - 1)
                        shooter = players_k[local]
                        counts["shots"][sims, shooter] += 1
                        p_ot = np.clip(self.ot[shooter, j] * (self.acc_mult if t != "penalty" else 1.0),
                                       0.01, 0.98)
                        is_ot = rng.random(sims.size) < p_ot
                        counts["shots_on_target"][sims[is_ot], shooter[is_ot]] += 1
                        p_goal_given_ot = np.clip(self.xg[shooter, j] / p_ot * self.keeper_mult[k],
                                                  0.0, 0.97)
                        is_goal = is_ot & (rng.random(sims.size) < p_goal_given_ot)
                        if not is_goal.any():
                            continue
                        gs, gp = sims[is_goal], shooter[is_goal]
                        counts["goal"][gs, gp] += 1
                        goals[gs, k] += 1
                        # Assist
                        has_assist = rng.random(gs.size) < ASSIST_RATE[t]
                        gs, gp = gs[has_assist], gp[has_assist]
                        if gs.size == 0:
                            continue
                        wa = self.xa[players_k][None, :] * on_pitch[np.ix_(gs, players_k)]
                        wa[np.arange(gs.size), np.searchsorted(players_k, gp)] = 0.0
                        tot_a = wa.sum(1)
                        ok = tot_a > 0
                        gs, wa, tot_a = gs[ok], wa[ok], tot_a[ok]
                        if gs.size == 0:
                            continue
                        cum = np.cumsum(wa, axis=1)
                        u = rng.random(gs.size) * tot_a
                        local = np.minimum((cum < u[:, None]).sum(1), len(players_k) - 1)
                        counts["assist"][gs, players_k[local]] += 1

        return SimResult(
            player_ids=[p.player_id for p in self.players],
            team_of=self.team_of, played=played, counts=counts,
            goals_home=goals[:, 0], goals_away=goals[:, 1],
        )

    def run(self) -> SimResult:
        cfg = self.cfg.sim
        rng = np.random.default_rng(cfg.seed)
        scale = np.ones(2)
        target = np.array([self.match.home.exp_goals, self.match.away.exp_goals])
        pen_goals = np.array([
            self.rates[k]["penalty"] * self.teams[k].xg_per_shot_type.get("penalty", 0.76)
            for k in (0, 1)])
        n_cal = max(2000, cfg.n_sims // 3)
        for _ in range(cfg.calibration_passes):
            r = self._run(n_cal, rng, scale)
            sim_goals = np.array([r.goals_home.mean(), r.goals_away.mean()])
            open_sim = np.maximum(sim_goals - pen_goals, 1e-3)
            open_target = np.maximum(target - pen_goals, 1e-3)
            scale *= open_target / open_sim
        self.scale = scale
        return self._run(cfg.n_sims, rng, scale)
