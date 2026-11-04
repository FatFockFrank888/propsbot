# Propsbot – alla parametrar

Genereras från de värden boten använder (`python -m propsbot parametrar`).

## Gemensamt

| Parameter | Värde | Förklaring |
|---|---|---|
| Spelbara bolag | svenskaspel, betmgm, expekt, atg, unibet | Bara Kambi-bolag. Paf och LeoVegas läses bara för att mäta marginalen. |
| Minsta edge (alla spel) | 5 % | edge = sannolikhet × odds − 1. Gäller alla marknader och sporter. |
| Oddsram | 1,60–6,00 | Inga spel utanför. |
| Max oddsfall | 3 % | Inget spel om bästa oddset fallit mer än så från det högsta vi sett (för sent). |
| Sharp money mot oss | 2 procentenheter | Inget spel om den skarpa referensen (Pinnacle/konsensus) rört sig så mycket mot oss efter 30 min. |
| Sharp money med oss | 1.5 procentenheter | Markeras i notisen (⬆). |
| Orimlig edge | 25 % | Större edge = nästan alltid fel linje, olika regler eller spelaren spelar inte. Inte spelbart. |
| Ett spel per spelare och match | ja, över allt | Över alla marknader, linjer, sidor (över/under), bolag och körningar. Störst edge vinner; det som redan skickats står kvar. |
| Över eller under | den sida som har EV+ | Båda sidor prövas på samma krav. Under kräver en tvåsidig eller skarp referens (annars är marginalen på undersidan okänd). |
| Notiser | bara LIVE-spel | En notis per spel, aldrig två på samma spelare i samma match. Misslyckad notis skickas igen nästa körning (före start). |
| Unit | 1u = 0,2 % av bankrullen | Insats 1–10u efter ¼ Kelly (taket 10u = 2 %). |
| Skuggspel | ≥ 2 % edge, stoppat av en regel | Bokförs och rättas för att se om reglerna kostar eller sparar pengar. Ingen notis. |

## Fotboll

| Parameter | Värde | Förklaring |
|---|---|---|
| Status | LIVE (notiser) | football_live i settings.json. Påslaget 2026-11-04 på användarens begäran. Spelen är regelspelen (alla gemensamma krav); risktak: högst 10u per spel och 5 % per match. |
| LIVE: högsta insats | 2u per spel | Fotbollen saknar historik med edge och CLV. Höjs när ca 50 avgjorda spel visar positiv CLV. |
| Marknader som spelas | shots_on_target | Övriga marknader används bara för att mäta Kambis marginal. |
| Edgekrav per marknad (före gemensamt krav) | shots 2 %, shots_on_target 2 %, goal 4 %, assist 4 % | Gemensamma kravet 5 % gäller ovanpå. |
| Utan Pinnacle/tvåsidig källa | +3 % edge, minst 3 källor |  |
| Försiktig skottmarginal | k ≥ 1.2 | Edgen måste hålla även med en försiktig marginal, annars skuggspel. |
| Kambi mot Pinnacle (målförväntan) | max 10 % skillnad | Annars hoppas matchen över (olika regler, gamla linjer). |
| Spelarmodell | test, vikt 0.1 | ESPN-statistik. I läget test bokförs modellens spel separat (Modelltest). |
| CLV-signal | edge ≥ 1 %, förväntad CLV ≥ 2, Pinnacle ≥ +1.5 | Släpper igenom ben som bara stoppades av edgekravet när Pinnacle rör sig åt vårt håll. |
| Max odds-ålder | 180 s |  |
| Max avvikelse från konsensus | 18 % |  |
| Ligor | 35 st | England / Premier League, England / The Championship, England / Championship, Spain / La Liga, Spain / LaLiga, Germany / Bundesliga, Germany / 2. Bundesliga, Italy / Serie A, Italy / Serie B, France / Ligue 1, France / Ligue 2, Netherlands / Eredivisie, Portugal / Liga Portugal, Portugal / Primeira Liga, Belgium / Pro League, Belgium / Jupiler, Scotland / Premiership, Turkey / Süper Lig, Turkey / Super Lig, Denmark / Superliga, Norway / Eliteserien, Sweden / Allsvenskan, Austria / Bundesliga, Switzerland / Super League, Greece / Super League, USA / MLS, Brazil / Serie A, Argentina / Liga Profesional, Champions League, Europa League, Conference League, Australia / A-League, Brazil / Brasileirao, Brazil / Copa do Brasil, Mexico / Liga MX |
| Fouls (test) | på, minst 5 % edge | Egen modell (ESPN), domarfaktor ±15 %. Bara datainsamling. |
| Kort (test) | på, datainsamling | "To Get a Card" hos Kambi. Egen modell: spelarens kort per match (ESPN) × domarens stränghet. Bara datainsamling. |
| Parlays | på, max 3 ben, minst 5 % edge per ben | Notiser för parlays: av. |

