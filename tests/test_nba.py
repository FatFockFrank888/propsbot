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
