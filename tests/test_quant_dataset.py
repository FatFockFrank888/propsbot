import json
import math

from propsbot.quant import dataset


def _bet(**kw):
    b = {"key": "k1", "match_id": "m1", "spelare_id": "p1", "marknad": "points", "linje": 20.5, "sida": "over",
         "odds": 1.9, "avspark": 1000.0, "bokford": 500.0, "status": "vunnen", "p_marknad": 0.52,
         "p_modell": 0.6, "skarp_stang_p": 0.55, "f_b2b": True, "f_anv": None, "utfall": 24}
    b.update(kw)
    return b


def test_outcomes_and_skips():
    bets = [_bet(), _bet(key="k2", status="förlorad"), _bet(key="k3", status="struken"),
            _bet(key="k4", status="öppen"), _bet(key="k5", status="push")]
    rows = dataset.build(bets)
    assert [r["y"] for r in rows] == [1, 0]
    assert len(dataset.build(bets, settled_only=False)) == 5


def test_close_never_used_as_market():
    r = dataset.build([_bet(p_marknad=None)])[0]
    assert math.isnan(r["p_market"]) and r["p_close"] == 0.55


def test_missing_features_nan_and_bool():
    r = dataset.build([_bet()])[0]
    assert r["features"]["f_b2b"] == 1.0
    assert math.isnan(r["features"]["f_anv"])
    assert math.isnan(r["features"]["traff_l5"])
    assert r["prognos_ts"] == 500.0


def test_dedup_and_sorting(tmp_path):
    bets = [_bet(key="b", avspark=2000.0), _bet(key="a", avspark=1000.0), _bet(key="a", bokford=900.0, odds=1.5)]
    rows = dataset.build(bets)
    assert [r["key"] for r in rows] == ["a", "b"]
    assert rows[0]["odds"] == 1.9                       # första bokningen behålls
    f = tmp_path / "led.json"
    f.write_text(json.dumps({"bets": bets}), encoding="utf-8")
    assert len(dataset.load(f)) == 2


def test_bad_rows_dropped():
    assert dataset.build([_bet(odds=1.0), _bet(key="x", avspark=None)]) == []
