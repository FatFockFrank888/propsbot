"""Mina spel (18/11): spelen DU tagit, med ditt eget odds och din insats.

Klicket på webbsidan ("Jag tog spelet") skickas till en egen ntfy-kanal, <ntfy_topic>-mina, som ingen
telefon prenumererar på (alltså ingen notis för klicket). Boten läser kanalen vid varje körning
(ntfy sparar meddelanden i 12 h och boten körs var tionde minut) och sparar spelen i mina_spel.json.

Meddelandet (JSON): {"v": 1, "typ": "tog" | "angra", "ident": <tiers-identitet>, "kalla_fil", "kalla_key",
"sport", "odds", "units", "bolag", "ts"}. Samma ident igen = ändring (senaste vinner), "angra" tar bort.

Rättning: status och utfall följer botens egen rättning (tiers.json / källbokföringen), men resultatet räknas
på DITT odds och DINA units (asiatiska linjer: samma andel vunnet/förlorat som källan).
CLV på ditt odds: (skarp stängning − 1/ditt odds) × 100.

Livestatistiken (stat_now) delas med livebevakningen (livewatch.py) och speglas i webbsidan.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

NTFY = "https://ntfy.sh"
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
NBA_BOX = {"points": ("PTS",), "rebounds": ("REB",), "assists": ("AST",), "threes": ("3PT",), "steals": ("STL",),
           "blocks": ("BLK",), "pra": ("PTS", "REB", "AST"), "pr": ("PTS", "REB"), "ra": ("REB", "AST"), "pa": ("PTS", "AST")}
SOCCER_STAT = {"shots_on_target": ("shotsOnTarget",), "shots": ("totalShots",), "goal": ("totalGoals",),
               "assist": ("goalAssists",), "fouls": ("foulsCommitted",)}
MK_SV = {"points": "poäng", "rebounds": "returer", "assists": "assist", "threes": "trepoängare", "steals": "steals",
         "blocks": "blocks", "pra": "PRA", "pr": "poäng+returer", "ra": "returer+assist", "pa": "poäng+assist",
         "shots_on_target": "skott på mål", "shots": "skott", "goal": "mål", "assist": "assist", "fouls": "fouls",
         "corners": "hörnor", "corners_home": "hörnor", "corners_away": "hörnor", "total": "mål", "game_total": "poäng"}


def topic_of(settings: dict) -> str | None:
    t = settings.get("ntfy_topic")
    return f"{t}-mina" if t else None


# ------------------------------------------------------------------ inläsning av klick
POLL_ERR: list = []


def poll(topic: str, since: str = "24h") -> list[dict]:
    """ntfy:s historik för kanalen (rad-JSON). Bara "message"-händelser. Fel sparas i POLL_ERR (loggas)."""
    url = f"{NTFY}/{topic}/json?poll=1&since={since}"
    raw = None
    for _ in range(3):   # ntfy svarar ibland 429 (för många anrop) – försök igen
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "propsbot/1.0"}), timeout=20) as r:
                raw = r.read().decode("utf-8", errors="replace")
            break
        except Exception as e:  # noqa: BLE001 – får aldrig stoppa skanningen
            POLL_ERR.append(f"{type(e).__name__}: {e}")
            time.sleep(3)
    if raw is None:
        return []
    out = []
    for line in raw.splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("event") == "message":
            out.append(m)
    return out


class Book:
    def __init__(self, path: Path):
        self.path = path
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            d = {}
        self.bets: dict = d.get("spel", {})
        self.last_id: str | None = d.get("senaste_id")
        self.seen: set = set(d.get("sedda", []))

    def save(self) -> None:
        from .ledger import rensa_nan
        self.path.write_text(json.dumps(rensa_nan({"spel": self.bets, "senaste_id": self.last_id,
                                                   "sedda": sorted(self.seen)[-2000:]}), ensure_ascii=False),
                             encoding="utf-8")


def apply_messages(book: Book, msgs: list[dict], tiers_by_ident: dict, now: float) -> int:
    """Lägg in klicken. Returnerar antal ändringar."""
    n = 0
    for m in sorted(msgs, key=lambda x: x.get("time", 0)):
        if m.get("id") in book.seen:
            continue
        book.seen.add(m.get("id"))
        book.last_id = m.get("id")
        try:
            x = json.loads(m.get("message") or "{}")
        except json.JSONDecodeError:
            continue
        ident = x.get("ident")
        if not ident or x.get("v") != 1:
            continue
        if x.get("typ") == "angra":
            if book.bets.pop(ident, None) is not None:
                n += 1
            continue
        if x.get("typ") != "tog":
            continue
        base = dict(tiers_by_ident.get(ident) or {})
        base.pop("analys", None)
        try:
            odds, units = float(x["odds"]), float(x["units"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (1.01 <= odds <= 100 and 0 < units <= 20):
            continue
        b = book.bets.get(ident, {})
        b.update({k: base.get(k) for k in ("sport", "tier", "match_id", "match", "hemma", "borta", "liga", "avspark",
                                           "spelare", "spelare_id", "marknad", "linje", "sida", "spel_text", "edge",
                                           "kalla_fil", "kalla_key", "odds") if base.get(k) is not None})
        b.setdefault("sport", x.get("sport"))
        b.update(ident=ident, bot_odds=base.get("odds"), odds=odds, units=units, bolag=x.get("bolag") or base.get("bolag"),
                 tagen_ts=x.get("ts") or m.get("time") or now, status=b.get("status", "öppen"))
        book.bets[ident] = b
        n += 1
    return n


def _user_result(b: dict, src: dict) -> float | None:
    """Resultat i units på ditt odds: samma andel vunnet/förlorat som källan (halv vinst/förlust på kvartslinjer)."""
    st = b.get("status")
    if st not in ("vunnen", "förlorad", "push", "struken"):
        return None
    u, o = b["units"], b["odds"]
    ins, res, so = src.get("insats_pct"), src.get("resultat_enheter"), src.get("odds")
    if ins and res is not None and so:
        frac = res / ins
        if frac > 0:
            return frac / (so - 1) * (o - 1) * u
        return frac * u
    return (o - 1) * u if st == "vunnen" else -u if st == "förlorad" else 0.0


def settle(book: Book, root: Path, now: float) -> int:
    """Status, utfall och skarp stängning från botens rättning; resultat och CLV på ditt odds."""
    srcs: dict = {}
    n = 0
    for b in book.bets.values():
        f, k = b.get("kalla_fil"), b.get("kalla_key")
        if not f or not k:
            continue
        if f not in srcs:
            try:
                srcs[f] = {x.get("key"): x for x in json.loads((root / f).read_text(encoding="utf-8"))}
            except (FileNotFoundError, json.JSONDecodeError):
                srcs[f] = {}
        sb = srcs[f].get(k)
        if not sb:
            continue
        old = b.get("status")
        for key in ("status", "utfall", "skarp_stang_p", "pin_stang_p"):
            if key in sb:
                b[key] = sb[key]
        b["resultat_u"] = _user_result(b, sb)
        p = b.get("skarp_stang_p") or b.get("pin_stang_p")
        if p and (b.get("avspark") or now) < now:
            b["clv_pp"] = (p - 1 / b["odds"]) * 100
        n += old != b.get("status")
    return n


# ------------------------------------------------------------------ ESPN: match och livestatistik
def _get(url: str, params: dict | None = None):
    """ESPN m.fl. JSON. Samma webbläsar-User-Agent som resten av boten: ESPN svarar 403 på "propsbot/1.0"."""
    from urllib.parse import urlencode
    from .sources.http import UA
    full = url + ("?" + urlencode(params) if params else "")
    try:
        with urllib.request.urlopen(urllib.request.Request(full, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def find_event(b: dict, get=_get) -> tuple[str, str] | None:
    """(sökväg, event-id) hos ESPN för spelets match, t.ex. ("basketball/nba", "401..."), ("soccer/all", "740...")."""
    from datetime import datetime, timedelta, timezone
    from .sources.props_text import same_match
    path = "basketball/nba" if b.get("sport") == "nba" else "soccer/all"
    ko = b.get("avspark") or 0
    for d in (0, -1):
        day = (datetime.fromtimestamp(ko, timezone.utc) + timedelta(days=d)).strftime("%Y%m%d")
        sb = get(f"{ESPN}/{path}/scoreboard", {"dates": day}) or {}
        for ev in sb.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            t = {c.get("homeAway"): (c.get("team") or {}).get("displayName", "") for c in comp.get("competitors", [])}
            try:
                st = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError):
                continue
            if same_match(b.get("hemma") or "", b.get("borta") or "", ko, t.get("home", ""), t.get("away", ""), st):
                return path, ev["id"]
    return None


def game_state(summ: dict) -> dict:
    comp = ((summ.get("header") or {}).get("competitions") or [{}])[0]
    st = (comp.get("status") or {}).get("type") or {}
    sc = {c.get("homeAway"): c.get("score") for c in comp.get("competitors", [])}
    ab = {c.get("homeAway"): (c.get("team") or {}).get("abbreviation", "") for c in comp.get("competitors", [])}
    try:
        h, a = int(float(sc.get("home") or 0)), int(float(sc.get("away") or 0))
    except ValueError:
        h, a = 0, 0
    return {"state": st.get("state"), "done": bool(st.get("completed")), "detail": st.get("shortDetail") or st.get("detail") or "",
            "home": h, "away": a, "abbr_home": ab.get("home", ""), "abbr_away": ab.get("away", "")}


def _nba_player(summ: dict, name: str):
    from .sources.props_text import same_person
    for team in (summ.get("boxscore") or {}).get("players", []) or []:
        for grp in team.get("statistics", []) or []:
            labels = grp.get("labels") or grp.get("names") or []
            for a in grp.get("athletes", []) or []:
                if same_person((a.get("athlete") or {}).get("displayName", ""), name):
                    return labels, a
    return None


def _soccer_player(summ: dict, name: str):
    from .sources.props_text import same_person
    for team in summ.get("rosters", []) or []:
        for p in team.get("roster", []) or []:
            if same_person((p.get("athlete") or {}).get("displayName", ""), name):
                return p
    return None


def _corners(summ: dict) -> tuple[int, int] | None:
    got = {}
    for t in (summ.get("boxscore") or {}).get("teams", []) or []:
        v = next((x.get("displayValue") for x in t.get("statistics", []) or [] if x.get("name") == "wonCorners"), None)
        if v is not None and t.get("homeAway") in ("home", "away"):
            try:
                got[t["homeAway"]] = int(float(v))
            except ValueError:
                pass
    return (got["home"], got["away"]) if len(got) == 2 else None


def stat_now(b: dict, summ: dict) -> float | None:
    """Spelets räknare just nu: spelarens siffra (props), poäng/mål (totals), marginal (sides), hörnor."""
    mk, gs = b.get("marknad"), game_state(summ)
    if b.get("spelare_id") not in ("match", "hörnor"):
        if b.get("sport") == "nba":
            hit = _nba_player(summ, b.get("spelare") or "")
            if not hit:
                return None
            labels, a = hit
            stats = a.get("stats") or []
            tot = 0.0
            for key in NBA_BOX.get(mk, ()):
                if key not in labels or labels.index(key) >= len(stats):
                    return None
                v = str(stats[labels.index(key)]).split("-")[0]
                try:
                    tot += float(v)
                except ValueError:
                    return None
            return tot
        p = _soccer_player(summ, b.get("spelare") or "")
        if not p:
            return None
        st = {x.get("name"): x.get("value") for x in p.get("stats", []) or []}
        keys = SOCCER_STAT.get(mk)
        if not keys or any(st.get(k) is None for k in keys):
            return None
        return float(sum(st[k] for k in keys))
    if mk in ("corners", "corners_home", "corners_away", "cah"):
        c = _corners(summ)
        if c is None:
            return None
        return float(c[0] + c[1] if mk == "corners" else c[0] if mk == "corners_home" else c[1] if mk == "corners_away"
                     else (c[0] - c[1] if b.get("sida") == "home" else c[1] - c[0]))
    if mk in ("total", "game_total"):
        return float(gs["home"] + gs["away"])
    if mk in ("1x2", "ml", "ah", "spread"):          # marginal för vår sida
        return float(gs["home"] - gs["away"] if b.get("sida") == "home" else gs["away"] - gs["home"] if b.get("sida") == "away"
                     else -abs(gs["home"] - gs["away"]))
    return None


def decided(b: dict, v: float | None) -> str | None:
    """Avgjort före slutsignal? Över: klart när räknaren passerat linjen. Under: förlorat när den passerat."""
    if v is None or b.get("marknad") in ("1x2", "ml", "ah", "spread", "cah"):
        return None
    if v > (b.get("linje") or 0):
        return "vunnen" if b.get("sida") != "under" else "förlorad"
    return None


# ------------------------------------------------------------------ körningen
SITE_URL = "https://fatfockfrank888.github.io/propsbot/"


def send_pairing_link(root: Path, settings: dict, log=print, force: bool = False) -> bool:
    """Skicka EN notis till den vanliga kanalen med en länk som kopplar webbsidan till rätt kanal (#koppla=...).
    Då behöver kanalnamnet aldrig skrivas in för hand (felskrivet namn = boten får aldrig klicken).
    Bara en hash av kanalen sparas i läget (kanalnamnet ska inte synas publikt)."""
    import hashlib
    from urllib.parse import quote
    from .notify import send
    t = settings.get("ntfy_topic")
    if not t:
        return False
    h = hashlib.sha1(("koppla|" + t).encode()).hexdigest()[:12]
    f = root / "koppling_skickad.txt"
    if not force and f.exists() and f.read_text(encoding="utf-8").strip() == h:
        return False
    url = settings.get("site_url", SITE_URL) + "#koppla=" + quote(t)
    ok = send(t, "propsbot: koppla Mina spel", "Tryck här (på varje enhet du använder – mobil och dator) så kopplas webbsidan till boten "
              "och spelen du tar synkas automatiskt.", priority=4, tags="link", click=url)
    if ok:
        f.write_text(h, encoding="utf-8")
        log("Mina spel: kopplingslänk skickad till den vanliga kanalen")
    return ok


def run(root: Path, settings: dict, log=print, now: float | None = None) -> dict:
    now = now or time.time()
    book = Book(root / "mina_spel.json")
    topic = topic_of(settings)
    try:
        send_pairing_link(root, settings, log)
    except Exception as e:  # noqa: BLE001
        log(f"Mina spel: kopplingslänk fel {type(e).__name__}: {e}")
    try:
        tiers = {b["ident"]: b for b in json.loads((root / "tiers.json").read_text(encoding="utf-8")).get("bets", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        tiers = {}
    msgs = poll(topic) if topic else []
    n_new = apply_messages(book, msgs, tiers, now)
    n_set = settle(book, root, now)
    for b in book.bets.values():   # ESPN-matchen (för livescore på sidan och bevakningen)
        if not b.get("espn") and b.get("avspark") and now > b["avspark"] - 36 * 3600 and b.get("status") == "öppen":
            ev = find_event(b)
            if ev:
                b["espn"] = list(ev)
    book.save()
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    from .ledger import rensa_nan
    (site / "mina_spel.json").write_text(json.dumps(rensa_nan({"uppdaterad_ts": now, "spel": list(book.bets.values())}),
                                                    ensure_ascii=False), encoding="utf-8")
    # livebevakningen startas när ett av dina spel startar inom 25 min eller pågår (arbetsflödet läser filen)
    soon = [b for b in book.bets.values() if b.get("status") == "öppen" and b.get("avspark")
            and b["avspark"] - 25 * 60 <= now <= b["avspark"] + 5 * 3600]
    flag = root / "live_start.txt"
    if soon:
        flag.write_text(str(len(soon)), encoding="utf-8")
    elif flag.exists():
        flag.unlink()
    log(f"Mina spel: kanal {'satt' if topic else 'SAKNAS'}, {len(msgs)} meddelanden lästa"
        + (f" (ntfy-fel: {POLL_ERR[-1]})" if POLL_ERR else "") + f", {len(book.bets)} spel, {n_new} nya/ändrade klick, {n_set} nyrättade, {len(soon)} att bevaka live")
    return {"book": book, "soon": soon}
