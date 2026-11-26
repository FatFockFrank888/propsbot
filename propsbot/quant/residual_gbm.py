"""Fas 9 (docs/PLAN.md): LightGBM-residual med marknadens logit som init_score. Valfri (importeras bara här).

Kraftigt regulariserad: få löv, stort min_data_in_leaf, låg inlärningstakt, tidigt stopp på valideringen.
Utan träd (0 rundor) blir resultatet exakt marknaden. lightgbm är INTE ett krav för boten.
"""
from __future__ import annotations

import numpy as np

from .devig import base_logit

PARAMS = {"objective": "binary", "num_leaves": 7, "min_data_in_leaf": 100, "learning_rate": 0.02,
          "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 10.0,
          "verbose": -1, "seed": 7, "deterministic": True, "num_threads": 1}


def _off(p_market):
    return np.array([base_logit(p) for p in p_market])


def fit(X, y, p_market, X_val=None, y_val=None, p_val=None, rounds: int = 400, params: dict | None = None,
        early_stop: int = 50):
    import lightgbm as lgb
    X = np.asarray(X, float)
    tr = lgb.Dataset(X, label=np.asarray(y, float), init_score=_off(p_market), free_raw_data=False)
    valid, cb = [], []
    if X_val is not None:
        valid = [lgb.Dataset(np.asarray(X_val, float), label=np.asarray(y_val, float), init_score=_off(p_val),
                             reference=tr)]
        cb = [lgb.early_stopping(early_stop, verbose=False)]
    return lgb.train({**PARAMS, **(params or {})}, tr, num_boost_round=rounds, valid_sets=valid or None, callbacks=cb)


def predict(model, X, p_market):
    if model is None or getattr(model, "num_trees", lambda: 0)() == 0:
        return 1 / (1 + np.exp(-_off(p_market)))
    raw = model.predict(np.asarray(X, float), raw_score=True, num_iteration=model.best_iteration or None)
    return 1 / (1 + np.exp(-(_off(p_market) + raw)))
