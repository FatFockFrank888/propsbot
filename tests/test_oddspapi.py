import json
import time

from propsbot.sources import oddspapi as op

CATALOG_RAW = [
    {"marketId": 108992, "marketType": "playertotals-shotsongoal", "handicap": 0.5, "period": "p1"},
    {"marketId": 108996, "marketType": "playertotals-shotsongoal", "handicap": 1.5, "period": "p1"},
    {"marketId": 108968, "marketType": "playertotals-shotsongoal", "handicap": 1.0, "period": "fulltime"},   # heltal: hoppas över
    {"marketId": 108886, "marketType": "playertotals-shots", "handicap": 0.5, "period": "fulltime"},
    {"marketId": 612712, "marketType": "playertotals-headshots", "handicap": 10.5, "period": "p5"},           # e-sport
]


def pl(name, price, active=True):
    return {"playerName": name, "price": price, "active": active, "changedAt": "2026-11-26T07:15:33.259Z"}


def fixture(start="2026-11-26T20:00:00.000Z"):
    return {"fixtureId": "f1", "participant1Id": 1, "participant2Id": 2, "startTime": start, "hasOdds": True,
            "bookmakerOdds": {"bet365": {"bookmakerIsActive": True, "markets": {
                "108992": {"marketActive": True, "outcomes": {"108992": {"players": {
                    "10": pl("Rodri", 3.75), "11": pl("Wood, Chris", 4.5), "12": pl("Stängd Spelare", 1.01, active=False)}}}},
                "108996": {"marketActive": True, "outcomes": {"108996": {"players": {"10": pl("Rodri", 9.0)}}}},
                "108968": {"marketActive": True, "outcomes": {"108968": {"players": {"10": pl("Rodri", 2.0)}}}},
                "612712": {"marketActive": True, "outcomes": {"1": {"players": {"10": pl("Rodri", 2.0)}}}}}}}}


def test_catalog_keeps_only_half_lines_of_our_markets():
    cat = op.build_catalog(CATALOG_RAW)
    assert set(cat) == {"108992", "108996", "108886"}
    assert cat["108992"] == ["shots_on_target", 0.5, "p1"]


def test_parse_fixture_only_active_players_and_normalised_names():
    rows, multi = op.parse_fixture(fixture(), op.build_catalog(CATALOG_RAW))
    got = {(r["market"], r["line"], r["player"], r["odds"]) for r in rows}
    assert got == {("shots_on_target", 0.5, "Rodri", 3.75), ("shots_on_target", 0.5, "Chris Wood", 4.5),
                   ("shots_on_target", 1.5, "Rodri", 9.0)}
    assert multi == 0


class D:
    def __init__(self):
        self.lines = []

    def log(self, m):
        self.lines.append(m)


def run(tmp_path, monkeypatch, settings=None, state=None, now=None):
    now = now or time.time()
    monkeypatch.setenv("ODDS_PAPI_KEY", "k" * 12)
    monkeypatch.setattr(op.time, "sleep", lambda s: None)
    calls = []

    def fake_get(path, key, **params):
        calls.append((path, params))
        assert key == "k" * 12
        if path == "markets":
            return CATALOG_RAW
        if path == "participants":
            return {"1": "Manchester City FC", "2": "Real Madrid CF", "999": "Annat"}
        if path == "odds-by-tournaments":
            return [fixture(time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(now + 3 * 3600)))]
        raise AssertionError(path)
    monkeypatch.setattr(op, "_get", fake_get)
    if state is not None:
        (tmp_path / op.STATE).write_text(json.dumps(state))
    evd = {"id": "m1", "home_team": "Manchester City", "away_team": "Real Madrid", "commence_time": now + 3 * 3600}
    qs, nm = [], {}
    d = D()
    n = op.add_oddspapi(tmp_path, [(evd, qs, nm)], settings or {}, d)
    return n, calls, qs, d


def test_no_key_does_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("ODDS_PAPI_KEY", raising=False)
    d = D()
    assert op.add_oddspapi(tmp_path, [], {}, d) == 0
    assert not (tmp_path / op.STATE).exists()


