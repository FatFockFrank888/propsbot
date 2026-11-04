import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from nhl.bot_settings import BotSettings
from nhl.config import Settings
from nhl.engine import best_per_player, evaluate_game, leg_key
from nhl.history import LineHistory
from nhl.ledger import Ledger, bet_from_leg, boxscore_sog
from nhl.market import (
    Quote,
    group_fairs,
    market_probability,
    power_devig,
    shift_over_prob,
)
from nhl.model import line_probs
from nhl.nhl_api import Game, LogEntry, Skater
from nhl.projections import estimate_mean
from nhl.slate import Projection
from nhl.sources.kambi import is_sog_label, parse_sog_betoffers, person_name
from nhl.sources.pinnacle import parse_specials
from nhl.sources.us_books import Budget

NOW = 1_800_000_000.0
ALPHA = 0.05


# ------------------------------------------------------------------ market maths
def test_power_devig_fair_and_favourite_bias():
    o, u = power_devig(1.90, 1.90)
    assert o == pytest.approx(0.5)
    o, u = power_devig(1.40, 3.00)
    assert o + u == pytest.approx(1.0)
    # power method shifts more margin onto the longshot than proportional
    prop_o = (1 / 1.40) / (1 / 1.40 + 1 / 3.00)
    assert o > prop_o


def test_shift_over_prob_monotone_and_identity():
    assert shift_over_prob(0.55, 2.5, 2.5, ALPHA) == pytest.approx(0.55)
    up = shift_over_prob(0.55, 2.5, 3.5, ALPHA)
    down = shift_over_prob(0.55, 2.5, 1.5, ALPHA)
    assert down > 0.55 > up
    mu = 3.0
    p25 = line_probs(2.5, mu, ALPHA).over
    assert shift_over_prob(p25, 2.5, 3.5, ALPHA) == pytest.approx(line_probs(3.5, mu, ALPHA).over, abs=1e-4)


def _q(source, group, line, over, under=None, playable=False, player="Tage Thompson", ts=NOW):
    return Quote(source, group, player, line, over, under, ts, playable)


def test_group_fairs_one_per_group_and_excludes_kambi():
    quotes = [
        _q("us:draftkings", "draftkings", 2.5, 1.95, 1.85),
        _q("us:fanduel", "fanduel", 2.5, 2.00),  # one-sided
        _q("us:betrivers", "kambi", 2.5, 1.80, 2.00),  # Kambi-priced: not a reference
        _q("unibet", "kambi", 2.5, 2.10, 1.70, playable=True),
        _q("pinnacle", "pinnacle", 3.5, 2.60, 1.52),  # neighbouring line -> interpolated
    ]
    over = group_fairs(quotes, 2.5, "over", ALPHA, 0.08, 1.0)
    assert sorted(f.group for f in over) == ["draftkings", "fanduel", "pinnacle"]
    pin = next(f for f in over if f.group == "pinnacle")
    assert pin.interpolated and pin.sharp
    under = group_fairs(quotes, 2.5, "under", ALPHA, 0.08, 1.0)
    assert sorted(f.group for f in under) == ["draftkings", "pinnacle"]  # one-sided can't price unders
    p = market_probability(over, 2.0)
    assert 0.3 < p < 0.7


# ------------------------------------------------------------------ sources
KAMBI_RAW = {
    "betOffers": [
        {
            "criterion": {"englishLabel": "Player's shots on goal - Including Overtime"},
            "outcomes": [
                {"englishLabel": "Over", "type": "OT_OVER", "participant": "Thompson, Tage", "line": 2500, "odds": 2100, "status": "OPEN"},
                {"englishLabel": "Under", "type": "OT_UNDER", "participant": "Thompson, Tage", "line": 2500, "odds": 1700, "status": "OPEN"},
                {"englishLabel": "Over", "type": "OT_OVER", "participant": "Dahlin, Rasmus", "line": 1500, "odds": 1500, "status": "SUSPENDED"},
            ],
        },
        {
            "criterion": {"englishLabel": "Player to have at least 4 shots on goal"},
            "outcomes": [{"englishLabel": "Yes", "participant": "Thompson, Tage", "odds": 3200, "status": "OPEN"}],
        },
        {
            "criterion": {"englishLabel": "Total Shots on Goal by Buffalo Sabres"},
            "outcomes": [{"englishLabel": "Over", "type": "OT_OVER", "line": 30500, "odds": 1900}],
        },
        {"criterion": {"englishLabel": "To score - Including Overtime"}, "outcomes": []},
    ]
}


