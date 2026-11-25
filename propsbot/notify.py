"""Mobilnotiser via ntfy (gratis app för Android/iPhone, ingen inloggning).

Installera appen "ntfy", tryck + och prenumerera på kanalnamnet i settings.json
(ntfy_topic). Varje nytt spelbart ben skickas en gång med hög prioritet (plingar).
"""
from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

NTFY = "https://ntfy.sh"
TG = "https://api.telegram.org"
# Telegram (18/11): ntfy:s iPhone-app gav inga pushnotiser. configure() kopplar varje ntfy-kanal till en
# Telegram-chatt: {ntfy-kanal: chat_id}. Token i miljövariabeln TELEGRAM_TOKEN (GitHub-hemlighet).
TG_ROUTE: dict = {}
TG_ONLY = False


def oddsvakt_topic(settings: dict) -> str | None:
    """Kanal för Odds Alert (oddsvakt.py): oddsvakt_ntfy_topic, annars en egen kanal <nivåkanal>-oddsvakt när
    telegram_chats.oddsvakt finns (egen Telegram-chatt "Odds Alert"), annars nivåkanalen (samma chatt som A/B-notiserna)."""
    if settings.get("oddsvakt_ntfy_topic"):
        return settings["oddsvakt_ntfy_topic"]
    base = settings.get("tier_ntfy_topic") or settings.get("ntfy_topic")
    if base and (settings.get("telegram_chats") or {}).get("oddsvakt"):
        return f"{base}-oddsvakt"
    return base


def configure(settings: dict) -> None:
    """Läser telegram_chats = {"main": id, "tier": id, "live": id, "oddsvakt": id} och kopplar rollerna till
    ntfy-kanalerna. Saknas oddsvakt går Odds Alert till nivåchatten (tier)."""
    global TG_ONLY
    chats = settings.get("telegram_chats") or {}
    TG_ROUTE.clear()
    for role, key in (("main", "ntfy_topic"), ("tier", "tier_ntfy_topic"), ("live", "live_ntfy_topic")):
        t = settings.get(key) or settings.get("ntfy_topic")
        cid = chats.get(role) or chats.get("main")
        if t and cid and t not in TG_ROUTE:
            TG_ROUTE[t] = cid
    t = oddsvakt_topic(settings)
    cid = chats.get("oddsvakt") or chats.get("tier") or chats.get("main")
    if t and cid and t not in TG_ROUTE:
        TG_ROUTE[t] = cid
    TG_ONLY = bool(settings.get("telegram_only", False))


def send_telegram(chat_id, title: str, message: str, priority: int = 4, click: str | None = None,
                  link: tuple | None = None) -> bool:
    import html
    import os
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token or not chat_id:
        if chat_id and not token and not getattr(send_telegram, "_warned", False):
            print("  VARNING: Telegram-chatt kopplad men TELEGRAM_TOKEN saknas (GitHub-hemlighet) – skickar bara till ntfy", flush=True)
            send_telegram._warned = True
        return False
    body = {"chat_id": chat_id, "text": f"<b>{html.escape(title)}</b>\n{html.escape(message)}", "parse_mode": "HTML",
            "disable_web_page_preview": True, "disable_notification": priority <= 2}
    btns = ([{"text": "Öppna", "url": click}] if click else []) + ([{"text": link[0], "url": link[1]}] if link else [])
    if btns:
        body["reply_markup"] = {"inline_keyboard": [btns]}
    req = urllib.request.Request(f"{TG}/bot{token}/sendMessage", data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    ok = False
    for attempt in range(3):                       # 24/11: upp till 3 försök, respekterar Telegrams 429 retry_after
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                ok = json.loads(r.read().decode("utf-8")).get("ok", False)
            break
        except urllib.error.HTTPError as e:
            wait = 2 ** attempt
            if e.code == 429:
                try:
                    wait = min(30, int(json.loads(e.read().decode("utf-8")).get("parameters", {}).get("retry_after", wait)))
                except Exception:
                    pass
            elif e.code < 500:
                print(f"  (Telegram avvisade: HTTP {e.code})")
                return False
            if attempt < 2:
                time.sleep(wait)
        except Exception as e:  # notiser får aldrig stoppa skanningen
            print(f"  (kunde inte skicka Telegram: {type(e).__name__})")
            if attempt < 2:
                time.sleep(2 ** attempt)
    if not ok:
        return False
    print(f"  telegram: {'ok' if ok else 'FEL'} – {title}", flush=True)
    return ok


def new_topic() -> str:
    return "propsbot-" + secrets.token_hex(6)


def send(topic: str, title: str, message: str, priority: int = 4, tags: str = "soccer", click: str | None = None,
         link: tuple | None = None) -> bool:
    if not topic:
        return False
    if link and link[1] not in message:   # länken i texten: pushförhandsvisningen visar inga knappar
        message = f"{message}\n{link[0]}: {link[1]}"
    tg = TG_ROUTE.get(topic)
    tg_ok = (send_telegram(tg, title, message, priority, click, **({"link": link} if link else {})) if tg else False)
    if TG_ONLY and tg:
        return tg_ok
    # ntfy tar emot JSON på rot-URL:en; då fungerar å, ä, ö även i rubriken.
    body = json.dumps({"topic": topic, "title": title, "message": message,
                       "priority": priority, "tags": tags.split(","), **({"click": click} if click else {}),
                       **({"actions": [{"action": "view", "label": link[0], "url": link[1]}]} if link else {})}).encode("utf-8")
    req = urllib.request.Request(NTFY, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
    except Exception as e:  # notiser får aldrig stoppa skanningen
        print(f"  (kunde inte skicka notis: {e})")
        return tg_ok                  # gick den fram på Telegram räknas den som skickad (ingen dubblett)
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
