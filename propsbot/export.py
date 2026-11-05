"""Skriver webbsidans data (radar + bokföring) till en mapp som publiceras på GitHub Pages."""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import DecisionConfig
from .decision import kelly_stake
from .ledger import Ledger
from .line_adjust import rate_for_prob
from .pipeline import MARKET_LABEL
from .scan import ScanRow

WEB = Path(__file__).resolve().parent.parent / "web"


def _spel(market: str, line: float, side: str = "over") -> str:
    if side == "under":
        return f"{MARKET_LABEL.get(market, market).lower()} under {line:g}"
    if market == "goal" and line == 0.5:
        return "gör mål"
    if market == "assist" and line == 0.5:
        return "assist"
    return f"{MARKET_LABEL.get(market, market).lower()} över {line:g}"


def radar_rows(rows: list[ScanRow], settings: dict, limit: int = 800, live_keys: set | None = None) -> list[dict]:
    from .ledger import bet_key
    out = []
    for r in rows:
        d = r.row.decision
        c = d.cand
        if not d.show:  # utanför oddsramen
            continue
        if c.edge < settings.get("min_edge_display", 0.02):   # bara spel med minst 2 % edge
            continue
        out.append({
            "spelare": c.player_name, "match": r.match, "avspark": r.kickoff,
            "spel": _spel(c.market, c.line, c.best.side), "marknad": c.market, "sida": c.best.side,
            "prognos": round(r.expected, 1) if r.expected is not None else (
                round(rate_for_prob(min(max(c.p, 1e-4), 0.999), c.line), 2)
                if c.market in ("shots", "shots_on_target", "goal", "assist") else None),
            "odds": c.best.odds, "bolag": c.best.book, "sannolikhet": c.p,
            "ratt_odds": 1.0 / c.p, "edge": c.edge, "spela_fran": d.play_from,
            "insats_pct": d.stake if d.playable else 0.0,
            # Förslag efter EV för alla rader: ¼ Kelly, högst 2 %, 0 vid negativt EV.
            "insats_forslag": kelly_stake(c.p, c.best.odds, DecisionConfig().kelly_fraction,
                                          DecisionConfig().max_stake_per_bet),
            "spelbar": d.playable,
            "live": bool(live_keys) and bet_key(r) in live_keys,
            "forv_clv_pp": getattr(r, "clv_pp", None),
            "clv_signal": any("CLV-signal" in x for x in d.reasons),
            "p_modell": None if r.row.p_model != r.row.p_model else r.row.p_model,
            "kommentar": "; ".join(d.reasons),
        })
    out.sort(key=lambda x: -x["edge"])
    return out[:limit]


def write_site(site: Path, rows: list[ScanRow], ledger: Ledger, settings: dict,
               test_ledger: Ledger | None = None, parlays: dict | None = None,
               shadow_ledger: Ledger | None = None, sport: str = "Fotboll",
               live_ledger: Ledger | None = None, live_keys: set | None = None) -> None:
    site.mkdir(parents=True, exist_ok=True)
    data = {
        "sport": sport,
        "live_enabled": settings.get("live_enabled", True),
        "uppdaterad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "uppdaterad_ts": time.time(),
        "regler": {"min_odds": 1.40, "max_odds": 6.0, "kelly": 0.25, "unit": 0.002},
        "radar": radar_rows(rows, settings, live_keys=live_keys),
        # Med live: fliken Bokföring = de riktiga (live) spelen; övriga spel är data (spel_data).
        # Fotboll LIVE (football_live): regelspelen är de spelade spelen (notis) och visas som Live.
        "live": live_ledger is not None or (sport == "Fotboll" and bool(settings.get("football_live"))),
        "bokforing": sorted((live_ledger or ledger).counted, key=lambda b: -b["bokford"]),
        "sammanfattning": (live_ledger or ledger).summary(),
        "spel_data": sorted(ledger.counted, key=lambda b: -b["bokford"]) if live_ledger is not None else [],
        "modelltest": sorted(test_ledger.counted, key=lambda b: -b["bokford"]) if test_ledger else [],
        "modelltest_sammanfattning": test_ledger.summary() if test_ledger else None,
        "skuggspel": sorted(shadow_ledger.counted, key=lambda b: -b["bokford"]) if shadow_ledger else [],
        "skuggspel_sammanfattning": shadow_ledger.summary() if shadow_ledger else None,
        **(parlays or {}),
    }
    fl = site.parent / "bokforing_fouls_test.json" if sport == "Fotboll" else None
    if fl and fl.exists():
        from .ledger import Ledger as _L
        f_ledger = _L(fl)
        data["fouls_test"] = sorted(f_ledger.counted, key=lambda b: -b["bokford"])
        data["fouls_sammanfattning"] = f_ledger.summary()
    kl = site.parent / "bokforing_kort_test.json" if sport == "Fotboll" else None
    if kl and kl.exists():
        from .ledger import Ledger as _L
        k_ledger = _L(kl)
        data["kort_test"] = sorted(k_ledger.counted, key=lambda b: -b["bokford"])
        data["kort_sammanfattning"] = k_ledger.summary()
    (site / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if (WEB / "index.html").exists():
        shutil.copy(WEB / "index.html", site / "index.html")
