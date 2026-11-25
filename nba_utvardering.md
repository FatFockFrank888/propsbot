# NBA – utvärdering på framåtriktad data (2026-11-25T00:03:49+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 46 | 46 | 39 | 18 | 46 | -1.1 % | +0.1 % | 5.2 | 3.12 (+2.39…+3.92) | 3.07 | 0.91 | +87.0 % | 2.38 | – |
| spel | 510 | 510 | 164 | 24 | 482 | +5.4 % | +3.6 % | 14.5 | 2.24 (+1.89…+2.64) | 2.14 | 0.83 | +77.5 % | 2.51 | – |
| skugga | 1563 | 1563 | 178 | 24 | 1481 | +2.1 % | +2.2 % | 39.8 | 0.82 (+0.63…+1.04) | 0.70 | 0.83 | +66.2 % | 1.71 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.36…+0.40) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 337 | 1.11 (+0.49…+1.51) | +71.6 % | +3.7 % |
| blocks | **ok** | 23 | 3.97 (+2.68…+4.82) | +95.7 % | +22.9 % |
| pa | **osäker** | 43 | 0.77 (-1.62…+1.10) | +61.9 % | +0.4 % |
| points | **ok** | 765 | 1.20 (+0.70…+1.44) | +67.3 % | -0.4 % |
| pr | **ok** | 91 | 1.33 (+0.33…+2.30) | +71.3 % | +2.3 % |
| pra | **ok** | 40 | 0.99 (+0.16…+2.57) | +66.7 % | -15.1 % |
| ra | **osäker** | 116 | 0.47 (-0.98…+0.96) | +61.7 % | +12.4 % |
| rebounds | **ok** | 423 | 0.97 (+0.57…+1.33) | +70.1 % | -2.0 % |
| steals | **ok** | 42 | 4.50 (+3.38…+7.64) | +92.9 % | +37.3 % |
| threes | **ok** | 239 | 1.37 (+0.62…+1.91) | +68.8 % | +11.2 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 24 | 3.12 | -0.7 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 136 | 2.68 | +7.6 % |
| spel | borttagen | 61 | 2.88 | -22.2 % |
| spel | flyttad linje (för oss) | 44 | 4.25 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 465 | 0.32 | +1.8 % |
| skugga | borttagen | 189 | 1.12 | -4.6 % |
| skugga | flyttad linje (för oss) | 206 | 4.72 | +19.1 % |
| skugga | flyttad linje (mot oss) | 49 | -4.87 | -16.3 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 232 | -0.03 | -3.0 % |
| modelltest | borttagen | 146 | 0.30 | +0.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0369…+0.0519 | 1.05 (+0.23…+1.89) | 8 | -33.1 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0948 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0087…+0.0472 | -0.46 (-0.87…+0.12) | 9 | -12.7 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0435…+0.0790 | -0.23 (-1.77…+1.21) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0010…+0.1231 | -0.08 (-0.96…+0.89) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0400…+0.0539 | 0.10 (-0.95…+0.95) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0010…+0.0686 | -0.33 (-0.77…+0.12) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0135…+0.1269 | 3.50 (+1.66…+5.14) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0122…+0.0642 | 0.11 (-0.72…+1.27) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.480, assists 0.633, threes 0.910, pra 0.965, points 0.969, rebounds 0.978, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 340 | 0.2454 | 0.2453 | 0.2782 | -0.0015…+0.0021 |
| p_modell_min | 340 | 0.2871 | 0.2453 | 0.2782 | +0.0223…+0.0616 |
| p_faktorer | 318 | 0.2455 | 0.2445 | 0.2807 | -0.0020…+0.0049 |
| p_faktorer_ra | 318 | 0.2734 | 0.2445 | 0.2807 | +0.0126…+0.0531 |
| p_betyg | 246 | 0.2426 | 0.2418 | 0.2671 | -0.0029…+0.0059 |
| p_betyg_ra | 246 | 0.2806 | 0.2418 | 0.2671 | +0.0154…+0.0732 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 21 | +14.9 % | 3.71 |
| 2.00–2.50 | 22 | -14.3 % | 2.45 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
