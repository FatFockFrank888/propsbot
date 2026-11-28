import json

from propsbot import spelarprops as sp
from propsbot import tiers
from propsbot.player_model import ELASTICITY, ELASTICITY_ALT, ELASTICITY_HYB


def bet(**k):
    b = {"key": "k", "match": "A – B", "match_id": "k123456", "spelare": "X Y", "marknad": "shots_on_target", "linje": 1.5,
         "sida": "over", "bolag": "unibet", "odds": 2.1, "sannolikhet": 0.52, "edge": 0.092, "status": "vunnen",
         "avspark": 1.8e9, "bokford": 1.79e9, "insats_pct": 0.004, "resultat_enheter": 0.0044, "stangning": 2.0,
         "stopp": "", "p_raw_cur": 0.6, "p_raw_alt": 0.5, "p_raw_hyb": 0.55}
    b.update(k)
    return b


def test_hybrid_is_midpoint():
    for m in ELASTICITY:
        assert abs(ELASTICITY_HYB[m] - (ELASTICITY[m] + ELASTICITY_ALT[m]) / 2) < 1e-12


def test_annotate_never_above_c_without_sharp_ref():
    c = tiers.cfg({})
    a = sp.annotate(bet(), c)
    assert a["hade_blivit"] in ("C", "–") and isinstance(a["varfor_inte_hogre"], list) and a["motiv"]["fair_odds"]


def test_export_writes_json_and_csv(tmp_path):
    (tmp_path / sp.LEDGER).write_text(json.dumps([bet()]), encoding="utf-8")   # Ledger.save() skriver en ren lista
    assert sp.export(tmp_path, {}) == 1
    d = json.loads((tmp_path / "site" / "spelarprops.json").read_text(encoding="utf-8"))
    assert d["bets"][0]["hade_blivit"] in ("C", "–")
    rows = (tmp_path / "site" / "csv" / "spelarprops.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("Bokförd,Avspark") and len(rows) == 2 and "0.55" in rows[1]


def test_record_hyb_books_consensus_arm(tmp_path):
    from types import SimpleNamespace as NS
    from propsbot.models import OddsQuote
    from propsbot.sources.propline import parse
    from propsbot.sources import propline as pl
    ev = {"bookmakers": [
        {"key": k, "markets": [{"key": "player_shots_on_target", "outcomes": [
            {"description": "Cole Palmer", "name": "1+ Shots on Target", "price": pr, "point": None}]}]}
        for k, pr in (("draftkings", -200), ("fanduel", -190))]}
    q, _ = parse(ev, "m1", 1.0)
    pid = q[0].player_id
    best = NS(odds=1.8, book="unibet", side="over")
    cand = NS(match_id="m1", player_id=pid, market="shots_on_target", line=0.5, best=best, edge=-0.03, p=0.54,
              player_name="Cole Palmer")
    dec = NS(cand=cand, playable=False, show=False, reasons=[], stake=0.0, play_from=1.9)
    row = NS(row=NS(decision=dec, p_model=0.5, p_market=0.5), extra=None, match="A – B", kickoff="2026-11-25 20:00")

    class D:
        lines = []
        def log(self, m): self.lines.append(m)
    d = D()
    import propsbot.free_scan as fs
    fs.apply_lineups = lambda *a, **k: "ok"          # ingen nätverksanrop i testet
    n = sp.record_hyb(tmp_path, [row], [], {"m1": {"id": "m1", "commence_time": 9e9, "home_team": "A", "away_team": "B"}},
                      [({"id": "m1"}, q, {})], {"football_markets": ["shots_on_target"]}, d)
    assert row.extra["arm"] == "konsensus" and row.extra["edge_cons"] > 0.02
    assert any("Spelarprops-konsensus" in x for x in d.lines)