def test_kambi_parse():
    quotes, labels = parse_sog_betoffers(KAMBI_RAW, "unibet", playable=True, now=NOW)
    by_line = {q.line: q for q in quotes}
    assert set(by_line) == {2.5, 3.5}
    assert by_line[2.5].player == "Tage Thompson"
    assert (by_line[2.5].over, by_line[2.5].under) == (2.1, 1.7)
    assert by_line[3.5].over == 3.2 and by_line[3.5].under is None
    assert all(q.playable and q.group == "kambi" for q in quotes)
    assert len(labels) == 3


def test_kambi_label_and_name_helpers():
    assert is_sog_label("Shots on Goal - Including Overtime")
    assert not is_sog_label("Blocked shots")
    assert not is_sog_label("Total Goals")
    assert person_name("Stützle, Tim") == "Tim Stützle"
    assert person_name("Connor McDavid") == "Connor McDavid"


def test_pinnacle_parse():
    related = [{"id": 11, "type": "special", "special": {"description": "Tage Thompson (Shots On Goal)", "category": "Player Props"},
                "participants": [{"id": 1, "name": "Over"}, {"id": 2, "name": "Under"}]}]
    markets = [{"matchupId": 11, "isAlternate": False, "prices": [
        {"participantId": 1, "price": 110, "points": 3.5}, {"participantId": 2, "price": -135, "points": 3.5}]}]
    (q,) = parse_specials(related, markets, now=NOW)
    assert q.group == "pinnacle" and q.line == 3.5
    assert q.over == pytest.approx(2.10) and q.under == pytest.approx(1.7407, abs=1e-3)


def test_boxscore_sog():
    data = {"gameState": "OFF", "playerByGameStats": {
        "homeTeam": {"forwards": [{"playerId": 1, "sog": 4}], "defense": [{"playerId": 2, "sog": 0}]},
        "awayTeam": {"forwards": [{"playerId": 3, "sog": 2}], "defense": []}}}
    assert boxscore_sog(data) == {1: 4, 2: 0, 3: 2}
    assert boxscore_sog({"gameState": "LIVE"}) is None


def test_budget(tmp_path):
    b = Budget(tmp_path / "b.json", monthly=500, share=0.25, reserve=20)
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)  # 10 days left
    b.observe({"x-requests-remaining": "420"})
    assert b.daily_budget(now) == int((420 - 20) / 10 * 0.25)  # 10
    for _ in range(10):
        assert b.can_spend(1, now)
        b.spend(1, now)
    assert not b.can_spend(1, now)


def test_secrets_from_environment_override_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    BotSettings.load(path)
    monkeypatch.setenv("NTFY_TOPIC", "topic-from-env")
    monkeypatch.setenv("PINNACLE_API_KEY", "key-from-env")
    s = BotSettings.load(path)
    assert s.ntfy_topic == "topic-from-env" and s.pinnacle_api_key == "key-from-env"
    assert "key-from-env" not in path.read_text(encoding="utf-8")  # never written back to the file


def test_history_stores_only_changes(tmp_path):
    h = LineHistory(tmp_path / "h.sqlite")
    for i in range(5):
        h.record("leg", 2.10, 0.5, None, NOW + i)
    h.record("leg", 2.20, 0.5, None, NOW + 10)
    assert h.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
    assert h.get("leg").max_odds == 2.20


def test_settings_roundtrip_and_validation(tmp_path):
    path = tmp_path / "settings.json"
    s = BotSettings.load(path)  # writes defaults
    assert path.exists() and s.live_max_units == 5
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["live_min_edge"] = 0.08
    raw["bogus"] = 1
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert BotSettings.load(path).live_min_edge == 0.08
    raw["live_odds_min"] = 0.5
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        BotSettings.load(path)


