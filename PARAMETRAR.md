# Propsbot – alla parametrar

Genereras från de värden boten använder (`python -m propsbot parametrar`).

## Gemensamt

| Parameter | Värde | Förklaring |
|---|---|---|
| Spelbara bolag | svenskaspel, betmgm, expekt, atg, unibet | Bara Kambi-bolag. Paf och LeoVegas läses bara för att mäta marginalen. |
| Minsta edge (alla spel) | 5 % | edge = sannolikhet × odds − 1. Gäller alla marknader och sporter. |
| Oddsram | 1,40–6,00 | Inga spel utanför. |
| Max oddsfall | 3 % | Inget spel om bästa oddset fallit mer än så från det högsta vi sett (för sent). |
| Sharp money mot oss | 2 procentenheter | Inget spel om den skarpa referensen (Pinnacle/konsensus) rört sig så mycket mot oss efter 30 min. |
| Sharp money med oss | 1.5 procentenheter | Markeras i notisen (⬆). |
| Topp 5 som notis | ja, en per spel | Bara LIVE-spel (klarar LIVE-reglerna). När ett spel för första gången hamnar bland de fem starkaste (samma ranking som fliken Topp 5) skickas en notis 🏆 med rank, odds, spela från, edge, modell, styrka och insats. Märkt LIVE eller data. Inte inom 10 min före start. |
| Lagnyheter (varje skanning) | NBA: ESPN skadelista · fotboll: startelvan | Out/doubtful, ute eller inte i laget/startelvan = inget spel; questionable markeras. Öppna LIVE-spel kontrolleras igen före start och ger en notis (📰) om spelarens status ändras – och i NBA även när en lagkamrat (minst 15 min/match) blir out efter att spelet lades, med modellens nya speltid, väntat värde och edge vid vårt odds. |
| Orimlig edge | 25 % | Större edge = nästan alltid fel linje, olika regler eller spelaren spelar inte. Inte spelbart. |
| Ett spel per spelare och match | ja, över allt | Över alla marknader, linjer, sidor (över/under), bolag och körningar. Störst edge vinner; det som redan skickats står kvar. |
| Över eller under | den sida som har EV+ | Båda sidor prövas på samma krav. Under kräver en tvåsidig eller skarp referens (annars är marginalen på undersidan okänd). |
| Notiser | bara LIVE-spel | En notis per spel, aldrig två på samma spelare i samma match. Misslyckad notis skickas igen nästa körning (före start). |
| Unit | 1u = 0,2 % av bankrullen | Insats 1–10u efter ¼ Kelly (taket 10u = 2 %). |
| Skuggspel | ≥ 2 % edge, stoppat av en regel | Bokförs och rättas för att se om reglerna kostar eller sparar pengar. Ingen notis. |

## Fotboll

