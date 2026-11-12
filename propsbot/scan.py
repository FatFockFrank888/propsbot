"""Skanna kommande matcher via The Odds API och hitta spelbara props.

Läge "marknad": utan spelardata (xG, skottdata, startelvor) är den bästa
skattningen en marknadskonsensus där Pinnacle väger tyngst och varje
leverantörsgrupp (t.ex. alla Kambi-bolag) räknas som EN röst. Bästa pris jämförs
mot konsensus från de ANDRA grupperna (leave-one-out), så att ett bolag aldrig
får "edge" mot sig självt. När spelardata kopplas in tar simulatorn + blandningen
i pipeline.py över för de spelare som har profil.
"""
from __future__ import annotations

import csv
import dataclasses
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from .config import Config
from .decision import Candidate, apply_portfolio_limits, evaluate
from .kambi import group_books_by_provider
from .market import devig_power, fair_prob_one_sided, inv_logit, logit
from .models import OddsQuote
from .pipeline import MARKET_LABEL, Row
from .sources.the_odds_api import (MATCH_MARKETS, OddsApiError, TheOddsApi, parse_match_lines,
                                   parse_props)
from .store import Store

DEFAULT_SETTINGS = {
    "sports": ["soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
               "soccer_italy_serie_a", "soccer_france_ligue_one", "soccer_uefa_champs_league",
               "soccer_sweden_allsvenskan"],
    "hours_ahead": 36,
    "prop_markets": ["player_shots_on_target", "player_shots", "player_goal_scorer_anytime",
                     "player_assists"],
    "regions": "uk,eu",
    "bookmakers": [],
    # Bolag ni spelar hos. Övriga (t.ex. Paf, LeoVegas) används bara för att mäta marginal.
    "playable_books": ["svenskaspel", "betmgm", "expekt", "atg", "unibet"],
    "sharp_book": "pinnacle",
    "kambi_hint_prefixes": ["unibet", "leovegas", "paf", "betrivers", "svenskaspel", "atg"],
    "max_events_per_run": 8,
    "bankroll": 1000,   # används inte för visning; all insats visas som units (1u = 0,2 %)
    "extra_edge_without_sharp": 0.03,
    "min_groups_without_sharp": 3,
    "max_plausible_edge": 0.25,
    # Bolag som bara används som jämförelse, aldrig som spelbolag.
    "excluded_books": ["pinnacle", "williamhill", "onexbet"],
    # Öppna källor (gratis). The Odds API används bara om use_the_odds_api = true.
    "use_kambi": True,
    "use_pinnacle": True,
    "use_the_odds_api": False,
    "kambi_market": "SE",
    "kambi_offerings": {"ubse": "unibet", "paf": "paf", "atg": "atg", "leose": "leovegas",
                        "svenskaspel": "svenskaspel", "expektse": "expekt",
                        "betmgmse": "betmgm"},
    # Pinnacle-marknader som får användas som referens. Mål är avstängt tills
    # tolkningen av Pinnacles målmarknad är verifierad mot riktiga råsvar.
    "pinnacle_trusted_markets": ["shots", "shots_on_target"],
    "league_words": ["England / Premier League", "England / The Championship", "England / Championship", "Spain / La Liga", "Spain / LaLiga", "Germany / Bundesliga", "Germany / 2. Bundesliga", "Italy / Serie A", "Italy / Serie B", "France / Ligue 1", "France / Ligue 2", "Netherlands / Eredivisie", "Portugal / Liga Portugal", "Portugal / Primeira Liga", "Belgium / Pro League", "Belgium / Jupiler", "Scotland / Premiership", "Turkey / Süper Lig", "Turkey / Super Lig", "Denmark / Superliga", "Norway / Eliteserien", "Sweden / Allsvenskan", "Austria / Bundesliga", "Switzerland / Super League", "Greece / Super League", "USA / MLS", "Brazil / Serie A", "Argentina / Liga Profesional", "Champions League", "Europa League", "Conference League", "Australia / A-League", "Brazil / Brasileirao", "Brazil / Copa do Brasil", "Mexico / Liga MX"],
    "pinnacle_league_words": ["England - Premier League", "England - Championship", "Spain - La Liga", "Germany - Bundesliga", "Germany - 2. Bundesliga", "Italy - Serie A", "Italy - Serie B", "France - Ligue 1", "France - Ligue 2", "Netherlands - Eredivisie", "Portugal - Primeira Liga", "Portugal - Liga Portugal", "Belgium - Pro League", "Belgium - First Division A", "Scotland - Premiership", "Turkey - Super Lig", "Denmark - Superliga", "Norway - Eliteserien", "Sweden - Allsvenskan", "Austria - Bundesliga", "Switzerland - Super League", "Greece - Super League", "USA - Major League Soccer", "Brazil - Serie A", "Argentina - Liga Profesional", "UEFA - Champions League", "UEFA - Europa League", "UEFA - Conference League", "Australia - A-League", "Mexico - Liga MX", "Brazil - Copa do Brasil"],
    "max_kambi_events": 60,
    # Hoppa över matcher där Kambis och Pinnacles målförväntan skiljer mer än så.
    "max_line_ratio_dev": 0.10,
    "min_power_k_shots": 1.20,  # försiktig skottmarginal för live-spel (annars skuggspel)
    "min_edge_display": 0.02,   # webbsidan visar bara ben med minst så här stor edge
    # Egen spelarmodell (ESPN-statistik). Vikt mot marknaden i log-odds.
    # Spel före matchstart (notiser + bokföring). False = allt bokförs som skuggspel.
    # Spel under pågående match görs aldrig (matcher filtreras bort vid avspark).
    "live_enabled": True,
    "use_player_model": True,
    # "test" = modellens spel bokförs separat utan notiser; "aktiv" = modellen styr spelen.
    "model_mode": "test",
    "model_weight": 0.10,
    "model_market_mult": {"shots": 1.0, "shots_on_target": 1.0, "goal": 0.7, "assist": 0.6},
    # NBA (Kambi-bolagen mot Pinnacles tvåsidiga spelarodds)
    "nba_enabled": True,
    "nba_hours_ahead": 30,
    "nba_max_events": 15,
    # DraftKings/FanDuel m.fl. via The Odds API (gratiskvot, kreditbudget per dag).
    "nba_us_books": True,
    # The Odds API-krediterna delas: NBA 60 %, fotboll 40 % av dagsbudgeten.
    "oddsapi_share_nba": 0.6,
    "oddsapi_share_football": 0.4,
    "oddsapi_reserve": 20,
    "football_extra_books": True,
    "football_fetch_window": [45, 300],
    # Kalshi (prediktionsbörs, gratis): bara likvida linjer räknas som referens.
    "use_kalshi": True,
    "kalshi_max_spread": 0.04,
    "kalshi_min_volume": 500,
    "nba_us_fetch_window": [40, 240],
    # Parlays: 2–3 ben, olika matcher, samma bolag, minst 5 % edge per ben.
    "parlays_enabled": True,
    "parlay_max_legs": 3,
    "parlay_min_leg_edge": 0.05,
    "parlay_max_odds": 40.0,
    "parlay_max_stake": 0.005,
    "parlay_pool_per_book": 8,
    "parlay_max_suggestions": 5,
    # Gemensamma spelregler (2/11, efter 210 spel): minst 5 % edge överallt, ett spel per
    # spelare och match, inget spel om oddset fallit > 3 %, inget spel när sharp money
    # (Pinnacle/konsensus) har rört sig mot oss. Fotbollen spelas på samma regler.
    "min_edge_all": 0.05,
    "odds_window_all": [1.40, 6.0],     # inga spel under 1,40 eller över 6,00 (alla sporter)
    "max_odds_drop": 0.03,
    "sharp_against_pp": 2.0,
    "sharp_with_pp": 1.5,
    # Sides & totals (5/11): Kambis 1X2/total/handikapp mot Pinnacle utan marginal. Datainsamling
    # tills ca 50 spel med stängning visar att vi slår Pinnacles stängning; då sides_live = true.
    # Startelvor (5/11): fotbollsspel (props och sides) blir spelbara först när båda elvorna är kända
    # hos ESPN, eller inom 55 min före avspark. Props: spelaren måste starta.
    "lineup_required": True, "lineup_fallback_minutes": 55, "lineup_lookup_minutes": 150,
    "sides_low_limit": 2000, "sides_low_limit_extra_edge": 0.01,
    # Mindre ligor/lägre divisioner (bara sides): Kambis övriga fotbollsmatcher inom 3 h (ej esport).
    "sides_extra_leagues": True, "sides_extra_hours": 12, "sides_extra_max_events": 150,
    "sides_extra_books": 2,
    "sides_enabled": True,
    "sides_live": False,
    "sides_markets": ["1x2", "total", "ah", "corners", "cah", "corners_home", "corners_away"],
    "sides_min_edge": 0.03,
    "sides_max_edge": 0.1,
    "sides_alt_extra_edge": 0.01,
    "sides_odds_window": [1.4, 6.0],
    "sides_min_pin_limit": 500,
    "sides_max_hours": 24,
    "sides_shadow_min_edge": 0.01,
    "sides_max_units": 3,
    "football_shadow": False,
    "football_odds_window": [1.60, 2.50],
    # LIVE (3/11): bara dessa spel skickas som notis och bokförs i nba_live.json.
    # Övriga bokföringar fortsätter med 5 %-reglerna för att samla data.
    "live_on": True,
    # 4/11 (ca 400 avgjorda NBA-spel): modellens stöd är det som skiljer – edge 5–15 % + modell ≥ 5 %
    # gav ROI +20 % och CLV +2,7 pe; edge över 15 % slog inte stängningen.
    "live_min_edge": {"points": 0.05, "threes": 0.05, "assists": 0.05, "rebounds": 0.05},
    "live_model_min_edge": 0.05,
    "live_max_edge": 0.15,
    "football_live_max_units": 5,   # samma tak som NBA LIVE
    "football_kelly_scale": 0.5,
    "sides_lineup_gate": False,     # sides väntar inte på startelvor (Pinnacle prisar redan in dem)
    "graduation_min_bets": 50,      # uppgradering (sides -> LIVE, fotboll -> full insats): spel med stängning
    "graduation_min_t": 1.0,        # ... och snitt-CLV > 0 med minst detta t-värde    # fotboll utan historik: halva Kelly-insatsen tills CLV visats (storleken följer ändå styrkan)
    "live_min_groups": 2,
    "live_odds_window": [1.40, 3.00],
    "live_block_degraded": True,    # NBA: marknader med status degraded (nba_eval) ger inga LIVE-spel
    "live_max_units": 5,          # 5u = 1 % av bankrullen per spel
    "live_max_per_match": 2,
    "live_max_per_day": 8,
    "live_max_units_day": 25,     # högst 5 % av bankrullen i spel per matchdag
    "football_live": False,       # fotbollen samlar bara data
    "football_markets": ["shots_on_target"],   # bara skott på mål (3/11)
    # Fouls (Player's fouls conceded): egen modell, bara testbokföring (bokforing_fouls_test.json).
    "fouls_enabled": True,
    "fouls_min_edge": 0.05,
    "fouls_min_apps": 2.5,
    "fouls_opp_elasticity": 0.5,
    "parlays_notify": False,      # parlays bokförs som test, ingen notis
    # Notiser till mobilen via ntfy (gratis app). Tomt = av.
    "ntfy_topic": "",
    "watch_interval_minutes": 10,
}