# ------------------------------------------------------------------ engine
CFG = Settings()


def _game():
    return Game(42, date(2026, 11, 4), datetime(2026, 11, 5, 0, 30, tzinfo=timezone.utc), "BUF", "OTT", "FUT", 2, "20262027")


def _proj(mu=3.6, active=True, games=20, pid=1, name="Tage Thompson"):
    start = date(2026, 10, 1)
    log = [LogEntry(i, start + timedelta(days=i), "BUF", "OTT", True, 3, 18.0) for i in range(games)]
    est = replace(estimate_mean(log, "F", CFG), base_mu=mu)
    return Projection(_game(), Skater(pid, name, "BUF", "F", "C"), "OTT", True, est, 1.0, 1.0, mu, active,
                      date(2026, 11, 2), games, 3.0, (3,) * 10)


def _bot(**kw):
    return replace(BotSettings(), **kw)


def _evaluate(quotes, s=None, proj=None, hist=None, tmp=None):
    s = s or _bot()
    history = hist or LineHistory(tmp / "h.sqlite")
    legs, unmatched = evaluate_game(_game(), [proj or _proj()], quotes, history, s, ALPHA, NOW)
    return legs, unmatched, history


def _refs(over=1.80, under=2.00):
    return [
        _q("us:draftkings", "draftkings", 2.5, over, under),
        _q("us:fanduel", "fanduel", 2.5, over + 0.02, under - 0.02),
        _q("us:caesars", "caesars", 2.5, over - 0.02, under + 0.02),
    ]


def test_engine_live_ok_leg(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True), _q("atg", "kambi", 2.5, 2.20, 1.65, playable=True)] + _refs(1.95, 1.87)
    legs, _, _ = _evaluate(quotes, proj=_proj(mu=3.0), tmp=tmp_path)
    over = next(l for l in legs if l.side == "over")
    assert over.book == "unibet" and over.odds == 2.25
    assert 0.06 < over.edge < 0.25
    assert over.groups == 3 and over.has_two_sided and not over.has_sharp
    assert over.edge > 0.06 and over.model_edge > 0.03
    assert over.blocks == [] and over.live_blocks == [], (over.blocks, over.live_blocks)
    assert 1 <= over.units <= 10
    under = next(l for l in legs if l.side == "under")
    assert under.blocks  # negative edge


def test_engine_under_needs_two_sided_reference(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 2.40, playable=True), _q("us:fanduel", "fanduel", 2.5, 1.80)]
    legs, _, _ = _evaluate(quotes, tmp=tmp_path)
    assert [l.side for l in legs] == ["over"]
    assert any("without sharp" in b for b in legs[0].blocks)


def test_engine_blocks_implausible_and_dropping_odds(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 3.40, 1.30, playable=True)] + _refs()
    legs, _, hist = _evaluate(quotes, tmp=tmp_path)
    over = next(l for l in legs if l.side == "over")
    assert any("implausible" in b for b in over.blocks)
    assert any("consensus" in b for b in over.blocks)

    # odds were 2.40 earlier, now 2.25 -> dropped > 3%
    hist.record(leg_key(42, 1, 2.5, "over"), 2.40, 0.5, None, NOW - 600)
    legs, _, _ = _evaluate([_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True)] + _refs(), hist=hist)
    over = next(l for l in legs if l.side == "over")
    assert any("dropped" in b for b in over.blocks)


def test_engine_sharp_movement(tmp_path):
    pin = [_q("pinnacle", "pinnacle", 2.5, 1.85, 1.98)]
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True)] + pin + _refs()
    hist = LineHistory(tmp_path / "h.sqlite")
    # 40 min ago the sharp side was priced 6pp higher -> moved against us
    hist.record(leg_key(42, 1, 2.5, "over"), 2.25, 0.55, 0.58, NOW - 2400)
    legs, _, _ = _evaluate(quotes, hist=hist)
    over = next(l for l in legs if l.side == "over")
    assert any("sharp moved" in b for b in over.blocks)

    hist2 = LineHistory(tmp_path / "h2.sqlite")
    hist2.record(leg_key(42, 1, 2.5, "over"), 2.25, 0.45, 0.48, NOW - 2400)
    legs, _, _ = _evaluate(quotes, hist=hist2)
    over = next(l for l in legs if l.side == "over")
    assert "Sharp money with us ⬆" in over.tags


