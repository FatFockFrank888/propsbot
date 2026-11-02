import math
from pathlib import Path

import numpy as np
import pytest

from propsbot.blend import (SettledLine, blend, cluster_level_bias, fit_level_calibration,
                            model_weight)
from propsbot.config import SHOT_TYPES, BlendConfig, CalibrationConfig, Config, DecisionConfig, \
    MarketConfig, MatchupConfig
from propsbot.decision import Candidate, apply_portfolio_limits, evaluate, play_from_odds
from propsbot.form import PlayerMatchRow, build_player_profile, role_changed
from propsbot.kambi import group_books_by_provider, master_prices, measure_lag
from propsbot.market import (_outcome_probs, _p_over_total, devig_power, devig_proportional,
                             devig_shin, estimate_one_sided_margin, fair_prob_one_sided,
                             lambda_from_team_total, lambdas_from_1x2_total, prop_market_prob)
from propsbot.models import MinutesModel, OddsQuote
from propsbot.simulator import MatchSimulator
from propsbot.sources.json_source import load_match
from propsbot.store import Store
from propsbot.volume import matchup_multipliers

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "match.json"


# ------------------------------------------------------------------ market
@pytest.mark.parametrize("fn", [devig_proportional, devig_power, devig_shin])
def test_devig_sums_to_one(fn):
    p = fn([1.62, 4.10, 5.60])
    assert abs(sum(p) - 1) < 1e-9
    assert p[0] > p[1] > 0 and p[0] > p[2]


def test_power_devig_shifts_margin_to_longshot():
    prop = devig_proportional([1.30, 3.60])
    power = devig_power([1.30, 3.60])
    assert power[0] > prop[0]  # favoriten får högre sannolikhet än proportionellt


def test_lambdas_roundtrip():
    lh, la = 1.75, 1.05
    h, d, a, grid = _outcome_probs(lh, la)
    po = _p_over_total(grid, 2.5)
    rh, ra = lambdas_from_1x2_total(h, a, po, 2.5)
    assert abs(rh - lh) < 0.01 and abs(ra - la) < 0.01


def test_team_total_roundtrip():
    lam = 1.4
    p_over = 1 - math.exp(-lam) * (1 + lam)  # över 1.5
    assert abs(lambda_from_team_total(p_over, 1.5) - lam) < 0.01


def test_one_sided_margin_estimation_recovers_truth():
    rng = np.random.default_rng(0)
    pairs = []
    for _ in range(2000):
        p = rng.uniform(0.1, 0.7)
        odds = 1 / (p * (1 + 0.09 + 0.02 * (1 / p - 2)))
        # odds-2 ≈ 1/p-2 när marginalen är liten; generera exakt via iteration
        for _ in range(5):
            odds = 1 / (p * (1 + 0.09 + 0.02 * (odds - 2)))
        pairs.append((odds, p))
    base, slope = estimate_one_sided_margin(pairs, prior=(0.05, 0.0), prior_n=20)
    assert abs(base - 0.09) < 0.01 and abs(slope - 0.02) < 0.005


def test_kambi_counts_as_one_vote_and_pinnacle_dominates():
    cfg = MarketConfig()
    v = prop_market_prob("shots", cfg, pinnacle_over=1.90, pinnacle_under=1.95,
                         kambi_master_over=1.70)
    assert v.pinnacle_present
    assert abs(v.p_market - v.p_pinnacle) < abs(v.p_market - v.p_kambi)
    assert fair_prob_one_sided("shots", 1.70, cfg) < 1 / 1.70


# --------------------------------------------------------------- simulator
@pytest.fixture(scope="module")
def example():
    match, quotes = load_match(EXAMPLE)
    cfg = Config()
    cfg.sim.n_sims = 5000
    sim = MatchSimulator(match, cfg).run()
    return match, quotes, sim, cfg


def test_sim_goals_match_pinnacle(example):
    match, _, sim, _ = example
    assert abs(sim.goals_home.mean() - match.home.exp_goals) < 0.08
    assert abs(sim.goals_away.mean() - match.away.exp_goals) < 0.08


def test_sim_consistency(example):
    _, _, sim, _ = example
    c = sim.counts
    assert (c["shots"] >= c["shots_on_target"]).all()
    assert (c["shots_on_target"] >= c["goal"]).all()
    # mål per lag = summan av spelarnas mål
    home = sim.team_of == 0
    assert (c["goal"][:, home].sum(1) == sim.goals_home).all()


def test_non_playing_player_excluded(example):
    _, _, sim, _ = example
    assert sim.n_played("H12") == 0          # bänk, byts aldrig in
    assert math.isnan(sim.prob_over("H12", "shots", 0.5))
    assert sim.n_played("H1") == sim.played.shape[0]  # startande målvakt


