# NBA – utvärdering på framåtriktad data (2026-11-26T01:20:17+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 50 | 50 | 43 | 20 | 47 | -3.2 % | -1.2 % | 5.2 | 2.92 (+2.08…+3.76) | 2.86 | 0.92 | +83.7 % | 2.47 | – |
| spel | 531 | 531 | 172 | 25 | 489 | +5.4 % | +3.7 % | 14.5 | 2.28 (+1.91…+2.69) | 2.16 | 0.83 | +77.6 % | 2.52 | – |
| skugga | 1617 | 1617 | 187 | 25 | 1497 | +1.9 % | +1.8 % | 39.8 | 0.83 (+0.65…+1.05) | 0.71 | 0.83 | +66.2 % | 1.74 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.40) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 351 | 1.17 (+0.54…+1.57) | +71.6 % | +4.2 % |
| blocks | **ok** | 23 | 3.97 (+2.68…+4.81) | +95.7 % | +22.9 % |
| pa | **osäker** | 51 | 0.59 (-1.68…+0.74) | +61.2 % | +0.1 % |
| points | **ok** | 781 | 1.24 (+0.72…+1.49) | +67.5 % | -0.6 % |
| pr | **ok** | 95 | 1.28 (+0.51…+2.38) | +71.0 % | -0.4 % |
| pra | **ok** | 42 | 1.07 (+0.37…+2.54) | +69.0 % | -21.3 % |
| ra | **osäker** | 121 | 0.45 (-0.91…+0.91) | +61.7 % | +11.4 % |
| rebounds | **ok** | 435 | 0.99 (+0.57…+1.34) | +70.1 % | -1.2 % |
| steals | **ok** | 48 | 4.28 (+3.12…+7.13) | +93.5 % | +37.3 % |
| threes | **ok** | 251 | 1.35 (+0.64…+1.84) | +68.3 % | +10.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 27 | 2.77 | -4.7 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 150 | 2.58 | +8.0 % |
| spel | borttagen | 64 | 2.93 | -20.2 % |
| spel | flyttad linje (för oss) | 46 | 4.58 | +5.9 % |
| spel | flyttad linje (mot oss) | 11 | -3.76 | -5.5 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 495 | 0.36 | +1.4 % |
| skugga | borttagen | 198 | 1.16 | -3.5 % |
| skugga | flyttad linje (för oss) | 213 | 4.64 | +18.1 % |
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
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0369…+0.0521 | 1.05 (+0.22…+1.86) | 8 | -33.1 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0948 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0089…+0.0479 | -0.46 (-0.87…+0.11) | 10 | -21.4 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0794 | -0.23 (-1.85…+1.28) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0028…+0.1240 | -0.08 (-0.95…+0.92) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0430…+0.0589 | 0.10 (-0.94…+0.96) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0027…+0.0697 | -0.33 (-0.75…+0.12) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0184…+0.1269 | 3.50 (+1.72…+5.09) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0119…+0.0657 | 0.11 (-0.71…+1.27) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.473, assists 0.627, threes 0.912, pra 0.969, points 0.972, rebounds 0.978, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 340 | 0.2454 | 0.2453 | 0.2782 | -0.0015…+0.0022 |
| p_modell_min | 340 | 0.2871 | 0.2453 | 0.2782 | +0.0227…+0.0618 |
| p_faktorer | 318 | 0.2455 | 0.2445 | 0.2807 | -0.0021…+0.0049 |
| p_faktorer_ra | 318 | 0.2734 | 0.2445 | 0.2807 | +0.0126…+0.0528 |
| p_betyg | 246 | 0.2426 | 0.2418 | 0.2671 | -0.0029…+0.0059 |
| p_betyg_ra | 246 | 0.2806 | 0.2418 | 0.2671 | +0.0154…+0.0732 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 22 | +9.7 % | 3.72 |
| 2.00–2.50 | 22 | -14.3 % | 2.17 |
| 2.50–3.00 | 3 | -16.7 % | 2.83 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