def load_settings(path: Path) -> dict:
    import os
    s = dict(DEFAULT_SETTINGS)
    if path.exists():
        s.update(json.loads(path.read_text(encoding="utf-8")))
    else:
        path.write_text(json.dumps(DEFAULT_SETTINGS, indent=2, ensure_ascii=False), encoding="utf-8")
    if os.environ.get("NTFY_TOPIC"):
        s["ntfy_topic"] = os.environ["NTFY_TOPIC"]
    return s


# ------------------------------------------------------------- konsensus
@dataclass
class Consensus:
    p: float
    n_groups: int
    has_sharp_or_two_sided: bool


def provider_groups(quotes: list[OddsQuote], settings: dict, cfg: Config) -> dict[str, int]:
    """book -> grupp-id. Automatisk gruppering (samma leverantör) + namnledtråd."""
    books = sorted({q.book for q in quotes})
    groups: list[set[str]] = group_books_by_provider(quotes, cfg.market, min_common=20)
    hint = [b for b in books if any(b.startswith(p) for p in settings["kambi_hint_prefixes"])]
    if len(hint) > 1:
        merged = set(hint)
        rest = []
        for g in groups:
            if g & merged:
                merged |= g
            else:
                rest.append(g)
        groups = rest + [merged]
    gid = {}
    for i, g in enumerate(groups):
        for b in g:
            gid[b] = i
    for b in books:
        gid.setdefault(b, len(gid) + 1000)
    return gid


