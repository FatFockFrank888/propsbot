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
