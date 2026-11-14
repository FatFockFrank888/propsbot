"""Faktormodellen (nba_factors) mot ESPN-format med position, skottförsök och schema med motståndare."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone

from propsbot.nba_factors import FactorModel, factor_summary
from propsbot.nba_model import NbaModel
from propsbot.sources import http as httpmod
from propsbot.sources.http import JsonClient

NOW = time.time()
UP = NOW + 5 * 3600
LABELS = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


class _R(io.BytesIO):
    def __init__(self, d):
        super().__init__(json.dumps(d).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def ath(name, pos, mins, pts, reb, ast, starter=True):
    return {"athlete": {"displayName": name, "position": {"abbreviation": pos}}, "starter": starter,
            "stats": [str(mins), str(pts), "8-18", "2-6", "4-5", str(reb), str(ast), "2", "1", "1", "1",
                      str(max(reb - 1, 0)), "2", "+3"]}


ROSTER = {
    "10": [("Star Guard", "G", 36, 30, 5, 8), ("Hurt Guard", "G", 32, 20, 4, 6), ("Big Man", "C", 30, 14, 11, 2),
           ("Wing", "F", 28, 12, 6, 3), ("Bench Guard", "G", 18, 7, 2, 3)],
    "20": [("Opp Guard", "G", 36, 25, 4, 7), ("Opp Center", "C", 34, 18, 14, 2), ("Opp Wing", "F", 30, 14, 6, 3),
           ("Opp Bench", "G", 20, 8, 2, 2)],
}


def fake(req, timeout=20, **kw):
    u = urllib.parse.urlparse(req.full_url)
    path, q = u.path, urllib.parse.parse_qs(u.query)
    if path.endswith("/scoreboard"):
        return _R({"events": [{"id": "1", "date": iso(UP), "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"id": "10", "displayName": "Boston Celtics"}},
            {"homeAway": "away", "team": {"id": "20", "displayName": "New York Knicks"}}]}]}]})
    if path.endswith("/schedule"):
        tid = path.split("/")[-2]
        prev = "season" in q
        evs = []
        for i in range(6 if not prev else 3):
            opp = "20" if i in (0, 3) else "99"      # två matcher i år mot motståndaren
            evs.append({"id": f"{'p' if prev else ''}{tid}{i}", "date": iso(NOW - (i + 1) * 2 * 86400 - (400 * 86400 if prev else 0)),
                        "competitions": [{"status": {"type": {"completed": True}}, "competitors": [
                            {"id": tid, "homeAway": "home"}, {"id": "20" if prev else opp, "homeAway": "away"}]}]})
        return _R({"team": {"displayName": tid}, "season": {"year": 2027}, "events": evs})
    if path.endswith("/summary"):
        eid = q["event"][0].lstrip("p")
        tid = eid[:2]
        other = "20" if tid == "10" else "10"
        mine = [ath(*r) for r in ROSTER[tid]]
        theirs = [ath(*r) for r in ROSTER[other]]
        return _R({"header": {"competitions": [{"competitors": [{"id": tid, "score": "112"}, {"id": other, "score": "108"}]}]},
                   "boxscore": {"players": [{"team": {"id": tid}, "statistics": [{"labels": LABELS, "athletes": mine}]},
                                            {"team": {"id": other}, "statistics": [{"labels": LABELS, "athletes": theirs}]}]}})
    if path.endswith("/injuries"):
        return _R({"injuries": [{"injuries": [
            {"athlete": {"displayName": "Hurt Guard"}, "status": "Out", "shortComment": "Out (ankle)."},
            {"athlete": {"displayName": "Big Man"}, "status": "Day-To-Day",
             "shortComment": "Big Man will play but is on a minutes restriction."}]}]})
    raise AssertionError(req.full_url)


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)
    nm = NbaModel(JsonClient(tmp_path / "c", min_interval_s=0), tmp_path / "box")
    th, ta = nm.team("10", UP), nm.team("20", UP)
    fm = FactorModel(nm)
    fm.set_league([th, ta])
    return nm, fm, th, ta


def test_box_v2_and_profile(tmp_path, monkeypatch):
    nm, fm, th, ta = _setup(tmp_path, monkeypatch)
    assert th.players["star guard"].pos == "G" and th.players["big man"].pos == "C"
    assert th.games[0][2] == "20" and th.games[0][3] is True
    prof = fm.profile(th)
    assert 80 < prof["pace"] < 120
    assert fm.league and fm.league["allowed"]["C"]["rebounds"] > fm.league["allowed"]["G"]["rebounds"]


def test_expected_factors(tmp_path, monkeypatch):
    nm, fm, th, ta = _setup(tmp_path, monkeypatch)
    base = nm.expected(th, ta, UP, 110.0)
    e = fm.expected(th, ta, UP, True, total=224.0, spread_home=-4.0)
    assert "hurt guard" not in e
    star, bench = e["star guard"], e["bench guard"]
    # samma position som den skadade får mer av minuterna än grundmodellens proportionella fördelning
    assert bench["_min"] - 18 > (base["bench guard"]["_min"] - 18) * 0.95
    # användning: stjärnan tar en del av den skadades produktion utöver minuterna
    assert star["_f"]["stat"]["points"]["anv"] > 1.0
    # minutbegränsning -> färre minuter och större spridning
    # (under sina 30 min trots att en lagkamrat är ute och laget skalas upp mot 241 min)
    assert e["big man"]["_f"]["minutbegransning"] and e["big man"]["_min"] < 27
    assert e["big man"]["_min_sd"] > th.players["big man"].min_sd
    # marknadens lagtotal: (224 + 4) / 2 = 114 för hemmalaget
    assert star["_f"]["lag_vantade_poang"] == 114.0 and star["_f"]["miljo_kalla"] == "pinnacle"
    s = factor_summary(star, "pra")
    assert all(s[f"f_{n}"] is not None for n in ("anv", "miljo", "tempo", "pos", "mot"))
    for x in e.values():
        for st in x["_f"]["stat"].values():
            assert 0.85 <= st["miljo"] <= 1.15 and 0.88 <= st["pos"] <= 1.12 and 0.92 <= st["mot"] <= 1.08


def test_hit_rates(tmp_path, monkeypatch):
    nm, fm, th, ta = _setup(tmp_path, monkeypatch)
    hr = fm.hit_rates(th, "star guard", "points", 29.5, "20", True)
    assert hr["traff_l5"] == 1.0 and hr["traff_l5_n"] == 5 and hr["traff_sasong_n"] == 6
    assert hr["traff_mot_n"] == 2 + 3          # två i år + tre förra säsongen
    hr2 = fm.hit_rates(th, "star guard", "pra", 50.5, "20", True)
    assert hr2["traff_sasong"] == 0.0          # 30+5+8 = 43 < 50,5


def test_model_test_rows_logs_factor_shadow(tmp_path, monkeypatch):
    """Hela kedjan i nba.model_test_rows: faktormodellens skuggfält och träffbild hamnar i extra."""
    from propsbot import nba
    from propsbot.config import Config
    from propsbot.decision import Candidate, Decision
    from propsbot.models import OddsQuote
    from propsbot.pipeline import Row
    from propsbot.scan import ScanRow

    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)
    monkeypatch.setitem(nba.SPREADS, "nba1", -4.0)
    monkeypatch.setitem(nba.TOTALS, "nba1", 224.0)
    evd = {"id": "nba1", "home_team": "Boston Celtics", "away_team": "New York Knicks", "commence_time": UP}
    q = OddsQuote("unibet", "nba1", "star guard", "points", 29.5, "under", 1.9, NOW)
    cand = Candidate("nba1", "star guard", "Star Guard", "points", 29.5, 0.5, q, 1.9, NOW, False, 300)
    rows = [ScanRow("NBA", "BOS-NYK", iso(UP), Row(Decision(cand, False, True, 2.0, 0.0, []), 0.5, 0.5, 0.0), 1)]

    class D:
        def log(self, m):
            print(m)

    out = nba.model_test_rows(tmp_path, rows, {"nba1": (evd, [], {})}, {}, Config(), D())
    assert len(out) == 1
    x = out[0].extra
    assert 0 < x["p_faktorer"] < 1 and 0 < x["p_faktorer_ra"] < 1 and x["vantat_faktorer"] > 0
    assert x["f_lag_poang"] == 114.0 and x["f_miljo_kalla"] == "pinnacle"
    # under 29,5: stjärnan gjorde 30 i alla matcher -> 0 % för vår sida
    assert x["traff_l5"] == 0.0 and x["traff_sasong_n"] == 6
