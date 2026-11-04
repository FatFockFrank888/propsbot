from datetime import date, datetime, timezone

import pytest

from nhl.names import NameMatcher, normalize_book, normalize_name
from nhl.nhl_api import Game
from nhl.odds import OddsEvent, load_odds_csv, match_events, parse_event_odds


def test_normalize_name():
    assert normalize_name("J.T. Miller") == "jt miller"
    assert normalize_name("JT Miller") == "jt miller"
    assert normalize_name("Tim Stützle") == "tim stutzle"
    assert normalize_name("Ryan O'Reilly") == "ryan oreilly"
    assert normalize_name("Pierre-Luc Dubois") == "pierre luc dubois"
    assert normalize_name("Martin St. Louis Jr.") == "martin st louis"
    assert normalize_name("Stützle, Tim") == "tim stutzle"
    assert normalize_name("Smith, Jr.") == "smith"


def test_normalize_book():
    assert normalize_book("Svenska Spel") == "svenskaspel"
    assert normalize_book("svenskaspel_se") == "svenskaspel"
    assert normalize_book("Oddset") == "svenskaspel"
    assert normalize_book("Unibet (SE)") == "unibet"
    assert normalize_book("unibet_se") == "unibet"
    assert normalize_book("ATG") == "atg"
    assert normalize_book("atg_se") == "atg"


def test_matcher_fallbacks_and_ambiguity():
    m = NameMatcher([("Mitchell Marner", 1), ("Auston Matthews", 2), ("Erik Karlsson", 3), ("Elias Karlsson", 4)])
    assert m.match("Mitch Marner") == 1  # initial + last name
    assert m.match("auston matthews") == 2
    assert m.match("E. Karlsson") is None  # ambiguous
    assert m.match("Erik Karlsson") == 3
    assert m.match("Nobody Here") is None


def test_parse_event_odds_groups_sides():
    data = {
        "bookmakers": [
            {
                "key": "unibet_se",
                "markets": [
                    {
                        "key": "player_shots_on_goal",
                        "outcomes": [
                            {"name": "Over", "description": "Rasmus Dahlin", "price": 1.9, "point": 2.5},
                            {"name": "Under", "description": "Rasmus Dahlin", "price": 1.85, "point": 2.5},
                        ],
                    }
                ],
            }
        ]
    }
    quotes = parse_event_odds(data, game_id=7)
    assert len(quotes) == 1
    q = quotes[0]
    assert (q.book, q.player, q.line, q.over, q.under, q.game_id) == ("unibet", "Rasmus Dahlin", 2.5, 1.9, 1.85, 7)


def test_match_events():
    game = Game(1, date(2026, 11, 4), datetime(2026, 11, 5, 0, 30, tzinfo=timezone.utc), "BUF", "MTL", "FUT", 2, "20262027")
    names = {"buffalo sabres": "BUF", "montreal canadiens": "MTL"}
    events = [OddsEvent("abc", "Buffalo Sabres", "Montréal Canadiens", datetime(2026, 11, 5, 0, 30, tzinfo=timezone.utc))]
    assert match_events([game], events, names) == {1: "abc"}


def test_load_odds_csv(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text(
        "book;player;team;line;over;under\n"
        "Unibet;Rasmus Dahlin;BUF;2,5;1,90;1,85\n"
        "Svenska Spel;Tage Thompson;BUF;3.5;2.10;\n"
        ";Blank Book;BUF;2.5;1.9;1.9\n"
        "ATG;No Odds;BUF;1.5;;\n",
        encoding="utf-8",
    )
    quotes = load_odds_csv(path)
    assert len(quotes) == 2
    assert quotes[0].book == "unibet" and quotes[0].line == 2.5 and quotes[0].over == pytest.approx(1.9)
    assert quotes[1].book == "svenskaspel" and quotes[1].under is None


def test_load_odds_csv_bad_value(tmp_path):
    path = tmp_path / "odds.csv"
    path.write_text("book,player,team,line,over,under\nUnibet,X,BUF,2.5,abc,1.9\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_odds_csv(path)


def test_pinnacle_special_description_strips_market_suffix():
    from nhl.sources.pinnacle import parse_specials
    related = [{"id": 7, "type": "special", "units": "Shots On Goal",
                "special": {"category": "Player Props", "description": "Claude Giroux Total Shots On Goal"},
                "participants": [{"id": 1, "name": "Over"}, {"id": 2, "name": "Under"}]}]
    markets = [{"matchupId": 7, "prices": [{"participantId": 1, "points": 2.5, "price": 120},
                                           {"participantId": 2, "points": 2.5, "price": -150}]}]
    (q,) = parse_specials(related, markets)
    assert q.player == "Claude Giroux" and q.line == 2.5 and q.over == 2.2