def group_fair_prob(qs: list[OddsQuote], market: str, is_sharp: bool, cfg: Config
                    ) -> tuple[float, bool] | None:
    """Rättvis sannolikhet för en grupp: tvåsidigt där det finns, annars ensidigt."""
    by_book: dict[str, dict[str, float]] = defaultdict(dict)
    for q in qs:
        by_book[q.book][q.side] = q.odds
    two = [devig_power((d["over"], d["under"]))[0] for d in by_book.values()
           if "over" in d and "under" in d]
    if two:
        return median(two), True
    overs = [d["over"] for d in by_book.values() if "over" in d]
    if not overs:
        return None
    o = median(overs)
    if is_sharp:
        return 1.0 / (o * 1.03), True
    return fair_prob_one_sided(market, o, cfg.market), False


def consensus(qs: list[OddsQuote], gid: dict[str, int], exclude_group: int | None,
              sharp: str, market: str, cfg: Config) -> Consensus | None:
    by_group: dict[int, list[OddsQuote]] = defaultdict(list)
    for q in qs:
        g = gid[q.book]
        if g != exclude_group:
            by_group[g].append(q)
    parts = []
    for g, gq in by_group.items():
        is_sharp = any(q.book == sharp for q in gq)
        r = group_fair_prob(gq, market, is_sharp, cfg)
        if r:
            parts.append((r[0], r[1], is_sharp))
    if not parts:
        return None
    sharp_parts = [p for p in parts if p[2]]
    others = [p for p in parts if not p[2]]
    if sharp_parts and others:
        ws = cfg.market.pinnacle_weight / (cfg.market.pinnacle_weight + cfg.market.kambi_weight)
        x = ws * logit(sharp_parts[0][0]) + (1 - ws) * sum(logit(p[0]) for p in others) / len(others)
    else:
        x = sum(logit(p[0]) for p in parts) / len(parts)
    return Consensus(inv_logit(x), len(parts), any(p[1] for p in parts))


