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
    (tmp_path / sp.LEDGER).write_text(json.dumps({"bets": [bet()]}), encoding="utf-8")
    assert sp.export(tmp_path, {}) == 1
    d = json.loads((tmp_path / "site" / "spelarprops.json").read_text(encoding="utf-8"))
    assert d["bets"][0]["hade_blivit"] in ("C", "–")
    rows = (tmp_path / "site" / "csv" / "spelarprops.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("Bokförd,Avspark") and len(rows) == 2 and "0.55" in rows[1]
