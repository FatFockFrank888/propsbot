from types import SimpleNamespace as NS

from propsbot.clv_signal import History, final_rules, line_key
from propsbot.decision import Candidate, Decision
from propsbot.models import OddsQuote


def row(match, player, market, odds, p, playable=True, sharp=False, line=0.5):
    q = OddsQuote(book="unibet", match_id=match, player_id=player, market=market, line=line,
                  side="over", odds=odds, ts=0.0)
    c = Candidate(match, player, player, market, line, p, q, None, 0.0, True, 120.0)
    d = Decision(c, playable, True, 1.4, 0.01 if playable else 0.0, [])
    return NS(row=NS(decision=d), sharp_ref=sharp)


S = {"min_edge_all": 0.05, "max_odds_drop": 0.03, "football_shadow": True,
     "football_odds_window": [1.6, 2.5]}


def test_min_edge_five_percent():
    a, b = row("m", "x", "points", 2.0, 0.52), row("m", "y", "points", 2.0, 0.56)   # 4 % / 12 %
    final_rules([a, b], S, None, "nba")
    assert not a.row.decision.playable and b.row.decision.playable


def test_one_bet_per_player_best_edge_wins():
    a = row("m", "x", "points", 2.0, 0.56)
    b = row("m", "x", "threes", 2.0, 0.60)
    c = row("m", "x", "assists", 2.0, 0.58)
    final_rules([a, b, c], S, None, "nba")
    assert [r.row.decision.playable for r in (a, b, c)] == [False, True, False]


def test_player_already_booked_in_earlier_run():
    a = row("m", "x", "threes", 2.0, 0.60)
    final_rules([a], S, None, "nba", taken={("m", "x"): "m|x|points|0.5|unibet"})
    assert not a.row.decision.playable


def test_odds_drop_blocks(tmp_path):
    a = row("m", "x", "points", 2.10, 0.56)
    h = History(tmp_path / "h.json")
    h.update([a], 0.0)
    a.row.decision.cand.best = a.row.decision.cand.best.__class__(**{**a.row.decision.cand.best.__dict__, "odds": 2.00})
    h.update([a], 10.0)
    assert h.d[line_key(a.row.decision.cand)][4] == 2.10
    final_rules([a], S, h, "nba")          # 2,10 -> 2,00 = 4,8 % fall
    assert not a.row.decision.playable


def test_football_shadow_unless_sharp_and_window():
    a = row("m", "x", "shots", 2.0, 0.60, sharp=False)
    b = row("m", "y", "shots", 2.0, 0.60, sharp=True)
    c = row("m", "z", "shots", 3.0, 0.40, sharp=True)
    final_rules([a, b, c], S, None, "fotboll")
    assert [r.row.decision.playable for r in (a, b, c)] == [False, True, False]


def test_sharp_money_against_blocks_and_with_tags(tmp_path):
    a = row("m", "x", "points", 2.0, 0.60)
    b = row("m", "y", "points", 2.0, 0.60)
    h = History(tmp_path / "h.json")
    h.update([a, b], 0.0)
    a.row.decision.cand.p = 0.57          # referensen har gått 3 enheter mot oss
    b.row.decision.cand.p = 0.62          # 2 enheter med oss
    h.update([a, b], 4000.0)
    final_rules([a, b], S, h, "nba")
    assert not a.row.decision.playable
    assert b.row.decision.playable and any("sharp money med" in x for x in b.row.decision.reasons)


def test_source_change_resets_baseline(tmp_path):
    a = row("m", "x", "points", 2.0, 0.60)
    a.n_groups = 2
    h = History(tmp_path / "h.json")
    h.update([a], 0.0)
    a.row.decision.cand.p, a.n_groups = 0.55, 3     # DK/FD tillkom
    h.update([a], 4000.0)
    assert h.momentum_pp(a.row.decision.cand) == 0.0
