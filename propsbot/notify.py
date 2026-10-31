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
        with urllib.request.urlopen(req, timeout=15):
            return True
    except Exception as e:  # notiser får aldrig stoppa skanningen
        print(f"  (kunde inte skicka notis: {e})")
        return False


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
