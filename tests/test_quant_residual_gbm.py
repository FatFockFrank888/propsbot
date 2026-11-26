import numpy as np
import pytest

lgb = pytest.importorskip("lightgbm")

from propsbot.quant import evaluate, residual_gbm  # noqa: E402


def _data(n, seed, signal=0.0):
    r = np.random.default_rng(seed)
    p = r.uniform(0.25, 0.75, n)
    X = r.normal(size=(n, 4))
    z = np.log(p / (1 - p)) + signal * X[:, 0]
    y = (r.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(float)
    return X, y, p


def test_zero_trees_is_market():
    X, y, p = _data(500, 1)
    assert np.allclose(residual_gbm.predict(None, X, p), p)


def test_noise_does_not_hurt_and_deterministic():
    X, y, p = _data(8000, 2)
    tr, va, te = slice(0, 5000), slice(5000, 6500), slice(6500, None)
    m = residual_gbm.fit(X[tr], y[tr], p[tr], X[va], y[va], p[va])
    ll = evaluate.logloss(residual_gbm.predict(m, X[te], p[te]), y[te])
    assert ll <= evaluate.logloss(p[te], y[te]) + 0.002
    m2 = residual_gbm.fit(X[tr], y[tr], p[tr], X[va], y[va], p[va])
    assert np.allclose(residual_gbm.predict(m, X[te], p[te]), residual_gbm.predict(m2, X[te], p[te]))


def test_signal_learned():
    X, y, p = _data(8000, 3, signal=0.6)
    m = residual_gbm.fit(X[:5000], y[:5000], p[:5000], X[5000:6500], y[5000:6500], p[5000:6500])
    assert evaluate.logloss(residual_gbm.predict(m, X[6500:], p[6500:]), y[6500:]) < evaluate.logloss(p[6500:], y[6500:]) - 0.01
