"""Skanning med öppna källor (Kambi-bolagen + Pinnacle), utan krediter.

Flöde per körning:
1. Lista kommande matcher från Kambi (en offering räcker – alla Kambi-bolag har samma matcher).
2. Hämta spelarprops från varje Kambi-bolag (Unibet, Paf, ATG, LeoVegas …).
3. Hämta Pinnacles matcher i samma ligor, para ihop med Kambi-matcherna och hämta props.
4. Para ihop spelarnamn mellan källorna.
5. (Valfritt) The Odds API som komplement om use_the_odds_api = true.
6. Utvärdera: bästa spelbara pris mot konsensus från de ANDRA källorna (Pinnacle väger tyngst).
7. Skriv CSV, logga i SQLite, skicka mobilnotis för nya spelbara ben.

Allt som går fel per källa skrivs i diagnos/diagnos.txt, och råsvar sparas i diagnos/
så att tolkningen kan rättas om ett bolag ändrar format.
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .models import OddsQuote
from .notify import SeenStore, send
from .pipeline import MARKET_LABEL
from .scan import ScanRow, evaluate_event_market_only, format_scan, load_settings, write_csv
from .sources.http import JsonClient, SourceError
from .sources.kambi_public import KambiEvent, KambiPublic
from .sources.pinnacle_public import PinnaclePublic
from .line_adjust import evaluate_line_adjusted, kambi_match_lines, pinnacle_match_lines
from .sources.props_text import same_match, same_person
from .store import Store


@dataclass
class Diag:
    lines: list[str] = field(default_factory=list)
    dir: Path = Path("diagnos")

    def log(self, msg: str) -> None:
        print(msg)
        self.lines.append(msg)

    def raw(self, name: str, data) -> None:
        self.dir.mkdir(exist_ok=True)
        f = self.dir / f"{name}.json"
        if not f.exists() or f.stat().st_size < 50:
            f.write_text(json.dumps(data, ensure_ascii=False)[:2_000_000], encoding="utf-8")

    def save(self) -> None:
        self.dir.mkdir(exist_ok=True)
        (self.dir / "diagnos.txt").write_text("\n".join(self.lines), encoding="utf-8")


def _unify_players(quotes: list[OddsQuote], names: dict[str, str]) -> None:
    """Para ihop spelarnamn som stavas olika i olika källor (Kambi är facit)."""
    kambi_ids = {q.player_id for q in quotes if q.provider == "kambi"}
    canon: dict[str, str] = {}
    for q in quotes:
        if q.player_id in kambi_ids or q.player_id in canon:
            continue
        match = next((k for k in kambi_ids if same_person(q.player_id, k)), None)
        canon[q.player_id] = match or q.player_id
    for q in quotes:
        if q.player_id in canon:
            q.player_id = canon[q.player_id]
    for old, new in canon.items():
        if old != new and old in names:
            names.setdefault(new, names[old])


def collect(settings: dict, diag: Diag, cache_dir: Path) -> list[tuple[dict, list[OddsQuote], dict]]:
    hours = settings["hours_ahead"]
    out: list[tuple[dict, list[OddsQuote], dict]] = []
    offerings: dict[str, str] = settings["kambi_offerings"]

    # ---------------------------------------------------------------- Kambi
    kambi = KambiPublic(JsonClient(cache_dir, ttl_s=90), market=settings["kambi_market"])
    events: list[KambiEvent] = []
    working: dict[str, str] = {}
    if settings["use_kambi"]:
        for code, book in offerings.items():
            try:
                evs, raw = kambi.football_events(code, hours, settings["league_words"])
            except SourceError as e:
                diag.log(f"Kambi {book} ({code}): FEL {e}")
                continue
            if raw is None:
                diag.log(f"Kambi {book} ({code}): finns inte (404) – hoppas över")
                continue
            working[code] = book
            if not events:
                events = evs
                diag.raw(f"kambi_{code}_lista", raw)
                diag.log(f"Kambi {book} ({code}): OK, {len(evs)} matcher i valda ligor")
            else:
                diag.log(f"Kambi {book} ({code}): OK")
        events.sort(key=lambda e: e.start)
        events = events[: settings["max_kambi_events"]]
        if not working:
            diag.log("VARNING: inget Kambi-bolag svarade.")

    per_event: dict[int, tuple[dict, list[OddsQuote], dict]] = {}
    for ev in events:
        evd = {"id": f"k{ev.event_id}", "home_team": ev.home, "away_team": ev.away,
               "commence_time": ev.start, "league": ev.league}
        quotes: list[OddsQuote] = []
        names: dict[str, str] = {}
        for code, book in working.items():
            try:
                qs, nm, raw = kambi.event_props(code, book, ev, evd["id"])
            except SourceError as e:
                diag.log(f"  {ev.home} – {ev.away}: Kambi {book} FEL {e}")
                continue
            if raw is not None and qs:
                diag.raw(f"kambi_{code}_match", raw)
            if raw is not None and "kambi_lines" not in evd:
                kl = kambi_match_lines(raw)
                if kl:
                    evd["kambi_lines"] = kl
            quotes += qs
            names.update(nm)
        per_event[ev.event_id] = (evd, quotes, names)

    # -------------------------------------------------------------- Pinnacle
    if settings["use_pinnacle"] and per_event:
        try:
            pin = PinnaclePublic(JsonClient(cache_dir, ttl_s=60, min_interval_s=0.6))
            leagues = pin.leagues(settings["pinnacle_league_words"])
            diag.log(f"Pinnacle: OK, {len(leagues)} ligor")
            pevs = []
            failed = []
            for lg in leagues:
                try:
                    pevs += pin.events(lg, hours)
                except SourceError as e:
                    failed.append(f"{lg.get('name')} ({e})")
            if failed:
                diag.log(f"Pinnacle: {len(failed)} ligor svarade inte och hoppas över: "
                         + "; ".join(failed)[:300])
            n_props = 0
            for kid, (evd, quotes, names) in per_event.items():
                pe = next((p for p in pevs if same_match(evd["home_team"], evd["away_team"],
                                                         evd["commence_time"], p.home, p.away,
                                                         p.start)), None)
                if not pe:
                    continue
                try:
                    qs, nm, raw = pin.event_props(pe, evd["id"])
                except SourceError as e:
                    diag.lines.append(f"  {evd['home_team']} – {evd['away_team']}: Pinnacle FEL {e}")
                    continue
                pl = pinnacle_match_lines(raw.get("markets") or [], pe.matchup_id)
                if pl:
                    evd["pin_lines"] = pl
                trusted = set(settings.get("pinnacle_trusted_markets", []))
                qs = [q for q in qs if q.market in trusted]
                if qs:
                    diag.raw("pinnacle_match", raw)
                elif raw.get("related"):
                    diag.raw("pinnacle_match_utan_props", raw)
                n_props += len(qs)
                quotes += qs
                names.update(nm)
            n_lines = sum("pin_lines" in v[0] for v in per_event.values())
            diag.log(f"Pinnacle: {len(pevs)} matcher, matchlinjer för {n_lines} av "
                     f"{len(per_event)} Kambi-matcher, {n_props} spelarodds som används")
            from .sources.pinnacle_public import SEEN_SPECIALS
            if SEEN_SPECIALS:
                diag.lines.append("Pinnacles specialmarknader (beskrivning -> tolkning), exempel:")
                for k, v in list(SEEN_SPECIALS.items())[:60]:
                    diag.lines.append(f"  {k}  ->  {v}")
        except SourceError as e:
            diag.log(f"Pinnacle: FEL {e} (kan vara geoblockerat från er uppkoppling)")
        except Exception as e:  # inofficiellt format – logga och fortsätt
            diag.log(f"Pinnacle: oväntat format ({type(e).__name__}: {e})")
            diag.lines.append(traceback.format_exc())

    # --------------------------------------------------------- The Odds API
    if settings["use_the_odds_api"] and per_event:
        try:
            from .sources.the_odds_api import TheOddsApi, parse_props
            api = TheOddsApi(cache_dir=cache_dir)
            for sport in settings["sports"]:
                for oe in api.events(sport, hours):
                    from datetime import datetime
                    st = datetime.fromisoformat(oe["commence_time"].replace("Z", "+00:00")).timestamp()
                    hit = next((v for v in per_event.values()
                                if same_match(v[0]["home_team"], v[0]["away_team"],
                                              v[0]["commence_time"], oe["home_team"],
                                              oe["away_team"], st)), None)
                    if not hit:
                        continue
                    data = api.event_odds(sport, oe["id"], settings["prop_markets"],
                                          settings["regions"], settings["bookmakers"] or None)
                    if data:
                        qs, nm = parse_props(data)
                        for q in qs:
                            q.match_id = hit[0]["id"]
                        hit[1].extend(qs)
                        hit[2].update(nm)
            diag.log(f"The Odds API: krediter kvar {api.usage.remaining}")
        except Exception as e:
            diag.log(f"The Odds API: {e}")

    for evd, quotes, names in per_event.values():
        _unify_players(quotes, names)
        out.append((evd, quotes, names))
    return out


def scan_once(root: Path, settings_path: Path, notify: bool = True) -> list[ScanRow]:
    settings = load_settings(settings_path)
    # Alla Kambi-bolag är en leverantörsgrupp.
    settings["kambi_hint_prefixes"] = list(set(settings["kambi_hint_prefixes"])
                                           | set(settings["kambi_offerings"].values()))
    cfg = Config()
    diag = Diag(dir=root / "diagnos")
    diag.log(time.strftime("Skanning %Y-%m-%d %H:%M"))
    data = collect(settings, diag, root / ".cache_odds")
    rows: list[ScanRow] = []
    books: set[str] = set()
    store = Store(root / "propsbot.sqlite")
    for evd, quotes, names in data:
        if not quotes:
            continue
        books |= {q.book for q in quotes}
        has_pin_props = any(q.book == settings["sharp_book"] for q in quotes)
        if has_pin_props:
            res = evaluate_event_market_only(evd, quotes, names, settings, cfg, time.time(), "fotboll")
        elif "pin_lines" in evd and "kambi_lines" in evd:
            res, info = evaluate_line_adjusted(evd, quotes, names, settings, cfg, time.time(),
                                               evd["pin_lines"], evd["kambi_lines"])
            diag.lines.append(f"  {evd['home_team']} – {evd['away_team']}: {info}")
        else:
            miss = "Pinnacle" if "pin_lines" not in evd else "Kambi"
            diag.lines.append(f"  {evd['home_team']} – {evd['away_team']}: saknar matchlinjer från {miss}")
            continue
        rows += res
        for r in res:
            d = r.row.decision
            store.log_prediction(dict(
                ts=time.time(), match_id=d.cand.match_id, player_id=d.cand.player_id,
                player_name=d.cand.player_name, market=d.cand.market, line=d.cand.line,
                p_model=None, p_market=r.row.p_market, p_final=d.cand.p, w_model=0.0,
                lineup_confirmed=0, best_book=d.cand.best.book, best_odds=d.cand.best.odds,
                edge=d.cand.edge, play_from=d.play_from, playable=int(d.playable),
                shown=int(d.show), stake=d.stake, reasons="; ".join(d.reasons)))
    rows.sort(key=lambda r: -r.row.decision.cand.edge)
    diag.log(f"Bolag med spelarodds: {', '.join(sorted(books)) or 'inga'}")
    from collections import Counter
    mc = Counter(q.market for _, qs, _ in data for q in qs)
    diag.log("Spelarodds per marknad: " + ", ".join(f"{k} {v}" for k, v in sorted(mc.items())))
    if "pinnacle" not in books:
        diag.log("Pinnacle har inga spelarprops här – använder linjejustering mot Pinnacles matchlinjer.")
    playable = [r for r in rows if r.row.decision.playable and r.row.decision.show]
    diag.log(f"{len(playable)} spelbara ben.")
    for r in playable:
        c, d = r.row.decision.cand, r.row.decision
        diag.log(f"SPEL: {r.match} ({r.kickoff} UTC) | {c.player_name} | "
                 f"{MARKET_LABEL.get(c.market, c.market)} över {c.line} | {c.best.book} {c.best.odds:.2f} | "
                 f"Kambi rättvis {r.row.p_market:.1%} -> justerad {c.p:.1%} | edge {c.edge:.1%} | "
                 f"spela från {d.play_from:.2f} | {'; '.join(d.reasons)}")
    out_dir = root / "resultat"
    out_dir.mkdir(exist_ok=True)
    write_csv(rows, out_dir / f"spel_{time.strftime('%Y%m%d_%H%M')}.csv", settings["bankroll"], False)
    # ---- bokföring, stängningsodds, rättning och webbsida
    from .export import write_site
    from .ledger import Ledger
    from .results import settle_open
    ledger = Ledger(root / "bokforing.json")
    evd_by_id = {evd["id"]: evd for evd, _, _ in data}
    new_bets = ledger.record(rows, evd_by_id)
    ledger.update_closing(rows, time.time())
    try:
        for line in settle_open(ledger, JsonClient(root / ".cache_odds", ttl_s=900)):
            diag.log(line)
    except Exception as e:  # rättningen får aldrig stoppa skanningen
        diag.log(f"Rättning: oväntat fel {type(e).__name__}: {e}")
    ledger.save()
    diag.log(f"Bokförda nya spel: {len(new_bets)}")
    write_site(root / "site", rows, ledger, settings)

    if notify and settings.get("ntfy_topic"):
        # Första körningen mot en ny kanal: skicka ett test så att man ser att det fungerar.
        import hashlib
        th = hashlib.sha1(settings["ntfy_topic"].encode()).hexdigest()[:12]
        tf = root / "ntfy_kanal.txt"   # bara en hash – kanalnamnet ska inte synas publikt
        if not tf.exists() or tf.read_text(encoding="utf-8").strip() != th:
            ok = send(settings["ntfy_topic"], "propsbot är igång",
                      "Notiser fungerar. Du får en notis för varje nytt spelbart ben (odds 1,40–6,00).",
                      priority=3, tags="white_check_mark")
            if ok:
                tf.write_text(th, encoding="utf-8")
                diag.log("Testnotis skickad till mobilen.")
        n = notify_new(playable, settings, root)
        diag.log(f"Notiser skickade: {n}")
    diag.save()
    import os
    if os.environ.get("GITHUB_ACTIONS"):
        keep = [l for l in diag.lines if l.startswith(("Kambi", "Pinnacle", "Bolag", "VARNING"))
                or l.startswith(("SPEL:", "Spelarodds", "Rätt", "Struken", "Bokförda"))
                or "spelbara" in l or "otis" in l][:45]
        print("::notice title=diagnos::" + "%0A".join(x.replace("%", "%25") for x in keep))
    return rows


def notify_new(playable: list[ScanRow], settings: dict, root: Path) -> int:
    # Separat minne per kanal, så att byte av kanal inte tappar notiser.
    import hashlib
    th = hashlib.sha1(settings["ntfy_topic"].encode()).hexdigest()[:12]
    seen = SeenStore(root / f"notifierade_{th}.json")
    sent = 0
    for r in playable:
        c = r.row.decision.cand
        d = r.row.decision
        key = f"{c.match_id}|{c.player_id}|{c.market}|{c.line}|{c.best.book}"
        if not seen.is_new(key, c.best.odds):
            continue
        title = f"SPELA: {c.player_name} {MARKET_LABEL.get(c.market, c.market)} över {c.line}"
        msg = (f"{r.match} ({r.kickoff} UTC)\n"
               f"{c.best.book}: {c.best.odds:.2f}  (spela från {d.play_from:.2f})\n"
               f"Sannolikhet {c.p:.1%}, edge {c.edge:.1%}, insats {d.stake * settings['bankroll']:.0f} kr")
        if send(settings["ntfy_topic"], title, msg):
            seen.mark(key, c.best.odds)
            sent += 1
    seen.save()
    if sent:
        print(f"Skickade {sent} notiser till mobilen.")
    return sent


def watch(root: Path, settings_path: Path) -> None:
    settings = load_settings(settings_path)
    interval = max(3, float(settings["watch_interval_minutes"]))
    if settings.get("ntfy_topic"):
        send(settings["ntfy_topic"], "propsbot är igång",
             f"Bevakar var {interval:.0f}:e minut. Du får en notis för varje nytt spelbart ben.",
             priority=3, tags="white_check_mark")
    while True:
        try:
            rows = scan_once(root, settings_path)
            print()
            print(format_scan(rows, limit=15))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Fel i skanningen: {e}")
            traceback.print_exc()
        print(f"\nNästa skanning om {interval:.0f} minuter (Ctrl+C avslutar).")
        time.sleep(interval * 60)
