# NBA – utvärdering på framåtriktad data (2026-11-21T23:52:01+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 38 | 38 | 32 | 15 | 38 | +4.5 % | +5.6 % | 5.2 | 3.24 (+2.50…+4.13) | 3.24 | 0.95 | +86.8 % | 2.77 | – |
| spel | 472 | 472 | 146 | 21 | 445 | +5.0 % | +2.8 % | 14.5 | 2.27 (+1.89…+2.73) | 2.13 | 0.82 | +77.5 % | 2.59 | – |
| skugga | 1440 | 1440 | 159 | 21 | 1348 | +2.7 % | +3.2 % | 39.8 | 0.81 (+0.59…+1.06) | 0.69 | 0.84 | +65.7 % | 1.74 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1091 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.36…+0.36) | -0.12 | 0.81 | +46.0 % | 1.76 | 0.2724 / 0.2437 (593) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 315 | 1.05 (+0.37…+1.53) | +70.4 % | +2.9 % |
| blocks | **ok** | 22 | 3.91 (+2.55…+4.85) | +95.5 % | +16.6 % |
| pa | **osäker** | 36 | 0.72 (-1.51…+0.85) | +60.6 % | -3.0 % |
| points | **ok** | 709 | 1.20 (+0.70…+1.42) | +66.8 % | +1.4 % |
| pr | **osäker** | 72 | 1.34 (-0.02…+2.47) | +71.4 % | +9.7 % |
| pra | **ok** | 34 | 0.93 (+0.05…+2.75) | +64.7 % | -16.4 % |
| ra | **osäker** | 97 | 0.38 (-1.15…+0.60) | +60.7 % | +9.4 % |
| rebounds | **ok** | 396 | 1.00 (+0.62…+1.38) | +70.4 % | -1.4 % |
| steals | **ok** | 39 | 4.46 (+3.24…+7.86) | +92.3 % | +39.3 % |
| threes | **ok** | 230 | 1.38 (+0.62…+1.96) | +68.8 % | +9.3 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 18 | 3.49 | +0.4 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 101 | 2.85 | +2.5 % |
| spel | borttagen | 57 | 3.07 | -14.5 % |
| spel | flyttad linje (för oss) | 42 | 4.43 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 357 | 0.25 | +3.9 % |
| skugga | borttagen | 169 | 1.02 | -4.0 % |
| skugga | flyttad linje (för oss) | 194 | 4.75 | +18.4 % |
| skugga | flyttad linje (mot oss) | 47 | -4.68 | -16.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 231 | -0.02 | -3.4 % |
| modelltest | borttagen | 145 | 0.32 | +1.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0384…+0.0510 | 1.05 (+0.22…+1.91) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0103…+0.0948 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0105…+0.0492 | -0.45 (-0.85…+0.12) | 6 | -1.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0805 | -0.23 (-1.98…+1.32) | 1 | +86.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0094…+0.1244 | -0.08 (-0.93…+0.92) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0427…+0.0551 | 0.10 (-0.90…+0.93) | 1 | +96.0 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0023…+0.0688 | -0.33 (-0.76…+0.11) | 13 | +11.9 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0196…+0.1260 | 3.50 (+1.65…+5.13) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0116…+0.0663 | 0.11 (-0.71…+1.22) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.497, assists 0.601, threes 0.913, points 0.964, pra 0.969, rebounds 0.982, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 338 | 0.2455 | 0.2453 | 0.2783 | -0.0015…+0.0021 |
| p_modell_min | 338 | 0.2871 | 0.2453 | 0.2783 | +0.0225…+0.0620 |
| p_faktorer | 316 | 0.2456 | 0.2445 | 0.2807 | -0.0019…+0.0047 |
| p_faktorer_ra | 316 | 0.2735 | 0.2445 | 0.2807 | +0.0111…+0.0517 |
| p_betyg | 244 | 0.2426 | 0.2418 | 0.2671 | -0.0030…+0.0062 |
| p_betyg_ra | 244 | 0.2810 | 0.2418 | 0.2671 | +0.0160…+0.0723 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 17 | +20.1 % | 3.69 |
| 2.00–2.50 | 18 | -6.7 % | 2.72 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
