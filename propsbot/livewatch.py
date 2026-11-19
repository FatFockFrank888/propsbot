"""Livebevakning (18/11): notiser under match för spelen du tagit (mina_spel.json).

Körs som eget arbetsflöde (live.yml) som startas när ett av dina spel börjar inom 25 min. Läser ESPN:s
matchsammanfattning var POLL_S sekund och skickar en notis för varje händelse som rör dina spel,
fram till att spelet är avgjort (vunnet/förlorat) eller matchen är slut:

  NBA-props   varje ökning av spelets marknad ("+1 retur → 3 av 3,5, 1 kvar"), kombos på alla delar
  NBA sides   ställningen efter varje period + slut (en notis per korg blir för många)
  Fotboll     mål (med målskytt och ställning), straff, rött kort, bortdömt mål (VAR) i matcher du har spel i;
              props: varje ökning för spelaren (skott på mål, skott, mål, assist); hörnspel: varje hörna
  Alla        "✅ VUNNET" / "❌ FÖRLORAT" när det avgörs, slutresultat vid slutsignal

Inga dubbletter och ingen historik: första gången en match läses sparas läget utan notis (startas
bevakningen om mitt i en match plingar den bara om nya händelser). Notiserna kommer bara när källan har
registrerat händelsen – ESPN ligger oftast 15–60 s efter TV-bilden. Nya klick (Jag tog spelet) läses
varje minut, så ett spel som tas under matchen bevakas direkt.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import mina

POLL_S = 20
PRIO_QUIET = 2                   # tyst (Telegram: ingen pling) – varje enskild ökning
MAX_S = 5 * 3600 + 40 * 60      # GitHub-jobbet får köra högst 6 h
PRIO_BIG, PRIO_SMALL = 5, 4      # fulla notiser hela natten (användarens val 18/11)


def _fmt(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _period(gs: dict) -> str:
    return gs.get("detail") or ""


def _score(gs: dict) -> str:
    return f"{gs['abbr_home'] or 'Hemma'} {gs['home']}–{gs['away']} {gs['abbr_away'] or 'Borta'}"


def _who(b: dict) -> str:
    return b["spelare"] if b.get("spelare_id") not in ("match", "hörnor") else (b.get("spel_text") or b["match"])


def _bet_txt(b: dict) -> str:
    return b.get("spel_text") or f"{mina.MK_SV.get(b['marknad'], b['marknad'])} {'under' if b.get('sida') == 'under' else 'över'} {_fmt(b['linje'])}"


def _side(b: dict) -> str:
    return "UNDER" if b.get("sida") == "under" else "ÖVER"


def bet_head(b: dict) -> str:
    """Spelet tydligt: "Carter Jr. · UNDER 7,5 returer @ 2,15"."""
    if b.get("spelare_id") in ("match", "hörnor"):
        return f"{b.get('spel_text') or b.get('match')} @ {b['odds']:.2f}"
    unit = mina.MK_SV.get(b.get("marknad"), b.get("marknad"))
    return f"{b['spelare']} · {_side(b)} {_fmt(b.get('linje') or 0)} {unit} @ {b['odds']:.2f}"


def state(b: dict, v: float | None) -> tuple[str, str, int | None]:
    """(emoji, text, marginal) för ett props/total-spel. Över: hur många till som behövs. Under: hur många till som tål."""
    import math
    if v is None or b.get("marknad") in ("1x2", "ml", "ah", "spread", "cah"):
        return ("", "", None)
    line = b.get("linje") or 0
    if b.get("sida") == "under":
        room = math.floor(line) - int(v)          # under 7,5 och 2 -> tål 5 till
        if room < 0:
            return ("❌", "förlorat", room)
        return ("🟠" if room <= 1 else "🟢", "⚠️ en till = förlust" if room == 0 else f"tål {room} till", room)
    need = math.floor(line) + 1 - int(v)          # över 3,5 och 2 -> behöver 2 till
    if need <= 0:
        return ("✅", "klart", need)
    return ("🟢" if need <= 1 else "🟡", f"behöver {need} till", need)


SOCCER_EVENTS = {"goal": ("⚽ MÅL", PRIO_BIG), "penalty": ("🎯 STRAFF", PRIO_BIG), "red": ("🟥 RÖTT KORT", PRIO_BIG)}


def soccer_event_kind(ev: dict) -> str | None:
    t = ((ev.get("type") or {}).get("text") or "").lower()
    if "own goal" in t or t.startswith("goal") or ev.get("scoringPlay"):
        return "goal"
    if "penalty" in t:
        return "penalty"
    if "red card" in t or "second yellow" in t:
        return "red"
    return None


class Watcher:
    def __init__(self, settings: dict, send=None, get=None, log=print):
        from .notify import send as _send
        self.s = settings
        # egen kanal för plingarna under match (18/11), så att de kan ha ett eget ljud i ntfy-appen
        self.topic = settings.get("live_ntfy_topic") or settings.get("ntfy_topic")
        self.send = send or (lambda t, m, prio, tags: _send(self.topic, t, m, priority=prio, tags=tags))
        self.get = get or mina._get
        self.log = log
        self.games: dict = {}      # (sökväg, id) -> {"events": set, "period": str, "done": bool}
        self.vals: dict = {}       # ident -> senaste räknare
        self.closed: set = set()   # ident som är avgjorda/klara (inga fler notiser)

    def notify(self, title: str, msg: str, prio: int = PRIO_SMALL, tags: str = "") -> None:
        self.log(f"NOTIS: {title} | {msg}")
        self.send(title, msg, prio, tags)

    def step(self, bets: list[dict], now: float) -> int:
        """En omgång: läs varje aktiv match en gång och skicka det som är nytt. Returnerar antal aktiva spel."""
        by_game: dict = {}
        for b in bets:
            if b["ident"] in self.closed or b.get("status") != "öppen" or not b.get("avspark"):
                continue
            if not (b["avspark"] - 15 * 60 <= now <= b["avspark"] + 5 * 3600):
                continue
            if not b.get("espn"):
                ev = mina.find_event(b, self.get)
                if not ev:
                    continue
                b["espn"] = list(ev)
            by_game.setdefault(tuple(b["espn"]), []).append(b)
        for (path, eid), bs in by_game.items():
            summ = self.get(f"{mina.ESPN}/{path}/summary", {"event": eid})
            if not summ:
                continue
            self._game(path, eid, summ, bs)
        return sum(len(v) for v in by_game.values())

    def _game(self, path: str, eid: str, summ: dict, bets: list[dict]) -> None:
        gs = mina.game_state(summ)
        g = self.games.get((path, eid))
        first = g is None
        if first:
            g = self.games[(path, eid)] = {"events": set(), "period": _period(gs), "done": gs["done"], "state": gs["state"]}
        nba = path.startswith("basketball")
        # matchhändelser (fotboll): mål, straff, rött kort; mål som försvinner = bortdömt
        if not nba:
            cur = {}
            for ev in summ.get("keyEvents", []) or []:
                k = soccer_event_kind(ev)
                if k and ev.get("id"):
                    cur[str(ev["id"])] = (k, ev)
            if not first and (gs["state"] == "in" or (gs["done"] and not g["done"])):
                for i, (k, ev) in cur.items():
                    if i in g["events"]:
                        continue
                    lab, prio = SOCCER_EVENTS[k]
                    who = ", ".join((p.get("athlete") or {}).get("displayName", "") for p in ev.get("participants", []) or [])
                    team = (ev.get("team") or {}).get("displayName", "")
                    clock = (ev.get("clock") or {}).get("displayValue", "")
                    self.notify(f"{lab} {clock} – {bets[0]['match']}",
                                f"{team}{': ' + who if who else ''}\nStällning {_score(gs)}\nDitt spel: " + "; ".join(_bet_txt(b) for b in bets),
                                prio, "soccer")
                gone = [i for i in g["events"] if i not in cur and g.get("kinds", {}).get(i) == "goal"]
                for i in gone:
                    self.notify(f"↩️ MÅL BORTDÖMT – {bets[0]['match']}", f"Målet finns inte längre hos källan (VAR?)\nStällning {_score(gs)}",
                                PRIO_BIG, "soccer")
            g["events"] = set(cur)
            g["kinds"] = {i: k for i, (k, _ev) in cur.items()}
        # spelen: räknaren och avgörandet. Nivåer (18/11): varje ökning TYST, "nära" och avgjort MED LJUD,
        # plus en sammanfattning per match efter varje period.
        for b in bets:
            if b["ident"] in self.closed:
                continue
            v = mina.stat_now(b, summ)
            old = self.vals.get(b["ident"])
            self.vals[b["ident"]] = v
            props = b.get("spelare_id") not in ("match", "hörnor")
            per_event = props or b.get("marknad") in ("corners", "corners_home", "corners_away", "cah")
            if first or v is None:
                if first and v is not None and gs["state"] == "in":
                    self.notify(f"👀 Bevakar: {bet_head(b)}", f"Just nu {_fmt(v)} · {_score(gs)} · {_period(gs)}", PRIO_QUIET, "eyes")
                continue
            emo, txt, marg = state(b, v)
            if per_event and old is not None and v > old:
                icon = "🏀" if nba else "🚩" if b.get("marknad", "").startswith("corner") or b.get("marknad") == "cah" else "⚽"
                self.notify(f"{icon} {bet_head(b)}", f"{_fmt(v)} (+{_fmt(v - old)}) · {txt} · {_score(gs)} · {_period(gs)}",
                            PRIO_QUIET, "basketball" if nba else "soccer")
            dec = mina.decided(b, v)
            if dec:
                self.closed.add(b["ident"])
                self.notify(("✅ VUNNET: " if dec == "vunnen" else "❌ FÖRLORAT: ") + bet_head(b),
                            f"{_fmt(v)} mot linjen {_fmt(b.get('linje') or 0)} · {b['units']:g}u · {_score(gs)} · {_period(gs)}",
                            PRIO_BIG, "white_check_mark" if dec == "vunnen" else "x")
                continue
            near = marg is not None and ((b.get("sida") == "under" and marg == 0) or (b.get("sida") != "under" and marg == 1))
            if near and not b.get("_nara") and gs["state"] == "in":
                b["_nara"] = True
                self.notify(("⚠️ NÄRA FÖRLUST: " if b.get("sida") == "under" else "⚠️ NÄRA VINST: ") + bet_head(b),
                            f"{_fmt(v)} · {txt} · {_score(gs)} · {_period(gs)}", PRIO_BIG, "warning")
        # sammanfattning per match efter varje period (NBA: kvart/halvtid, fotboll: halvtid)
        per = _period(gs)
        if (not first and gs["state"] == "in" and per != g["period"]
                and any(w in per.lower() for w in ("end", "half"))):
            rows = []
            for b in bets:
                v = self.vals.get(b["ident"])
                emo, txt, _m = state(b, v)
                if b["ident"] in self.closed and not emo:
                    continue
                rows.append(f"{emo or '•'} {bet_head(b)} – {_fmt(v) if v is not None else '–'}" + (f" ({txt})" if txt else ""))
            if rows:
                self.notify(f"{'🏀' if nba else '⚽'} {per}: {bets[0]['match']}", f"{_score(gs)}\n" + "\n".join(rows), PRIO_SMALL,
                            "basketball" if nba else "soccer")
        if not first and gs["done"] and not g["done"]:
            for b in bets:
                if b["ident"] in self.closed:
                    continue
                self.closed.add(b["ident"])
                v = self.vals.get(b["ident"])
                self.notify(f"🏁 Slut: {bet_head(b)}",
                            f"Slutresultat {_score(gs)}" + (f" · räknare {_fmt(v)} mot {_fmt(b.get('linje') or 0)}" if v is not None else "")
                            + "\nRättas av boten inom några minuter.", PRIO_BIG, "checkered_flag")
        elif first and gs["done"]:
            for b in bets:
                self.closed.add(b["ident"])
        g["period"], g["done"], g["state"] = _period(gs), gs["done"], gs["state"]


def main(root: Path, settings: dict, log=print) -> None:
    """Loopen i live.yml: kör tills inget av dina spel startar inom 30 min eller pågår, högst MAX_S."""
    t0 = time.time()
    book = mina.Book(root / "mina_spel.json")
    try:
        tiers = {b["ident"]: b for b in json.loads((root / "tiers.json").read_text(encoding="utf-8")).get("bets", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        tiers = {}
    w = Watcher(settings, log=log)
    import os
    from .notify import TG_ROUTE
    log(f"Livebevakning: {len(book.bets)} spel, kanal {'satt' if w.topic else 'SAKNAS'}, Telegram "
        + ("på" if os.environ.get("TELEGRAM_TOKEN") and w.topic in TG_ROUTE else "AV (TELEGRAM_TOKEN eller telegram_chats saknas)"))
    last_poll = 0.0
    idle_since = None
    while time.time() - t0 < MAX_S:
        now = time.time()
        if now - last_poll > 60 and mina.topic_of(settings):   # nya klick under matchen
            mina.apply_messages(book, mina.poll(mina.topic_of(settings), "6h"), tiers, now)
            last_poll = now
        bets = list(book.bets.values())
        active = w.step(bets, now)
        upcoming = [b for b in bets if b.get("status") == "öppen" and b["ident"] not in w.closed and b.get("avspark")
                    and now < b["avspark"] + 5 * 3600 and b["avspark"] - now < 30 * 60]
        if not active and not upcoming:
            idle_since = idle_since or now
            if now - idle_since > 120:
                log("Livebevakning: inga aktiva spel – klar")
                return
        else:
            idle_since = None
        time.sleep(POLL_S)
    log("Livebevakning: tidsgränsen nådd – nästa körning tar över")
