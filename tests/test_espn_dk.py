"""DraftKings via ESPN: över/under ur ordningen och milstolparna, bara rimliga tvåsidiga halvlinjer."""
from propsbot.sources.espn_dk import parse

REF = "http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2027/athletes/{}?lang=en"


def it(aid, name, line, dec, upd="2026-11-12T09:33Z"):
    return {"athlete": {"$ref": REF.format(aid)}, "type": {"name": name}, "lastUpdated": upd,
            "odds": {"decimal": {"value": str(dec)}, "total": {"value": str(line)}}}


NOW = 1794480000.0   # 2026-11-12 ~10 UTC


def test_order_is_over_first():
    rows = parse([it(1, "Total Points", 17.5, 2.0), it(1, "Total Points", 17.5, 1.78)], NOW)
    assert ("1", "points", 17.5, "over", 2.0) == rows[0][:5] and rows[1][3:5] == ("under", 1.78)


def test_milestone_flips_side_when_order_is_wrong():
    rows = parse([it(2, "Total Assists", 3.5, 1.66), it(2, "Total Assists", 3.5, 2.14),
                  it(2, "Assists Milestones", "4+", 2.15)], NOW)
    assert {r[3]: r[4] for r in rows} == {"over": 2.14, "under": 1.66}


def test_rejects_whole_lines_bad_margin_and_one_sided():
    rows = parse([it(3, "Total Rebounds", 7, 1.9), it(3, "Total Rebounds", 7, 1.9),          # heltal
                  it(4, "Total Rebounds", 6.5, 1.3), it(4, "Total Rebounds", 6.5, 1.3),      # marginal 54 %
                  it(5, "Total Rebounds", 5.5, 1.9),                                         # bara en sida
                  it(6, "First Basket", 0.5, 9.0), it(6, "First Basket", 0.5, 1.05)], NOW)   # inte en marknad
    assert rows == []
