"""Spela från i nivånotisen: krav_edge per källa, rättat spela_fran, rum och ⚠️ snävt."""
import json
import time

import pytest

from propsbot.tiers import TierBook, cfg, krav_edge, min_odds, run, spela_fran_text

S = {"min_edge_all": 0.06, "live_min_edge": {"points": 0.07, "rebounds": 0.07}, "sides_min_edge": 0.03,
     "nba_sides_min_edge": 0.03, "sides_alt_extra_edge": 0.01, "sides_single_ref_extra_edge": 0.01,
     "sides_low_limit": 2000, "sides_low_limit_extra_edge": 0.01, "extra_edge_without_sharp": 0.03}
C = cfg(S)


def prop(**kw):
    now = time.time()
    b = {"key": "k1", "match_id": "m1", "spelare_id": "p1", "spelare": "X", "marknad": "shots", "linje": 1.5,
         "sida": "over", "odds": 2.30, "sannolikhet": 0.4652, "edge": 0.07, "stopp": "", "bokford": now - 60,
         "avspark": now + 7200, "match": "A – B", "liga": "L", "bolag": "Unibet", "spela_fran": 2.20,
         "status": "öppen", "pin_stang_p": 0.45, "insats_pct": 0.002}
    b.update(kw)
    return b


def side(**kw):
    b = prop(spelare_id="match", spelare="A", marknad="total", linje=2.5, spel_text="över 2,5 mål",
             pin_grans=5000, alternativ_linje=False)
    b.update(kw)
    return b


def test_min_odds():
    assert min_odds(0.5, 0.06) == 2.12
    assert min_odds(0.53, 0.06) == 2.0            # 1,06/0,53 = 2,0 exakt – ingen avrundning uppåt av flyttal
    assert min_odds(0.4652, 0.06) == pytest.approx(2.28)


def test_krav_props():
    assert krav_edge(prop(), "A", "spel", "fotboll", C) == 0.06                 # min_edge_all
    assert krav_edge(prop(), "B", "spel", "fotboll", C) == 0.05                 # B: tier_b_min_edge
    assert krav_edge(prop(), "C", "skugga", "fotboll", C) == 0.04
    # mål utan Pinnacle/tvåsidig källa: 4 % + 3 % = 7 % > min_edge_all
    weak = prop(marknad="goal", stopp="ingen Pinnacle/tvåsidig källa – högre edgekrav")
    assert krav_edge(weak, "A", "spel", "fotboll", C) == 0.07
    # NBA: A kräver LIVE-kravet per marknad (7 %)
    assert krav_edge(prop(marknad="points"), "A", "live", "nba", C) == 0.07
    assert krav_edge(prop(marknad="points"), "B", "spel", "nba", C) == 0.05


def test_krav_sides():
    assert krav_edge(side(), "A", "spel", "fotboll", C) == 0.05                  # 3 % < B-kravet 5 %
    assert krav_edge(side(alternativ_linje=True, pin_grans=1000), "A", "spel", "fotboll", C) == 0.05
    s2 = dict(S, sides_min_edge=0.05)
    c2 = cfg(s2)
    assert krav_edge(side(alternativ_linje=True, pin_grans=1000), "A", "spel", "fotboll", c2) == 0.07
    assert krav_edge(side(marknad="corners", spelare_id="hörnor", pin_grans=10 ** 6), "A", "spel", "fotboll", c2) == 0.06
    c3 = cfg(dict(S, nba_sides_min_edge=0.045))
    assert krav_edge(side(marknad="spread", alternativ_linje=True), "A", "spel", "nba", c3) == 0.055
    assert krav_edge(side(marknad="spread", pin_grans=900), "A", "spel", "nba", c3) == 0.055


def _run(tmp_path, files, settings=S):
    for f, bets in files.items():
        (tmp_path / f).write_text(json.dumps(bets))
    sent = []
    import propsbot.notify as nt
    orig = nt.send
    nt.send = lambda *a, **k: sent.append(a) or True
    try:
        res = run(tmp_path, dict(settings, ntfy_topic="t"), notify=True, log=lambda *_: None)
    finally:
        nt.send = orig
    return {b["kalla_key"]: b for b in res["book"].bets}, sent