| Parameter | Värde | Förklaring |
|---|---|---|
| Status | bara datainsamling (inga notiser) | football_live i settings.json. Pausat 2026-11-07 (on hold) tills vi hittar en skarp källa för fotbollsprops – Kambis marginal ~20 % och ingen referens. Påslaget 2026-11-04. Spelen är regelspelen (alla gemensamma krav); risktak: högst 5u per spel och 5 % per match. |
| LIVE: insats | ¼ Kelly × 0.5, högst 5u per spel | Insatsen följer styrkan (edge och odds) som i NBA, men i halv storlek eftersom fotbollen saknar historik med edge och CLV. Går automatiskt upp till full ¼ Kelly när 50 spel med stängning visar positiv CLV (t-gräns som tål upprepad prövning, se nedan), med en notis. |
| Automatisk uppgradering | 50 spel, CLV > 0, t ≥ ~3,7 vid 50 spel (~3,0 vid 500) | Gränsen är tidsoberoende (Robbins, α 0.1 delat på 2 marknader): en marknad utan verklig CLV uppgraderas inte av slump fast den prövas vid varje skanning. Prövas vid varje skanning för fotbollsprops (halv -> full insats) och sides/totals (data -> LIVE med notiser, ¼ Kelly upp till 5u). Vänder CLV till negativt över minst 30 spel går marknaden tillbaka till försiktigt läge. |
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
| Sides/totals: status | datainsamling (inga notiser) | 1X2, mål över/under och asiatiskt handikapp hos Kambi mot Pinnacle utan marginal (start 5/11). LIVE slås på när ca 50 spel visar att vi slår Pinnacles stängning. |
| Sides/totals: marknader | 1x2, total, ah, corners, cah, corners_home, corners_away | 1X2, mål över/under och asiatiskt handikapp – halvlinjer (x,5) och asiatiska linjer: hela (push = insatsen tillbaka) och kvarts (halva insatsen på var närliggande linje). 90 minuter + tillägg. |
| Startelvor (props) | krävs | Används när den finns: har ESPN matchen är props spelbara först när båda elvorna är kända (ca 1 h före avspark, senast 55 min före) och spelaren måste starta. Saknar ESPN matchen (mindre ligor) bortser vi från startelvan. |
| Startelvor (sides/totals) | väntar inte | Av sedan 7/11: Pinnacle prisar redan in laguppställningar och nyheter. Spärren stoppade 138 skuggspel som slog Pinnacles stängning med +2 pe i snitt. Startelvan syns ändå i loggen och sharp money-spärren gäller. |
| Skarpa referenser (sides) | Pinnacle + Smarkets (börs) | Smarkets öppna API: köp/sälj-mitten när spreaden är högst 4 pe. Finns båda är facit snittet och Smarkets måste också visa värde. Hörnor – total, lagtotal och handikapp (Kambis 3-vägs = tvåvägs halvlinjer) – jämförs bara mot Smarkets (Pinnacle saknar dem), mot det försiktiga priset (mitten minus halva spreaden) och med +1 % extra edge; ett hörnspel och ett målspel per match; rättas mot ESPN:s matchprotokoll. Spelarprops, fouls och målskytt hos Smarkets saknar likviditet – används inte. |
| Sides/totals: edgekrav | 3 % (alternativ Pinnacle-linje +1 %) | Lägre än 5 % eftersom referensen är Pinnacles huvudlinje (skarpast i världen): mot den är 3 % en verklig edge. 1 %–3 % bokförs som Sides-skugga för att mäta nivån. |
| Sides/totals: högsta edge | 10 % | Större edge mot Pinnacle = nästan alltid gammal linje, nyhet (uppställning/skada) eller fel match. Bokförs som skugga. |
| Sides/totals: oddsram | 1,40–6,00 | Bredare än props uppåt så att oavgjort och små skrällar kommer med. |
| Sides/totals: Pinnacles insatsgräns | minst 500; under 2000 krävs +1 % edge | Gränsen visar hur skarp Pinnacles linje är. Låg gräns (ofta lägre divisioner) = svagare referens -> högre krav. |
| Sides/totals: mindre ligor | på – alla Kambi-ligor (ej esport) inom 12 h före avspark, max 150 matcher | Lägre divisioner och mindre ligor har oftare felsatta linjer. Bara huvudmarknaderna hämtas (snabbt). Rättas mot ESPN:s samlade resultattavla. |
| Sides/totals: övrigt | max oddsfall 3 %, sharp money mot oss 2 pe, ett spel per match, inom 24 h före avspark, max 3u | Samma spärrar som övriga sporter. Rättas mot ESPN:s slutresultat. |

## NBA

| Parameter | Värde | Förklaring |
|---|---|---|
| Status | LIVE (notiser) |  |
| LIVE: edgekrav per marknad | points 5 %, threes 5 %, assists 5 %, rebounds 5 % | Marknader som saknas här (steals, blocks, PRA …) spelas inte live. |
| LIVE: högsta edge | 15 % | Större edge slog inte stängningen i datan (oftast fel i linje/modell). |
| LIVE: modellen | får inte säga emot (modellens edge ≥ 5 % om den har en rad); krävs för points | 12/11, 1 378 spel: assist/returer/trepoängare utan modellrad slog stängningen med +2,8 pe (t 11,6); poäng över utan modellens stöd gav −18 %. Spel med modellens stöd väljs först. |
| LIVE: jämförelsekällor | minst 2, varav Pinnacle | Pinnacle, Kalshi, DraftKings (via ESPN), SportsGameOdds, The Odds API |
| LIVE: oddsram | 1,60–3,00 |  |
| LIVE: risk | max 5u/spel, 2/match, 16 spel och 40u per matchdag |  |
| Modellvikt | 0.3 × dq | Blandas med marknaden i log-odds. dq = datakvalitet 0,2–1 (antal matcher i underlaget / 15): tunt underlag -> marknaden väger mer. Halveras när modell och marknad skiljer mycket. |
| Brier modell / marknad | visas under Resultat | Mäter om modellen slår marknadens egen sannolikhet på avgjorda spel (lägre = bättre). |
| Matcher | inom 30 h, max 15 |  |
| US-bolag via The Odds API | 40–240 min före start | Andel av krediterna: 60 %. |

