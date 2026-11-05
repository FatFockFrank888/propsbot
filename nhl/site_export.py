"""NHL data for the merged propsbot site, in the same (Swedish) format as football and NBA.

radar_rows(): every current line with at least 2 % edge (written to <data>/radar.json each scan).
ledger_sv(): one NHL ledger bet -> the football/NBA ledger format (spelare, marknad, linje, sida ...).
Units: the site counts stakes and results as a share of the bankroll (1u = unit_pct = 0.2 %).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .engine import Leg

STATUS_SV = {"open": "öppen", "won": "vunnen", "lost": "förlorad", "push": "push", "void": "struken"}


def _ts(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _spel(line: float, side: str) -> str:
    return f"skott på mål {'under' if side == 'under' else 'över'} {line:g}"


def radar_rows(legs: Iterable[Leg], s, live_keys: set[str] | None = None, min_edge: float = 0.02) -> list[dict[str, Any]]:
    out = []
    for leg in legs:
        if leg.edge is None or leg.edge < min_edge:
            continue
        if not (s.odds_min_all <= leg.odds <= s.odds_max_all):
            continue
        g = leg.game
        playable = not leg.blocks
        out.append({
            "spelare": leg.projection.skater.name,
            "match": f"{g.away} – {g.home}",
            "avspark": g.start_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") if g.start_utc else "",
            "spel": _spel(leg.line, leg.side), "marknad": "sog", "sida": leg.side,
            "prognos": round(leg.projection.mu, 2),
            "odds": round(leg.odds, 3), "bolag": leg.book,
            "sannolikhet": leg.p_fair, "ratt_odds": 1 / leg.p_fair if leg.p_fair else None,
            "edge": leg.edge,
            "spela_fran": (1 + s.min_edge_all) / leg.p_fair if leg.p_fair else None,
            "insats_pct": leg.units * s.unit_pct if playable else 0.0,
            "insats_forslag": leg.units * s.unit_pct,
            "spelbar": playable,
            "live": bool(live_keys) and leg.key in live_keys,
            "forv_clv_pp": None, "clv_signal": False,
            "p_modell": leg.p_model,
            "kommentar": "; ".join(leg.blocks + leg.live_blocks + list(leg.tags)
                                   + [f"källor: {', '.join(f.group for f in leg.refs)}"]),
        })
    out.sort(key=lambda x: -x["edge"])
    return out[:800]


def ledger_sv(b: dict[str, Any], unit_pct: float) -> dict[str, Any]:
    away, _, home = (b.get("game") or "").partition("@")
    edge = b.get("edge")
    return {
        "key": f"nhl|{b.get('game_id')}|{b.get('player_id')}|sog|{b.get('line')}|{b.get('side')}",
        "id": b.get("id"), "bokford": _ts(b.get("created")),
        "match_id": f"nhl{b.get('game_id')}", "match": f"{away} – {home}" if home else b.get("game"),
        "hemma": home, "borta": away, "liga": "NHL", "avspark": _ts(b.get("start")),
        "spelare": b.get("player"), "spelare_id": b.get("player_id"),
        "marknad": "sog", "linje": b.get("line"), "sida": b.get("side"),
        "bolag": b.get("book"), "odds": b.get("odds"),
        "sannolikhet": b.get("p_fair") if b.get("p_fair") is not None else b.get("p_model"),
        "ratt_odds": (1 / b["p_fair"]) if b.get("p_fair") else None,
        "edge": edge if edge is not None else b.get("model_edge"),
        "modell_edge": b.get("model_edge"),
        "prognos": b.get("proj_sog"),
        "spela_fran": b.get("play_down_to"),
        "insats_pct": (b.get("units") or 0) * unit_pct,
        "stangning": b.get("close_odds"),
        "status": STATUS_SV.get(b.get("status"), b.get("status")),
        "stopp": "; ".join(b.get("reasons") or []),
        "clv_signal": False, "forv_clv_pp": None,
        "utfall": b.get("result_sog"),
        "resultat_enheter": None if b.get("profit_units") is None else b["profit_units"] * unit_pct,
        "notis": b.get("notified"),
        "nyhet": b.get("nyhet"), "nyhet_status": b.get("nyhet_status"),
    }
