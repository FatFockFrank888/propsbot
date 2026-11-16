import json

from propsbot.models import OddsQuote
from propsbot.stang_arkiv import freeze, observe


def q(book, side, odds, line=24.5, ts=100.0):
    return OddsQuote(book=book, match_id="m", player_id="x", market="points", line=line, side=side,
                     odds=odds, ts=ts)


def test_devig_within_own_pair_and_one_sided_skipped():
    pend = {}
    evd = {"id": "m", "home_team": "A", "away_team": "B", "commence_time": 1000.0}
    qs = [q("pinnacle", "over", 1.90), q("pinnacle", "under", 1.95), q("us_draftkings", "over", 2.0),
          q("unibet", "over", 2.2), q("unibet", "under", 1.6)]
    assert observe(pend, evd, qs, {"x": "X"}, 100.0) == 1          # DK ensidig, Unibet inte skarp
    r = pend["m"]["rader"]["x|points|24.5|pinnacle"]
    assert abs(r["p_over"] - (1 / 1.9) / (1 / 1.9 + 1 / 1.95)) < 1e-4 and r["marginal"] > 0


def test_freeze_appends_after_start_only(tmp_path):
    pend = {}
    evd = {"id": "m", "home_team": "A", "away_team": "B", "commence_time": 1000.0}
    observe(pend, evd, [q("pinnacle", "over", 1.9, ts=400.0), q("pinnacle", "under", 1.95, ts=400.0)], {}, 400.0)
    assert freeze(tmp_path, pend, 900.0) == 0 and "m" in pend
    assert freeze(tmp_path, pend, 1000.0) == 1 and "m" not in pend
    line = json.loads(next((tmp_path / "stangning_arkiv").glob("nba-*.jsonl")).read_text().splitlines()[0])
    assert line["bolag"] == "pinnacle" and line["min_fore_start"] == 10.0
