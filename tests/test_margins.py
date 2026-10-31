import math

from propsbot.config import Config
from propsbot.line_adjust import kambi_fair, measure_margins
from propsbot.models import OddsQuote


def test_goal_margin_recovered_from_pinnacle_total():
    # 22 spelare vars sanna takter summerar till 2,8*0,97 mål; Kambi lägger power-marginal k=1,35
    rates = [0.45, 0.35, 0.3, 0.25, 0.2, 0.18, 0.15, 0.12, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05,
             0.05, 0.04, 0.04, 0.03, 0.03, 0.02, 0.02, 0.02]
    scale = 2.8 * 0.97 / sum(rates)
    rates = [r * scale for r in rates]
    k_true = 1.35
    qs = []
    for i, r in enumerate(rates):
        p = 1 - math.exp(-r)
        odds = (1 / p) ** (1 / k_true)
        qs.append(OddsQuote("unibet", "m", f"p{i}", "goal", 0.5, "over", odds, 0, provider="kambi",
                            variant="to score"))
    mm = measure_margins(qs, 2.8, Config())
    assert abs(mm.power[("unibet", "goal")] - k_true) < 0.01
    p0, measured = kambi_fair([qs[0]], "goal", Config(), mm)
    assert measured and abs(p0 - (1 - math.exp(-rates[0]))) < 1e-3
