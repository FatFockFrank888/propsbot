# NBA – utvärdering på framåtriktad data (2026-11-22T07:35:04+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 40 | 40 | 33 | 16 | 40 | +4.1 % | +6.2 % | 5.2 | 3.29 (+2.54…+4.10) | 3.29 | 0.95 | +87.5 % | 2.55 | – |
| spel | 476 | 476 | 146 | 21 | 454 | +4.8 % | +2.8 % | 14.5 | 2.27 (+1.90…+2.72) | 2.14 | 0.82 | +77.3 % | 2.57 | – |
| skugga | 1449 | 1449 | 160 | 22 | 1380 | +1.9 % | +2.3 % | 39.8 | 0.82 (+0.61…+1.06) | 0.71 | 0.83 | +65.7 % | 1.73 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1091 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.34…+0.41) | -0.12 | 0.81 | +46.0 % | 1.76 | 0.2724 / 0.2437 (593) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 316 | 1.07 (+0.43…+1.50) | +70.4 % | +2.8 % |
| blocks | **ok** | 23 | 3.97 (+2.70…+4.81) | +95.7 % | +22.9 % |
| pa | **osäker** | 36 | 0.75 (-1.44…+1.02) | +61.1 % | +0.1 % |
| points | **ok** | 717 | 1.23 (+0.73…+1.48) | +67.0 % | +0.7 % |
| pr | **ok** | 73 | 1.21 (+0.05…+2.35) | +69.9 % | +10.2 % |
| pra | **ok** | 34 | 0.93 (+0.07…+2.85) | +64.7 % | -16.4 % |
| ra | **osäker** | 97 | 0.48 (-0.95…+0.75) | +60.4 % | +3.3 % |
| rebounds | **ok** | 399 | 0.98 (+0.58…+1.39) | +70.1 % | -1.8 % |
| steals | **ok** | 39 | 4.46 (+3.23…+7.77) | +92.3 % | +39.3 % |
| threes | **ok** | 231 | 1.39 (+0.65…+1.99) | +68.9 % | +8.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 20 | 3.56 | +0.0 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 110 | 2.84 | +2.1 % |
| spel | borttagen | 57 | 3.07 | -14.5 % |
| spel | flyttad linje (för oss) | 43 | 4.28 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 381 | 0.34 | +2.0 % |
| skugga | borttagen | 176 | 1.01 | -4.9 % |
| skugga | flyttad linje (för oss) | 196 | 4.68 | +17.7 % |
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
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0393…+0.0484 | 1.05 (+0.24…+1.91) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0052…+0.0931 | -1.44 (-2.23…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0122…+0.0488 | -0.45 (-0.87…+0.14) | 8 | -1.8 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0436…+0.0799 | -0.23 (-1.88…+1.25) | 1 | +86.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0030…+0.1240 | -0.08 (-0.93…+0.87) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0422…+0.0566 | 0.10 (-0.93…+0.97) | 1 | +96.0 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0018…+0.0672 | -0.33 (-0.75…+0.09) | 13 | +11.9 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0166…+0.1271 | 3.50 (+1.74…+5.12) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0125…+0.0650 | 0.11 (-0.73…+1.24) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.463, assists 0.623, threes 0.922, points 0.960, pra 0.970, rebounds 0.980, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 338 | 0.2455 | 0.2453 | 0.2783 | -0.0014…+0.0022 |
| p_modell_min | 338 | 0.2871 | 0.2453 | 0.2783 | +0.0226…+0.0619 |
| p_faktorer | 316 | 0.2456 | 0.2445 | 0.2807 | -0.0019…+0.0050 |
| p_faktorer_ra | 316 | 0.2735 | 0.2445 | 0.2807 | +0.0118…+0.0530 |
| p_betyg | 244 | 0.2426 | 0.2418 | 0.2671 | -0.0028…+0.0061 |
| p_betyg_ra | 244 | 0.2810 | 0.2418 | 0.2671 | +0.0155…+0.0731 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 18 | +24.2 % | 3.74 |
| 2.00–2.50 | 19 | -11.6 % | 2.78 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