# ------------------------------------------------------------------ skanning
@dataclass
class ScanRow:
    sport: str
    match: str
    kickoff: str
    row: Row
    n_groups: int
    expected: float | None = None   # modellens väntade värde (visas som Prognos)


def evaluate_event_market_only(event: dict, quotes: list[OddsQuote], names: dict[str, str],
                               settings: dict, cfg: Config, fetch_ts: float, sport: str
                               ) -> list[ScanRow]:
    gid = provider_groups(quotes, settings, cfg)
    sharp = settings["sharp_book"]
    # Tom lista = alla bolag utom Pinnacle (referens, oftast inte spelbar/licensierad).
    excluded = set(settings.get("excluded_books", [])) | {sharp}
    playable = set(settings["playable_books"]) or {q.book for q in quotes if q.book not in excluded}
    ko = float(event["commence_time"]) if isinstance(event["commence_time"], (int, float)) else \
        datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")).timestamp()
    mtk = (ko - fetch_ts) / 60.0
    title = f"{event['home_team']} – {event['away_team']}"

    by_line: dict[tuple, list[OddsQuote]] = defaultdict(list)
    for q in quotes:
        by_line[(q.player_id, q.market, q.line)].append(q)

    out: list[ScanRow] = []
    for (pid, market, line), qs in by_line.items():
        for side in ("over", "under"):
            cands = [q for q in qs if q.side == side and q.book in playable]
            if not cands:
                continue
            best = max(cands, key=lambda q: q.odds)
            cons = consensus(qs, gid, gid[best.book], sharp, market, cfg)
            if cons is None:
                continue  # ingen oberoende källa att jämföra mot
            if side == "under":
                # Under kräver tvåsidig/skarp referens (annars okänd marginal på undersidan).
                if not cons.has_sharp_or_two_sided:
                    continue
                cons = Consensus(1.0 - cons.p, cons.n_groups, cons.has_sharp_or_two_sided)
            dcfg = dataclasses.replace(cfg.decision,
                                       min_edge_by_market=dict(cfg.decision.min_edge_by_market))
            if not cons.has_sharp_or_two_sided:
                for k in dcfg.min_edge_by_market:
                    dcfg.min_edge_by_market[k] += settings["extra_edge_without_sharp"]
            cand = Candidate(event["id"], pid, names.get(pid, pid), market, line, cons.p,
                             dataclasses.replace(best, ts=fetch_ts), consensus_odds=1.0 / cons.p,
                             now=fetch_ts, lineup_confirmed=True, minutes_to_kickoff=mtk)
            d = evaluate(cand, dcfg)
            weak = not cons.has_sharp_or_two_sided
            if weak:
                d.reasons.append("ingen Pinnacle/tvåsidig källa – högre edgekrav")
            # Spärr 1: en enda ensidig jämförelsekälla räcker inte. Då jämförs bara två
            # bolags marginaler och skillnader i regler, inte en verklig sannolikhet.
            if weak and cons.n_groups < settings["min_groups_without_sharp"]:
                d.playable, d.stake = False, 0.0
                d.reasons.append(f"bara {cons.n_groups} jämförelsekälla – inte spelbart")
            # Spärr 2: orimligt stor edge betyder nästan alltid olika regler, fel linje,
            # gammalt pris eller att spelaren inte spelar – inte ett fynd.
            if d.cand.edge > settings["max_plausible_edge"]:
                d.playable, d.stake = False, 0.0
                d.reasons.append(f"edge över {settings['max_plausible_edge']:.0%} – orimligt, kontrollera")
            out.append(ScanRow(sport, title, datetime.fromtimestamp(ko, timezone.utc).strftime(
                "%Y-%m-%d %H:%M"), Row(d, float("nan"), cons.p, 0.0), cons.n_groups))
    apply_portfolio_limits([r.row.decision for r in out], cfg.decision)
    return out