def test_probabilities_monotone_in_line(example):
    _, _, sim, _ = example
    ps = [sim.prob_over("H11", "shots", l) for l in (0.5, 1.5, 2.5, 3.5)]
    assert all(a > b for a, b in zip(ps, ps[1:]))


def test_goalkeeper_never_shoots(example):
    _, _, sim, _ = example
    assert sim.mean("H1", "shots") == 0


# ---------------------------------------------------------------- matchup
def test_low_block_increases_distance_and_is_capped(example):
    match, _, _, _ = example
    cfg = MatchupConfig()
    import copy
    team = copy.deepcopy(match.home)
    team.opponent.allowed_mult = {t: 1.0 for t in SHOT_TYPES}
    team.opponent.block_height = -1.5
    m_low = matchup_multipliers(team, 0.55, cfg)
    team.opponent.block_height = 1.5
    m_high = matchup_multipliers(team, 0.55, cfg)
    assert m_low["distance"] > m_high["distance"]
    assert m_high["counter"] > m_low["counter"]
    team.opponent.block_height = -10
    m_ext = matchup_multipliers(team, 0.9, cfg)
    assert all(abs(m_ext[t] - 1) <= cfg.max_effect + 1e-9 for t in SHOT_TYPES if t != "penalty")


# ------------------------------------------------------------- blandning
def test_model_weight_rules():
    cfg = BlendConfig()
    pre = model_weight("shots", False, False, 0.5, 0.5, cfg)
    post = model_weight("shots", True, False, 0.5, 0.5, cfg)
    pin = model_weight("shots", True, True, 0.5, 0.5, cfg)
    far = model_weight("shots", True, False, 0.8, 0.4, cfg)
    goal = model_weight("goal", True, False, 0.5, 0.5, cfg)
    assert pre < post and pin < post and far < post and goal < post
    assert far >= cfg.w_model_min


def test_blend_between():
    p = blend(0.6, 0.4, 0.5)
    assert 0.4 < p < 0.6


def test_level_calibration_shrinks():
    lines = [SettledLine(f"m{i // 10}", "shots", 0.5, int(i % 10 < 6 and i % 37 != 0))
             for i in range(400)]
    small_k = fit_level_calibration(lines, CalibrationConfig(shrink_k=50))
    big_k = fit_level_calibration(lines, CalibrationConfig(shrink_k=600))
    assert small_k.offset["shots"] > big_k.offset["shots"] > 0
    assert small_k.n_matches["shots"] == 40
    mean, se = cluster_level_bias(lines)["shots"]
    assert 0.0 < mean < 0.1 and se > 0


# --------------------------------------------------------------- beslut
def _cand(p, odds, ts=1000.0, now=1000.0, market="shots", player="x", consensus=None,
          lineup=True, mtk=60.0):
    q = OddsQuote("unibet", "m", player, market, 0.5, "over", odds, ts)
    return Candidate("m", player, player, market, 0.5, p, q, consensus, now, lineup, mtk)


def test_play_from_and_thresholds():
    cfg = DecisionConfig()
    assert play_from_odds(0.8, 0.02, 1.40) == pytest.approx(1.40)
    assert play_from_odds(0.5, 0.02, 1.40) == pytest.approx(2.04)
    d = evaluate(_cand(0.55, 2.00), cfg)
    assert d.playable and d.show and d.stake > 0
    d = evaluate(_cand(0.70, 1.65), cfg)        # inom ramen 1,60–6,00
    assert d.playable and d.show
    d = evaluate(_cand(0.75, 1.45), cfg)        # under 1,60 – varken spel eller visning
    assert not d.playable and not d.show
    d = evaluate(_cand(0.25, 7.00), cfg)        # över 6,00
    assert not d.playable and not d.show
    d = evaluate(_cand(0.80, 1.35), cfg)        # under 1,60
    assert not d.playable
    d = evaluate(_cand(0.55, 2.00, ts=0, now=1000), cfg)  # gammalt odds
    assert not d.playable
    d = evaluate(_cand(0.30, 4.00, market="goal"), cfg)   # 20 % edge men...
    assert d.playable
    d = evaluate(_cand(0.27, 3.80, market="goal"), cfg)   # 2.6 % < 4 % för mål
    assert not d.playable
    d = evaluate(_cand(0.55, 2.0, lineup=False, mtk=10), cfg)
    assert not d.playable


