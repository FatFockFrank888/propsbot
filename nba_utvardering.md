# NBA – utvärdering på framåtriktad data (2026-11-25T15:03:50+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 47 | 47 | 40 | 19 | 47 | -3.2 % | -1.2 % | 5.2 | 3.13 (+2.43…+3.89) | 3.08 | 0.91 | +87.2 % | 2.31 | – |
| spel | 518 | 518 | 168 | 25 | 489 | +5.4 % | +3.7 % | 14.5 | 2.29 (+1.92…+2.70) | 2.18 | 0.83 | +77.8 % | 2.50 | – |
| skugga | 1585 | 1585 | 186 | 25 | 1497 | +1.9 % | +1.8 % | 39.8 | 0.83 (+0.63…+1.04) | 0.72 | 0.83 | +66.3 % | 1.71 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.36…+0.41) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 344 | 1.10 (+0.47…+1.53) | +71.4 % | +4.2 % |
| blocks | **ok** | 23 | 3.97 (+2.71…+4.84) | +95.7 % | +22.9 % |
| pa | **osäker** | 47 | 0.82 (-1.46…+1.11) | +63.6 % | +0.1 % |
| points | **ok** | 772 | 1.23 (+0.72…+1.49) | +67.5 % | -0.6 % |
| pr | **ok** | 92 | 1.26 (+0.47…+2.41) | +71.4 % | -0.4 % |
| pra | **ok** | 41 | 1.03 (+0.28…+2.50) | +68.3 % | -21.3 % |
| ra | **osäker** | 117 | 0.47 (-0.90…+0.95) | +61.7 % | +11.4 % |
| rebounds | **ok** | 429 | 1.00 (+0.60…+1.35) | +70.4 % | -1.2 % |
| steals | **ok** | 42 | 4.50 (+3.33…+7.59) | +92.9 % | +37.3 % |
| threes | **ok** | 243 | 1.37 (+0.60…+1.89) | +68.8 % | +10.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 25 | 3.15 | -4.7 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 138 | 2.70 | +8.0 % |
| spel | borttagen | 62 | 2.90 | -20.2 % |
| spel | flyttad linje (för oss) | 45 | 4.56 | +5.9 % |
| spel | flyttad linje (mot oss) | 11 | -3.76 | -5.5 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 471 | 0.35 | +1.4 % |
| skugga | borttagen | 191 | 1.11 | -3.5 % |
| skugga | flyttad linje (för oss) | 207 | 4.73 | +18.1 % |
| skugga | flyttad linje (mot oss) | 51 | -4.85 | -19.7 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 232 | -0.03 | -3.0 % |
| modelltest | borttagen | 146 | 0.30 | +0.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0368…+0.0511 | 1.05 (+0.22…+1.86) | 8 | -33.1 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0103…+0.0948 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0094…+0.0460 | -0.46 (-0.87…+0.13) | 10 | -21.4 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0791 | -0.23 (-1.94…+1.23) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0058…+0.1256 | -0.08 (-0.94…+0.90) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0403…+0.0533 | 0.10 (-0.96…+0.98) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0025…+0.0712 | -0.33 (-0.78…+0.10) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0179…+0.1294 | 3.50 (+1.72…+5.08) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0131…+0.0634 | 0.11 (-0.71…+1.26) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.480, assists 0.635, threes 0.911, points 0.968, pra 0.974, rebounds 0.976, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 340 | 0.2454 | 0.2453 | 0.2782 | -0.0015…+0.0022 |
| p_modell_min | 340 | 0.2871 | 0.2453 | 0.2782 | +0.0209…+0.0617 |
| p_faktorer | 318 | 0.2455 | 0.2445 | 0.2807 | -0.0020…+0.0048 |
| p_faktorer_ra | 318 | 0.2734 | 0.2445 | 0.2807 | +0.0119…+0.0540 |
| p_betyg | 246 | 0.2426 | 0.2418 | 0.2671 | -0.0029…+0.0060 |
| p_betyg_ra | 246 | 0.2806 | 0.2418 | 0.2671 | +0.0156…+0.0722 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 22 | +9.7 % | 3.72 |
| 2.00–2.50 | 22 | -14.3 % | 2.45 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