def run_scan(settings_path: Path, out_dir: Path, db_path: Path | None = None,
             only_playable: bool = False) -> list[ScanRow]:
    settings = load_settings(settings_path)
    cfg = Config()
    api = TheOddsApi()
    store = Store(db_path) if db_path else None
    rows: list[ScanRow] = []

    available = {s["key"] for s in api.soccer_sports()}
    sports = [s for s in settings["sports"] if s in available]
    skipped = [s for s in settings["sports"] if s not in available]
    if skipped:
        print(f"Inte aktiva just nu (hoppas över): {', '.join(skipped)}")

    events = []
    for sport in sports:
        for ev in api.events(sport, settings["hours_ahead"]):
            events.append((sport, ev))
    events.sort(key=lambda x: x[1]["commence_time"])
    events = events[: settings["max_events_per_run"]]
    n_reg = 1 if settings["bookmakers"] else len(settings["regions"].split(","))
    est = len(events) * (len(MATCH_MARKETS) + len(settings["prop_markets"])) * n_reg
    print(f"{len(events)} matcher, uppskattad kostnad högst {est} krediter "
          f"(kvar innan: {api.usage.remaining or 'okänt'})")

    all_books: set[str] = set()
    for sport, ev in events:
        try:
            props = api.event_odds(sport, ev["id"], settings["prop_markets"],
                                   settings["regions"], settings["bookmakers"] or None)
        except OddsApiError as e:
            print(f"  {ev['home_team']} – {ev['away_team']}: {e}")
            continue
        fetch_ts = time.time()
        if not props or not props.get("bookmakers"):
            print(f"  {ev['home_team']} – {ev['away_team']}: inga props")
            continue
        quotes, names = parse_props(props)
        if not quotes:
            print(f"  {ev['home_team']} – {ev['away_team']}: inga props")
            continue
        books = sorted({q.book for q in quotes})
        all_books.update(books)
        print(f"  {ev['home_team']} – {ev['away_team']}: {len(quotes)} odds från {', '.join(books)}")
        res = evaluate_event_market_only(ev, quotes, names, settings, cfg, fetch_ts, sport)
        rows.extend(res)
        if store:
            for r in res:
                d = r.row.decision
                store.log_prediction(dict(
                    ts=fetch_ts, match_id=d.cand.match_id, player_id=d.cand.player_id,
                    player_name=d.cand.player_name, market=d.cand.market, line=d.cand.line,
                    p_model=None, p_market=r.row.p_market, p_final=d.cand.p, w_model=0.0,
                    lineup_confirmed=0, best_book=d.cand.best.book, best_odds=d.cand.best.odds,
                    edge=d.cand.edge, play_from=d.play_from, playable=int(d.playable),
                    shown=int(d.show), stake=d.stake, reasons="; ".join(d.reasons)))

    rows.sort(key=lambda r: -r.row.decision.cand.edge)
    sharp = settings["sharp_book"]
    kambi = [b for b in all_books if any(b.startswith(x) for x in settings["kambi_hint_prefixes"])]
    print(f"\nBolag med props: {', '.join(sorted(all_books)) or 'inga'}")
    if sharp not in all_books:
        print(f"VARNING: {sharp} saknas i datan – ingen skarp referens. Resultaten är svaga.")
    if not kambi:
        print("VARNING: inga Kambi-bolag (t.ex. Unibet) i datan.")
    out_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M")
    write_csv(rows, out_dir / f"spel_{stamp}.csv", settings["bankroll"], only_playable)
    print(f"Krediter kvar: {api.usage.remaining} (anrop {api.usage.calls}, från cache {api.usage.cached})")
    return rows


