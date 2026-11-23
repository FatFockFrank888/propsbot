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

    from .tiers import cfg as _tcfg
    from .oddsvakt import cfg as _ocfg
    t = _tcfg(s)
    ov = _ocfg(s)
    tiers = [
        ("A/B/C Tier", "på" if t["tiers_on"] else "av",
         "Ersätter Official Bets (18/11). Varje bokfört spel (LIVE, regelspel, skuggspel; props och sides; fotboll och NBA) hamnar "
         "i den högsta nivå det klarar. Ett spel per spelare och match. Nivåerna rättas var för sig (fliken Tier-resultat)."),
        ("C Tier", f"edge ≥ {_pct(t['tier_c_min_edge'])}, odds {_odds(*t['tier_c_odds'])}",
         "Edge och statistik talar för spelet. Inga hårda spärrar (skadelista out/doubtful, startelva, orimlig edge, avvikande pris) "
         f"och inget sharp money mot oss. Edge över {_pct(t['tier_max_edge'])} räknas inte. Bara bokföring: visar om kraven för B/A är för skarpa."),
        ("B Tier", f"C + edge {_pct(t['tier_b_min_edge'])}–{_pct(t['tier_b_max_edge'])}, odds {_odds(*t['tier_b_odds'])}",
         "Fokus på CLV: Pinnacle (eller DraftKings där Pinnacle saknar marknaden) som referens, oddset har inte fallit, ingen annan skarp "
         "källa säger emot, Pinnacles gräns räcker, förväntad CLV ≥ 0 där den finns. Spelas, ingen notis."),
        ("A Tier", f"B + alla parametrar, odds {_odds(*t['tier_a_odds'])}",
         "NBA: klarar LIVE-kraven (se NBA nedan). Fotboll: klarar alla regler (regelspel). Spelas."),
        ("Notiser för nya spel", " och ".join(t["tier_notify"]) + " Tier" + (f" · kanal {s['tier_ntfy_topic']}" if s.get("tier_ntfy_topic") else ""),
         "En notis per nytt spel i nivån (rubrik \"A TIER …\" / \"B TIER …\") i en egen ntfy-kanal (tier_ntfy_topic). C ger aldrig notis. "
         "Övriga notiser (nyheter, uppgraderingar) går till den vanliga kanalen."),
        ("Livenotiser (Mina spel)", s.get("live_ntfy_topic") or "vanliga kanalen",
         "Plingarna under match för dina spel (mål, straff, rött kort, returer, poäng, vunnet/förlorat) i en egen kanal (live_ntfy_topic), "
         "så att den kan ha ett eget ljud i ntfy-appen."),
        ("Insats (A/B)", f"flat 1–3u, 1u = {_pct(t['tier_unit'])} av kassan",
         f"1u standard. 2u high: edge ≥ {_pct(t['tier_2u_edge'])}. 3u maxbet: edge {_pct(t['tier_3u_edge'])}–{_pct(t['tier_3u_max_edge'])} "
         "med Pinnacle som referens och sharp money med oss (högre edge är oftast fel i linjen). Ingen Kelly."),
        ("Tak (A/B)", "inga", "Inga dags- eller matchbudgetar (18/11): du väljer själv vilka spel du tar. Alla A- och B-spel räknas som spelade."),
        ("Odds Alert (oddsvakt)", ("på" if ov["oddsvakt_on"] else "av") + f", läsning var {ov['oddsvakt_poll_s']} s, "
         f"{ov['oddsvakt_bekrafta']} läsningar i rad, högst en notis per spel och {ov['oddsvakt_cooldown_s'] // 60} min",
         "Bevakar Kambi-oddset för A/B-spelen som fått notis (och dina egna bevakningar från webbsidan) fram till start. "
         "✅ BACK UP när oddset är tillbaka på lägsta oddset, ❌ GONE när det fallit under eller spelet är borta. "
         "Lägsta odds = max(spela från, odds som ger kravet på edge mot den senaste skarpa sannolikheten). "
         "Spel du tagit bevakas inte. Egen Telegram-chatt telegram_chats.oddsvakt "
         + ("(satt)." if (s.get("telegram_chats") or {}).get("oddsvakt") else "(saknas: går till nivåchatten).")),
    ]
    shared = tiers + [
        ("Spelbara bolag", ", ".join(s["playable_books"]), "Bara Kambi-bolag. Paf och LeoVegas läses bara för att mäta marginalen."),
        ("Minsta edge (alla spel)", _pct(s.get("min_edge_all", 0.05)), "edge = sannolikhet × odds − 1. Gäller alla marknader och sporter."),
        ("Oddsram", _odds(lo, hi), "Inga spel utanför."),
        ("Max oddsfall", _pct(s.get("max_odds_drop", 0.03)), "Inget spel om bästa oddset fallit mer än så från det högsta vi sett (för sent)."),
        ("Sharp money mot oss", f"{s.get('sharp_against_pp', 2.0):g} procentenheter",
         "Inget spel om den skarpa referensen (Pinnacle/konsensus) rört sig så mycket mot oss efter 30 min."),
        ("Sharp money med oss", f"{s.get('sharp_with_pp', 1.5):g} procentenheter", "Markeras i notisen (⬆)."),
        ("Topp 5 som notis", "nej (14/11)",
         "Topp 5 är alltid LIVE-spel som redan fått en LIVE-notis, så en egen topp 5-notis blev en dubblett. Listan finns kvar i fliken Topp 5."),
        ("Lagnyheter (varje skanning)", "NBA: ESPN skadelista · fotboll: startelvan",
         "Out/doubtful, ute eller inte i laget/startelvan = inget spel; questionable markeras. Öppna LIVE-spel kontrolleras igen före start och ger en notis (📰) om spelarens status ändras – och i NBA även när en lagkamrat (minst 15 min/match) blir out efter att spelet lades, med modellens nya speltid, väntat värde och edge vid vårt odds."),
        ("Orimlig edge", _pct(s.get("max_plausible_edge", 0.25)), "Större edge = nästan alltid fel linje, olika regler eller spelaren spelar inte. Inte spelbart."),
        ("Ett spel per spelare och match", "ja, över allt",
         "Över alla marknader, linjer, sidor (över/under), bolag och körningar. Störst edge vinner; det som redan skickats står kvar."),
        ("Över eller under", "den sida som har EV+",
         "Båda sidor prövas på samma krav. Under kräver en tvåsidig eller skarp referens (annars är marginalen på undersidan okänd)."),
        ("Notiser", ("nya spel i " + "/".join(t["tier_notify"]) + " Tier") if t["tiers_on"] else "bara LIVE-spel", "En notis per spel, aldrig två på samma spelare i samma match. Misslyckad notis skickas igen nästa körning (före start)."),
        ("Unit (data/LIVE-bokföringen)", "1u = 0,2 % av bankrullen, 1–10u efter styrkan",
         "LIVE-insatsen följer styrkan (samma tal som Topp 5: edge upp till 15 + halva modellens edge + sharp money + 1). "
         "Styrka ≤ 7 = 1u, 9,5 = 3u, 11 = 4u, 14 = 6u, 17 = 8u, ≥ 20 = 10u. 10u (2 %) = maxinsats, ett av de starkaste spelen. "
         "Radarn visar samma skala. Data- och skuggbokföringen behåller ¼ Kelly (taket 10u)."),
        ("Skuggspel", "≥ 2 % edge, stoppat av en regel", "Bokförs och rättas för att se om reglerna kostar eller sparar pengar. Ingen notis."),
    ]
    football = [
        ("Hörnmodell (test)", "på" if s.get("corners_enabled", True) else "av",
         "Bara bokföring (bokforing_hornor_test.json), ingen notis, inte i A/B/C. Underlag: football-data.co.uk (hörnor per match, 17 ligor, "
         "innevarande + förra säsongen). Väntade hörnor = marknadens förväntan ur Pinnacles 1X2 och mål 2,5 × lagens egna hörnor "
         f"utöver oddsen (vikt 0,5, halveringstid {s.get('corners_half_life_days', 120)} d, krympning {s.get('corners_shrink_k', 6.0):g} matcher), "
         "negativ binomial per lag. Holdout 45 d: Brier 0,2227 mot 0,2258 (bara lagdata)."),
        ("Hörnmodell: testspel", f"edge {_pct(s.get('corners_min_edge', 0.05))}–{_pct(s.get('corners_max_edge', 0.25))} mot modellen, "
         f"odds {_odds(*s.get('corners_odds', [1.40, 6.50]))}, ett per match",
         "Unibets hörnor totalt, lagens hörnor och hörnhandikapp. Kambis pris utan marginal sparas (p_marknad) för att mäta modellen mot marknaden."),
        ("Status", "LIVE (notiser)" if s.get("football_live") else "bara datainsamling (inga notiser)",
         "football_live i settings.json. Pausat 2026-11-07 (on hold) tills vi hittar en skarp källa för fotbollsprops – Kambis marginal ~20 % och ingen referens. Påslaget 2026-11-04. Spelen är regelspelen "
         "(alla gemensamma krav); risktak: högst 10u per spel och 5 % per match."),
        ("LIVE: insats", f"styrka 1–10u × {s.get('football_kelly_scale', 0.5):g}, högst {s.get('football_live_max_units', 10)}u per spel",
         "Insatsen följer styrkan som i NBA, men i halv storlek eftersom fotbollen saknar historik "
         "med edge och CLV. Går automatiskt upp till full skala när 50 spel med stängning visar positiv CLV (t-gräns som tål upprepad prövning, se nedan), med en notis."),
        ("Automatisk uppgradering", f"{s.get('graduation_min_bets', 50)} spel, CLV > 0, t ≥ ~3,7 vid 50 spel (~3,0 vid 500)",
         "Gränsen är tidsoberoende (Robbins, α " + f"{s.get('graduation_alpha', 0.10):g}" + " delat på 2 marknader): en marknad utan verklig CLV "
         "uppgraderas inte av slump fast den prövas vid varje skanning. Prövas vid varje skanning för fotbollsprops (halv -> full insats) och sides/totals (data -> LIVE med notiser, insats 1–10u efter styrkan). "
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
        ("Startelvor (props)", "krävs" if s.get("lineup_required", True) else "av",
         f"Används när den finns: har ESPN matchen är props spelbara först när båda elvorna är kända (ca 1 h före "
         f"avspark, senast {s.get('lineup_fallback_minutes', 55)} min före) och spelaren måste starta. Saknar ESPN matchen "
         "(mindre ligor) bortser vi från startelvan."),
        ("Startelvor (sides/totals)", "väntar" if s.get("sides_lineup_gate", False) else "väntar inte",
         "Av sedan 7/11: Pinnacle prisar redan in laguppställningar och nyheter. Spärren stoppade 138 skuggspel som slog "
         "Pinnacles stängning med +2 pe i snitt. Startelvan syns ändå i loggen och sharp money-spärren gäller."),
        ("Skarpa referenser (sides)", "Pinnacle + Smarkets (börs)",
         "Smarkets öppna API: köp/sälj-mitten när spreaden är högst 4 pe. Finns båda är facit snittet och Smarkets måste "
         "också visa värde. Hörnor – total, lagtotal och handikapp (Kambis 3-vägs = tvåvägs halvlinjer) – jämförs bara mot Smarkets "
         "(Pinnacle saknar dem), mot det försiktiga priset (mitten minus halva spreaden) och med +1 % extra edge; "
         "ett hörnspel och ett målspel per match; rättas mot ESPN:s matchprotokoll. Spelarprops, fouls och målskytt hos Smarkets saknar likviditet – används inte."),
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
         f"ett spel per match, inom {s.get('sides_max_hours', 24)} h före avspark, insats 1–10u efter styrkan (max {s.get('sides_max_units', 10)}u)",
         "Samma spärrar som övriga sporter. Rättas mot ESPN:s slutresultat."),
        ("Sides/totals: rättning", "ESPN, FotMob, LiveScore, goal-api" + (", SportScore" if __import__("os").environ.get("SPORTSCORE_API_KEY") else "") + (", API-Football" if __import__("os").environ.get("API_FOOTBALL_KEY") else ", API-Football (av: ingen nyckel)")
         + "; void efter 48 h vid uppskjuten/inställd/avbruten match",
         "Ser en källa att matchen är uppskjuten, inställd eller avbruten och den inte spelats inom 48 h från avspark blir spelet "
         "struket (void, insatsen tillbaka). Matcher som ingen källa täcker rättas för hand i rattning_manuell.json (repot)."),
    ]
    nba = [
        ("Status", "LIVE (notiser)" if s.get("live_on", True) and s.get("nba_enabled", True) else "av", ""),
        ("LIVE: edgekrav per marknad", ", ".join(f"{k} {_pct(v)}" for k, v in live_th.items()),
         "Marknader som saknas här (steals, blocks, PRA …) spelas inte live."),
        ("LIVE: högsta edge", _pct(s.get("live_max_edge", 0.15)), "Större edge slog inte stängningen i datan (oftast fel i linje/modell)."),
        ("LIVE: modellen", f"får inte säga emot (modellens edge ≥ {_pct(s.get('live_model_min_edge', 0.05))} om den har en rad); "
                           f"krävs för {', '.join(s.get('live_model_required_markets', ['points']))}",
         "12/11, 1 378 spel: assist/returer/trepoängare utan modellrad slog stängningen med +2,8 pe (t 11,6); "
         "poäng över utan modellens stöd gav −18 %. Spel med modellens stöd väljs först."),
        ("LIVE: jämförelsekällor", f"minst {s.get('live_min_groups', 2)}" + (", varav Pinnacle" if s.get('live_require_sharp', True) else ""), "Pinnacle, Kalshi, DraftKings (via ESPN), SportsGameOdds, The Odds API"),
        ("LIVE: oddsram", _odds(llo, lhi), ""),
        ("LIVE: risk", f"max {_u(s.get('live_max_units', 10))}/spel i LIVE-bokföringen; inga tak per match eller dag",
         "Taken togs bort 18/11 (du väljer själv). Insatsen du spelar är nivåernas flat 1–3u."),
        ("Modellen: kalibrering", "automatisk, per marknad, prövad framåt",
         "Alla ben modellen räknar på loggas och rättas (inte bara de som bokas). Varje körning prövas tre varianter på de "
         "nyaste avgjorda benen: marknaden, kalibrerad marknad och marknad + modellens avvikelser. Modellen får vikt bara "
         "om den slår marknaden spel för spel (t ≥ 2, minst 150 testben); vikten krymps då efter hur överkonfident den är. "
         "Modelltestet bokar bara på marknader där modellen har förtjänat vikt (20/11: 1 143 spel visade ingen vikt)."),
        ("Skuggspel", f"edge ≥ {_pct(s.get('nba_shadow_min_edge', 0.04))} som stoppats av en regel",
         "Golvet höjdes från 2 % till 4 % (20/11): 1 036 skuggspel på 2–4 % gav ROI +0,3 % och CLV +0,4. "
         "Marknadens och modellens träffsäkerhet följs i kalibreringsloggen, som har alla ben."),
        ("Brier modell / marknad", "visas under Resultat", "Mäter om modellen slår marknadens egen sannolikhet på avgjorda spel (lägre = bättre)."),
        ("Matcher", f"inom {s.get('nba_hours_ahead', 30)} h, max {s.get('nba_max_events', 15)}", ""),
        ("US-bolag via The Odds API", f"{s.get('nba_us_fetch_window', [40, 240])[0]}–{s.get('nba_us_fetch_window', [40, 240])[1]} min före start",
         f"Andel av krediterna: {_pct(s.get('oddsapi_share_nba', 0.6))}."),
        ("Sides/totals", ("på" if s.get("nba_sides_enabled", True) else "av") + " – moneyline, spread, totala poäng mot Pinnacle",
         "Hela matchen inkl. förlängning. Pinnacle utan marginal är facit; samma regler som fotbollens sides (insatsgräns, "
         "alternativ linje +1 % edge, oddsfall, sharp money, ett spel per match). Inga extra anrop: priserna finns i props-svaren."),
        ("Sides/totals: edge", f"{_pct(s.get('nba_sides_min_edge', 0.03))}–{_pct(s.get('nba_sides_max_edge', 0.15))}",
         "Under = skuggspel (från 1 %). Över = nästan alltid gammal linje eller nyhet."),
        ("Sides/totals: oddsram", _odds(*s.get("nba_sides_odds_window", [1.40, 6.50])), "Nivåerna (A/B/C) har sina egna oddsramar ovanpå."),
        ("Sides/totals: utklassning", f"över på totalen stoppas vid risk > {_pct(s.get('nba_sides_blowout_max', 0.40))}",
         "P(|marginal| > 15) ur Pinnacles spread (marginal ~ Normal(spread, 12,5)). 40 % ≈ spread 11,5: tempot går ner och startarna sätter sig."),
    ]
    sec = lambda rows: [{"namn": a, "varde": b, "forklaring": c} for a, b, c in rows]
    return {"Gemensamt": sec(shared), "Fotboll": sec(football), "NBA": sec(nba)}


def as_markdown(settings_path: Path) -> str:
    out = ["# Propsbot – alla parametrar", "",
           "Genereras från de värden boten använder (`python -m propsbot parametrar`).", ""]
    for sport, rows in all_params(settings_path).items():
        out += [f"## {sport}", "", "| Parameter | Värde | Förklaring |", "|---|---|---|"]
        out += [f"| {r['namn']} | {r['varde']} | {r['forklaring'].replace('|', '/')} |" for r in rows]
        out.append("")
    return "\n".join(out)
