import pytest

from nhl.engine import play_down_to
from nhl.sources.bovada import parse_events, parse_sog
from nhl.validate import bet_validation, edge_buckets, leg_validation, mean_se, needed_n, verdict

BOVADA_EVENT = [{
    "events": [{
        "id": "1", "live": False, "startTime": 1793750400000, "link": "/hockey/nhl/x",
        "competitors": [{"name": "Columbus Blue Jackets", "home": True}, {"name": "Colorado Avalanche", "home": False}],
        "displayGroups": [{"description": "Shots on Goal", "markets": [
            {"descriptionKey": "Total Shots On Goal - Adam Fantilli", "description": "Total Shots On Goal - Adam Fantilli (CBJ)",
             "status": "O", "period": {"main": True},
             "outcomes": [{"type": "O", "status": "O", "price": {"handicap": "2.5", "decimal": "1.666667"}},
                          {"type": "U", "status": "O", "price": {"handicap": "2.5", "decimal": "2.150"}}]},
            {"descriptionKey": "Total Shots on Goal", "status": "O", "outcomes": []},
            {"descriptionKey": "Total Shots On Goal - Cale Makar", "status": "O", "period": {"main": False}, "outcomes": [
                {"type": "O", "status": "O", "price": {"handicap": "3.5", "decimal": "2.0"}}]},
        ]}],
    }]
}]


def test_bovada_parse():
    (ev,) = parse_events(BOVADA_EVENT)
    assert (ev.home, ev.away, ev.link) == ("Columbus Blue Jackets", "Colorado Avalanche", "/hockey/nhl/x")
    (q,) = parse_sog(BOVADA_EVENT, now=1.0)
    assert (q.player, q.line, q.over, q.under, q.group) == ("Adam Fantilli", 2.5, pytest.approx(1.6667), 2.15, "bovada")
    assert not q.playable


def test_bovada_ladder_fit_recovers_mu_and_margin():
    from nhl.model import line_probs
    from nhl.sources.bovada import fit_ladder, ladder_quotes

    mu, margin = 3.1, 0.07
    rungs = {n: 1 / ((1 + margin) * line_probs(n - 0.5, mu, 0.05).over) for n in range(1, 6)}
    fit_mu, fit_margin = fit_ladder(rungs, 0.05)
    assert fit_mu == pytest.approx(mu, abs=0.02)
    assert fit_margin == pytest.approx(margin, abs=0.005)
    quotes = ladder_quotes("Tage Thompson", rungs, 0.05, 1.0)
    q25 = next(q for q in quotes if q.line == 2.5)
    assert 1 / q25.over == pytest.approx(line_probs(2.5, mu, 0.05).over, abs=0.005)
    assert 1 / q25.over + 1 / q25.under == pytest.approx(1.0, abs=1e-3)
    assert fit_ladder({2: 1.2, 3: 1.6}, 0.05) is None  # too few rungs


def test_play_down_to():
    assert play_down_to(0.5, 0.06) == 2.12
    assert play_down_to(None, 0.06) is None


def test_mean_se_and_needed_n():
    m, se, n = mean_se([0.1, -0.1, 0.1, -0.1])
    assert m == 0 and n == 4 and se > 0
    assert needed_n(0.05, 0.01, 100) == pytest.approx(16, abs=1)  # sd = 0.1 -> (1.96*0.1/0.05)^2
    assert needed_n(-0.01, 0.01, 100) is None


def _bet(edge, clv, status="won", odds=2.0, units=2):
    profit = units * (odds - 1) if status == "won" else (-units if status == "lost" else 0)
    return {"edge": edge, "clv": clv, "kambi_clv": clv / 2, "price_clv": 0.0, "status": status, "units": units,
            "odds": odds, "profit_units": profit if status != "open" else None}


def test_bet_validation_and_verdict_positive_clv():
    bets = [_bet(0.07, 0.04 + (i % 3) * 0.01, "won" if i % 2 else "lost") for i in range(40)]
    v = bet_validation(bets)
    assert v["settled"] == 40 and v["clv"]["n"] == 40
    assert v["clv"]["t"] > 2
    text = "\n".join(verdict(v, None))
    assert "Beating the closing line" in text


def test_verdict_needs_sample():
    v = bet_validation([_bet(0.07, 0.03)])
    assert "needs at least" in verdict(v, None)[0]


def test_edge_buckets():
    rows = edge_buckets([_bet(0.06, 0.02), _bet(0.10, 0.04), _bet(0.20, 0.08, "lost")])
    assert [r["n"] for r in rows] == [1, 1, 1]
    assert rows[2]["roi"] == -1.0


def test_leg_validation_scores_and_flagged():
    legs = []
    for i in range(20):
        won = i % 2 == 0
        legs.append({
            "game_id": 1, "player_id": i, "line": 2.5, "side": "over", "outcome": "won" if won else "lost",
            "close_p_model": 0.6 if won else 0.4, "close_p_market": 0.5, "close_p_fair": 0.55 if won else 0.45,
            "close_p_kambi": 0.5, "max_edge": 0.08, "max_edge_passed": 1, "max_edge_odds": 2.2,
        })
    out = leg_validation(legs, 0.05)
    assert out["graded_lines"] == 20 and out["compared"] == 20
    assert out["scores"]["close_p_model"]["log_loss"] < out["scores"]["close_p_market"]["log_loss"]
    assert out["flagged_clv"]["mean"] == pytest.approx(2.2 * 0.5 - 1)
    assert out["calibration"]
