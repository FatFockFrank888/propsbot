# Kvantrapport NBA, 2026-11-26 (docs/PLAN.md fas 7)

Data: grenen `data` 26/11 (`nba_modelltest.json` 1 214 rader, `tiers.json` 1 209 spel). Körning:
`python tools/quant_report.py --ledger nba_modelltest.json --tiers tiers.json`. Ingen parameter är ändrad.

## Tolkning

1. **Marknaden är svår att slå på utfall.** Ingen variant slår marknadens p på osedd data (log-loss poolad 0,6868).
   Bokförd slutlig p (modell 0,3 × dq i logit + marknad) är 0,0055 sämre. Rå modell är klart sämre (+0,086).
   Platt på marknaden hjälper inte, så marknadens nivå är redan rätt för NBA.
2. **Urvalet fungerar ändå:** CLV mot skarp stängning är +0,45 pe (95 % CI +0,08 … +0,84, n = 594).
   Edgen kommer från att hitta priser som avviker, inte från en bättre sannolikhet.
3. **Modellen har information, men lite.** Modellens avvikelse mot marknaden förutsäger stängningens rörelse
   (korrelation +0,19, t ≈ 4,7). Lutningen 0,075 betyder att marknaden i snitt rör sig 7,5 % av vägen mot modellen.
   Det motsvarar en modellvikt på cirka 0,08 i logit, mot 0,3 × dq i dag (`nba_model_weight`).
   **Förslag (kräver beslut):** sänk vikten eller låt stacken (`p_stack`) ta över, eftersom den skattar vikten ur data.
   Bägge kräver CLV + ROI enligt CLAUDE.md, och n = 414 i test räcker för en skuggjämförelse.
4. **Residual med mål = stängning** ligger nära marknaden (+0,0004) och är den bästa inlärda varianten.
   Residual mot utfall överanpassar (+0,008). Det stöder att träna mot stängningen och vänta med LightGBM.
5. **NB-form:** r̂ points 8 (i dag 15), rebounds 13 (10), assists ≈ Poisson (10), pr 5. n = 41–71: för litet för
   att ändra `NB_R`, men points kan vara underspridd i modellen. Följs upp när n ≥ 150 per marknad.
6. **Insats:** flat 1–3u behålls (beslut 26/11). Jämförelsen mot ¼ Kelly nedan är bara information.
   Kelly-fälten på tier-spelen är ren loggning.
7. **Beslut 26/11: modellvikten sänks från 0,3 till 0,075** (`nba_model_weight`, modellversion `2026-11-26-vikt0075`).
   Två oberoende skattningar ger samma svar: stängningens rörelse mot modellen (lutning 0,075) och walk-forward på
   kalibreringsloggen (5 374 ben, 44 matcher), där vikten valdes till 0,1 och 0,075 i respektive veck.
   0,3 var sämre än marknaden på points, pra och assists. Vinsten är liten och osäker (intervallet för vald vikt mot
   marknaden täcker 0), så det viktiga är att 0,3 var för högt, inte att 0,075 är exakt rätt.
   Vad som påverkas: `p_blend` och skuggfälten `p_faktorer`/`p_betyg` i modelltestet. LIVE (marknaden + modellens
   veto) och vad modelltestet bokar (kalibreringen M0/M1/M2) påverkas inte.
   Viktanalysen körs om med `--kalib nba_kalibrering.json.gz`.

Tidigare punkt 6 (insats), som underlag: tiers 1–3u ligger 2,1 × över ¼ Kelly vid odds 3–6,5 (99 % av spelen över Kelly) och under Kelly vid
   odds 1,4–2. Exponeringen per match och dag är som mest 12 %, och 21 % av matcherna ligger över 3,5 %.
   Kelly-förslaget bokförs nu som `kelly_pct`/`kelly_u` på varje tier-spel (skugga), så jämförelsen kan göras på
   resultat när det finns ≥ 150 nya avgjorda.

Fotboll: benloggen har 0 avgjorda ben med marknadens p (start 25/11). Rapporten körs när det finns ≥ 150.

## Rådata från rapporten


## Modellvikt (w0) walk-forward på kalibreringsloggen

| Modell | n | veck | vald w0 per veck | Δ log-loss mot marknad: 0 · 0.025 · 0.05 · 0.075 · 0.1 · 0.15 · 0.2 · 0.3 | vald vs marknad, 95 % CI |
|---|---|---|---|---|---|
| spelarmodell | 5374 | 2 | [0.1, 0.075] | +0.0000 · -0.0001 · -0.0002 · -0.0002 · -0.0003 · -0.0003 · -0.0002 · +0.0000 | -0.0016 … +0.0009 |
| faktormodell | 5374 | 2 | [0.0, 0.0] | +0.0000 · -0.0001 · -0.0003 · -0.0004 · -0.0005 · -0.0006 · -0.0006 · -0.0005 | +0.0000 … +0.0000 |
| betygsmodell | 5374 | 2 | [0.05, 0.05] | +0.0000 · -0.0000 · -0.0001 · -0.0001 · -0.0001 · +0.0000 · +0.0002 · +0.0008 | -0.0008 … +0.0007 |


Walk-forward (3 veck, grupperat per match, 6 h embargo). Test = osedd data i varje veck.

Avgjorda unika ben med marknadens p: **595** (av 1214 rader).

| Modell | n test | log-loss (poolad) | Brier | Δ log-loss mot marknad per veck |
|---|---|---|---|---|
| marknad | 414 | 0.6868 | 0.2468 | +0.0000, +0.0000, +0.0000 |
| modell (rå) | 414 | 0.7725 | 0.2840 | +0.1300, +0.0916, +0.0248 |
| slutlig p (bokförd) | 414 | 0.6923 | 0.2495 | +0.0108, +0.0082, -0.0043 |
| marknad + Platt | 414 | 0.6910 | 0.2489 | +0.0073, +0.0053, -0.0007 |
| residual (utfall) | 414 | 0.6953 | 0.2506 | +0.0159, +0.0058, +0.0030 |
| residual (mål: stängning) | 414 | 0.6872 | 0.2470 | +0.0010, +0.0006, -0.0006 |

Vald ridge (l2) per veck: [10.0, 1000.0, 1000.0]. Negativt Δ = bättre än marknaden.

CLV mot skarp stängning: +0.45 pe (95 % CI +0.08 … +0.84, n = 594).

Modellens avvikelse mot marknaden förutsäger stängningens rörelse: korrelation +0.188, lutning +0.075 (n = 594). Lutning 0 = ingen information, 1 = marknaden går hela vägen till modellen.

NB-form r skattad ur (väntat, utfall), momentmetod:

| Marknad | n | r̂ |
|---|---|---|
| points | 71 | 8.2 |
| rebounds | 57 | 13.0 |
| assists | 45 | 200.0 |
| pr | 41 | 5.1 |

## Tiers insats mot ¼ Kelly (tak 2 %)

| Odds | n | medel tier-insats % | medel ¼ Kelly % | andel över Kelly |
|---|---|---|---|---|
| 1.4–2.0 | 676 | 1.13 | 1.72 | 1% |
| 2.0–3.0 | 380 | 1.19 | 1.34 | 31% |
| 3.0–6.6 | 153 | 1.06 | 0.50 | 99% |

Exponering per match och dag: median 1.0 %, max 12.0 %, andel över 3,5 %: 21% (610 matcher).
Units i dag: {1: 1054, 2: 144, 3: 11}. Med ¼ Kelly (1u = 1 %, tak 2u): {0: 89, 1: 497, 2: 623}.
