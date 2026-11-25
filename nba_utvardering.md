# NBA – utvärdering på framåtriktad data (2026-11-25T23:28:58+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 50 | 50 | 43 | 20 | 47 | -3.2 % | -1.2 % | 5.2 | 3.13 (+2.43…+3.89) | 3.08 | 0.91 | +87.2 % | 2.31 | – |
| spel | 529 | 529 | 172 | 25 | 489 | +5.4 % | +3.7 % | 14.5 | 2.29 (+1.92…+2.69) | 2.18 | 0.82 | +77.8 % | 2.52 | – |
| skugga | 1610 | 1610 | 187 | 25 | 1497 | +1.9 % | +1.8 % | 39.8 | 0.84 (+0.63…+1.05) | 0.72 | 0.83 | +66.4 % | 1.72 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.42) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 350 | 1.13 (+0.49…+1.56) | +71.5 % | +4.2 % |
| blocks | **ok** | 23 | 3.97 (+2.65…+4.89) | +95.7 % | +22.9 % |
| pa | **osäker** | 50 | 0.82 (-1.43…+1.13) | +63.6 % | +0.1 % |
| points | **ok** | 780 | 1.24 (+0.76…+1.48) | +67.6 % | -0.6 % |
| pr | **ok** | 94 | 1.26 (+0.48…+2.40) | +71.4 % | -0.4 % |
| pra | **ok** | 42 | 1.07 (+0.37…+2.49) | +69.0 % | -21.3 % |
| ra | **osäker** | 121 | 0.49 (-1.00…+0.99) | +62.1 % | +11.4 % |
| rebounds | **ok** | 434 | 1.00 (+0.62…+1.37) | +70.4 % | -1.2 % |
| steals | **ok** | 46 | 4.50 (+3.34…+7.63) | +92.9 % | +37.3 % |
| threes | **ok** | 249 | 1.37 (+0.62…+1.89) | +68.8 % | +10.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 25 | 3.15 | -4.7 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 138 | 2.70 | +8.0 % |
| spel | borttagen | 63 | 2.89 | -20.2 % |
| spel | flyttad linje (för oss) | 45 | 4.56 | +5.9 % |
| spel | flyttad linje (mot oss) | 11 | -3.76 | -5.5 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 473 | 0.37 | +1.4 % |
| skugga | borttagen | 192 | 1.12 | -3.5 % |
| skugga | flyttad linje (för oss) | 208 | 4.72 | +18.1 % |
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
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0370…+0.0530 | 1.05 (+0.22…+1.92) | 8 | -33.1 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0948 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0093…+0.0470 | -0.46 (-0.87…+0.14) | 10 | -21.4 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0791 | -0.23 (-1.91…+1.31) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0054…+0.1249 | -0.08 (-0.90…+0.91) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0429…+0.0576 | 0.10 (-0.93…+0.96) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0019…+0.0700 | -0.33 (-0.78…+0.15) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0228…+0.1308 | 3.50 (+1.65…+5.17) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0137…+0.0662 | 0.11 (-0.71…+1.28) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.477, assists 0.632, threes 0.905, points 0.969, pra 0.971, rebounds 0.975, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 340 | 0.2454 | 0.2453 | 0.2782 | -0.0015…+0.0022 |
| p_modell_min | 340 | 0.2871 | 0.2453 | 0.2782 | +0.0227…+0.0618 |
| p_faktorer | 318 | 0.2455 | 0.2445 | 0.2807 | -0.0019…+0.0049 |
| p_faktorer_ra | 318 | 0.2734 | 0.2445 | 0.2807 | +0.0126…+0.0531 |
| p_betyg | 246 | 0.2426 | 0.2418 | 0.2671 | -0.0028…+0.0059 |
| p_betyg_ra | 246 | 0.2806 | 0.2418 | 0.2671 | +0.0156…+0.0713 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 22 | +9.7 % | 3.72 |
| 2.00–2.50 | 22 | -14.3 % | 2.45 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
