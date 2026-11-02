from types import SimpleNamespace as NS

from propsbot.models import OddsQuote
from propsbot.sources.kalshi import add_to_events, fetch


class FakeClient:
    def __init__(self, markets):
        self.markets = markets

    def get(self, url, params=None, ttl=None):
        return {"markets": self.markets if params["series_ticker"] == "KXNBAPTS" else []}


def test_fetch_filters_liquid_and_parses_line():
    ms = [{"title": "Trey Murphy III: 20+ points", "yes_bid_dollars": "0.3200", "yes_ask_dollars": "0.3500",
           "volume_fp": "2104.59", "close_time": "2026-11-05T01:00:00Z"},
          {"title": "Thin Guy: 10+ points", "yes_bid_dollars": "0.30", "yes_ask_dollars": "0.50",
           "volume_fp": "5000", "close_time": "2026-11-05T01:00:00Z"},
          {"title": "Low Vol: 10+ points", "yes_bid_dollars": "0.30", "yes_ask_dollars": "0.32",
           "volume_fp": "10", "close_time": "2026-11-05T01:00:00Z"}]
    out = fetch(FakeClient(ms), {})
    assert len(out) == 1
    x = out[0]
    assert x["marknad"] == "points" and x["linje"] == 19.5 and abs(x["p_over"] - 0.335) < 1e-9


def test_add_to_events_matches_player_and_time():
    ko = 1793750400.0      # 2026-11-04 23:00 UTC
    kq = OddsQuote(book="unibet", match_id="nba1", player_id="trey murphy iii", market="points",
                   line=19.5, side="over", odds=2.6, ts=0, provider="kambi")
    per = {1: ({"id": "nba1", "commence_time": ko}, [kq], {})}
    lines = [{"namn": "Trey Murphy III", "pid": "trey murphy iii", "marknad": "points", "linje": 19.5,
              "p_over": 0.335, "stanger": ko + 7200, "volym": 2000, "glapp": 0.03},
             {"namn": "Trey Murphy III", "pid": "trey murphy iii", "marknad": "points", "linje": 24.5,
              "p_over": 0.12, "stanger": ko + 3 * 86400, "volym": 2000, "glapp": 0.03}]   # annan match
    assert add_to_events(per, lines, 0.0) == 1
    qs = [q for q in per[1][1] if q.book == "kalshi"]
    assert {q.side for q in qs} == {"over", "under"} and abs(1 / qs[0].odds + 1 / qs[1].odds - 1) < 1e-9
