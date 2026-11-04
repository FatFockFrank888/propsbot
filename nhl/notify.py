"""Phone notifications via ntfy (free app, no login). Subscribe to the topic in settings.json."""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime

log = logging.getLogger(__name__)

NTFY = "https://ntfy.sh"


def send(topic: str, title: str, message: str, priority: int = 4, tags: str = "ice_hockey") -> bool:
    if not topic:
        return False
    body = json.dumps(
        {"topic": topic, "title": title, "message": message, "priority": priority, "tags": tags.split(",")},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(NTFY, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
    except Exception as exc:  # noqa: BLE001 - a failed notification must never stop scanning
        log.warning("Could not send notification: %s", exc)
        return False
    try:
        from propsbot.notify import log_receipt
        log_receipt(raw, title)
    except ImportError:  # the nhl package run on its own
        pass
    return True


SIDE_SV = {"over": "över", "under": "under"}


def format_live_bet(bet: dict, currency: str) -> tuple[str, str]:
    """Same layout as the football/NBA pushes (Swedish)."""
    title = f"LIVE NHL SPELA: {bet['player']} skott på mål {SIDE_SV.get(bet['side'], bet['side'])} {bet['line']:g}"
    start = ""
    if bet.get("start"):
        start = " (" + datetime.fromisoformat(bet["start"]).strftime("%Y-%m-%d %H:%M") + " UTC)"
    lines = [
        f"{bet['game'].replace('@', ' @ ')}{start}",
        f"{bet['book']}: {bet['odds']:.2f}" + (f"  (spela från {bet['play_down_to']:.2f})" if bet.get("play_down_to") else ""),
        f"Sannolikhet {bet['p_fair']:.1%}, edge {bet['edge']:.1%}, modell {bet['model_edge']:+.1%}"
        if bet.get("p_fair") is not None else f"Edge {bet['edge']:.1%}",
        f"Prognos {bet['proj_sog']:.2f} skott | källor: {', '.join(bet['groups'])}",
        f"Insats: {bet['units']}/10 units ({bet['stake']:.0f} {currency})",
    ]
    others = {b: o for b, o in (bet.get("alt_prices") or {}).items() if b != bet["book"]}
    if others:
        lines.append("Även: " + ", ".join(f"{b} {o:.2f}" for b, o in others.items()))
    if bet.get("tags"):
        lines.append(" | ".join(bet["tags"]))
    return title, chr(10).join(lines)


class PlayerGuard:
    """One push per player per game across every market, line, side, book and run.
    The merged bot points NOTIS_SPELARE at the file football and NBA use too."""

    def __init__(self, path):
        from pathlib import Path
        self.path = Path(path)
        self.d: dict = {}
        if self.path.exists():
            try:
                self.d = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.d = {}

    @classmethod
    def shared(cls) -> "PlayerGuard":
        import os
        from .bot_settings import BotSettings
        return cls(os.environ.get("NOTIS_SPELARE") or BotSettings().data_path / "notis_spelare.json")

    @staticmethod
    def key(sport: str, game_id, player: str) -> str:
        from .names import normalize_name
        return f"{sport}|{game_id}|{normalize_name(player)}"

    def allows(self, sport: str, game_id, player: str, bet: str) -> bool:
        x = self.d.get(self.key(sport, game_id, player))
        return x is None or x.get("spel") == bet

    def mark(self, sport: str, game_id, player: str, bet: str) -> None:
        import time
        self.d[self.key(sport, game_id, player)] = {"spel": bet, "ts": time.time()}

    def save(self) -> None:
        import time
        now = time.time()
        self.d = {k: v for k, v in self.d.items() if now - v.get("ts", now) < 4 * 86400}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.d, ensure_ascii=False), encoding="utf-8")


def format_recap(day: str, live, ledgers: dict, history, s) -> tuple[str, str]:
    from .validate import bet_validation

    yday = [b for b in live.bets if b["us_date"] == day and b["status"] in ("won", "lost", "push", "void")]
    w = sum(b["status"] == "won" for b in yday)
    l = sum(b["status"] == "lost" for b in yday)
    p = sum(b["status"] == "push" for b in yday)
    pnl = sum(b["profit_units"] or 0 for b in yday)
    v = bet_validation(live.bets)
    clv = v["clv"]
    lines = [f"{day}: {w}-{l}-{p}, {pnl:+.1f}u" if yday else f"{day}: inga LIVE-spel avgjorda"]
    if v["settled"]:
        roi = v["roi_weighted"]
        lines.append(f"Totalt: {v['settled']} avgjorda, {v['profit_units']:+.1f}u, ROI {roi:+.1%}")
    if clv["n"]:
        t = f", t={clv['t']:.1f}" if clv["t"] is not None else ""
        lines.append(f"Snitt-CLV {clv['mean']:+.1%} över {clv['n']} spel{t}")
    counts = history.leg_counts()
    graded = counts.get("won", 0) + counts.get("lost", 0)
    lines.append(f"Rättade linjer: {graded} | granskning vid {v['settled']}/150 LIVE-spel")
    return "NHL – dagens sammanfattning", "\n".join(lines)
