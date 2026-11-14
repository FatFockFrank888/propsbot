import math
import random

from propsbot.nba_minutes import (BASE_BLOWOUT, blowout_minutes, fit_stack, nb_over_minutes, p_blowout,
                                  r_conditional, stack_p)
from propsbot.player_model import nb_over


def test_blowout_symmetric_and_conserves_minutes():
    assert abs(p_blowout(-10) - p_blowout(10)) < 1e-12
    assert p_blowout(-12) > BASE_BLOWOUT
    team = {"a": 36.0, "b": 34.0, "c": 30.0, "d": 18.0, "e": 12.0}
    out = blowout_minutes(team, -13.5)
    assert abs(sum(out.values()) - sum(team.values())) < 1e-9
    assert out["a"] < 36.0 and out["e"] > 12.0
    assert blowout_minutes(team, None) == team


def test_minutes_mixture_reduces_to_nb_without_spread():
    assert abs(nb_over_minutes(0.6, 30.0, 0.0, 17.5, 15) - nb_over(18.0, 17.5, 15)) < 1e-12


def test_minutes_mixture_keeps_average_variance():
    # Volatil speltid ger bredare fördelning: högre P(över) långt över medel än stabil speltid.
    r_v = r_conditional(15, 0.04)
    stable = nb_over_minutes(0.6, 30.0, 1.0, 27.5, r_v)
    volatile = nb_over_minutes(0.6, 30.0, 9.0, 27.5, r_v)
    assert volatile > stable
    assert r_v > 15


def test_stack_without_data_is_market():
    assert abs(stack_p({}, "points", 0.70, 0.52) - 0.52) < 1e-9
    p = fit_stack([])
    assert abs(stack_p(p, "points", 0.70, 0.52) - 0.52) < 1e-9


def test_stack_learns_informative_model_and_shrinks_noise():
    rnd = random.Random(1)

    def bets(informative: bool, n: int):
        out = []
        for i in range(n):
            true = rnd.uniform(0.3, 0.7)
            pk = min(0.95, max(0.05, true + rnd.gauss(0, 0.08)))
            pm = true if informative else rnd.uniform(0.2, 0.8)
            won = rnd.random() < true
            out.append({"status": "vunnen" if won else "förlorad", "p_modell": pm, "p_marknad": pk,
                        "sida": "över", "marknad": "points", "match_id": str(i), "spelare_id": "x", "linje": 1.5,
                        "bokford": i})
        return out
    good = fit_stack(bets(True, 3000))["points"]
    noise = fit_stack(bets(False, 3000))["points"]
    assert good["b_modell"] > 0.5
    assert abs(noise["b_modell"]) < 0.15