def write_csv(rows: list[ScanRow], path: Path, bankroll: float, only_playable: bool) -> None:
    from .clv_signal import units   # insats visas alltid som units, aldrig kronor
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Status", "Avspark (UTC)", "Match", "Spelare", "Marknad", "Linje", "Bolag",
                    "Odds", "Sannolikhet", "Edge", "Spela från", "Insats (units 1–10)", "Källor", "Kommentar"])
        for r in rows:
            d = r.row.decision
            c = d.cand
            if only_playable and not d.playable:
                continue
            if not d.show and not d.playable:
                continue
            w.writerow([
                "SPELA" if d.playable and d.show else "-",
                r.kickoff, r.match, c.player_name, MARKET_LABEL.get(c.market, c.market),
                f"över {c.line}".replace(".", ","), c.best.book, f"{c.best.odds:.2f}".replace(".", ","),
                f"{c.p:.1%}".replace(".", ","), f"{c.edge:.1%}".replace(".", ","),
                f"{d.play_from:.2f}".replace(".", ","), f"{units(d.stake)}u",
                r.n_groups, "; ".join(d.reasons)])
    print(f"Sparat: {path}")


def format_scan(rows: list[ScanRow], limit: int = 40) -> str:
    head = f"{'Match':<32}{'Spelare':<24}{'Marknad':<14}{'Linje':>6}{'Bolag':>14}{'Odds':>7}" \
           f"{'p':>7}{'Edge':>7}{'Från':>7}  Status"
    lines = [head, "-" * len(head)]
    n = 0
    for r in rows:
        d = r.row.decision
        if not d.show:
            continue
        c = d.cand
        st = "SPELA" if d.playable else "-"
        lines.append(f"{r.match[:31]:<32}{c.player_name[:23]:<24}"
                     f"{MARKET_LABEL.get(c.market, c.market):<14}{c.line:>6}{c.best.book[:13]:>14}"
                     f"{c.best.odds:>7.2f}{c.p:>7.1%}{c.edge:>7.1%}{d.play_from:>7.2f}  {st}")
        n += 1
        if n >= limit:
            break
    return "\n".join(lines)


def discover_books(settings_path: Path) -> None:
    """Visa vilka bolag och marknader nyckeln ger för nästa match i varje liga."""
    settings = load_settings(settings_path)
    api = TheOddsApi()
    available = {s["key"]: s["title"] for s in api.soccer_sports()}
    for sport in settings["sports"]:
        if sport not in available:
            continue
        evs = api.events(sport, 168)
        if not evs:
            continue
        ev = evs[0]
        data = api.event_odds(sport, ev["id"], list(MATCH_MARKETS) + settings["prop_markets"],
                              settings["regions"], settings["bookmakers"] or None)
        print(f"\n{available[sport]}: {ev['home_team']} – {ev['away_team']}")
        if not data:
            data = api.event_odds(sport, ev["id"], list(MATCH_MARKETS), settings["regions"],
                                  settings["bookmakers"] or None)
            print("  (props avvisades för den här ligan – visar bara matchlinjer)")
        for bm in (data or {}).get("bookmakers", []):
            mk = ", ".join(m["key"] for m in bm.get("markets", []))
            print(f"  {bm['key']:<22} {mk}")
        ml = parse_match_lines(data or {"home_team": ev["home_team"], "away_team": ev["away_team"]},
                               settings["sharp_book"]) if data else None
        if ml:
            print(f"  Matchlinjer från {ml.source}: 1X2 {ml.odds_1x2}, total {ml.total_line} {ml.odds_total}")
    print(f"\nKrediter kvar: {api.usage.remaining}")
