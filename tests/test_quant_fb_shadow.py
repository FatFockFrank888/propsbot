"""F5: per 90-skuggan (p_fb2) i spelarmodellen och benloggen – styr ingenting, ändrar inte dagens modell."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone
from types import SimpleNamespace as NS

from propsbot import benlogg
from propsbot.player_model import PlayerModel, model_probs
from propsbot.sources import http as httpmod
from propsbot.sources.http import JsonClient

NOW = time.time()
CALLS = []


class _R(io.BytesIO):
    def __init__(self, d):
        super().__init__(json.dumps(d).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _roster(tid, i):
    out = [{"athlete": {"displayName": f"Anfallare {tid}"}, "starter": True, "position": {"abbreviation": "F"},
            "subbedOut": True, "plays": [{"substitution": True, "clock": {"displayValue": "70'"}}],
            "stats": [{"name": "totalShots", "value": 4}, {"name": "shotsOnTarget", "value": 2}]}]
    out += [{"athlete": {"displayName": f"Back{k} {tid}"}, "starter": True, "position": {"abbreviation": "CD-L"},
             "stats": [{"name": "totalShots", "value": 1 if k == 1 else 0}, {"name": "shotsOnTarget", "value": 0}]}
            for k in range(1, 11)]
    return out


def fake(req, timeout=20, **kw):
    path = urllib.parse.urlparse(req.full_url).path
    if path.endswith("/schedule"):
        tid = path.split("/")[-2]
        return _R({"team": {"displayName": "T" + tid}, "events": [
            {"id": f"{tid}0{i:02d}", "date": iso(NOW - (i + 1) * 7 * 86400),
             "competitions": [{"status": {"type": {"completed": True}}}]} for i in range(20)]})
    if path.endswith("/summary"):
        eid = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)["event"][0]
        CALLS.append(eid)
        tid = eid[0]
        return _R({"header": {"competitions": [{"competitors": [{"id": tid, "score": "1"}]}]},
                   "rosters": [{"team": {"id": tid}, "roster": _roster(tid, int(eid[2:]))}]})
    raise AssertionError(req.full_url)


def _pm(tmp_path, **kw):
    return PlayerModel(JsonClient(tmp_path / "c", ttl_s=0, min_interval_s=0), tmp_path / "espn", **kw)


def test_fb2_computed_and_m0_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    tm = _pm(tmp_path, fb2_matches=15).team("eng.1", "1", NOW)
    (tmp_path / "b").mkdir()
    base = _pm(tmp_path / "b", fb2_matches=0).team("eng.1", "1", NOW)       # utan skuggan
    for k, pr in base.players.items():
        assert tm.players[k].rate == pr.rate and tm.players[k].apps == pr.apps   # dagens modell exakt oförändrad
    fw = tm.players["anfallare 1"]
    assert fw.fb2_grp == "ST" and 60 < fw.fb2_emin < 80                      # byts vid 70', prior 80
    # 4 skott på 70 min = 5,1 per 90, krympt mot anfallarsnittet (bara han i gruppen -> samma) ≈ 5,1
    assert abs(fw.fb2["shots"] - 4 * 90 / 70) < 0.05
    back = tm.players["back2 1"]
    assert back.fb2_grp == "CB" and back.fb2["shots"] < 0.2                   # mittbackar: lågt snitt
    out = model_probs(tm, tm.avg_goals)
    assert abs(fw.mu_fb2["shots"] - fw.fb2["shots"] * fw.fb2_emin / 90) < 1e-9   # ratio = 1
    assert (("anfallare 1", "shots") in out) and "goal" not in fw.mu_fb2


def test_backfill_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    d = tmp_path / "espn"
    d.mkdir()
    for i in range(20):                                                       # gamla v1-utdrag utan minuter
        (d / f"eng.1_10{i:02d}.json").write_text(json.dumps({"teams": {"1": [{"n": "Anfallare 1", "s": True,
                                                  "shots": 4, "shots_on_target": 2, "goal": 0, "assist": 0}]}}))
    CALLS.clear()
    pm = _pm(tmp_path, fb2_matches=15, fb2_backfill=5)
    pm.team("eng.1", "1", NOW)
    assert pm.store.refetched == 5 and len(CALLS) == 5                        # bara inom budget
    v2 = [f for f in d.glob("eng.1_*.json") if json.loads(f.read_text()).get("v") == 2]
    assert len(v2) == 5
    pm2 = _pm(tmp_path, fb2_matches=15, fb2_backfill=0)                       # utan budget: inga nya anrop
    CALLS.clear()
    pm2.team("eng.1", "1", NOW)
    assert CALLS == []


def _row(extra, lu="start"):
    c = NS(match_id="m1", player_id="p1", player_name="P", market="shots", line=1.5,
           best=NS(book="unibet", odds=2.2))
    return NS(lu_state=lu, extra=extra, row=NS(decision=NS(cand=c)), match="A – B")


def test_benlogg_records_fb2(tmp_path):
    ev = {"m1": {"commence_time": time.time() + 3600, "home_team": "A", "borta": "B"}}
    led = benlogg.record_all(tmp_path, [_row({"p_raw_hyb": 0.4, "p_raw_fb2": 0.47, "p_raw_fb2k": 0.5})], ev)
    b = led.bets[0]
    assert b["p_fb2"] == 0.47 and b["p_fb20"] == 0.47 and b["p_fb2k"] == 0.5 and b["p_fb2k0"] == 0.5
    led = benlogg.record_all(tmp_path, [_row({"p_raw_hyb": 0.4})], ev)        # utan fb2: ingen krasch
    assert led.bets[0].get("p_fb2") is None
    # gamla avgjorda rader (utan de nya kolumnerna) läses fortfarande
    old = {"cols": benlogg.COLS[:-4], "rows": [["k", 1.0, "shots", 1.5, 1, 0.4, 0.4, 0.4, 0.4, None, None, None,
                                                 None, 2.0, None, 2.0, 0.4, None, None, 0.4]]}
    benlogg.analyse(tmp_path, old, {}, NS(log=lambda *_: None))
    assert benlogg.COLS[-4:] == ["p_fb2", "p_fb20", "p_fb2k", "p_fb2k0"]


def test_fb2_context(tmp_path, monkeypatch):
    from propsbot.player_model import apply_fb2_context
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    pm = _pm(tmp_path, fb2_matches=15)
    tm1, tm2 = pm.team("eng.1", "1", NOW), pm.team("eng.1", "2", NOW)
    assert tm1.conc == [] and tm2.conc == []            # låtsasmatcherna har bara ett lag per utdrag
    lc = pm.league_conceded("eng.1")
    assert lc == {}                                     # för få matcher med två lag -> ingen motståndarfaktor
    model_probs(tm1, tm1.avg_goals)
    apply_fb2_context(tm1, tm2, True, lc, {"shots": 0.75}, {"shots": 0.1, "shots_on_target": 0.15})
    fw = tm1.players["anfallare 1"]
    assert abs(fw.mu_fb2k["shots"] - fw.mu_fb2["shots"] * 1.1) < 1e-9          # bara hemmafaktorn
    assert abs(fw.mu_fb2k["shots_on_target"] - fw.mu_fb2["shots_on_target"] * 1.15) < 1e-9
    # med motståndardata: medgivet 18 mot ligasnitt 12 -> faktor 1,25 (krympt), ^0,75
    tm2.conc = [{"shots": 18.0, "shots_on_target": 6.0}] * 5
    apply_fb2_context(tm1, tm2, False, {"shots": 12.0, "shots_on_target": 4.0}, {"shots": 0.75}, {"shots": 0.1})
    assert abs(fw.mu_fb2k["shots"] - fw.mu_fb2["shots"] * 1.25 ** 0.75 / 1.1) < 1e-9
    assert abs(fw.mu_fb2k["shots_on_target"] - fw.mu_fb2["shots_on_target"]) < 1e-9   # e = 0, h = 0
    before = {k: dict(p.rate) for k, p in tm1.players.items()}
    apply_fb2_context(tm1, None, None, {}, {"shots": 1.0}, {"shots": 0.2})
    assert {k: p.rate for k, p in tm1.players.items()} == before                # dagens modell orörd
    assert abs(fw.mu_fb2k["shots"] - fw.mu_fb2["shots"]) < 1e-9                  # saknad data -> 1


def test_conceded_from_two_team_extracts(tmp_path):
    d = tmp_path / "espn"
    d.mkdir()
    for i in range(25):
        (d / f"eng.1_{i}.json").write_text(json.dumps({"v": 2, "teams": {
            "1": [{"n": "a", "s": True, "shots": 10, "shots_on_target": 4}],
            "2": [{"n": "b", "s": True, "shots": 14, "shots_on_target": 5}]}}))
    pm = _pm(tmp_path)
    assert pm.league_conceded("eng.1") == {"shots": 12.0, "shots_on_target": 4.5}
