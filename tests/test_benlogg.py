import json
import math
import random
import time
from types import SimpleNamespace as NS

from propsbot import benlogg as bl
from propsbot.consensus import consensus_p, p_from_parts
from propsbot.models import OddsQuote

TS = 1.8e9


class D:
    def __init__(self):
        self.lines = []

    def log(self, m):
        self.lines.append(m)


def stub_row(pid="x y", line=0.5, state="start", odds=1.9, p_hyb=0.4, with_model=True, match="A – B"):
    best = NS(odds=odds, book="unibet", side="over")
    cand = NS(match_id="k1", player_id=pid, market="shots_on_target", line=line, best=best, edge=0.0, p=0.4,
              player_name="X Y")
    dec = NS(cand=cand, playable=True, show=True, reasons=[], stake=0.0, play_from=2.0)
    ex = {"p_raw_hyb": p_hyb, "p_raw_cur": p_hyb + 0.01, "p_raw_alt": p_hyb - 0.01, "p_adj": 0.38, "p_k": 0.37,
          "p_cons": 0.42, "n_cons": 3, "parts": "p0.4100;q0.4500;q0.4400", "p_mod_utfall": 0.39} if with_model else {}
    return NS(row=NS(decision=dec), extra=ex, match=match, lu_state=state)


EVD = {"k1": {"id": "k1", "commence_time": TS, "home_team": "A", "away_team": "B"}}


def test_fit_logistic_recovers_parameters():
    random.seed(1)
    pairs = []
    for _ in range(6000):
        x = random.uniform(-2.5, 1.0)
        y = 1.0 if random.random() < bl._sig(-0.4 + 0.8 * x) else 0.0
        pairs.append((x, y))
    a, b = bl.fit_logistic(pairs)
    assert abs(a + 0.4) < 0.08 and abs(b - 0.8) < 0.08


def test_consensus_parts_roundtrip_and_margin_effect():
    qs = [OddsQuote("pl_draftkings", "m1", "p1", "shots_on_target", 0.5, "over", 1.80, 0.0, provider="propline"),
          OddsQuote("pl_fanduel", "m1", "p1", "shots_on_target", 0.5, "over", 1.90, 0.0, provider="propline")]
    r = consensus_p(qs, "p1", "shots_on_target", 0.5, 0.07, 2)
    assert "parts" in r and abs(p_from_parts(r["parts"], 0.07) - r["p"]) < 1e-4
    assert p_from_parts(r["parts"], 0.20) < r["p"]            # högre marginal -> lägre p


def test_record_all_only_confirmed_starters_before_kickoff(tmp_path):
    now = TS - 3600
    led = bl.record_all(tmp_path, [stub_row(), stub_row(pid="bänk", state="bänk"), stub_row(pid="vantar", state="väntar"),
                                   stub_row(pid="ingenmodell", with_model=False)], EVD, now=now)
    assert [b["key"] for b in led.bets] == ["k1|x y|shots_on_target|0.5"] and led.stats == (1, 0)
    led.save()
    led2 = bl.record_all(tmp_path, [stub_row(odds=2.0)], EVD, now=now + 600)       # uppdaterar ögonblicksbilden
    assert led2.stats == (0, 1) and led2.bets[0]["odds"] == 2.0 and len(led2.bets) == 1
    led3 = bl.record_all(tmp_path, [stub_row(pid="sen")], EVD, now=TS + 60)         # efter avspark: loggas inte
    assert led3.stats == (0, 0)


def test_finish_harvests_settled_and_does_not_duplicate(tmp_path, monkeypatch):
    import propsbot.results as res
    monkeypatch.setattr(res, "settle_open", lambda led, client: None)
    led = bl.record_all(tmp_path, [stub_row(), stub_row(pid="z z")], EVD, now=TS - 7200)
    led.bets[0]["status"] = "vunnen"
    led.bets[1]["status"] = "struken"
    d = D()
    bl.finish(tmp_path, led, None, {}, d, now=TS + 86400)
    done = json.loads((tmp_path / bl.DONE_FILE).read_text())
    assert len(done["rows"]) == 1 and done["rows"][0][4] == 1 and done["cols"] == bl.COLS
    assert json.loads((tmp_path / bl.LEG_FILE).read_text()) == []                   # avgjorda och struken borta
    led2 = bl.record_all(tmp_path, [stub_row()], EVD, now=TS - 100)                  # redan avgjort: loggas inte igen
    assert led2.bets == []


