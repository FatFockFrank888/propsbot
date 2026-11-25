"""Odds Alert (oddsvakt, 23/11): snabb bevakning av oddset för A/B-spelen som fått notis.

Problemet: när notisen kommer och bolaget öppnas har oddset ofta redan fallit. Data (A/B-notiser):
17 % ligger under lägsta godtagbara odds redan vid nästa skanning (10 min), 41 % inom 60 min, 75 % före
start. 21 % av dem som faller kommer tillbaka till lägsta oddset senare (typiskt efter ~1,7 h) och
fönstret är öppet i median ~40 min (ofta bara några minuter). Skanningen var tionde minut är för långsam,
så oddsvakten läser Kambi var oddsvakt_poll_s sekund (30 s) och skickar en notis när läget ändras:

  ✅ BACK UP   oddset är tillbaka på/över lägsta oddset ("ODDS ALERT ✅ …", hög prioritet)
  ❌ GONE      oddset har fallit under lägsta oddset eller spelet är borta hos bolaget ("ODDS ALERT ❌ …")

Körs som eget arbetsflöde (oddsvakt.yml) som bevaka.yml startar när det finns något att bevaka
(filen oddsvakt_start.txt, skrivs av write_start_flag() i skanningen). Kör högst ~5 h 40 min, sedan tar
nästa start över; avslutas efter oddsvakt_tomgang_s utan något att bevaka.

Vad som bevakas
  * Nivåspel i tiers.json: tier A/B, notis skickad, status öppen, avspark i framtiden. Spel du redan
    tagit (mina_spel.json eller ett "tog"-klick) bevakas inte alls.
  * Egna bevakningar från webbsidan (ntfy-kanalen <ntfy_topic>-mina, samma som "Jag tog spelet"):
      {"v": 1, "typ": "bevaka", "ident", "sport", "kalla_fil", "kalla_key", "bolag", "min_odds", "ts"}
      {"v": 1, "typ": "sluta_bevaka", "ident", "ts"}
    Spelet slås upp i tiers.json (ident) eller i källbokföringen (kalla_fil + kalla_key). Lägsta oddset
    är ditt min_odds. Senaste meddelandet per ident vinner (ts). Bevakas till avspark eller sluta_bevaka,
    även om spelet är taget (du har bett om det uttryckligen).

Lägsta odds (nivåspel): max(spela_fran, min_odds(p_nu, krav_edge)).
  krav_edge från spelet (tiers.py), annars tier_b_min_edge. p_nu = den rättvisa sannolikhet som
  skanningen räknar om var tionde minut fram till start (inte "sannolikhet", som låses vid bokningen):
    props   skarp_stang_p (referensen boten räknar edge mot: Pinnacle/DK/konsensus), om nyare än bokningen –
            används som FÖRÄNDRING sedan bevakningen började (p_eff = sannolikhet + p_nu − p0), se required_odds
    sides   Pinnacles pris utan marginal (pin_stang_p), snittet med Smarkets (smk_stang_p) när båda finns –
            samma facit som sides.py
  Försiktigt: max() med spela_fran gör att lägsta oddset aldrig sänks under notisens nivå när
  marknaden rört sig åt vårt håll, men höjs när den skarpa sannolikheten fallit (då krävs mer).

Läge per spel: over / under / borta (marknaden borta eller stängd hos bolaget). Notis bara vid byte,
när oddsvakt_bekrafta (2) läsningar i rad visar det nya läget, högst en notis per spel och
oddsvakt_cooldown_s (600 s) – ett byte under spärren skickas när den gått ut (om läget står kvar).
Startläge = läget vid notisen ("over"), så första fallet ger GONE. Egna bevakningar har inget
startläge: första bekräftade läget sparas utan notis. Hämtfel räknas inte som läsning.

Filer i datagrenen (bara oddsvaktens egna, skrivs aldrig av skanningen):
  oddsvakt_lage.json     läge per spel (så att en omstart inte plingar igen), egna bevakningar, lästa meddelanden
  oddsvakt_logg.jsonl    prislogg: en rad per spel vid första läsningen, varje prisändring och var 10:e min
                         oförändrat ({"t", "i": ident, "b": bolag, "o": odds|null, "m": lägsta, "s": läge}).
                         Oförändrat pris mellan raderna = samma pris vid varje läsning. Rensas efter 7 dagar.
  site/oddsvakt.json     för webbsidan:
      {"uppdaterad_ts", "poll_s",
       "bevakningar": {ident: {"ident", "typ": "tier"|"egen", "sport", "match", "spelare", "spel_text",
                               "bolag", "avspark", "odds_nu": float|null, "spela_fran": float|null,
                               "min_odds": float|null, "status": "over"|"under"|"borta"|null,
                               "ts": senaste läsning, "notis_ts": senaste notis|null}}}
      status null = inte läst än (eller spelet hittades inte). Webbsidan ser filen när nästa skanning
      publicerar sidan (≤ ~10 min).
Skanningens fil oddsvakt_start.txt (antal att bevaka) skrivs bara av skanningen.
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

try:
    from .tiers import min_odds
except ImportError:          # tiers.min_odds (agent A) saknas än – samma formel
    def min_odds(p: float, krav_edge: float) -> float:
        return math.ceil((1 + krav_edge) / p * 100 - 1e-9) / 100

DEFAULTS = {
    "oddsvakt_on": True,
    "oddsvakt_poll_s": 30,
    "oddsvakt_cooldown_s": 600,
    "oddsvakt_bekrafta": 2,
    "oddsvakt_omlas_s": 600,          # läs om läget (tiers.json m.m.) och spara till datagrenen
    "oddsvakt_mina_s": 60,            # läs nya klick/bevakningar från ntfy
    "oddsvakt_max_s": 5 * 3600 + 40 * 60,
    "oddsvakt_tomgang_s": 900,        # avsluta efter så lång tid utan något att bevaka
    "oddsvakt_logg_dagar": 7,
}
STATE_FILE = "oddsvakt_lage.json"
LOG_FILE = "oddsvakt_logg.jsonl"
SITE_FILE = "site/oddsvakt.json"
FLAG_FILE = "oddsvakt_start.txt"
OWN_FILES = (STATE_FILE, LOG_FILE, SITE_FILE)
HEARTBEAT_S = 600
PRIO_UP, PRIO_GONE = 5, 3
SIDE_IDS = ("match", "hörnor")
NBA_SIDE_MK = ("ml", "spread", "game_total")
SITE_URL = "https://fatfockfrank888.github.io/propsbot/"


def cfg(settings: dict) -> dict:
    return {k: settings.get(k, v) for k, v in DEFAULTS.items()}


def event_id(match_id) -> int | None:
    """Kambis event-id ur bokföringens match_id: "k123" (fotboll), "nba123" (NBA)."""
    m = re.fullmatch(r"(?:k|nba)(\d+)", str(match_id or ""))
    return int(m.group(1)) if m else None


def p_now(b: dict) -> float | None:
    """Senaste rättvisa sannolikhet för spelets sida (se modulens beskrivning)."""
    if b.get("spelare_id") in SIDE_IDS:
        pin, smk = b.get("pin_stang_p"), b.get("smk_stang_p")
        ps = [x for x in (pin, smk) if isinstance(x, (int, float)) and 0 < x < 1]
        return sum(ps) / len(ps) if ps else None
    p, ts = b.get("skarp_stang_p"), b.get("skarp_stang_ts")
    if isinstance(p, (int, float)) and 0 < p < 1 and (ts is None or ts >= (b.get("bokford") or 0)):
        return p
    return None


def required_odds(b: dict, settings: dict, p0: float | None = None) -> float | None:
    """Lägsta odds för ett nivåspel: max(spela_fran, min_odds(p_eff, krav_edge)).

    sides: p_eff = p_nu (Pinnacle/Smarkets utan marginal – samma skala som spelets sannolikhet).
    props: spelets sannolikhet är modellens/blandningens, inte den skarpa referensens, så nivåerna kan inte
      blandas (då skulle många spel se ut att vara under gränsen direkt vid notisen). I stället flyttas
      sannolikheten lika mycket som den skarpa referensen rört sig sedan bevakningen började:
      p_eff = sannolikhet + (p_nu − p0), där p0 = första skarpa sannolikheten vakten såg. Utan p0: bara spela_fran."""
    krav = b.get("krav_edge")
    if krav is None:
        krav = settings.get("tier_b_min_edge", 0.05)
    cand = [x for x in (b.get("spela_fran"),) if isinstance(x, (int, float)) and x > 1]
    p = p_now(b)
    if p and b.get("spelare_id") not in SIDE_IDS:
        s = b.get("sannolikhet")
        p = (s + (p - p0)) if (p0 and isinstance(s, (int, float)) and 0 < s < 1) else None
        if p is not None and not 0 < p < 1:
            p = None
    if p:
        cand.append(min_odds(p, krav))
    return max(cand) if cand else None


# ------------------------------------------------------------------ Kambi: hitta spelets odds
def _same_line(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def _player_ok(b: dict, participant: str) -> bool:
    from .sources.props_text import name_key, same_person
    return name_key(participant) == b.get("spelare_id") or same_person(participant, b.get("spelare") or "")


def find_odds(b: dict, raw: dict | None) -> float | None:
    """Bolagets odds för spelet (spelare, marknad, linje, sida) i Kambis betoffer-svar; None = borta."""
    if not raw:
        return None
    mk, line, side = b.get("marknad"), b.get("linje"), b.get("sida")
    if b.get("spelare_id") in SIDE_IDS:
        if b.get("sport") == "nba" or mk in NBA_SIDE_MK:
            from .nba_sides import kambi_main
        else:
            from .sides import kambi_main
        km = kambi_main(raw, b.get("hemma") or "", b.get("borta") or "")
        got = [o for (m, ln, sd), o in km.items() if m == mk and sd == side and _same_line(ln, line)]
        return max(got) if got else None
    best = None
    if b.get("sport") == "nba":
        from .nba import nba_market
        for bo in raw.get("betOffers", []) or []:
            if nba_market((bo.get("criterion") or {}).get("englishLabel") or "") != mk:
                continue
            for o in bo.get("outcomes", []) or []:
                if o.get("status", "OPEN") != "OPEN" or not o.get("odds") or o.get("line") is None:
                    continue
                t, lab = (o.get("type") or "").upper(), (o.get("englishLabel") or o.get("label") or "").lower()
                sd = "over" if (t == "OT_OVER" or lab == "over") else "under" if (t == "OT_UNDER" or lab == "under") else None
                if sd != side or not _same_line(o["line"] / 1000.0, line) or not _player_ok(b, o.get("participant") or ""):
                    continue
                best = max(best or 0.0, o["odds"] / 1000.0)
        return best
    from .sources.kambi_public import parse_betoffers
    quotes, names = parse_betoffers(raw, b.get("bolag") or "", b.get("match_id") or "")
    for q in quotes:
        if q.market == mk and q.side == side and _same_line(q.line, line) and (
                q.player_id == b.get("spelare_id") or _player_ok(b, names.get(q.player_id, q.player_id))):
            best = max(best or 0.0, q.odds)
    return best


def kambi_fetcher(root: Path, settings: dict):
    """fetch(offering, event_id) -> betoffer-svar (None = 404/borttaget). Ingen cache (ttl 0). Fel = undantag."""
    from .sources.http import JsonClient
    from .sources.kambi_public import KambiPublic
    k = KambiPublic(JsonClient(root / ".cache_odds", ttl_s=0, min_interval_s=0.25), market=settings.get("kambi_market", "SE"))

    def fetch(offering: str, eid: int):
        return k._get(offering, f"betoffer/event/{eid}.json", {"includeParticipants": "true"})
    return fetch


# ------------------------------------------------------------------ texter
def _who(b: dict) -> str:
    return b.get("spelare") or b.get("match") or "?"


def _bet_txt(b: dict) -> str:
    if b.get("spel_text"):
        return b["spel_text"]
    from .mina import MK_SV
    ln = b.get("linje")
    return f"{MK_SV.get(b.get('marknad'), b.get('marknad'))} {'under' if b.get('sida') == 'under' else 'över'} {ln:g}" if ln is not None \
        else str(b.get("marknad") or "")


def _ko(b: dict) -> str:
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(b["avspark"], timezone.utc).strftime("%Y-%m-%d %H:%M") + " UTC"
    except (KeyError, TypeError, ValueError, OSError):
        return ""


def alert_text(kind: str, w: dict, odds: float | None) -> tuple[str, str]:
    b, mn = w["b"], w["min"]
    head = f"{_who(b)} {_bet_txt(b)}"
    match = f"{b.get('match') or ''} ({_ko(b)})"
    egen = " · din bevakning" if w["typ"] == "egen" else ""
    if kind == "up":
        return f"ODDS ALERT ✅ {head}", f"{w['bolag']} {odds:.2f} ≥ spela från {mn:.2f} – ta det nu\n{match}{egen}"
    if odds is None:
        return f"ODDS ALERT ❌ {head}", f"{w['bolag']}: spelet är borta (stängt/borttaget) – spela inte\n{match}{egen}"
    return f"ODDS ALERT ❌ {head}", f"{w['bolag']} {odds:.2f} < {mn:.2f} – spela inte\n{match}{egen}"


# ------------------------------------------------------------------ bevakningen
class Vakt:
    def __init__(self, root: Path, settings: dict, send=None, fetch=None, log=print):
        self.root, self.s, self.c, self.log = Path(root), settings, cfg(settings), log
        self._send = send
        self._fetch = fetch
        self.offering = {book: code for code, book in (settings.get("kambi_offerings") or {}).items()}
        try:
            d = json.loads((self.root / STATE_FILE).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            d = {}
        self.st: dict = d.get("vakter", {})           # ident -> läge
        self.egna: dict = d.get("egna", {})           # ident -> bevakningsmeddelandet
        self.msg_ts: dict = d.get("meddelande_ts", {})  # ident -> senaste ts för bevaka/sluta_bevaka
        self.bas_p: dict = d.get("bas_p", {})        # ident -> skarp sannolikhet vid bevakningens start (props)
        self.seen: list = d.get("sedda", [])
        self._seen = set(self.seen)
        self.tagna_msg: dict = d.get("tagna", {})     # ident -> True/False från "tog"/"angra" (efter mina_spel.json)
        self.last_log: dict = {}
        self.cur: dict = {}                           # ident -> bevakning (senaste step)
        self.warned: set = set()
        self.reload()

    # ---------- underlag
    def reload(self) -> None:
        def _j(name, default):
            try:
                return json.loads((self.root / name).read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                return default
        self.tiers = {b["ident"]: b for b in (_j("tiers.json", {}) or {}).get("bets", []) if b.get("ident")}
        self.mina = set(((_j("mina_spel.json", {}) or {}).get("spel") or {}).keys())
        self._src: dict = {}

    def _source(self, f: str, k: str) -> dict | None:
        if not f or not k or "/" in f or ".." in f:
            return None
        if f not in self._src:
            try:
                self._src[f] = {x.get("key"): x for x in json.loads((self.root / f).read_text(encoding="utf-8"))
                                if isinstance(x, dict)}
            except (FileNotFoundError, json.JSONDecodeError, TypeError):
                self._src[f] = {}
        return self._src[f].get(k)

    def taken(self, ident: str) -> bool:
        if ident in self.tagna_msg:
            return self.tagna_msg[ident]
        return ident in self.mina

    def read_messages(self, msgs: list[dict], now: float) -> int:
        """Klick från webbsidan: bevaka / sluta_bevaka (egna bevakningar), tog / angra (sluta bevaka nivåspelet)."""
        n = 0
        for m in sorted(msgs or [], key=lambda x: x.get("time", 0)):
            mid = m.get("id")
            if mid in self._seen:
                continue
            self._seen.add(mid)
            self.seen.append(mid)
            try:
                x = json.loads(m.get("message") or "{}")
            except json.JSONDecodeError:
                continue
            if not isinstance(x, dict) or x.get("v") != 1 or not x.get("ident"):
                continue
            ident, typ = str(x["ident"]), x.get("typ")
            ts = x.get("ts") or m.get("time") or now
            if typ in ("tog", "angra"):
                self.tagna_msg[ident] = typ == "tog"
                n += 1
                continue
            if typ not in ("bevaka", "sluta_bevaka"):
                continue
            if ts < self.msg_ts.get(ident, 0):
                continue                               # äldre än det vi redan har
            self.msg_ts[ident] = ts
            if typ == "sluta_bevaka":
                if self.egna.pop(ident, None) is not None:
                    self.st.pop(ident, None)
                    n += 1
                continue
            try:
                mo = float(x["min_odds"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (1.01 <= mo <= 100):
                continue
            self.egna[ident] = {k: x.get(k) for k in ("ident", "sport", "kalla_fil", "kalla_key", "bolag")} | {
                "min_odds": round(mo, 2), "ts": ts}
            old = self.st.get(ident)
            if old is not None and (old.get("typ") != "egen" or old.get("min") != round(mo, 2)):
                self.st.pop(ident, None)               # ny/ändrad bevakning: nytt startläge
            n += 1
        self.seen = self.seen[-2000:]
        self._seen = set(self.seen)
        return n

    def targets(self, now: float) -> dict:
        """ident -> {"typ", "b": spelet, "bolag", "min", "spela_fran"} för allt som ska bevakas nu."""
        out: dict = {}
        for ident, b in self.tiers.items():
            if (b.get("tier") in ("A", "B") and b.get("notis") and b.get("status", "öppen") == "öppen"
                    and (b.get("avspark") or 0) > now and not self.taken(ident)):
                pn = p_now(b)
                if pn and ident not in self.bas_p:
                    self.bas_p[ident] = pn                # skarp sannolikhet när bevakningen började (props)
                mn = required_odds(b, self.s, p0=self.bas_p.get(ident))
                if mn:
                    out[ident] = {"typ": "tier", "b": b, "bolag": b.get("bolag"), "min": mn, "spela_fran": b.get("spela_fran")}
        for ident, e in list(self.egna.items()):
            b = self.tiers.get(ident) or self._source(e.get("kalla_fil"), e.get("kalla_key"))
            if b is None:
                continue
            b = dict(b, ident=ident, sport=b.get("sport") or e.get("sport"))
            if (b.get("avspark") or 0) <= now:
                self.egna.pop(ident, None)               # matchen har startat: bevakningen är klar
                continue
            if b.get("status", "öppen") != "öppen":
                continue
            out[ident] = {"typ": "egen", "b": b, "bolag": e.get("bolag") or b.get("bolag"), "min": e["min_odds"],
                          "spela_fran": b.get("spela_fran")}
        return out

    # ---------- en omgång
    def step(self, now: float) -> int:
        tg = self.targets(now)
        self.cur = tg
        groups: dict = {}
        for ident, w in tg.items():
            eid, code = event_id(w["b"].get("match_id")), self.offering.get(w["bolag"])
            if eid is None or code is None:
                if ident not in self.warned:
                    self.warned.add(ident)
                    self.log(f"Oddsvakt: kan inte bevaka {ident} (match {w['b'].get('match_id')}, bolag {w['bolag']})")
                continue
            groups.setdefault((code, eid), []).append(ident)
        fetch = self._fetch or kambi_fetcher(self.root, self.s)
        self._fetch = fetch
        for (code, eid), idents in groups.items():
            try:
                raw, ok = fetch(code, eid), True
            except Exception as e:  # noqa: BLE001 – hämtfel = ingen läsning
                raw, ok = None, False
                self.log(f"Oddsvakt: Kambi {code} {eid} fel {type(e).__name__}: {e}")
            for ident in idents:
                w = tg[ident]
                if not ok:
                    continue
                try:
                    odds = find_odds(dict(w["b"], bolag=w["bolag"]), raw)
                except Exception as e:  # noqa: BLE001
                    self.log(f"Oddsvakt: tolkningsfel {ident} {type(e).__name__}: {e}")
                    continue
                self.observe(ident, w, odds, now)
        for ident in [i for i, x in self.st.items() if (x.get("avspark") or 0) < now - 86400]:
            self.st.pop(ident, None)
        return len(tg)

    def observe(self, ident: str, w: dict, odds: float | None, now: float) -> str | None:
        """Ny läsning för ett spel. Returnerar "up"/"gone" om en notis skickades."""
        obs = "borta" if odds is None else "over" if odds >= w["min"] - 1e-9 else "under"
        x = self.st.get(ident)
        if x is None or x.get("typ") != w["typ"]:
            x = self.st[ident] = {"typ": w["typ"], "state": "over" if w["typ"] == "tier" else None,
                                  "pend": None, "pend_n": 0, "last_alert": None}
        x.update(odds=odds, obs=obs, min=w["min"], ts=now, avspark=w["b"].get("avspark"), bolag=w["bolag"])
        self._log_price(ident, w, odds, obs, now)
        if obs == x["state"]:
            x["pend"], x["pend_n"] = None, 0
            return None
        if obs == x["pend"]:
            x["pend_n"] += 1
        else:
            x["pend"], x["pend_n"] = obs, 1
        if x["pend_n"] < max(1, int(self.c["oddsvakt_bekrafta"])):
            return None
        old = x["state"]
        kind = None
        if old is not None:
            if obs == "over" and old in ("under", "borta"):
                kind = "up"
            elif obs in ("under", "borta") and old == "over":
                kind = "gone"
        if kind and x.get("last_alert") and now - x["last_alert"] < self.c["oddsvakt_cooldown_s"]:
            return None                                 # spärren: bytet väntar (skickas om läget står kvar)
        x["state"], x["pend"], x["pend_n"] = obs, None, 0
        if kind:
            x["last_alert"] = now
            self.alert(kind, w, odds)
        return kind

    def alert(self, kind: str, w: dict, odds: float | None) -> bool:
        from urllib.parse import quote
        title, msg = alert_text(kind, w, odds)
        click = self.s.get("site_url", SITE_URL) + "#ta=" + quote(w["b"].get("ident") or "", safe="")
        prio = PRIO_UP if kind == "up" else PRIO_GONE
        self.log(f"NOTIS: {title} | {msg}")
        if self._send is not None:
            return bool(self._send(title, msg, prio, click))
        from .notify import oddsvakt_topic, send
        topic = oddsvakt_topic(self.s)
        from .msg import unibet_url
        ub = unibet_url(w["b"].get("match_id"), w["b"].get("bolag"))
        ok = bool(topic) and send(topic, title, msg, priority=prio, tags="chart_with_upwards_trend" if kind == "up" else "x",
                                  click=click, link=("Hos Unibet", ub) if ub else None)
        if not ok:
            self.log("Oddsvakt: notisen gick inte fram")
        return ok

    # ---------- filer
    def _log_price(self, ident: str, w: dict, odds, obs: str, now: float) -> None:
        prev = self.last_log.get(ident)
        if prev and prev[0] == odds and prev[1] == obs and prev[2] == w["min"] and now - prev[3] < HEARTBEAT_S:
            return
        self.last_log[ident] = (odds, obs, w["min"], now)
        line = {"t": int(now), "i": ident, "b": w["bolag"], "o": odds, "m": w["min"], "s": obs}
        if w["typ"] == "egen":
            line["e"] = 1
        with (self.root / LOG_FILE).open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n")

    def prune_log(self, now: float) -> int:
        f = self.root / LOG_FILE
        if not f.exists():
            return 0
        cut = now - self.c["oddsvakt_logg_dagar"] * 86400
        keep, n = [], 0
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("t", 0) >= cut:
                    keep.append(line)
                    continue
            except json.JSONDecodeError:
                pass
            n += 1
        if n:
            f.write_text("".join(x + "\n" for x in keep), encoding="utf-8")
        return n

    def save(self, now: float) -> None:
        from .ledger import rensa_nan
        (self.root / STATE_FILE).write_text(json.dumps(rensa_nan({
            "uppdaterad_ts": now, "vakter": self.st, "egna": self.egna, "meddelande_ts": self.msg_ts,
            "tagna": dict(list(self.tagna_msg.items())[-500:]), "bas_p": dict(list(self.bas_p.items())[-500:]), "sedda": self.seen[-2000:]}), ensure_ascii=False), encoding="utf-8")
        pub = {}
        for ident, w in self.cur.items():
            x = self.st.get(ident) or {}
            b = w["b"]
            pub[ident] = {"ident": ident, "typ": w["typ"], "sport": b.get("sport"), "match": b.get("match"),
                          "spelare": b.get("spelare"), "spel_text": _bet_txt(b), "bolag": w["bolag"],
                          "avspark": b.get("avspark"), "odds_nu": x.get("odds"), "spela_fran": w.get("spela_fran"),
                          "min_odds": w["min"], "status": x.get("obs"), "ts": x.get("ts"), "notis_ts": x.get("last_alert")}
        site = self.root / "site"
        site.mkdir(parents=True, exist_ok=True)
        (self.root / SITE_FILE).write_text(json.dumps(rensa_nan({"uppdaterad_ts": now, "poll_s": self.c["oddsvakt_poll_s"],
                                                                 "bevakningar": pub}), ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ datagrenen
def git_sync(root: Path, log=print, run=None) -> bool:
    """Spara oddsvaktens egna filer i datagrenen och hämta det senaste läget (tiers.json m.m.).
    Samma mönster som bevaka.yml: commit, push; har grenen ändrats läggs vår commit ovanpå (-X theirs =
    vår version vinner, men våra commits innehåller bara våra egna filer – skanningens filer rörs aldrig)."""
    import subprocess
    run = run or (lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, timeout=120))
    files = [f for f in OWN_FILES if (root / f).exists()]
    if files:
        run("add", "--", *files)
        run("commit", "-q", "-m", f"oddsvakt {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", "--", *files)
    for _ in range(3):
        f = run("fetch", "-q", "--deepen=50", "origin", "data")
        if f.returncode != 0:
            log(f"Oddsvakt: git fetch fel {f.stderr.strip()[:200]}")
            return False
        r = run("rebase", "-q", "-X", "theirs", "FETCH_HEAD")
        if r.returncode != 0:
            run("rebase", "--abort")
            log(f"Oddsvakt: kunde inte lägga läget ovanpå datagrenen: {r.stderr.strip()[:200]}")
            return False
        p = run("push", "-q", "origin", "HEAD:data")
        if p.returncode == 0:
            return True
    log("Oddsvakt: kunde inte spara till datagrenen (försöker igen nästa gång)")
    return False


# ------------------------------------------------------------------ skanningens sida
def write_start_flag(root: Path, settings: dict, now: float | None = None, msgs: list | None = None, log=print) -> int:
    """Anropas av skanningen: skriver oddsvakt_start.txt (antal att bevaka) om det finns något att bevaka,
    annars tas filen bort. bevaka.yml startar oddsvakt.yml när filen finns. Läser bara oddsvaktens läge."""
    now = now or time.time()
    flag = Path(root) / FLAG_FILE
    n = 0
    if cfg(settings)["oddsvakt_on"]:
        v = Vakt(root, settings, send=lambda *a: False, fetch=lambda *a: None, log=lambda *_: None)
        if msgs:
            v.read_messages(msgs, now)
        n = len(v.targets(now))
    if n:
        flag.write_text(str(n), encoding="utf-8")
    elif flag.exists():
        flag.unlink()
    log(f"Oddsvakt: {n} spel att bevaka" + (" (startas)" if n else ""))
    return n


# ------------------------------------------------------------------ körningen
def main(root: Path, settings: dict, log=print, clock=time.time, sleep=time.sleep, fetch=None, send=None,
         poll=None, git: bool | None = None) -> None:
    import os
    from . import mina
    c = cfg(settings)
    if not c["oddsvakt_on"]:
        log("Oddsvakt: av (oddsvakt_on = false)")
        return
    git = bool(os.environ.get("PROPSBOT_ODDSVAKT_GIT")) if git is None else git
    poll = poll or mina.poll
    chats = settings.get("telegram_chats") or {}
    if not chats.get("oddsvakt"):
        log("VARNING: telegram_chats.oddsvakt saknas i settings.json – Odds Alert skickas till nivåchatten (tier)")
    v = Vakt(root, settings, send=send, fetch=fetch, log=log)
    topic = mina.topic_of(settings)
    t0 = clock()
    last_sync, last_mina, idle_since = t0, 0.0, None
    log(f"Oddsvakt: start, läsning var {c['oddsvakt_poll_s']} s, kanal för klick {'satt' if topic else 'SAKNAS'}")
    try:
        while clock() - t0 < c["oddsvakt_max_s"]:
            now = clock()
            if now - last_sync >= c["oddsvakt_omlas_s"]:
                v.save(now)
                v.prune_log(now)
                if git:
                    git_sync(Path(root), log)
                v.reload()
                last_sync = now
            if topic and now - last_mina >= c["oddsvakt_mina_s"]:
                try:
                    v.read_messages(poll(topic, "12h"), now)
                except Exception as e:  # noqa: BLE001
                    log(f"Oddsvakt: ntfy fel {type(e).__name__}: {e}")
                last_mina = now
            try:
                n = v.step(now)
            except Exception as e:  # noqa: BLE001 – bevakningen får aldrig dö på ett enskilt fel
                log(f"Oddsvakt: fel {type(e).__name__}: {e}")
                n = 1
            v.save(now)
            if n == 0:
                idle_since = idle_since or now
                if now - idle_since >= c["oddsvakt_tomgang_s"]:
                    log("Oddsvakt: inget att bevaka – klar")
                    break
            else:
                idle_since = None
            sleep(c["oddsvakt_poll_s"])
        else:
            log("Oddsvakt: tidsgränsen nådd – nästa start tar över")
    finally:
        now = clock()
        v.save(now)
        v.prune_log(now)
        if git:
            git_sync(Path(root), log)
