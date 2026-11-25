import time

from propsbot.consensus import consensus_p, voice_of
from propsbot.models import OddsQuote
from propsbot.sources.propline import american_to_decimal, parse


def ev():
    def oc(desc, nm, price, point=None):
        return {"description": desc, "name": nm, "price": price, "point": point}
    return {"bookmakers": [
        {"key": "draftkings", "markets": [{"key": "player_shots_on_target", "outcomes": [
            oc("Cole Palmer", "1+ Shots on Target", -150), oc("Cole Palmer", "2+ Shots on Target", 180)]}]},
        {"key": "fanduel", "markets": [{"key": "player_shots_on_target", "outcomes": [
            oc("Cole Palmer", "1+ Shots on Target", -140)]}]},
        {"key": "unibet", "markets": [{"key": "player_shots_on_target", "outcomes": [
            oc("Cole Palmer", "1+ Shots on Target", -245)]}]},          # Kambi: används inte
        {"key": "bovada", "markets": [{"key": "player_shots", "outcomes": [
            oc("Cole Palmer", "Over", -120, 2.5), oc("Cole Palmer", "Under", 100, 2.5)]}]}]}


def test_american_to_decimal():
    assert abs(american_to_decimal(-150) - 1.6667) < 1e-3 and american_to_decimal(180) == 2.8 and american_to_decimal(0) is None


def test_parse_milestones_and_overunder_skips_kambi():
    q, names = parse(ev(), "m1", 1.0)
    books = {(x.book, x.market, x.line, x.side) for x in q}
    assert ("pl_draftkings", "shots_on_target", 0.5, "over") in books and ("pl_draftkings", "shots_on_target", 1.5, "over") in books
    assert ("pl_bovada", "shots", 2.5, "under") in books
    assert not any(x.book == "pl_unibet" for x in q) and names["cole palmer"] == "Cole Palmer"


def test_consensus_needs_two_independent_voices():
    q, _ = parse(ev(), "m1", time.time())
    pid = q[0].player_id
    c = consensus_p(q, pid, "shots_on_target", 0.5)
    assert c and c["n"] == 2 and c["voices"] == ["draftkings", "fanduel"] and 0.55 < c["p"] < 0.62
    assert consensus_p(q[:1], pid, "shots_on_target", 0.5) is None          # en röst räcker inte
    kam = [OddsQuote("unibet", "m1", pid, "shots_on_target", 0.5, "over", 1.4, 0.0, "kambi")] + q[:1]
    assert consensus_p(kam, pid, "shots_on_target", 0.5) is None            # Kambi räknas aldrig som referens


def test_voice_of_kambi_books_none():
    assert voice_of("unibet") is None and voice_of("svenskaspel") is None and voice_of("pl_draftkings") == "draftkings"


def test_redact_secrets_and_strip(monkeypatch):
    from propsbot.free_scan import redact
    monkeypatch.setenv("PROPLINE_API_KEY", "abcdef1234567890\n")
    assert "abcdef1234567890" not in redact("Invalid header value b'abcdef1234567890\\n'")
    assert redact("ingen hemlighet här") == "ingen hemlighet här"


def test_empty_cached_event_list_is_refetched(tmp_path, monkeypatch):
    import json
    import time as t
    from propsbot.sources import propline as pl
    monkeypatch.setenv("PROPLINE_API_KEY", "k" * 12)
    now = t.time()
    (tmp_path / pl.STATE).write_text(json.dumps({"day": t.strftime("%Y-%m-%d", t.gmtime(now)), "used": 0,
                                                 "events": {"soccer_epl": {"ts": now - 1800, "list": []}}, "odds": {}}))
    calls = []
    monkeypatch.setattr(pl, "_get", lambda path, key: (calls.append(path) or [], 990))

    class D:
        def log(self, m): pass
    data = [({"id": "k1", "home_team": "A", "away_team": "B", "commence_time": now + 3600}, [], {})]
    pl.add_propline(tmp_path, data, {"propline_leagues": ["soccer_epl"]}, D())
    assert calls == ["/sports/soccer_epl/events"]          # tom lista äldre än 10 min hämtas om
