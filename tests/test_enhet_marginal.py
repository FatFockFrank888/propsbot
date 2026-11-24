"""24/11: enhetsskala och Pinnacle-marginal ska vara enhetliga."""
from propsbot import market, scan, skarp_clv, workbook
from propsbot.tiers import KRAV_KEYS, LIVE_KEYS
import json
from pathlib import Path


def test_unit_is_tier_unit():
    assert workbook.UNIT == 0.01          # 1u = 1 % av kassan, som A/B/C
    assert 0.01 / workbook.UNIT == 1.0    # gammal ¼-Kelly på 1 % = 1u, inte 5u


def test_one_sided_pinnacle_single_constant():
    assert scan.PIN_ONE_SIDED is market.PIN_ONE_SIDED is skarp_clv.PIN_ONE_SIDED == 1.04
    assert abs(1 / (2.0 * market.PIN_ONE_SIDED) - 0.4808) < 1e-3


def test_fallbacks_match_settings():
    s = json.loads((Path(__file__).parent.parent / "settings.json").read_text(encoding="utf-8"))
    assert KRAV_KEYS["min_edge_all"] == s["min_edge_all"]
    assert LIVE_KEYS["live_min_edge"] == s["live_min_edge"]
    assert LIVE_KEYS["live_max_edge"] == s["live_max_edge"]
    assert LIVE_KEYS["live_odds_window"] == s["live_odds_window"]
