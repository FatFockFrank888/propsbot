"""Kambi-nivån mot utfall (benlogg.fit_kambi_level / kambi_level): spärrar, riktning och avstängning."""
import math
import random

from propsbot import benlogg

S = {"kambi_level_min_n": 150, "kambi_level_min_matches": 40, "kambi_level_prior_n": 300}


def _rows(n_matches, per_match, bias, seed=1):
    rnd = random.Random(seed)
    R = []
    for m in range(n_matches):
        for k in range(per_match):
            p_true = rnd.uniform(0.15, 0.6)
            p_adj = min(0.95, p_true + bias)
            R.append({"key": f"m{m}|p{k}|shots_on_target|0.5", "avspark": 1e9 + m * 86400, "marknad": "shots_on_target",
                      "linje": 0.5, "y": 1 if rnd.random() < p_true else 0, "p_adj": p_adj})
    return R


def test_biased_market_is_corrected():
    fits, log = benlogg.fit_kambi_level(_rows(120, 6, 0.10), S)
    f = fits["shots_on_target|0.5"]
    assert f["matcher"] == 120 and f["logloss_kal_holdout"] < f["logloss_ra_holdout"]
    benlogg.CAL_KAMBI.clear()
    benlogg.CAL_KAMBI.update(fits)
    try:
        assert benlogg.kambi_level(0.40, "shots_on_target", 0.5, {}) < 0.37          # för hög nivå dras ned
        assert benlogg.kambi_level(0.40, "shots_on_target", 0.5, {"kambi_level_cal": False}) == 0.40
        assert benlogg.kambi_level(0.40, "shots", 0.5, {}) == 0.40                    # ingen anpassning för marknaden
    finally:
        benlogg.CAL_KAMBI.clear()


def test_gates_wait_for_enough_matches():
    fits, log = benlogg.fit_kambi_level(_rows(15, 18, 0.08), S)           # som 26/11: 262 ben, 15 matcher
    assert fits == {} and "väntar på 150 ben och 40 matcher" in log[0]
    fits, _ = benlogg.fit_kambi_level(_rows(60, 2, 0.08), S)              # många matcher men för få ben
    assert fits == {}


def test_unbiased_market_stays_near_identity():
    fits, _ = benlogg.fit_kambi_level(_rows(120, 6, 0.0, seed=5), S)
    f = fits.get("shots_on_target|0.5")
    if f:                                                                 # sparas bara om den slår rå; då nära identitet
        for p in (0.2, 0.4, 0.6):
            q = 1 / (1 + math.exp(-(f["a"] + f["b"] * math.log(p / (1 - p)))))
            assert abs(q - p) < 0.03


def test_no_fit_is_identity():
    benlogg.CAL_KAMBI.clear()
    assert benlogg.kambi_level(0.33, "shots_on_target", 1.5, {}) == 0.33