def test_props_record_and_push(tmp_path):
    bets, sent = _run(tmp_path, {"bokforing_v3.json": [prop()]})
    b = bets["k1"]
    assert b["tier"] == "A" and b["krav_edge"] == 0.06
    assert b["spela_fran_kalla"] == 2.20 and b["spela_fran"] == pytest.approx(2.28)
    assert b["rum"] == pytest.approx(2.30 / 2.28 - 1)
    assert "@ 2,30 (spela från 2,28, rum +0,9 %)" in sent[0][2] and "snävt rum" in sent[0][2]


def test_football_sides_record(tmp_path):
    b = side(odds=2.10, sannolikhet=0.5, edge=0.05, alternativ_linje=True, pin_grans=1500, spela_fran=2.06)
    bets, sent = _run(tmp_path, {"sides_spel.json": [b]}, dict(S, sides_min_edge=0.02))
    r = bets["k1"]
    assert r["tier"] == "A" and r["krav_edge"] == 0.05 and r["spela_fran"] == 2.10   # 2 % + 1 % + 1 % < 5 %
    assert "rum +0,0 %)" in sent[0][2] and "snävt rum" in sent[0][2]


def test_nba_sides_record(tmp_path):
    b = side(marknad="game_total", odds=2.20, sannolikhet=0.5, edge=0.10, spela_fran=2.06)
    bets, sent = _run(tmp_path, {"nba_sides_spel.json": [b]})
    r = bets["k1"]
    assert r["tier"] == "A" and r["sport"] == "nba" and r["krav_edge"] == 0.05
    assert r["spela_fran"] == 2.10 and r["rum"] == pytest.approx(2.20 / 2.10 - 1)
    assert "(spela från 2,10, rum +4,8 %)" in sent[0][2] and "snävt" not in sent[0][2]


def test_old_record_without_krav(tmp_path):
    """Ett gammalt, redan notifierat spel i tiers.json (utan krav_edge) räknas om vid nästa körning."""
    p = prop()
    (tmp_path / "bokforing_v3.json").write_text(json.dumps([p]))
    old = {k: p.get(k) for k in ("match_id", "match", "spelare", "spelare_id", "marknad", "linje", "sida", "bolag",
                                 "odds", "sannolikhet", "edge", "spela_fran", "stopp", "avspark", "analys")}
    old.update(ident="fotboll|m1|p1", sport="fotboll", tier="A", units=1, kalla="spel", kalla_fil="bokforing_v3.json",
               kalla_key="k1", bokford=p["bokford"], inte_hogre=[], unit_pct=0.01, id=1, notis=True, spelad=True)
    (tmp_path / "tiers.json").write_text(json.dumps({"bets": [old], "sedda": ["bokforing_v3.json|k1"]}))
    bets, sent = _run(tmp_path, {})
    r = bets["k1"]
    assert not sent                                                     # redan notifierat
    assert r["krav_edge"] == 0.06 and r["spela_fran_kalla"] == 2.20 and r["spela_fran"] == pytest.approx(2.28)
    # en körning till: spela_fran_kalla behålls (skrivs inte över med det rättade värdet)
    bets, _ = _run(tmp_path, {})
    assert bets["k1"]["spela_fran_kalla"] == 2.20
    saved = TierBook(tmp_path / "tiers.json").bets[0]
    assert saved["rum"] == pytest.approx(2.30 / 2.28 - 1)


def test_push_text():
    assert spela_fran_text({"spela_fran": 1.98, "rum": 2.05 / 1.98 - 1}) == "(spela från 1.98, rum +3,5 %)"
    assert spela_fran_text({"spela_fran": 2.0, "rum": 0.005}) == "(spela från 2.00, rum +0,5 %) ⚠️ snävt"
    assert spela_fran_text({"spela_fran": 2.0}) == "(spela från 2.00)"