def test_engine_stale_inactive_and_unmatched(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True, ts=NOW - 1000), _q("unibet", "kambi", 2.5, 2.0, 1.8, playable=True, player="Nobody Known")] + _refs()
    legs, unmatched, _ = _evaluate(quotes, proj=_proj(active=False), tmp=tmp_path)
    over = next(l for l in legs if l.side == "over")
    assert any("old" in b for b in over.blocks)
    assert "not in last lineup" in over.live_blocks
    assert unmatched == ["Nobody Known"]


def test_best_per_player():
    class L:
        def __init__(self, gid, pid, e):
            self.game, self.player_id, self.edge = type("G", (), {"game_id": gid})(), pid, e
    legs = [L(1, 1, 0.05), L(1, 1, 0.09), L(1, 2, 0.07)]
    best = best_per_player(legs, lambda l: l.edge)
    assert [(l.player_id, l.edge) for l in best] == [(1, 0.09), (2, 0.07)]


# ------------------------------------------------------------------ ledger
def test_ledger_upsert_settle_and_stats(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True)] + _refs()
    legs, _, _ = _evaluate(quotes, tmp=tmp_path)
    over = next(l for l in legs if l.side == "over")
    s = BotSettings()
    led = Ledger("bokforing", tmp_path / "led.json")
    assert led.upsert_best(bet_from_leg(over, "bokforing", s, 3))
    weaker = bet_from_leg(over, "bokforing", s, 3)
    weaker["edge"] = 0.01
    assert not led.upsert_best(weaker)
    stronger = bet_from_leg(over, "bokforing", s, 4)
    stronger["edge"] = 0.5
    assert led.upsert_best(stronger) and len(led.bets) == 1

    led.update_close({over.key: over})
    assert led.bets[0]["clv"] is not None

    assert led.settle({42: {1: 3}}) == 1  # 3 SOG > 2.5 -> won
    b = led.bets[0]
    assert b["status"] == "won" and b["profit_units"] == pytest.approx(4 * (b["odds"] - 1), abs=1e-3)
    led.save()
    again = Ledger("bokforing", tmp_path / "led.json")
    st = again.stats()
    assert st["won"] == 1 and st["roi"] > 0


def test_leg_log_close_and_settle(tmp_path):
    hist = LineHistory(tmp_path / "h.sqlite")
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True)] + _refs(1.95, 1.87)
    legs, _, _ = _evaluate(quotes, proj=_proj(mu=3.0), hist=hist)
    for leg in legs:
        hist.log_leg(leg, NOW)
    # later scan: price shortened, edge smaller -> close updates, max edge stays
    legs2, _, _ = _evaluate([_q("unibet", "kambi", 2.5, 2.05, 1.75, playable=True)] + _refs(1.85, 1.97),
                            proj=_proj(mu=3.0), hist=hist)
    for leg in legs2:
        hist.log_leg(leg, NOW + 600)
    assert hist.unsettled_games("2030-01-01T00:00:00+00:00") == [42]
    assert hist.settle_game(42, {1: 2}) == 2  # 2 SOG: over 2.5 lost, under won
    rows = {r["side"]: r for r in hist.settled_legs()}
    assert rows["over"]["outcome"] == "lost" and rows["under"]["outcome"] == "won"
    assert rows["over"]["max_edge_odds"] == 2.25 and rows["over"]["close_odds"] == 2.05
    assert rows["over"]["close_p_kambi"] is not None


def test_ledger_void_when_player_did_not_play(tmp_path):
    quotes = [_q("unibet", "kambi", 2.5, 2.25, 1.62, playable=True)] + _refs()
    legs, _, _ = _evaluate(quotes, tmp=tmp_path)
    led = Ledger("live", tmp_path / "live.json")
    led.add(bet_from_leg(legs[0], "live", BotSettings(), 2))
    led.settle({42: {999: 5}})
    assert led.bets[0]["status"] == "void" and led.bets[0]["profit_units"] == 0
