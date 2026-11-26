import numpy as np
import pytest

from propsbot.quant import calibration, evaluate, residual


def _market(n, seed):
    rnd = np.random.default_rng(seed)
    p = rnd.uniform(0.25, 0.75, n)
    return rnd, p


def test_market_only_and_no_features_reproduce_market():
    _, p = _market(200, 1)
    X = np.zeros((200, 0))
    m = residual.market_only()
    assert np.allclose(residual.predict(m, X, p), p, atol=1e-9)
    # utan features och med oändlig ridge -> exakt marknaden
    y = (np.random.default_rng(2).uniform(size=200) < p).astype(float)
    m2 = residual.fit(X, y, p, l2=1e12)
    assert np.allclose(residual.predict(m2, X, p), p, atol=1e-6)


def test_noise_features_do_not_hurt():
    rnd, p = _market(20000, 3)
    y = (rnd.uniform(size=len(p)) < p).astype(float)       # marknaden är rätt
    X = rnd.normal(size=(len(p), 5))
    X[rnd.uniform(size=X.shape) < 0.2] = np.nan
    tr, te = slice(0, 15000), slice(15000, None)
    m = residual.fit(X[tr], y[tr], p[tr], l2=50)
    se = 1 / np.sqrt((p[tr] * (1 - p[tr])).sum())          # interceptets standardfel
    assert abs(residual.delta_logit(m, X[te]).mean()) < 3 * se
    ll_m = evaluate.logloss(residual.predict(m, X[te], p[te]), y[te])
    assert ll_m <= evaluate.logloss(p[te], y[te]) + 0.002


def test_signal_is_learned_out_of_sample():
    rnd, p = _market(6000, 4)
    x = rnd.normal(size=len(p))
    true = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + 0.5 * x)))
    y = (rnd.uniform(size=len(p)) < true).astype(float)
    X = np.column_stack([x, rnd.normal(size=len(p))])
    m = residual.fit(X[:4000], y[:4000], p[:4000], l2=10)
    assert evaluate.logloss(residual.predict(m, X[4000:], p[4000:]), y[4000:]) < evaluate.logloss(p[4000:], y[4000:]) - 0.01


def test_close_target():
    rnd, p = _market(3000, 5)
    x = rnd.normal(size=len(p))
    p_close = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + 0.3 * x)))
    m = residual.fit(x[:, None], None, p, l2=1, target="close", p_close=p_close)
    assert abs(m["beta"][1] - 0.3) < 0.03        # standardiserad x ~ N(0,1)
    with pytest.raises(ValueError):
        residual.fit(x[:, None], None, p, target="close")


def test_platt_recovers_params():
    rnd = np.random.default_rng(6)
    p = rnd.uniform(0.05, 0.95, 20000)
    z = 0.2 + 0.8 * np.log(p / (1 - p))
    y = (rnd.uniform(size=len(p)) < 1 / (1 + np.exp(-z))).astype(float)
    a, b = calibration.platt_fit(p, y)
    assert abs(a - 0.2) < 0.05 and abs(b - 0.8) < 0.05
    # stark prior håller kvar identiteten
    a2, b2 = calibration.platt_fit(p[:50], y[:50], prior_n=1e9)
    assert abs(a2) < 1e-3 and abs(b2 - 1) < 1e-3


def test_isotonic_monotone_and_gated():
    rnd = np.random.default_rng(7)
    p = rnd.uniform(size=3000)
    y = (rnd.uniform(size=3000) < p).astype(float)
    mod = calibration.isotonic_fit(p, y)
    q = calibration.isotonic_apply(mod, np.linspace(0, 1, 101))
    assert np.all(np.diff(q) >= -1e-12)
    with pytest.raises(calibration.NotEnoughData):
        calibration.isotonic_fit(p[:100], y[:100])
