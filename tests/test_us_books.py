from propsbot.sources.us_books import parse


def test_parse_dk_fd_two_sided():
    ev = {"bookmakers": [{"key": "draftkings", "markets": [{"key": "player_threes", "outcomes": [
        {"name": "Over", "description": "Donovan Mitchell", "price": 1.87, "point": 3.5},
        {"name": "Under", "description": "Donovan Mitchell", "price": 1.95, "point": 3.5},
        {"name": "Over", "description": "", "price": 1.9, "point": 1.5}]}]},
        {"key": "fanduel", "markets": [{"key": "player_turnovers", "outcomes": [
            {"name": "Over", "description": "X", "price": 1.9, "point": 1.5}]}]}]}
    q, names = parse(ev, "nba1", 5.0)
    assert [(x.book, x.market, x.side, x.line, x.odds) for x in q] == [
        ("draftkings", "threes", "over", 3.5, 1.87), ("draftkings", "threes", "under", 3.5, 1.95)]
    assert names == {"donovan mitchell": "Donovan Mitchell"} and q[0].ts == 5.0
