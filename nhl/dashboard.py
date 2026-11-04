"""Self-contained HTML performance dashboard (output/dashboard.html).

Rebuilt after every scan; the page reloads itself every few minutes. No server and
no external scripts: data is embedded as JSON and charts are drawn as inline SVG.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bot_settings import BotSettings
from .history import LineHistory
from .ledger import Ledger, open_ledgers
from .state import BotState
from .validate import bet_validation, edge_buckets, leg_validation

REVIEW_AT = 150
ASSET = Path(__file__).with_name("dashboard_template.html")


def _cum_series(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settled = sorted(
        (b for b in bets if b["status"] in ("won", "lost", "push")),
        key=lambda b: (b.get("settled_at") or "", b.get("start") or ""),
    )
    out, total = [], 0.0
    for i, b in enumerate(settled, start=1):
        total += b["profit_units"] or 0.0
        out.append({
            "i": i, "date": b["us_date"], "cum": round(total, 3), "profit": b["profit_units"],
            "label": f"{b['player']} {b['side']} {b['line']:g} @ {b['odds']:.2f}", "status": b["status"],
        })
    return out


def _clv_series(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted((b for b in bets if b.get("clv") is not None), key=lambda b: b["created"])
    out, xs = [], []
    for i, b in enumerate(rows, start=1):
        xs.append(b["clv"])
        n = len(xs)
        m = sum(xs) / n
        se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else None
        out.append({"i": i, "mean": m, "lo": m - 1.96 * se if se else None, "hi": m + 1.96 * se if se else None,
                    "label": f"{b['player']} {b['side']} {b['line']:g}", "clv": b["clv"]})
    return out


def _status(v: dict[str, Any], min_bets: int = 30) -> dict[str, str]:
    clv = v["clv"]
    if clv["n"] < min_bets or clv["t"] is None:
        return {"level": "warning", "label": "Collecting data",
                "text": f"{clv['n']} of {min_bets} bets with a closing price needed for a CLV verdict."}
    if clv["t"] >= 2:
        return {"level": "good", "label": "Beating the close",
                "text": f"Average CLV {clv['mean']:+.1%} (t = {clv['t']:.1f}). The edges are real."}
    if clv["t"] <= -2:
        return {"level": "critical", "label": "Losing to the close",
                "text": f"Average CLV {clv['mean']:+.1%} (t = {clv['t']:.1f}). Pause live bets and retune."}
    need = f" About {clv['needed']} bets needed at this rate." if clv.get("needed") else ""
    return {"level": "warning", "label": "Not conclusive yet",
            "text": f"Average CLV {clv['mean']:+.1%} (t = {clv['t']:.1f}).{need}"}


def _bet_row(b: dict[str, Any]) -> dict[str, Any]:
    keys = ("us_date", "start", "game", "player", "side", "line", "book", "odds", "units", "stake", "edge",
            "model_edge", "clv", "status", "result_sog", "profit_units", "play_down_to")
    return {k: b.get(k) for k in keys}


def build_data(s: BotSettings, ledgers: dict[str, Ledger], history: LineHistory, state: BotState) -> dict[str, Any]:
    live = ledgers["live"]
    vals = {name: bet_validation(l.bets) for name, l in ledgers.items()}
    legs = leg_validation(history.settled_legs(), s.min_edge_all)
    open_live = sorted(live.open_bets(), key=lambda b: b.get("start") or "")
    settled_live = sorted((b for b in live.bets if b["status"] != "open"),
                          key=lambda b: b.get("settled_at") or "", reverse=True)[:40]
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": s.currency,
        "bankroll": s.bankroll,
        "unit_value": s.unit_value(),
        "review_at": REVIEW_AT,
        "last_scan": state.get("last_scan"),
        "status": _status(vals["live"]),
        "ledgers": {
            name: {**ledgers[name].stats(), "clv": v["clv"], "roi_ci": v["roi"], "kambi_clv": v["kambi_clv"]}
            for name, v in vals.items()
        },
        "cum": {"live": _cum_series(live.bets), "bokforing": _cum_series(ledgers["bokforing"].bets)},
        "clv_series": _clv_series(live.bets),
        "buckets": {"live": edge_buckets(live.bets), "bokforing": edge_buckets(ledgers["bokforing"].bets)},
        "legs": {"counts": history.leg_counts(), **legs},
        "open_live": [_bet_row(b) for b in open_live],
        "recent_live": [_bet_row(b) for b in settled_live],
    }


def render(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    return ASSET.read_text(encoding="utf-8").replace("__DATA__", payload)


def write_dashboard(s: BotSettings, out: Path, ledgers: dict[str, Ledger] | None = None,
                    history: LineHistory | None = None) -> Path:
    own_history = history is None
    history = history or LineHistory(s.data_path / "line_history.sqlite")
    try:
        data = build_data(s, ledgers or open_ledgers(s), history, BotState(s.data_path / "state.json"))
    finally:
        if own_history:
            history.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(render(data), encoding="utf-8")
    tmp.replace(out)
    return out
