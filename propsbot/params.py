"""Alla parametrar per sport, med förklaring – läses från de värden boten faktiskt använder.

Används av webbsidans flik Parametrar (site/parametrar.json) och av `python -m propsbot parametrar`.
"""
from __future__ import annotations

from pathlib import Path


def _pct(x, d=0) -> str:
    return "–" if x is None else f"{x * 100:.{d}f} %".replace(".", ",")


def _odds(lo, hi) -> str:
    return f"{lo:.2f}–{hi:.2f}".replace(".", ",")


def _u(x) -> str:
    return f"{x}u"


def all_params(settings_path: Path) -> dict:
    from .config import DecisionConfig
    from .scan import load_settings
    s = load_settings(settings_path)
    dc = DecisionConfig()
    lo, hi = s.get("odds_window_all", [1.60, 6.0])
    live_th = s.get("live_min_edge", {})
    llo, lhi = s.get("live_odds_window", [1.60, 3.00])

    shared = [
        ("Spelbara bolag", ", ".join(s["playable_books"]), "Bara Kambi-bolag. Paf och LeoVegas läses bara för att mäta marginalen."),
        ("Minsta edge (alla spel)", _pct(s.get("min_edge_all", 0.05)), "edge = sannolikhet × odds − 1. Gäller alla marknader och sporter."),
        ("Oddsram", _odds(lo, hi), "Inga spel utanför."),
        ("Max oddsfall", _pct(s.get("max_odds_drop", 0.03)), "Inget spel om bästa oddset fallit mer än så från det högsta vi sett (för sent)."),
        ("Sharp money mot oss", f"{s.get('sharp_against_pp', 2.0):g} procentenheter",
         "Inget spel om den skarpa referensen (Pinnacle/konsensus) rört sig så mycket mot oss efter 30 min."),
        ("Sharp money med oss", f"{s.get('sharp_with_pp', 1.5):g} procentenheter", "Markeras i notisen (⬆)."),
        ("Lagnyheter (varje skanning)", "NBA: ESPN skadelista · NHL: DailyFaceoff · fotboll: startelvan",
         "Out/doubtful, ute eller inte i laget/startelvan = inget spel; questionable markeras. Öppna LIVE-spel kontrolleras igen före start och ger en notis (📰) om spelarens status ändras."),
        ("Orimlig edge", _pct(s.get("max_plausible_edge", 0.25)), "Större edge = nästan alltid fel linje, olika regler eller spelaren spelar inte. Inte spelbart."),
        ("Ett spel per spelare och match", "ja, över allt",
         "Över alla marknader, linjer, sidor (över/under), bolag och körningar. Störst edge vinner; det som redan skickats står kvar."),
        ("Över eller under", "den sida som har EV+",
         "Båda sidor prövas på samma krav. Under kräver en tvåsidig eller skarp referens (annars är marginalen på undersidan okänd)."),
        ("Notiser", "bara LIVE-spel", "En notis per spel, aldrig två på samma spelare i samma match. Misslyckad notis skickas igen nästa körning (före start)."),
        ("Unit", "1u = 0,2 % av bankrullen", "Insats 1–10u efter ¼ Kelly (taket 10u = 2 %)."),
        ("Skuggspel", "≥ 2 % edge, stoppat av en regel", "Bokförs och rättas för att se om reglerna kostar eller sparar pengar. Ingen notis."),
    ]
    football = [
        ("Status", "LIVE (notiser)" if s.get("football_live") else "bara datainsamling (inga notiser)",
         "football_live i settings.json. Påslaget 2026-11-04 på användarens begäran. Spelen är regelspelen "
         "(alla gemensamma krav); risktak: högst 5u per spel och 5 % per match."),
        ("LIVE: insats", f"¼ Kelly × {s.get('football_kelly_scale', 0.5):g}, högst {s.get('football_live_max_units', 5)}u per spel",
         "Insatsen följer styrkan (edge och odds) som i NBA/NHL, men i halv storlek eftersom fotbollen saknar historik "
         "med edge och CLV. Går automatiskt upp till full ¼ Kelly när 50 spel med stängning visar positiv CLV (t ≥ 1), med en notis."),
        ("Automatisk uppgradering", f"{s.get('graduation_min_bets', 50)} spel, CLV > 0 (t ≥ {s.get('graduation_min_t', 1.0):g})",
         "Prövas vid varje skanning för fotbollsprops (halv -> full insats) och sides/totals (data -> LIVE med notiser, ¼ Kelly upp till 5u). "
         "Vänder CLV till negativt över minst 30 spel går marknaden tillbaka till försiktigt läge."),
        ("Marknader som spelas", ", ".join(s.get("football_markets", ["shots_on_target"])),
         "Övriga marknader används bara för att mäta Kambis marginal."),
        ("Edgekrav per marknad (före gemensamt krav)", ", ".join(f"{k} {_pct(v)}" for k, v in dc.min_edge_by_market.items()),
         "Gemensamma kravet 5 % gäller ovanpå."),
        ("Utan Pinnacle/tvåsidig källa", f"+{_pct(s.get('extra_edge_without_sharp', 0.03))} edge, minst {s.get('min_groups_without_sharp', 3)} källor", ""),
        ("Försiktig skottmarginal", f"k ≥ {s.get('min_power_k_shots', 1.2):g}", "Edgen måste hålla även med en försiktig marginal, annars skuggspel."),
        ("Kambi mot Pinnacle (målförväntan)", f"max {_pct(s.get('max_line_ratio_dev', 0.10))} skillnad", "Annars hoppas matchen över (olika regler, gamla linjer)."),
        ("Spelarmodell", f"{s.get('model_mode', 'test')}, vikt {s.get('model_weight', 0.1):g}",
         "ESPN-statistik. I läget test bokförs modellens spel separat (Modelltest)."),
        ("CLV-signal", f"edge ≥ {_pct(s.get('clv_min_edge', 0.01))}, förväntad CLV ≥ {s.get('clv_min_expected_pp', 2.0):g}, Pinnacle ≥ +{s.get('clv_min_momentum_pp', 1.5):g}",
         "Släpper igenom ben som bara stoppades av edgekravet när Pinnacle rör sig åt vårt håll."),
        ("Max odds-ålder", f"{dc.max_odds_age_s:.0f} s", ""),
        ("Max avvikelse från konsensus", _pct(dc.max_dev_from_consensus), ""),
        ("Ligor", f"{len(s.get('league_words', []))} st", ", ".join(s.get("league_words", []))),
        ("Fouls (test)", f"på, minst {_pct(s.get('fouls_min_edge', 0.05))} edge" if s.get("fouls_enabled", True) else "av",
         "Egen modell (ESPN), domarfaktor ±15 %. Bara datainsamling."),
        ("Kort (test)", "på, datainsamling" if s.get("cards_enabled", True) else "av",
         "\"To Get a Card\" hos Kambi. Egen modell: spelarens kort per match (ESPN) × domarens stränghet. Bara datainsamling."),
        ("Parlays", f"{'på' if s.get('parlays_enabled') else 'av'}, max {s.get('parlay_max_legs', 3)} ben, minst {_pct(s.get('parlay_min_leg_edge', 0.05))} edge per ben",
         "Notiser för parlays: " + ("på" if s.get("parlays_notify") else "av") + "."),
    ]
    so_lo, so_hi = s.get("sides_odds_window", [1.60, 4.00])
    football += [
        ("Sides/totals: status", ("LIVE (notiser)" if s.get("sides_live") else "datainsamling (inga notiser)")
         if s.get("sides_enabled", True) else "av",
         "1X2, mål över/under och asiatiskt handikapp hos Kambi mot Pinnacle utan marginal (start 5/11). "
         "LIVE slås på när ca 50 spel visar att vi slår Pinnacles stängning."),
        ("Sides/totals: marknader", ", ".join(s.get("sides_markets", ["1x2", "total", "ah"])),
         "1X2, mål över/under och asiatiskt handikapp – halvlinjer (x,5) och asiatiska linjer: hela (push = insatsen "
         "tillbaka) och kvarts (halva insatsen på var närliggande linje). 90 minuter + tillägg."),
        ("Startelvor (props och sides)", "krävs" if s.get("lineup_required", True) else "av",
         f"Spelbart först när båda startelvorna är kända hos ESPN (ca 1 h före avspark), annars inom "
         f"{s.get('lineup_fallback_minutes', 55)} min före avspark. Props: spelaren måste starta. Skador och avstängningar "
         "syns som att spelaren saknas i elvan, och Pinnacle har då prisat in dem. Tidigare edges bokförs som skugga."),
        ("Sides/totals: edgekrav", f"{_pct(s.get('sides_min_edge', 0.03))} (alternativ Pinnacle-linje +{_pct(s.get('sides_alt_extra_edge', 0.01))})",
         "Lägre än 5 % eftersom referensen är Pinnacles huvudlinje (skarpast i världen): mot den är 3 % en verklig edge. "
         f"{_pct(s.get('sides_shadow_min_edge', 0.01))}–{_pct(s.get('sides_min_edge', 0.03))} bokförs som Sides-skugga för att mäta nivån."),
        ("Sides/totals: högsta edge", _pct(s.get("sides_max_edge", 0.10)),
         "Större edge mot Pinnacle = nästan alltid gammal linje, nyhet (uppställning/skada) eller fel match. Bokförs som skugga."),
        ("Sides/totals: oddsram", _odds(so_lo, so_hi), "Bredare än props uppåt så att oavgjort och små skrällar kommer med."),
        ("Sides/totals: Pinnacles insatsgräns", f"minst {s.get('sides_min_pin_limit', 500)}; under {s.get('sides_low_limit', 2000)} "
         f"krävs +{_pct(s.get('sides_low_limit_extra_edge', 0.01))} edge",
         "Gränsen visar hur skarp Pinnacles linje är. Låg gräns (ofta lägre divisioner) = svagare referens -> högre krav."),
        ("Sides/totals: mindre ligor", (f"på – alla Kambi-ligor (ej esport) inom {s.get('sides_extra_hours', 3)} h före avspark, "
                                        f"max {s.get('sides_extra_max_events', 60)} matcher") if s.get("sides_extra_leagues", True) else "av",
         "Lägre divisioner och mindre ligor har oftare felsatta linjer. Bara huvudmarknaderna hämtas (snabbt). "
         "Rättas mot ESPN:s samlade resultattavla."),
        ("Sides/totals: övrigt", f"max oddsfall {_pct(s.get('max_odds_drop', 0.03))}, sharp money mot oss {s.get('sharp_against_pp', 2.0):g} pe, "
         f"ett spel per match, inom {s.get('sides_max_hours', 24)} h före avspark, max {s.get('sides_max_units', 3)}u",
         "Samma spärrar som övriga sporter. Rättas mot ESPN:s slutresultat."),
    ]
    nba = [
        ("Status", "LIVE (notiser)" if s.get("live_on", True) and s.get("nba_enabled", True) else "av", ""),
        ("LIVE: edgekrav per marknad", ", ".join(f"{k} {_pct(v)}" for k, v in live_th.items()),
         "Marknader som saknas här (steals, blocks, PRA …) spelas inte live."),
        ("LIVE: högsta edge", _pct(s.get("live_max_edge", 0.15)), "Större edge slog inte stängningen i datan (oftast fel i linje/modell)."),
        ("LIVE: modellen måste hålla med", f"modellens edge ≥ {_pct(s.get('live_model_min_edge', 0.05))}",
         "Det starkaste filtret i datan: med modellens stöd ROI +20 %, CLV +2,7 pe (34 spel, 4/11)."),
        ("LIVE: jämförelsekällor", f"minst {s.get('live_min_groups', 2)}", "Pinnacle, Kalshi, DraftKings/FanDuel …"),
        ("LIVE: oddsram", _odds(llo, lhi), ""),
        ("LIVE: risk", f"max {_u(s.get('live_max_units', 5))}/spel, {s.get('live_max_per_match', 2)}/match, "
                       f"{s.get('live_max_per_day', 8)} spel och {_u(s.get('live_max_units_day', 25))} per matchdag", ""),
        ("Modellvikt", f"{s.get('nba_model_weight', 0.3):g}", "Blandas med marknaden i log-odds."),
        ("Matcher", f"inom {s.get('nba_hours_ahead', 30)} h, max {s.get('nba_max_events', 15)}", ""),
        ("US-bolag via The Odds API", f"{s.get('nba_us_fetch_window', [40, 240])[0]}–{s.get('nba_us_fetch_window', [40, 240])[1]} min före start",
         f"Andel av krediterna: {_pct(s.get('oddsapi_share_nba', 0.6))}."),
    ]
    try:
        from nhl.bot_settings import BotSettings
        n = BotSettings.load(settings_path)
        nhl = [
            ("Status", "LIVE (notiser)" if n.live_on else "av", "Skott på mål (SOG) hos Kambi-bolagen."),
            ("LIVE: edge", _pct(n.live_min_edge), ""),
            ("LIVE: högsta edge", _pct(n.live_max_edge), "Samma tak som NBA."),
            ("LIVE: modellen måste hålla med", f"modellens edge ≥ {_pct(n.live_model_min_edge)}", "Samma krav som NBA (4/11)."),
            ("LIVE: jämförelsekällor", f"minst {n.live_min_groups}", "Bovada, Pinnacle (vikt ×2), US-bolag via The Odds API."),
            ("LIVE: oddsram", _odds(n.live_odds_min, n.live_odds_max), ""),
            ("LIVE: risk", f"max {_u(n.live_max_units)}/spel, {n.live_max_per_match}/match, {n.live_max_per_day} spel och "
                           f"{_u(n.live_max_units_day)} per matchdag, högst {_pct(n.max_stake_per_match_pct)} per match", ""),
            ("LIVE: spelaren i senaste uppställningen", "ja" if n.live_require_active else "nej", ""),
            ("Gemensamt edgekrav", _pct(n.min_edge_all), f"+{_pct(n.extra_edge_without_sharp)} utan skarp/tvåsidig källa."),
            ("Oddsram", _odds(n.odds_min_all, n.odds_max_all), ""),
            ("Max oddsfall / sharp mot / med", f"{_pct(n.max_odds_drop)} / {n.sharp_against_pp:g} / {n.sharp_with_pp:g} pe (efter {n.sharp_min_age_min:g} min)", ""),
            ("Orimlig edge / konsensusavvikelse", f"{_pct(n.max_plausible_edge)} / {_pct(n.max_dev_from_consensus)}", ""),
            ("Ensidig marginal (antagen)", _pct(n.one_sided_margin), "För ensidiga priser (t.ex. Bovadas \"N+ skott\"-stege)."),
            ("Modellvikt", f"{n.model_weight:g} (minst {n.model_min_games} matcher)", "NHL-statistik: skott per 60 × istid, motstånd, hemmaplan."),
            ("Pinnacle", "på" if n.use_pinnacle else "av", f"liga {n.pinnacle_league_id}"),
            ("US-bolag via The Odds API", f"{n.us_fetch_window_min[0]:g}–{n.us_fetch_window_min[1]:g} min före start",
             f"Andel av krediterna: {_pct(n.odds_api_share)}."),
            ("Bankrulle", f"{n.bankroll:,.0f} {n.currency}".replace(",", " "), f"1u = {n.unit_value():.0f} {n.currency}."),
            ("Test-marknader (data)", "poäng, assist, mål, power play-poäng", "Kambis NHL-poäng/assist/mål och power play-poäng (minst 1/2) bokförs mot en egen modell. PP-poäng: spelarens PP-poäng per PP-minut × lagets väntade PP-minuter × andel från PP-enheten (DailyFaceoff PP1/PP2, flyttad upp/ner) × motståndarens boxplay (och omgjord PK om ordinarie boxplayspelare saknas). Power play-mål per spelare tas med om ett bolag lägger ut dem. Inga notiser."),
        ]
    except Exception as e:  # noqa: BLE001
        nhl = [("Fel", f"{type(e).__name__}: {e}", "")]
    sec = lambda rows: [{"namn": a, "varde": b, "forklaring": c} for a, b, c in rows]
    return {"Gemensamt": sec(shared), "Fotboll": sec(football), "NBA": sec(nba), "NHL": sec(nhl)}


def as_markdown(settings_path: Path) -> str:
    out = ["# Propsbot – alla parametrar", "",
           "Genereras från de värden boten använder (`python -m propsbot parametrar`).", ""]
    for sport, rows in all_params(settings_path).items():
        out += [f"## {sport}", "", "| Parameter | Värde | Förklaring |", "|---|---|---|"]
        out += [f"| {r['namn']} | {r['varde']} | {r['forklaring'].replace('|', '/')} |" for r in rows]
        out.append("")
    return "\n".join(out)