def test_portfolio_one_leg_per_family():
    cfg = DecisionConfig()
    a = evaluate(_cand(0.55, 2.00, market="shots"), cfg)
    b = evaluate(_cand(0.40, 2.80, market="shots_on_target"), cfg)
    c = evaluate(_cand(0.30, 4.00, market="goal"), cfg)
    apply_portfolio_limits([a, b, c], cfg)
    assert sum(d.playable for d in (a, b)) == 1
    assert c.playable
    total = sum(d.stake for d in (a, b, c))
    assert total <= cfg.max_stake_per_match + 1e-12


# ----------------------------------------------------------------- kambi
def _book_quotes(book, base, noise, rng, ts=0.0):
    return [OddsQuote(book, "m", f"p{i}", "shots", 0.5, "over",
                      round(1 / min(0.95, max(0.05, b + rng.normal(0, noise))), 2), ts)
            for i, b in enumerate(base)]


def test_group_books_by_provider():
    rng = np.random.default_rng(1)
    base = rng.uniform(0.15, 0.8, 80)
    qs = (_book_quotes("unibet", base, 0.0, rng) + _book_quotes("paf", base, 0.002, rng)
          + _book_quotes("atg", base, 0.002, rng) + _book_quotes("bet365", base, 0.06, rng))
    groups = group_books_by_provider(qs, MarketConfig())
    assert {"unibet", "paf", "atg"} in groups
    assert {"bet365"} in groups


def test_measure_lag():
    group = {"unibet", "paf", "slow"}
    def snap(ts, prices):
        return ts, [OddsQuote(b, "m", "p", "shots", 0.5, "over", o, ts) for b, o in prices.items()]
    snaps = [snap(0, {"unibet": 2.0, "paf": 2.0, "slow": 2.0}),
             snap(10, {"unibet": 1.7, "paf": 1.7, "slow": 2.0}),
             snap(70, {"unibet": 1.7, "paf": 1.7, "slow": 1.7})]
    st = measure_lag(snaps, group)
    assert st["paf"].median_lag_s == 0
    assert st["slow"].median_lag_s == 60
    mp = master_prices(snaps[1][1], group)
    assert list(mp.values())[0] == 1.7


# ------------------------------------------------------------------ form
def _row(minutes=90, pos="ST", shots=3, team=15, manager="A", date="d"):
    return PlayerMatchRow(date=date, minutes=minutes, position=pos,
                          shots={"box": shots}, sot={"box": shots / 2}, xg={"box": 0.15 * shots},
                          team_shots={"box": team}, team_xa=1.0, xa=0.1, manager=manager)


def test_form_shrinks_with_little_data_and_weights_recent():
    mm = MinutesModel(p_start=1.0)
    few = build_player_profile("p", "P", "T", "ST", [_row(shots=12)], mm)
    many = build_player_profile("p", "P", "T", "ST", [_row(shots=12)] * 30, mm)
    assert few.share["box"] < many.share["box"]   # krympt mot prior
    old_hot = [_row(shots=8)] * 10 + [_row(shots=1)] * 10
    new_hot = [_row(shots=1)] * 10 + [_row(shots=8)] * 10
    a = build_player_profile("p", "P", "T", "ST", old_hot, mm)
    b = build_player_profile("p", "P", "T", "ST", new_hot, mm)
    assert b.share["box"] > a.share["box"]


def test_role_change_detection():
    rows = [_row(pos="W")] * 8 + [_row(pos="ST")] * 2 + [_row(pos="W")]
    assert role_changed(rows)
    rows = [_row(manager="A")] * 8 + [_row(manager="B")]
    assert role_changed(rows)
    assert not role_changed([_row()] * 10)


# ----------------------------------------------------------------- store
def test_store_roundtrip(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    s.log_prediction(dict(ts=1, match_id="m", player_id="p", player_name="P", market="shots",
                          line=0.5, p_model=0.5, p_market=0.5, p_final=0.55, w_model=0.5,
                          lineup_confirmed=1, best_book="unibet", best_odds=2.0, edge=0.1,
                          play_from=1.85, playable=1, shown=1, stake=0.01, reasons=""))
    s.record_closing("m", "p", "shots", 0.5, 0.53)
    s.record_result("m", "p", "shots", 2, True)
    (mk, n, clv, edge), = s.clv_report()
    assert mk == "shots" and n == 1 and clv == pytest.approx(0.06)
    (l,) = s.settled_lines()
    assert l.outcome == 1 and l.p == 0.55


def test_no_bets_after_kickoff():
    cfg = DecisionConfig()
    d = evaluate(_cand(0.55, 2.00, mtk=-5), cfg)
    assert not d.playable and any("startat" in r for r in d.reasons)
    assert evaluate(_cand(0.55, 2.00, mtk=30), cfg).playable
