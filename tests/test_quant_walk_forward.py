import random

import pytest

from propsbot.quant.walk_forward import Fold, LeakageError, assert_no_leak, splits

H = 3600.0


def _rows(n_matches=60, seed=3):
    rnd = random.Random(seed)
    rows = []
    for m in range(n_matches):
        ts = 1e9 + m * 20 * H + rnd.choice([0, 0, 2 * H])
        for leg in range(rnd.randint(1, 4)):          # flera ben per match
            rows.append({"ts": ts, "match_id": f"m{m}", "prognos_ts": ts - 5 * H})
    rnd.shuffle(rows)
    return rows


def test_chronological_and_group_disjoint():
    rows = _rows()
    folds = splits(rows, n_folds=4)
    assert folds
    for f in folds:
        tr = [rows[i]["ts"] for i in f.train]
        va = [rows[i]["ts"] for i in f.val]
        te = [rows[i]["ts"] for i in f.test]
        assert max(tr) < min(va) < min(te)
        assert max(va) < min(te)
        g = [{rows[i]["match_id"] for i in part} for part in (f.train, f.val, f.test)]
        assert not (g[0] & g[1]) and not (g[1] & g[2]) and not (g[0] & g[2])
        assert_no_leak(rows, f)


def test_embargo():
    rows = _rows()
    for f in splits(rows, n_folds=3, embargo_s=30 * H):
        va_start = min(rows[i]["ts"] for i in f.val)
        assert all(rows[i]["ts"] < va_start - 30 * H for i in f.train)


def test_expanding_grows_and_rolling_does_not():
    rows = _rows()
    exp = [len(f.train) for f in splits(rows, n_folds=4)]
    assert exp == sorted(exp) and exp[-1] > exp[0]
    roll = splits(rows, n_folds=4, expanding=False)
    assert max(len(f.train) for f in roll) < exp[-1]


def test_order_invariant():
    rows = _rows()
    srt = sorted(range(len(rows)), key=lambda i: rows[i]["ts"])
    rows2 = [rows[i] for i in srt]
    a = [[sorted(rows[i]["match_id"] for i in f.test)] for f in splits(rows)]
    b = [[sorted(rows2[i]["match_id"] for i in f.test)] for f in splits(rows2)]
    assert a == b


def test_leak_detection():
    rows = [{"ts": 1.0, "match_id": "a"}, {"ts": 2.0, "match_id": "b"}, {"ts": 3.0, "match_id": "c"}]
    assert_no_leak(rows, Fold([0], [1], [2]))
    with pytest.raises(LeakageError):
        assert_no_leak(rows, Fold([1], [0], [2]))              # träning efter validering
    bad = rows + [{"ts": 1.5, "match_id": "a"}]
    with pytest.raises(LeakageError):
        assert_no_leak(bad, Fold([0], [1, 3], [2]))          # samma match i två delar
    feat = [dict(r) for r in rows]
    feat[0]["prognos_ts"] = 5.0
    with pytest.raises(LeakageError):
        assert_no_leak(feat, Fold([0], [1], [2]))            # feature från framtiden
    mk = [dict(r) for r in rows]
    mk[1]["p_market_ts"] = 9.0
    with pytest.raises(LeakageError):
        assert_no_leak(mk, Fold([0], [1], [2]), market_ts_key="p_market_ts")


def test_too_few_groups():
    with pytest.raises(ValueError):
        splits([{"ts": 1.0, "match_id": "a"}], n_folds=3)
