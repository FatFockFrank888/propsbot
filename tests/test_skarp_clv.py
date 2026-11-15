from types import SimpleNamespace as NS

from propsbot.models import OddsQuote
from propsbot.skarp_clv import book_probs, clv_pp, line_key_bet, stats, update


def _bet(**kw):
    b = {"match_id": "m1", "spelare_id": "p1", "marknad": "points", "linje": 20.5, "sida": "over",
         "odds": 2.10, "stangning": 2.0, "avspark": 10_000.0, "status": "öppen"}
    b.update(kw)
    return b


def test_sharp_close_uses_last_note_before_kickoff():
    b = _bet()
    lg = NS(bets=[b])
    k = line_key_bet(b)
    update(lg, {k: [0.5, 0, 0.52, 9_000.0]}, 9_000.0)
    assert b["skarp_stang_p"] == 0.52
    assert abs(b["clv_skarp_pp"] - (0.52 - 1 / 2.10) * 100) < 1e-9
    # efter avspark (live) skrivs inget över
    update(lg, {k: [0.5, 0, 0.40, 10_500.0]}, 10_500.0)
    assert b["skarp_stang_p"] == 0.52
    # äldre notering (t.ex. bakåträkning) skriver inte över en nyare
    update(lg, {k: [None, None, 0.45, 8_000.0]}, 0.0, None, "bakåt")
    assert b["skarp_stang_p"] == 0.52 and b["skarp_kalla"] == "skanning"
    assert b["skarp_verifierad"] is True       # 1 000 s före start


def test_under_side_and_book_probs():
    qs = [OddsQuote("pinnacle", "m1", "p1", "points", 20.5, "over", 1.90, 0),
          OddsQuote("pinnacle", "m1", "p1", "points", 20.5, "under", 1.90, 0),
          OddsQuote("us_draftkings", "m1", "p1", "points", 20.5, "over", 1.80, 0),
          OddsQuote("us_draftkings", "m1", "p1", "points", 20.5, "under", 2.00, 0)]
    bp = book_probs(qs)[("m1", "p1", "points", 20.5)]
    assert abs(bp["pinnacle"] - 0.5) < 1e-9 and bp["draftkings"] > 0.5
    b = _bet(sida="under")
    update(NS(bets=[b]), {}, 9_000.0, {("m1", "p1", "points", 20.5): bp})
    assert abs(b["pin_stang_p"] - 0.5) < 1e-9 and b["dk_stang_p"] < 0.5
    assert b["clv_pin_pp"] is not None and b["clv_dk_pp"] < b["clv_pin_pp"]


def test_clv_prefers_sharp_and_stats():
    b = _bet(skarp_stang_p=0.50, skarp_stang_ts=9_990.0)
    assert abs(clv_pp(b) - (0.50 - 1 / 2.10) * 100) < 1e-9
    assert abs(clv_pp(_bet()) - (1 / 2.0 - 1 / 2.10) * 100) < 1e-9   # utan skarp: bolagets stängning
    update(NS(bets=[b]), {}, 0.0)
    b["clv_skarp_pp"] = (0.50 - 1 / 2.10) * 100
    s = stats([b], 20_000.0)
    assert s["clv_skarp_antal"] == 1 and s["clv_skarp_slog"] == 1.0


def test_book_snapshots_for_analysis():
    """Analysen: bolagens odds vid bokningen och senast före start sparas på spelet."""
    qs = [OddsQuote("pinnacle", "m1", "p1", "points", 20.5, "over", 1.90, 0),
          OddsQuote("pinnacle", "m1", "p1", "points", 20.5, "under", 1.90, 0),
          OddsQuote("unibet", "m1", "p1", "points", 20.5, "over", 2.10, 0)]
    b = _bet(bokford=8_990.0)
    lg = NS(bets=[b])
    update(lg, {}, 9_000.0, book_probs(qs))
    assert b["bolag_bokning"]["odds"]["unibet"]["over"] == 2.10
    assert b["bolag_bokning"]["odds"]["pinnacle"] == {"over": 1.90, "under": 1.90}
    qs[0] = OddsQuote("pinnacle", "m1", "p1", "points", 20.5, "over", 1.80, 0)
    update(lg, {}, 9_500.0, book_probs(qs))
    assert b["bolag_bokning"]["ts"] == 9_000.0 and b["bolag_stangning"]["odds"]["pinnacle"]["over"] == 1.80
    old = _bet(bokford=0.0)                     # bokat långt tidigare: ingen falsk "bokning"-notering
    update(NS(bets=[old]), {}, 9_000.0, book_probs(qs))
    assert "bolag_bokning" not in old and "bolag_stangning" in old


def test_dk_other_line_is_translated_to_ours():
    """DraftKings har ofta bara en huvudlinje: närmaste linje räknas om till Unibets linje."""
    qs = [OddsQuote("unibet", "m", "p", "threes", 2.5, "over", 2.32, 0),
          OddsQuote("us_draftkings", "m", "p", "threes", 1.5, "over", 1.45, 0),
          OddsQuote("us_draftkings", "m", "p", "threes", 1.5, "under", 2.75, 0)]
    d = book_probs(qs)[("m", "p", "threes", 2.5)]
    assert d["_draftkings_linje"] == 1.5 and 0.3 < d["draftkings"] < 0.55
    assert d["_raw"]["draftkings (1.5)"] == {"over": 1.45, "under": 2.75}
    b = _bet(marknad="threes", linje=2.5, bokford=8_990.0)
    b["match_id"], b["spelare_id"] = "m", "p"
    update(NS(bets=[b]), {}, 9_000.0, book_probs(qs))
    assert b["bolag_stangning"]["dk_linje"] == 1.5 and b["dk_stang_p"] == d["draftkings"]
