"""Mobilnotiser via ntfy (gratis app för Android/iPhone, ingen inloggning).

Installera appen "ntfy", tryck + och prenumerera på kanalnamnet i settings.json
(ntfy_topic). Varje nytt spelbart ben skickas en gång med hög prioritet (plingar).
"""
from __future__ import annotations

import json
import secrets
import urllib.request
from pathlib import Path

NTFY = "https://ntfy.sh"


def new_topic() -> str:
    return "propsbot-" + secrets.token_hex(6)


def send(topic: str, title: str, message: str, priority: int = 4, tags: str = "soccer") -> bool:
    if not topic:
        return False
    # ntfy tar emot JSON på rot-URL:en; då fungerar å, ä, ö även i rubriken.
    body = json.dumps({"topic": topic, "title": title, "message": message,
                       "priority": priority, "tags": tags.split(",")}).encode("utf-8")
    req = urllib.request.Request(NTFY, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
    except Exception as e:  # notiser får aldrig stoppa skanningen
        print(f"  (kunde inte skicka notis: {e})")
        return False
    log_receipt(raw, title)
    return True


def log_receipt(raw: bytes, title: str) -> None:
    """Skriver ntfy:s kvitto (meddelande-id + servertid) i loggen, så att en notis som inte
    syns på telefonen kan spåras: samma id står i appens meddelandedetaljer."""
    try:
        from datetime import datetime, timezone
        m = json.loads(raw.decode("utf-8"))
        t = datetime.fromtimestamp(m["time"], timezone.utc).strftime("%H:%M:%S")
        print(f"  ntfy-kvitto: id {m.get('id')} kl {t} UTC – {title}", flush=True)
    except Exception:
        print(f"  ntfy-kvitto: (oläsligt svar) – {title}", flush=True)


class SeenStore:
    """Håller koll på vilka ben som redan notifierats (match, spelare, marknad, linje, bolag).
    Ny notis skickas om samma ben dyker upp med klart bättre odds."""

    def __init__(self, path: Path):
        self.path = path
        self.seen: dict[str, float] = {}
        if path.exists():
            try:
                self.seen = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.seen = {}

    def is_new(self, key: str, odds: float, min_improvement: float = 0.05) -> bool:
        prev = self.seen.get(key)
        return prev is None or odds >= prev * (1 + min_improvement)

    def mark(self, key: str, odds: float) -> None:
        self.seen[key] = odds

    def save(self) -> None:
        self.path.write_text(json.dumps(self.seen), encoding="utf-8")


class PlayerGuard:
    """Ett enda spel (en notis) per spelare och match – över alla marknader, linjer, sidor,
    bolag, körningar och sporter. Delas av fotboll och NBA (samma fil)."""

    def __init__(self, path: Path):
        self.path = path
        self.d: dict[str, dict] = {}
        if path.exists():
            try:
                self.d = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.d = {}

    @staticmethod
    def key(sport: str, match_id, player: str) -> str:
        from .sources.props_text import name_key
        return f"{sport.lower()}|{match_id}|{name_key(player)}"

    def allows(self, sport: str, match_id, player: str, bet: str) -> bool:
        """True om spelaren är fri i matchen, eller om det är exakt samma spel som redan skickats."""
        x = self.d.get(self.key(sport, match_id, player))
        return x is None or x.get("spel") == bet

    def already_sent(self, sport: str, match_id, player: str) -> bool:
        return self.key(sport, match_id, player) in self.d

    def mark(self, sport: str, match_id, player: str, bet: str) -> None:
        import time
        self.d[self.key(sport, match_id, player)] = {"spel": bet, "ts": time.time()}

    def save(self) -> None:
        import time
        now = time.time()
        self.d = {k: v for k, v in self.d.items() if now - v.get("ts", now) < 4 * 86400}
        self.path.write_text(json.dumps(self.d, ensure_ascii=False), encoding="utf-8")
