from dataclasses import replace
from datetime import date, timedelta

import pytest

from nhl.backtest import Record, fit_dispersion, summarize
from nhl.config import Settings, previous_season, season_for
from nhl.edges import evaluate
from nhl.nhl_api import Game, LogEntry, Skater, TeamDefense, parse_toi
from nhl.odds import PropQuote
from nhl.projections import decay_weights, estimate_mean, opponent_factor, venue_factor
from nhl.slate import Projection

S = Settings()


def _log(shots, toi=18.0, n=None):
    shots = list(shots)
    start = date(2026, 10, 1)
    return [
        LogEntry(game_id=i, game_date=start + timedelta(days=i), team="BUF", opponent="TOR", home=i % 2 == 0, shots=s, toi=toi)
        for i, s in enumerate(shots)
    ]


def test_season_helpers():
    assert season_for(date(2026, 11, 4)) == "20262027"
    assert season_for(date(2027, 3, 1)) == "20262027"
    assert previous_season("20262027") == "20252026"
    assert parse_toi("23:20") == pytest.approx(23 + 1 / 3)
    assert parse_toi(None) == 0.0


def test_decay_weights():
    w = decay_weights(3, 1.0)
    assert w == [1.0, 0.5, 0.25]


def test_estimate_no_history_uses_prior():
    est = estimate_mean([], "F", S)
    assert est.games_used == 0
    assert est.proj_toi == S.forward_default_toi
    assert est.base_mu == pytest.approx(S.forward_prior_rate * S.forward_default_toi)


def test_estimate_shrinks_toward_prior_and_tracks_volume():
    high = estimate_mean(_log([5] * 25, toi=20.0), "F", S)
    low = estimate_mean(_log([0] * 25, toi=20.0), "F", S)
    assert low.base_mu < S.forward_prior_rate * 20 < high.base_mu
    assert high.base_mu < 5.0  # shrinkage
    assert high.base_mu > 4.0  # but not too much with 25 games
    assert high.proj_toi == pytest.approx(20.0)


def test_toi_ignores_short_injury_games():
    entries = _log([2] * 10, toi=18.0)
    entries[-1] = replace(entries[-1], toi=2.0)
    assert estimate_mean(entries, "D", S).proj_toi == pytest.approx(18.0)


def test_opponent_and_venue_factors():
    loose = TeamDefense("SJS", 40, 33.0)
    tight = TeamDefense("CAR", 40, 25.0)
    assert opponent_factor(loose, 29.0, S) > 1.0 > opponent_factor(tight, 29.0, S)
    assert opponent_factor(TeamDefense("X", 1, 60.0), 29.0, S) <= S.opp_factor_cap
    assert opponent_factor(None, 29.0, S) == 1.0
    assert venue_factor(True, S) > venue_factor(False, S)


def _projection(mu=3.2, active=True, games=20):
    game = Game(99, date(2026, 11, 4), None, "BUF", "MTL", "FUT", 2, "20262027")
    est = estimate_mean(_log([3] * games), "F", S)
    est = replace(est, base_mu=mu, games_used=games)
    return Projection(
        game=game, skater=Skater(1, "Tage Thompson", "BUF", "F", "C"), opponent="MTL", home=True,
        estimate=est, opp_factor=1.0, venue_factor=1.0, mu=mu, active=active, last_game=date(2026, 11, 2),
        season_gp=games, season_avg=3.0, recent_shots=(3,) * 10,
    )


def test_evaluate_finds_over_value_at_bet_book_only():
    proj = _projection(mu=3.6)
    quotes = [
        PropQuote("unibet", "Tage Thompson", 2.5, 2.05, 1.75, "csv"),
        PropQuote("draftkings", "Tage Thompson", 2.5, 1.95, 1.87, "odds_api", game_id=99),
    ]
    evals, unmatched = evaluate([proj], quotes, S)
    assert not unmatched
    picks = [e for e in evals if e.is_pick]
    assert len(picks) == 1
    pick = picks[0]
    assert pick.side == "over" and pick.book == "unibet" and pick.odds == 2.05
    assert pick.market_source == "reference"
    assert pick.ev > 0 and pick.stake > 0
    assert pick.stake <= S.bankroll * S.max_stake_pct


def test_evaluate_rejects_inactive_and_small_sample():
    q = [PropQuote("atg", "Tage Thompson", 2.5, 2.4, 1.6, "csv")]
    evals, _ = evaluate([_projection(mu=3.6, active=False)], q, S)
    assert not any(e.is_pick for e in evals)
    evals, _ = evaluate([_projection(mu=3.6, games=3)], q, S)
    assert not any(e.is_pick for e in evals)


def test_evaluate_ignores_non_bet_books():
    q = [PropQuote("draftkings", "Tage Thompson", 2.5, 3.0, 1.4, "odds_api", game_id=99)]
    evals, _ = evaluate([_projection(mu=3.6)], q, S)
    assert evals == []


def test_backtest_summary_and_dispersion():
    recs = [Record(mu=2.0, baseline=2.0, actual=a) for a in [0, 1, 2, 2, 3, 4, 2, 1, 3, 2]]
    summary = summarize(recs, [1.5], 0.0)
    assert summary["n"] == 10
    assert summary["mean_actual"] == pytest.approx(2.0)
    assert 0.0 <= summary["lines"][1.5]["brier_model"] <= 1.0
    assert fit_dispersion(recs) == 0.0  # underdispersed sample clips at 0
