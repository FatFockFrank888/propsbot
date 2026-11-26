import numpy as np

from propsbot.player_model import nb_over, poisson_over
from propsbot.quant.dispersion import fit_nb_r


def test_recovers_nb_shape():
    rnd = np.random.default_rng(11)
    mu = rnd.uniform(1.5, 6.0, 5000)
    r = 8.0
    y = rnd.poisson(rnd.gamma(r, mu / r))
    assert abs(fit_nb_r(mu, y) - r) / r < 0.15


def test_poisson_gives_large_r():
    rnd = np.random.default_rng(12)
    mu = rnd.uniform(1.0, 5.0, 5000)
    assert fit_nb_r(mu, rnd.poisson(mu)) >= 50


def test_small_n_stays_near_prior_and_empty():
    rnd = np.random.default_rng(13)
    mu = rnd.uniform(1, 4, 10)
    y = rnd.poisson(mu * 3)
    assert abs(fit_nb_r(mu, y, prior_r=10, prior_n=1e6) - 10) < 0.1
    assert fit_nb_r([], [], prior_r=7) == 7


def test_nb_tends_to_poisson():
    for mu, line in ((1.2, 0.5), (3.0, 2.5), (5.0, 4.5)):
        assert abs(nb_over(mu, line, 1e6) - poisson_over(mu, line)) < 1e-3
