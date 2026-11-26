# Backtest spelarmodell (skott / skott på mål), 2026-11-26

Skript: `tools/backtest_fotmob.py`, körs via `.github/workflows/backtest_fotmob.yml` (FotMob öppna JSON, cachat).
Data: 754 avslutade matcher 22/8–25/11 (PL, La Liga, Bundesliga, Serie A, Ligue 1, CL, EL, ECL).
Test: startande utespelare från 15/10 (n = 5 427 per marknad/linje). Validering: 1–14/10 (n = 919).
Mäter sannolikheter mot **utfall** (Brier, log-loss, parad t mot dagens modell). Inga odds: säger inget om hur modellen står sig mot marknaden.
Ingen skalning med Pinnacles väntade mål (finns inte historiskt), ratio = 1 för alla modeller.

## Modeller
- **M0** dagens logik (takt per framträdande, halveringstid 5, krympning 3, NB-spridning 10/6).
- **M3** lagsnitt för alla spelare.
- **M1** per 90 min × förväntade minuter. **M2** blandar in xG/xGOT (vikt 25 % / 50 %).
- **M4** M0 × motståndarens försvar (skott/skott på mål släppta, krympt) × hemmaplan, elasticitet 0,5 / 1,0.
- **\*kal** walk-forward-omkalibrering logit(p') = a + b·logit(p), anpassad på valideringsperioden.

## Resultat (test, parad t mot M0, positivt = bättre)
| Marknad / linje | M3 lagsnitt | M1 minuter | M2 xG 0,25 | M2 xG 0,5 | M4 e0,5 | M4 e1,0 | M0 kal | M4 kal e0,5 |
|---|---|---|---|---|---|---|---|---|
| SOT över 0,5 | −13,7 | −0,8 | −0,9 | −2,2 | **+4,6** | +2,8 | +1,0 | +3,3 |
| SOT över 1,5 | −7,8 | −1,5 | +0,5 | −0,1 | **+3,6** | +2,0 | −2,2 | −0,6 |
| Skott över 0,5 | −19,7 | −0,9 | +0,7 | −0,3 | **+6,7** | +5,2 | +3,0 | +5,4 |
| Skott över 1,5 | −21,8 | −2,0 | −0,3 | −1,7 | +6,0 | +3,8 | +6,6 | **+8,3** |
| Skott över 2,5 | −15,4 | −3,5 | −1,8 | −2,9 | **+4,3** | +2,5 | −1,4 | +2,3 |

Brier, M0 → M4 e0,5: SOT>0,5 0,1917→0,1900; skott>0,5 0,2151→0,2126; skott>1,5 0,1790→0,1765 (0,1750 omkalibrerad).

## Slutsatser
1. **Spelarens egen takt bär information** (M3 mycket sämre överallt).
2. **Minuter och xG tillför inget** utöver dagens skott-/SOT-takt (M1, M2 inte bättre, ofta sämre).
3. **Motståndare + hemmaplan förbättrar signifikant** (t 2–7) men effekten är liten (Brier ca 0,002). Produktionen fångar redan det via Pinnacles väntade mål (ratio^elasticitet), så detta bevisar inte någon ny edge.
4. **M0 överskattar låga linjer**: SOT>0,5 medel-p 0,335 mot utfall 0,302; skott>0,5 0,651 mot 0,601; skott>1,5 0,344 mot 0,308. Höga linjer är välkalibrerade.
5. Omkalibrering mot **utfall** hjälper på skott över 0,5 och 1,5 men skadar på de sällsynta linjerna (SOT>1,5, skott>2,5). Anpassa den per linje och bara där biasen är stor.

## Vad detta INTE visar
- Att modellen slår Unibet. Det kräver minst ~150 avgjorda ben med både modellens och marknadens p samt CLV mot skarp stängning. Idag finns 51 avgjorda (konsensusspåret, 25/11–26/11): utfall 37,3 %, konsensus-p 43,6 %, marknads-p 34,3 %, modell-p 40,0 %, CLV −5,3 pp. Alltför litet för slutsats, men konsensusens p är för hög (troligen för låg antagen marginal, 7 %).
- Inga trösklar ändras på detta underlag (CLAUDE.md regel 2).

## Förslag (kräver godkännande, modellen förblir i testläge)
1. Ankra modellens nivå mot **utfall** (omkalibrering per marknad och linje, walk-forward) i stället för mot marknaden (nuvarande "nivåavvikelse mot marknaden, dras bort" gör modellen beroende av Unibets nivå).
2. Logga modellens p, marknadens p och utfall för alla ben, så att jämförelsen mot marknaden når 150 avgjorda.
3. Kalibrera konsensusens antagna marginal mot avgjorda ben innan konsensusspåret får påverka något.