## NBA

| Parameter | Värde | Förklaring |
|---|---|---|
| Status | LIVE (notiser) |  |
| LIVE: edgekrav per marknad | points 5 %, threes 5 %, assists 5 %, rebounds 5 % | Marknader som saknas här (steals, blocks, PRA …) spelas inte live. |
| LIVE: högsta edge | 15 % | Större edge slog inte stängningen i datan (oftast fel i linje/modell). |
| LIVE: modellen måste hålla med | modellens edge ≥ 5 % | Det starkaste filtret i datan: med modellens stöd ROI +20 %, CLV +2,7 pe (34 spel, 4/11). |
| LIVE: jämförelsekällor | minst 2 | Pinnacle, Kalshi, DraftKings/FanDuel … |
| LIVE: oddsram | 1,60–3,00 |  |
| LIVE: risk | max 5u/spel, 2/match, 8 spel och 25u per matchdag |  |
| Modellvikt | 0.3 | Blandas med marknaden i log-odds. |
| Matcher | inom 30 h, max 15 |  |
| US-bolag via The Odds API | 40–240 min före start | Andel av krediterna: 45 %. |

## NHL

| Parameter | Värde | Förklaring |
|---|---|---|
| Status | LIVE (notiser) | Skott på mål (SOG) hos Kambi-bolagen. |
| LIVE: edge | 5 % |  |
| LIVE: högsta edge | 15 % | Samma tak som NBA. |
| LIVE: modellen måste hålla med | modellens edge ≥ 5 % | Samma krav som NBA (4/11). |
| LIVE: jämförelsekällor | minst 2 | Bovada, Pinnacle (vikt ×2), US-bolag via The Odds API. |
| LIVE: oddsram | 1,60–3,00 |  |
| LIVE: risk | max 5u/spel, 2/match, 8 spel och 25u per matchdag, högst 5 % per match |  |
| LIVE: spelaren i senaste uppställningen | ja |  |
| Gemensamt edgekrav | 5 % | +3 % utan skarp/tvåsidig källa. |
| Oddsram | 1,60–6,00 |  |
| Max oddsfall / sharp mot / med | 3 % / 2 / 1.5 pe (efter 30 min) |  |
| Orimlig edge / konsensusavvikelse | 25 % / 18 % |  |
| Ensidig marginal (antagen) | 8 % | För ensidiga priser (t.ex. Bovadas "N+ skott"-stege). |
| Modellvikt | 0.3 (minst 8 matcher) | NHL-statistik: skott per 60 × istid, motstånd, hemmaplan. |
| Pinnacle | på | liga 1456 |
| US-bolag via The Odds API | 40–240 min före start | Andel av krediterna: 25 %. |
| Bankrulle | 10 000 SEK | 1u = 20 SEK. |
| Test-marknader (data) | poäng, assist, mål | Kambis NHL-poäng/assist/mål bokförs mot en egen modell. Inga notiser. |

