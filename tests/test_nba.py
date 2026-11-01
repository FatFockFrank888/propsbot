"""NBA-tolkning (byggt efter källornas kända format, inte inspelat)."""
from propsbot.nba import _box_value, nba_market, pinnacle_nba_props


def test_nba_market_labels():
    assert nba_market("Points scored by the player - Including Overtime") == "points"
    assert nba_market("Player's rebounds - Including Overtime") == "rebounds"
    assert nba_market("Assists by the player - Including Overtime") == "assists"
    assert nba_market("3-point field goals made by the player - Including Overtime") == "threes"
    assert nba_market("Points, rebounds & assists by the player - Including Overtime") == "pra"
    assert nba_market("Pts+Rebs+Asts") == "pra"
    assert nba_market("Points + Rebounds") == "pr"
    assert nba_market("Rebounds + Assists by the player") == "ra"
    assert nba_market("Steals by the player - Including Overtime") == "steals"
    assert nba_market("Blocks by the player") == "blocks"
    assert nba_market("Points + Assists") is None
    assert nba_market("Points scored by the player - 1st Quarter") is None
    assert nba_market("To record a double double") is None


def test_box_value():
    labels = ["MIN", "FG", "3PT", "FT", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "+/-", "PTS"]
    stats = ["35", "10-18", "3-7", "4-4", "1", "6", "7", "9", "1", "0", "3", "2", "+8", "27"]
    assert _box_value(labels, stats, "points") == 27
    assert _box_value(labels, stats, "threes") == 3
    assert _box_value(labels, stats, "pra") == 43
    assert _box_value(labels, stats, "pr") == 34 and _box_value(labels, stats, "ra") == 16
    assert _box_value(labels, stats, "steals") == 1 and _box_value(labels, stats, "blocks") == 0


class _Pin:
    def __init__(self, related, markets):
        self.c = self
        self._d = {"related": related, "straight": markets}

    def get(self, url, *a, **k):
        return self._d["related"] if url.endswith("/related") else self._d["straight"]


def test_pinnacle_nba_props():
    related = [{"id": 5, "type": "special", "special": {"description": "LeBron James (Points)",
                                                         "category": "Player Props"},
                "participants": [{"id": 1, "name": "Over"}, {"id": 2, "name": "Under"}]},
               {"id": 6, "type": "special", "special": {"description": "Lakers Total Points",
                                                         "category": "Team Props"},
                "participants": [{"id": 3, "name": "Over"}]}]
    markets = [{"matchupId": 5, "prices": [{"participantId": 1, "price": -115, "points": 25.5},
                                           {"participantId": 2, "price": -105, "points": 25.5}]},
               {"matchupId": 6, "prices": [{"participantId": 3, "price": -110, "points": 115.5}]}]

    class Ev:
        matchup_id = 1
    qs, names = pinnacle_nba_props(_Pin(related, markets), Ev(), "nba1")
    assert {(q.market, q.line, q.side) for q in qs} == {("points", 25.5, "over"), ("points", 25.5, "under")}
    assert names == {"lebron james": "LeBron James"}


def test_interpolate_pinnacle_moves_line():
    from propsbot.models import OddsQuote
    from propsbot.nba import interpolate_pinnacle
    qs = [OddsQuote("pinnacle", "m", "x", "points", 25.5, "over", 1.90, 0, provider="pinnacle"),
          OddsQuote("pinnacle", "m", "x", "points", 25.5, "under", 1.90, 0, provider="pinnacle"),
          OddsQuote("unibet", "m", "x", "points", 23.5, "over", 1.60, 0, provider="kambi"),
          OddsQuote("unibet", "m", "x", "points", 30.5, "over", 4.00, 0, provider="kambi")]
    assert interpolate_pinnacle(qs) == 1              # 30,5 ligger för långt bort
    new = {q.side: q.odds for q in qs if q.line == 23.5 and q.book == "pinnacle"}
    p_over = 1 / new["over"]
    assert 0.55 < p_over < 0.7 and abs(1 / new["over"] + 1 / new["under"] - 1) < 1e-9


def test_under_is_evaluated_and_settled(tmp_path):
    import time
    from propsbot.config import Config
    from propsbot.ledger import Ledger
    from propsbot.models import OddsQuote
    from propsbot.scan import DEFAULT_SETTINGS, evaluate_event_market_only
    now = time.time()
    ev = {"id": "nba1", "home_team": "A", "away_team": "B", "commence_time": now + 7200}
    q = [OddsQuote("pinnacle", "nba1", "x", "points", 24.5, "over", 2.10, now, provider="pinnacle"),
         OddsQuote("pinnacle", "nba1", "x", "points", 24.5, "under", 1.78, now, provider="pinnacle"),
         OddsQuote("unibet", "nba1", "x", "points", 24.5, "over", 1.80, now, provider="kambi"),
         OddsQuote("unibet", "nba1", "x", "points", 24.5, "under", 1.98, now, provider="kambi")]
    rows = evaluate_event_market_only(ev, q, {"x": "X"}, dict(DEFAULT_SETTINGS, playable_books=[]),
                                      Config(), now, "NBA")
    under = [r for r in rows if r.row.decision.cand.best.side == "under"]
    assert under and under[0].row.decision.playable and under[0].row.decision.cand.edge > 0.02
    lg = Ledger(tmp_path / "b.json")
    lg.record(rows, {"nba1": ev})
    b = next(b for b in lg.bets if b["sida"] == "under")
    assert b["key"].endswith("|under")
    lg.settle(b, 20, True)
    assert b["status"] == "vunnen"                       # 20 poäng < 24,5
