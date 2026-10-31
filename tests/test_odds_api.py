"""Tester för The Odds API-kopplingen.

OBS: svaren nedan är byggda efter The Odds API:s dokumenterade v4-format
(bookmakers -> markets -> outcomes med name/description/price/point).
De är inte inspelade från riktiga anrop.
"""
import io
import json
import urllib.error

import pytest

from propsbot.config import Config
from propsbot.scan import DEFAULT_SETTINGS, consensus, evaluate_event_market_only, provider_groups
TEST_SETTINGS = dict(DEFAULT_SETTINGS, playable_books=[])  # alla bolag spelbara i testerna
from propsbot.sources import the_odds_api as toa
from propsbot.sources.the_odds_api import normalize_name, parse_match_lines, parse_props

EVENT = {
    "id": "ev1", "sport_key": "soccer_epl", "commence_time": "2099-01-01T15:00:00Z",
    "home_team": "Arsenal", "away_team": "Chelsea",
}


def _bm(key, markets, ts=1_700_000_000):
    return {"key": key, "title": key, "last_update": ts, "markets": markets}


def _sot(outcomes):
    return {"key": "player_shots_on_target", "last_update": 1_700_000_000, "outcomes": outcomes}


def test_normalize_name():
    assert normalize_name("Martin Ødegaard") == "martin odegaard"
    assert normalize_name("Kai  Havertz-Jr.") == "kai havertz jr"


def test_parse_props_both_layouts_and_yes_no():
    ev = dict(EVENT, bookmakers=[
        _bm("pinnacle", [_sot([
            {"name": "Over", "description": "Bukayo Saka", "price": 1.80, "point": 0.5},
            {"name": "Under", "description": "Bukayo Saka", "price": 2.05, "point": 0.5}])]),
        _bm("unibet_eu", [_sot([
            {"name": "Bukayo Saka", "description": "Over", "price": 1.72, "point": 0.5}])]),
        _bm("sport888", [{"key": "player_goal_scorer_anytime", "outcomes": [
            {"name": "Yes", "description": "Bukayo Saka", "price": 3.4}]}]),
        _bm("x", [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 1.5}]}]),
    ])
    quotes, names = parse_props(ev)
    assert names == {"bukayo saka": "Bukayo Saka"}
    keyed = {(q.book, q.market, q.side): q for q in quotes}
    assert keyed[("pinnacle", "shots_on_target", "under")].odds == 2.05
    assert keyed[("unibet_eu", "shots_on_target", "over")].line == 0.5
    g = keyed[("sport888", "goal", "over")]
    assert g.line == 0.5 and g.odds == 3.4
    assert len(quotes) == 4


def _match_markets(h, d, a, over, under, point=2.5):
    return [
        {"key": "h2h", "outcomes": [{"name": "Arsenal", "price": h}, {"name": "Draw", "price": d},
                                    {"name": "Chelsea", "price": a}]},
        {"key": "totals", "outcomes": [{"name": "Over", "price": over, "point": point},
                                       {"name": "Under", "price": under, "point": point},
                                       {"name": "Over", "price": 3.5, "point": 3.5},
                                       {"name": "Under", "price": 1.3, "point": 3.5}]},
    ]


def test_parse_match_lines_prefers_pinnacle():
    ev = dict(EVENT, bookmakers=[_bm("unibet_eu", _match_markets(1.9, 3.5, 4.0, 1.8, 2.0)),
                                 _bm("pinnacle", _match_markets(1.95, 3.7, 4.2, 1.85, 2.05))])
    ml = parse_match_lines(ev)
    assert ml.source == "pinnacle" and ml.odds_1x2 == (1.95, 3.7, 4.2)
    assert ml.total_line == 2.5


def test_parse_match_lines_consensus_fallback():
    ev = dict(EVENT, bookmakers=[_bm("unibet_eu", _match_markets(1.9, 3.5, 4.0, 1.8, 2.0)),
                                 _bm("betsson", _match_markets(1.92, 3.4, 4.1, 1.83, 1.97))])
    ml = parse_match_lines(ev)
    assert ml.source == "konsensus"
    assert abs(sum(1 / o for o in ml.odds_1x2) - 1) < 1e-9  # marginalfritt


def _prop_event():
    sot = lambda over, under=None: _sot(  # noqa: E731
        [{"name": "Over", "description": "Bukayo Saka", "price": over, "point": 0.5}]
        + ([{"name": "Under", "description": "Bukayo Saka", "price": under, "point": 0.5}]
           if under else []))
    return dict(EVENT, bookmakers=[
        _bm("pinnacle", [sot(1.80, 2.08)]),
        _bm("unibet_eu", [sot(1.66)]),
        _bm("leovegas", [sot(1.66)]),
        _bm("betsson", [sot(2.02)]),
    ])


