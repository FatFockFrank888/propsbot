# NBA – utvärdering på framåtriktad data (2026-11-23T01:37:12+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 43 | 43 | 36 | 17 | 41 | +1.6 % | +4.3 % | 5.2 | 3.11 (+2.35…+3.93) | 3.09 | 0.93 | +86.0 % | 2.47 | – |
| spel | 487 | 487 | 152 | 22 | 456 | +4.4 % | +2.4 % | 14.5 | 2.25 (+1.85…+2.67) | 2.14 | 0.82 | +77.4 % | 2.53 | – |
| skugga | 1481 | 1481 | 165 | 22 | 1388 | +2.0 % | +2.3 % | 39.8 | 0.83 (+0.63…+1.07) | 0.71 | 0.83 | +65.9 % | 1.69 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1091 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.41) | -0.12 | 0.81 | +46.0 % | 1.76 | 0.2724 / 0.2437 (593) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 326 | 1.08 (+0.46…+1.49) | +70.7 % | +2.9 % |
| blocks | **ok** | 23 | 3.97 (+2.70…+4.81) | +95.7 % | +22.9 % |
| pa | **osäker** | 39 | 0.90 (-1.30…+1.49) | +64.1 % | +0.1 % |
| points | **ok** | 733 | 1.25 (+0.77…+1.50) | +67.3 % | +0.2 % |
| pr | **osäker** | 74 | 1.20 (-0.02…+2.32) | +70.3 % | +10.2 % |
| pra | **ok** | 36 | 1.02 (+0.24…+2.75) | +66.7 % | -16.4 % |
| ra | **osäker** | 104 | 0.28 (-1.32…+0.56) | +59.2 % | +3.3 % |
| rebounds | **ok** | 405 | 0.97 (+0.58…+1.33) | +70.1 % | -1.5 % |
| steals | **ok** | 39 | 4.46 (+3.22…+7.96) | +92.3 % | +39.3 % |
| threes | **ok** | 232 | 1.40 (+0.63…+2.00) | +68.7 % | +9.0 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 22 | 3.17 | +0.0 % |
| live | borttagen | 3 | 3.42 | -38.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 119 | 2.77 | +1.2 % |
| spel | borttagen | 59 | 2.89 | -16.6 % |
| spel | flyttad linje (för oss) | 43 | 4.28 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 407 | 0.31 | +1.8 % |
| skugga | borttagen | 180 | 1.07 | -4.5 % |
| skugga | flyttad linje (för oss) | 199 | 4.74 | +18.3 % |
| skugga | flyttad linje (mot oss) | 48 | -4.66 | -16.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 231 | -0.02 | -3.4 % |
| modelltest | borttagen | 145 | 0.32 | +1.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0377…+0.0479 | 1.05 (+0.26…+1.90) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0931 | -1.44 (-2.23…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0095…+0.0478 | -0.45 (-0.87…+0.14) | 9 | -12.7 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0423…+0.0799 | -0.23 (-1.87…+1.25) | 1 | +86.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0048…+0.1222 | -0.08 (-0.93…+0.95) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0433…+0.0558 | 0.10 (-0.90…+0.95) | 1 | +96.0 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0016…+0.0679 | -0.33 (-0.75…+0.11) | 13 | +11.9 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0198…+0.1246 | 3.50 (+1.75…+5.18) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0131…+0.0652 | 0.11 (-0.70…+1.29) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.475, assists 0.616, threes 0.913, points 0.959, pra 0.974, rebounds 0.983, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 338 | 0.2455 | 0.2453 | 0.2783 | -0.0015…+0.0022 |
| p_modell_min | 338 | 0.2871 | 0.2453 | 0.2783 | +0.0228…+0.0622 |
| p_faktorer | 316 | 0.2456 | 0.2445 | 0.2807 | -0.0019…+0.0048 |
| p_faktorer_ra | 316 | 0.2735 | 0.2445 | 0.2807 | +0.0117…+0.0529 |
| p_betyg | 244 | 0.2426 | 0.2418 | 0.2671 | -0.0029…+0.0062 |
| p_betyg_ra | 244 | 0.2810 | 0.2418 | 0.2671 | +0.0159…+0.0731 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 18 | +24.2 % | 3.84 |
| 2.00–2.50 | 20 | -16.0 % | 2.36 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
