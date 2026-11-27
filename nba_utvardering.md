# NBA – utvärdering på framåtriktad data (2026-11-27T12:31:15+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 51 | 51 | 44 | 20 | 51 | -2.4 % | +0.6 % | 5.7 | 2.97 (+2.28…+3.77) | 2.91 | 0.92 | +84.3 % | 2.56 | – |
| spel | 535 | 535 | 175 | 26 | 509 | +6.2 % | +4.7 % | 14.5 | 2.30 (+1.94…+2.71) | 2.18 | 0.82 | +77.9 % | 2.55 | – |
| skugga | 1630 | 1630 | 193 | 26 | 1550 | +1.5 % | +1.3 % | 39.8 | 0.86 (+0.67…+1.09) | 0.74 | 0.83 | +66.6 % | 1.74 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.40) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 353 | 1.24 (+0.59…+1.69) | +72.1 % | +4.1 % |
| blocks | **ok** | 23 | 3.97 (+2.69…+4.91) | +95.7 % | +22.9 % |
| pa | **osäker** | 52 | 0.82 (-1.23…+1.00) | +62.7 % | +0.6 % |
| points | **ok** | 789 | 1.24 (+0.74…+1.47) | +67.6 % | -0.9 % |
| pr | **ok** | 96 | 1.38 (+0.63…+2.54) | +71.9 % | +0.2 % |
| pra | **ok** | 43 | 1.19 (+0.50…+2.64) | +69.8 % | -25.0 % |
| ra | **osäker** | 122 | 0.46 (-0.92…+0.92) | +62.0 % | +12.2 % |
| rebounds | **ok** | 436 | 0.99 (+0.60…+1.35) | +70.4 % | -0.8 % |
| steals | **ok** | 48 | 4.27 (+3.16…+7.16) | +93.8 % | +39.5 % |
| threes | **ok** | 254 | 1.34 (+0.62…+1.86) | +68.5 % | +9.2 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 29 | 2.86 | -3.1 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 154 | 2.65 | +11.9 % |
| spel | borttagen | 66 | 2.90 | -21.1 % |
| spel | flyttad linje (för oss) | 46 | 4.58 | +3.4 % |
| spel | flyttad linje (mot oss) | 11 | -3.76 | -5.5 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 508 | 0.41 | +1.0 % |
| skugga | borttagen | 201 | 1.19 | -4.9 % |
| skugga | flyttad linje (för oss) | 216 | 4.66 | +17.1 % |
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
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0369…+0.0521 | 1.05 (+0.22…+1.86) | 10 | -24.7 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0103…+0.0948 | -1.44 (-2.23…-0.88) | 1 | +110.0 % |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0092…+0.0487 | -0.46 (-0.87…+0.17) | 10 | -21.4 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0792 | -0.23 (-1.91…+1.26) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0029…+0.1251 | -0.08 (-0.94…+0.92) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0411…+0.0533 | 0.10 (-0.95…+0.96) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0031…+0.0668 | -0.33 (-0.78…+0.11) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0177…+0.1285 | 3.50 (+1.74…+5.11) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0114…+0.0647 | 0.11 (-0.69…+1.25) | 10 | +18.5 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.493, assists 0.627, threes 0.903, pra 0.971, points 0.974, rebounds 0.984, pr 1.000

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
| 1.60–2.00 | 23 | +4.9 % | 3.75 |
| 2.00–2.50 | 24 | -3.6 % | 2.23 |
| 2.50–3.00 | 4 | -37.5 % | 2.83 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