def test_kambi_hint_groups_unibet_and_leovegas():
    quotes, _ = parse_props(_prop_event())
    gid = provider_groups(quotes, TEST_SETTINGS, Config())
    assert gid["unibet_eu"] == gid["leovegas"]
    assert gid["pinnacle"] != gid["unibet_eu"] != gid["betsson"]


def test_market_only_leave_one_out_edge():
    ev = _prop_event()
    quotes, names = parse_props(ev)
    rows = evaluate_event_market_only(ev, quotes, names, TEST_SETTINGS, Config(),
                                      fetch_ts=1_700_000_000, sport="soccer_epl")
    assert len(rows) == 1
    d = rows[0].row.decision
    assert d.cand.best.book == "betsson"
    # Konsensus utan betsson ≈ Pinnacle (marginalfri ~0.536) vägd med Kambi
    assert 0.50 < d.cand.p < 0.56
    assert d.cand.edge > 0.02 and d.playable and d.show
    assert rows[0].n_groups == 2  # pinnacle + kambi (betsson utesluten)


def test_no_independent_source_gives_no_candidate():
    ev = dict(EVENT, bookmakers=[_bm("betsson", [_sot(
        [{"name": "Over", "description": "Bukayo Saka", "price": 2.5, "point": 0.5}])])])
    quotes, names = parse_props(ev)
    rows = evaluate_event_market_only(ev, quotes, names, TEST_SETTINGS, Config(),
                                      fetch_ts=1_700_000_000, sport="soccer_epl")
    assert rows == []


def test_consensus_without_sharp_flags_low_confidence():
    ev = dict(EVENT, bookmakers=[_bm("unibet_eu", [_sot(
        [{"name": "Over", "description": "A B", "price": 1.9, "point": 0.5}])]),
        _bm("betsson", [_sot([{"name": "Over", "description": "A B", "price": 2.2, "point": 0.5}])])])
    quotes, _ = parse_props(ev)
    gid = provider_groups(quotes, TEST_SETTINGS, Config())
    c = consensus(quotes, gid, gid["betsson"], "pinnacle", "shots_on_target", Config())
    assert c and not c.has_sharp_or_two_sided


# ------------------------------------------------------------- http-klient
class _Resp(io.BytesIO):
    def __init__(self, data, headers):
        super().__init__(json.dumps(data).encode())
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_client_caches_and_reads_usage(tmp_path, monkeypatch):
    calls = []

    def fake(url, timeout):
        calls.append(url)
        assert "apiKey=KEY" in url
        return _Resp([{"key": "soccer_epl", "has_outrights": False}],
                     {"x-requests-remaining": "480", "x-requests-used": "20", "x-requests-last": "0"})

    monkeypatch.setattr(toa.urllib.request, "urlopen", fake)
    api = toa.TheOddsApi(api_key="KEY", cache_dir=tmp_path)
    assert api.soccer_sports()[0]["key"] == "soccer_epl"
    api.soccer_sports()
    assert len(calls) == 1 and api.usage.remaining == "480" and api.usage.cached == 1
    assert "KEY" not in "".join(p.read_text() for p in tmp_path.iterdir())  # nyckeln sparas aldrig


def test_client_422_returns_none_and_401_raises(tmp_path, monkeypatch):
    def make(code):
        def fake(url, timeout):
            raise urllib.error.HTTPError(url, code, "x", {}, io.BytesIO(b'{"message":"x"}'))
        return fake

    api = toa.TheOddsApi(api_key="KEY", cache_dir=tmp_path)
    monkeypatch.setattr(toa.urllib.request, "urlopen", make(422))
    assert api.event_odds("soccer_epl", "ev1", ["player_shots"]) is None
    monkeypatch.setattr(toa.urllib.request, "urlopen", make(401))
    with pytest.raises(toa.OddsApiError):
        api.event_odds("soccer_epl", "ev2", ["player_shots"])


def test_missing_key_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(toa.OddsApiError):
        toa.TheOddsApi(cache_dir=tmp_path)


def test_single_one_sided_source_and_absurd_edge_blocked():
    """Fallet från första riktiga körningen: onexbet 8,00 mot bara William Hill."""
    def sot(price):
        return [{"name": "Over", "description": "Luca Netz", "price": price, "point": 0.5}]
    ev = dict(EVENT, bookmakers=[_bm("betsson", [_sot(sot(8.0))]),
                                 _bm("nordicbet", [_sot(sot(3.8))])])
    quotes, names = parse_props(ev)
    rows = evaluate_event_market_only(ev, quotes, names, TEST_SETTINGS, Config(),
                                      fetch_ts=1_700_000_000, sport="soccer_epl")
    d = rows[0].row.decision
    assert d.cand.best.book == "betsson"
    assert not d.playable and d.stake == 0
    assert any("jämförelsekälla" in r for r in d.reasons)
    assert any("orimligt" in r for r in d.reasons)
