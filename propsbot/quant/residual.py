"""Fas 4a: marknadsankrad residual – logistisk regression med offset = marknadens logit (specens init_score, linjär).

p = σ(base_logit + β·z), z = standardiserade features + saknad-flaggor. Ridge mot β = 0 ("lita på marknaden").
target="outcome": y ∈ {0, 1}. target="close": mjukt mål p_close (skarp stängning) – mer information per rad.
"""
from __future__ import annotations

import math

import numpy as np

from .calibration import logistic_offset_fit
from .devig import base_logit


def _prep(X, model=None):
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    miss = np.isnan(X)
    if model is None:
        mean = np.where(miss.all(0), 0.0, np.nanmean(np.where(miss.all(0)[None, :], 0.0, X), 0))
        Xi = np.where(miss, mean[None, :], X)
        sd = Xi.std(0)
        sd[sd < 1e-9] = 1.0
        flags = [j for j in range(X.shape[1]) if 0 < miss[:, j].sum() < len(X)]
        model = {"mean": mean, "sd": sd, "flags": flags, "flag_mean": miss[:, flags].mean(0) if flags else None}
    Xi = np.where(miss, model["mean"][None, :], X)
    Z = (Xi - model["mean"]) / model["sd"]
    if model["flags"]:
        Z = np.column_stack([Z, miss[:, model["flags"]].astype(float) - model["flag_mean"]])   # centrerade flaggor
    return Z, model


def fit(X, y, p_market, l2: float = 50.0, target: str = "outcome", p_close=None) -> dict:
    off = np.array([base_logit(p) for p in p_market])
    Z, prep = _prep(X)
    if target == "close":
        if p_close is None:
            raise ValueError("target='close' kräver p_close")
        yy = np.clip(np.asarray(p_close, float), 1e-4, 1 - 1e-4)
    else:
        yy = np.asarray(y, float)
    Z1 = np.column_stack([np.ones(len(Z)), Z])
    beta = logistic_offset_fit(Z1, yy, offset=off, l2=l2)
    return {"beta": beta, "prep": prep, "l2": l2, "target": target}


def delta_logit(model: dict, X):
    Z, _ = _prep(X, model["prep"])
    Z1 = np.column_stack([np.ones(len(Z)), Z])
    return Z1 @ model["beta"]


def predict(model: dict, X, p_market):
    off = np.array([base_logit(p) for p in p_market])
    return 1 / (1 + np.exp(-(off + delta_logit(model, X))))


def market_only() -> dict:
    """Noll-modell: ger exakt marknadens p."""
    return {"beta": np.zeros(1), "prep": {"mean": np.zeros(0), "sd": np.ones(0), "flags": [], "flag_mean": None}, "l2": math.inf,
            "target": "none"}
