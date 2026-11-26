import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import backtest_per90 as bt  # noqa: E402


def _match(i, shots_p1=1, date=None):
    ps = lambda tid: [{"id": f"{tid}p{k}", "n": f"{tid}p{k}", "s": k < 11, "min": 90.0 if k < 11 else 0.0,
                       "pos": "F" if k == 1 else "CD-L", "shots": (shots_p1 if k == 1 else 1), "sot": 0, "fouls": 1}
                      for k in range(14)]
    return {"lg": "eng.1", "id": f"m{i}", "date": date or f"2026-09-{i + 1:02d}T15:00Z", "teams": {"A": ps("A"), "B": ps("B")}}


def test_no_future_leakage(tmp_path):
    ms = [_match(i) for i in range(12)]
    base = {(r["mid"], r["stat"], r["line"], r["grp"]): (r["p0"], r["p1"]) for r in bt.predictions(ms, "2026-09-05")}
    ms2 = [dict(m) for m in ms]
    ms2[-1] = _match(11, shots_p1=25)                     # extremt utfall i SISTA matchen
    new = {(r["mid"], r["stat"], r["line"], r["grp"]): (r["p0"], r["p1"]) for r in bt.predictions(ms2, "2026-09-05")}
    for k, v in base.items():                             # alla prognoser (även för sista matchen) oförändrade
        assert new[k] == v


def test_only_outfield_starters_and_report(tmp_path):
    ms = [_match(i) for i in range(12)]
    rows = bt.predictions(ms, "2026-09-05")
    assert rows and all(r["grp"] != "GK" for r in rows)
    assert {r["stat"] for r in rows} == {"shots", "sot", "fouls"}
    for m in ms:
        (tmp_path / f"{m['id']}.json").write_text(json.dumps(m), encoding="utf-8")
    assert len(bt.load(str(tmp_path))) == 12
    txt = bt.report(rows, "2026-09-09", 12)
    assert "| Marknad |" in txt
