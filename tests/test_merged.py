"""Sammanslagna boten: spelarspärr, kort, NHL-testmarknader, webbsidans NHL-format."""
import math
from datetime import date

from propsbot.notify import PlayerGuard
from propsbot.sources.props_text import market_from_label


def test_player_guard_one_bet_per_player_and_match(tmp_path):
    g = PlayerGuard(tmp_path / "g.json")
    assert g.allows("nba", "m1", "LeBron James", "points|25.5")
    g.mark("nba", "m1", "LeBron James", "points|25.5")
    g.save()
    g = PlayerGuard(tmp_path / "g.json")
    assert g.allows("nba", "m1", "Lebron James", "points|25.5")          # samma spel: ok (omskick)
    assert not g.allows("nba", "m1", "LeBron James", "rebounds|7.5")     # annan marknad: nej
    assert not g.allows("nba", "m1", "LeBron James", "points|25.5|under")
    assert g.allows("nba", "m2", "LeBron James", "points|25.5")          # annan match: ok


def test_card_labels():
    assert market_from_label("To Get a Card") == ("cards", 0.5)
    assert market_from_label("To Get a Red Card") is None
    assert market_from_label("To Score or Get a Card") is None


def test_nhl_test_market_parse_and_poisson():
    from nhl.test_markets import market_of, parse_kambi, poisson_at_least
    assert market_of("Player to score at least 2 points - Including Overtime") == ("nhl_points", 1.5)
    assert market_of("Player to record at least 1 assists - Including Overtime") == ("nhl_assists", 0.5)
    assert market_of("To score - Including Overtime") == ("nhl_goals", 0.5)
    assert market_of("Player To score at least 1 Power Play Points -  Including Overtime") == ("nhl_pp_points", 0.5)
    assert market_of("Player To score at least 2 Power Play Points -  Including Overtime") == ("nhl_pp_points", 1.5)
    assert market_of("Total Power Play Goals by Utah Mammoth - Including Overtime") is None
    assert market_of("Total Power Play Goals - Including Overtime") is None
    assert market_of("Player's shots on goal - Including Overtime") is None
    raw = {"betOffers": [{"criterion": {"englishLabel": "Player to score at least 1 points - Including Overtime"},
                          "outcomes": [{"participant": "A B", "englishLabel": "Yes", "line": 1000, "odds": 2950},
                                       {"participant": "A B", "englishLabel": "No", "line": 1000, "odds": 1360}]}]}
    qs = parse_kambi(raw, "unibet")
    assert {(q.side, q.line, q.odds) for q in qs} == {("over", 0.5, 2.95), ("under", 0.5, 1.36)}
    assert abs(poisson_at_least(1, 0.5) - (1 - math.exp(-0.5))) < 1e-12


def test_nhl_pp_points_settle_from_game_log(tmp_path):
    from nhl.bot_settings import BotSettings
    from nhl.test_markets import TestMarkets
    tm = TestMarkets(tmp_path, BotSettings())
    tm.bets = [{"game_id": 5, "spelare_id": 9, "status": "öppen", "avspark": 1000, "marknad": "nhl_pp_points",
                "linje": 0.5, "sida": "over", "odds": 3.0, "insats_pct": 0.002}]
    box = {"gameState": "OFF", "playerByGameStats": {"homeTeam": {"forwards": [{"playerId": 9, "goals": 1, "assists": 0}]}}}
    assert tm.settle(lambda gid: box, now=1e10, fetch_pp=lambda pid, gid: None) == 0   # game log not updated yet
    assert tm.bets[0]["status"] == "öppen"
    assert tm.settle(lambda gid: box, now=1e10, fetch_pp=lambda pid, gid: {"pp_points": 1, "pp_goals": 1}) == 1
    assert tm.bets[0]["status"] == "vunnen" and tm.bets[0]["utfall"] == 1


def test_nhl_test_market_settles_from_boxscore(tmp_path):
    from nhl.bot_settings import BotSettings
    from nhl.test_markets import TestMarkets
    tm = TestMarkets(tmp_path, BotSettings())
    tm.bets = [{"game_id": 5, "spelare_id": 9, "status": "öppen", "avspark": 1000, "marknad": "nhl_points",
                "linje": 0.5, "sida": "under", "odds": 1.4, "insats_pct": 0.004}]
    box = {"gameState": "OFF", "playerByGameStats": {"homeTeam": {"forwards": [{"playerId": 9, "goals": 0, "assists": 0}]}}}
    assert tm.settle(lambda gid: box, now=1e10) == 1
    assert tm.bets[0]["status"] == "vunnen" and abs(tm.bets[0]["resultat_enheter"] - 0.0016) < 1e-9


def test_nhl_ledger_to_site_format():
    from nhl.site_export import ledger_sv
    b = {"id": "x", "created": "2026-11-04T16:00:00+00:00", "game_id": 1, "game": "OTT@BUF",
         "start": "2026-11-05T00:30:00+00:00", "player": "Tim Stützle", "player_id": 7, "line": 2.5, "side": "under",
         "book": "unibet", "odds": 1.9, "units": 3, "p_fair": 0.56, "edge": 0.064, "model_edge": 0.05,
         "close_odds": 1.85, "status": "won", "result_sog": 1, "profit_units": 2.7, "reasons": []}
    x = ledger_sv(b, 0.002)
    assert x["status"] == "vunnen" and x["marknad"] == "sog" and x["sida"] == "under"
    assert x["match"] == "OTT – BUF" and abs(x["insats_pct"] - 0.006) < 1e-12 and abs(x["resultat_enheter"] - 0.0054) < 1e-12