def _fake_done(n, a_true=-0.5, b_true=0.8, m_true=0.15, seed=3):
    random.seed(seed)
    rows = []
    for i in range(n):
        p_hyb = random.uniform(0.12, 0.6)
        y = 1 if random.random() < bl._sig(a_true + b_true * bl._logit(p_hyb)) else 0
        # konsensus: tre ensidiga röster vars "sanna" p = p_true, prissatta med marginal m_true
        p_true = bl._sig(a_true + b_true * bl._logit(p_hyb))
        qs = [min(0.95, p_true * (1 + m_true) * random.uniform(0.97, 1.03)) for _ in range(3)]
        parts = ";".join(f"q{q:.4f}" for q in qs)
        p_cons = p_from_parts(parts, 0.07)
        y2 = 1 if random.random() < p_true else 0
        rows.append([f"k{i}", TS + i * 60, "shots_on_target", 0.5, y2, p_hyb, p_hyb, p_hyb, p_hyb, p_hyb, p_cons, 3, parts, 1.9,
                     None])
    return {"cols": bl.COLS, "rows": rows}


def test_analyse_saves_outcome_calibration_and_consensus_margin(tmp_path):
    done = _fake_done(900)
    d = D()
    bl.analyse(tmp_path, done, {}, d)
    cal = json.loads((tmp_path / bl.CAL_FILE).read_text())["fits"]["shots_on_target|0.5"]
    assert abs(cal["a"] + 0.5) < 0.2 and abs(cal["b"] - 0.8) < 0.2 and cal["brier_kal_holdout"] < cal["brier_rå_holdout"]
    m = json.loads((tmp_path / bl.MARGIN_FILE).read_text())
    assert 0.10 <= m["m"] <= 0.20 and m["n"] >= 150
    assert any("nivåkalibrering" in x for x in d.lines) and any("konsensusmarginal" in x for x in d.lines)


def test_analyse_waits_for_enough_data(tmp_path):
    d = D()
    bl.analyse(tmp_path, _fake_done(60), {}, d)
    assert not (tmp_path / bl.CAL_FILE).exists() and not (tmp_path / bl.MARGIN_FILE).exists()


def test_load_cal_merges_prior_and_own_and_margin_loader(tmp_path):
    cal = bl.load_cal(tmp_path)
    assert cal["shots_on_target|0.5"]["src"].startswith("start") and bl.CAL["shots_on_target|0.5"]["b"] == 0.9306
    (tmp_path / bl.CAL_FILE).write_text(json.dumps({"fits": {"shots_on_target|0.5": {"a": -0.1, "b": 0.7, "n": 200}}}))
    assert bl.load_cal(tmp_path)["shots_on_target|0.5"]["src"].startswith("egen")
    assert bl.consensus_margin(tmp_path, {}) == 0.07                                  # ingen fil: antagen marginal
    (tmp_path / bl.MARGIN_FILE).write_text(json.dumps({"m": 0.13, "n": 300}))
    assert bl.consensus_margin(tmp_path, {}) == 0.13
    assert bl.consensus_margin(tmp_path, {"consensus_margin_auto": False}) == 0.07
    (tmp_path / bl.MARGIN_FILE).write_text(json.dumps({"m": 0.13, "n": 40}))
    assert bl.consensus_margin(tmp_path, {}) == 0.07                                  # för få ben: antagen marginal


def test_line_adjust_logs_outcome_level_and_switch(monkeypatch):
    from propsbot.config import Config
    from propsbot.line_adjust import Lines, evaluate_line_adjusted
    from propsbot.player_model import PlayerRates
    from propsbot.scan import DEFAULT_SETTINGS
    now = time.time()
    evd = {"id": "k1", "home_team": "A", "away_team": "B", "commence_time": now + 7200}
    kambi, pin = Lines((2.0, 3.5, 3.8), 2.5, (2.10, 1.75)), Lines((1.95, 3.7, 4.0), 2.5, (1.95, 1.90))
    q = [OddsQuote(b, "k1", "x y", "goal", 0.5, "over", o, now, provider="kambi")
         for b, o in (("unibet", 2.60), ("paf", 2.75), ("atg", 2.60))]
    pr = PlayerRates("X Y", "t", 10, 8, 10, rate={"goal": 0.4})
    pr.mu_alt["goal"] = pr.mu_cur["goal"] = pr.mu_hyb["goal"] = 0.4
    model = {("x y", "goal"): (0.4, pr)}
    monkeypatch.setitem(bl.CAL, "goal|0.5", {"a": 0.5, "b": 1.0, "src": "test", "n": 0})
    s = dict(DEFAULT_SETTINGS, playable_books=[])
    rows, _ = evaluate_line_adjusted(evd, q, {"x y": "X Y"}, s, Config(), now, pin, kambi, model, {}, None, None)
    ex = rows[0].extra
    assert {"p_adj", "p_k", "p_mod_utfall"} <= set(ex)
    p_marknad_niva = rows[0].row.p_model
    rows2, _ = evaluate_line_adjusted(evd, q, {"x y": "X Y"}, dict(s, model_level="utfall"), Config(), now, pin, kambi,
                                      model, {}, None, None)
    assert abs(rows2[0].row.p_model - ex["p_mod_utfall"]) < 1e-3 and rows2[0].row.p_model != p_marknad_niva
