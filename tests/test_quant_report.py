import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import quant_report  # noqa: E402


def _ledger(n=240, seed=5):
    rnd = random.Random(seed)
    bets = []
    for i in range(n):
        p = rnd.uniform(0.35, 0.65)
        bets.append({"key": f"k{i}", "match_id": f"m{i // 3}", "spelare_id": f"p{i}", "marknad": "points",
                     "linje": 20.5, "sida": "over", "odds": round(1 / p * 0.97, 2), "avspark": 1e9 + (i // 3) * 86400,
                     "bokford": 1e9 + (i // 3) * 86400 - 3600, "p_marknad": p, "p_modell": min(0.95, p + rnd.uniform(-.1, .1)),
                     "skarp_stang_p": p, "status": "vunnen" if rnd.random() < p else "förlorad",
                     "vantat_faktorer": 20.0, "utfall": rnd.randint(10, 30), "sannolikhet": p, "units": 1,
                     "unit_pct": 0.01, "sport": "nba"})
    return bets


def test_report_runs_and_is_summary_only(tmp_path):
    f = tmp_path / "l.json"
    f.write_text(json.dumps(_ledger()), encoding="utf-8")
    t = tmp_path / "t.json"
    t.write_text(json.dumps({"bets": _ledger()}), encoding="utf-8")
    out = tmp_path / "r.md"
    quant_report.main(["--ledger", str(f), "--tiers", str(t), "--out", str(out)])
    txt = out.read_text(encoding="utf-8")
    assert "| marknad |" in txt and "residual (utfall)" in txt and "¼ Kelly" in txt
    assert "p17" not in txt                       # inga rader per spelare
    assert len(txt.splitlines()) < 60


def test_report_requires_input():
    with pytest.raises(SystemExit):
        quant_report.main([])


def test_weight_grid_and_settings(tmp_path):
    import gzip
    import random as _r
    rnd = _r.Random(9)
    rader = []
    for i in range(600):
        pk = rnd.uniform(0.3, 0.7)
        rader.append({"match_id": f"m{i // 10}", "avspark": 1e9 + (i // 10) * 86400, "t0": 1e9 + (i // 10) * 86400 - 3600,
                      "pk": pk, "pm": min(0.95, max(0.05, pk + rnd.uniform(-0.15, 0.15))), "dq": 1.0,
                      "y": 1 if rnd.random() < pk else 0})
    g = quant_report.weight_grid(rader)
    assert g["folds"] >= 1 and set(g["chosen"]) <= set(quant_report.W_GRID)
    assert g["logloss"][0.0] <= g["logloss"][0.3]           # marknaden rätt -> hög vikt straffas
    f = tmp_path / "k.json.gz"
    with gzip.open(f, "wt", encoding="utf-8") as fh:
        json.dump({"rader": rader}, fh)
    out = tmp_path / "r.md"
    quant_report.main(["--kalib", str(f), "--out", str(out)])
    assert "Modellvikt" in out.read_text(encoding="utf-8")
    # blandningen i rapporten är samma som i boten
    from propsbot.nba import coherent_blend
    r = rader[0]
    assert abs(quant_report.blend_p(r, 0.075) - coherent_blend(r["pm"], r["pk"], 0.0, 0.075, 1.0)[1]) < 1e-6
    s = json.loads((Path(__file__).resolve().parents[1] / "settings.json").read_text(encoding="utf-8"))
    assert s["nba_model_weight"] == 0.075