def test_bulk_one_call_per_five_leagues_and_data_collection_only(tmp_path, monkeypatch):
    n, calls, qs, d = run(tmp_path, monkeypatch)
    assert [c[0] for c in calls] == ["markets", "odds-by-tournaments", "odds-by-tournaments", "participants"]
    assert calls[1][1]["tournamentIds"] == "17,8,23,35,34" and calls[1][1]["bookmakers"] == "bet365"
    assert calls[2][1]["tournamentIds"] == "7,34480"
    assert n == 6                                  # 3 rader per hämtat gruppanrop (samma testmatch)
    assert qs == []                                # standard: bara datainsamling, ingen röst
    saved = json.loads((tmp_path / op.OUT).read_text())
    assert len(saved["fixtures"]) == 1 and saved["fixtures"]["f1"]["match_id"] == "m1"
    st = json.loads((tmp_path / op.STATE).read_text())
    assert st["used"] == 4 and "ODDS" not in json.dumps(st)


def test_voice_setting_adds_quotes(tmp_path, monkeypatch):
    n, calls, qs, d = run(tmp_path, monkeypatch, {"oddspapi_voice": True})
    assert qs and all(q.book == "op_bet365" and q.side == "over" and q.provider == "oddspapi" for q in qs)
    from propsbot.consensus import voice_of
    assert voice_of("op_bet365") == "op_bet365"


def test_chunk_due_logic():
    now = 1_000_000.0
    h = 3600
    f = op.chunk_due
    assert f(None, now, 150 * 60, 6 * h, 24 * h)                                  # aldrig hämtad: förnya schema
    assert f(now - 60, now, 150 * 60, 6 * h, 24 * h) is True                      # gammalt format utan schema
    fresh = {"ts": now - 60, "starts": [now + 3 * h]}
    assert not f(fresh, now, 150 * 60, 6 * h, 24 * h)                             # match nära men nyss hämtad
    assert f({"ts": now - 200 * 60, "starts": [now + 3 * h]}, now, 150 * 60, 6 * h, 24 * h)   # nära + TTL ute
    assert not f({"ts": now - 200 * 60, "starts": [now + 20 * h]}, now, 150 * 60, 6 * h, 24 * h)   # ingen match nära
    assert f({"ts": now - 25 * h, "starts": [now + 20 * h]}, now, 150 * 60, 6 * h, 24 * h)   # schemat för gammalt


def test_far_groups_skipped_near_groups_fetched(tmp_path, monkeypatch):
    now = time.time()
    month = time.strftime("%Y-%m", time.gmtime(now))
    cat = op.build_catalog(CATALOG_RAW)
    st = {"month": month, "used": 10, "catalog": cat, "catalog_ts": now, "teams": {"1": "Manchester City", "2": "Real Madrid"},
          "teams_try": now,
          "chunks": {"17,8,23,35,34": {"ts": now - 4 * 3600, "starts": [now + 3 * 3600]},      # match nära + TTL ute -> hämtas
                     "7,34480": {"ts": now - 4 * 3600, "starts": [now + 30 * 3600]}}}          # inget nära -> hoppas över
    n, calls, qs, d = run(tmp_path, monkeypatch, state=st, now=now)
    assert [c[0] for c in calls] == ["odds-by-tournaments"] and calls[0][1]["tournamentIds"] == "17,8,23,35,34"
    assert any("1 ligagrupper hoppades över" in m for m in d.lines)
    saved = json.loads((tmp_path / op.STATE).read_text())
    assert saved["chunks"]["17,8,23,35,34"]["starts"] and saved["chunks"]["7,34480"]["starts"] == [now + 30 * 3600]


def test_month_stop_blocks(tmp_path, monkeypatch):
    now = time.time()
    st = {"month": time.strftime("%Y-%m", time.gmtime(now)), "used": 230, "chunks": {}, "catalog": op.build_catalog(CATALOG_RAW),
          "catalog_ts": now, "teams": {}, "teams_try": now}
    n, calls, qs, d = run(tmp_path, monkeypatch, state=st, now=now)
    assert calls == [] and any("månadsgräns" in m for m in d.lines)


def test_no_call_when_no_match_soon(tmp_path, monkeypatch):
    monkeypatch.setenv("ODDS_PAPI_KEY", "k" * 12)
    monkeypatch.setattr(op, "_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("anrop utan match")))
    evd = {"id": "m1", "home_team": "A", "away_team": "B", "commence_time": time.time() + 5 * 86400}
    assert op.add_oddspapi(tmp_path, [(evd, [], {})], {}, D()) == 0
