# NBA – utvärdering på framåtriktad data (2026-11-21T05:29:18+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 38 | 38 | 32 | 15 | 37 | +1.7 % | +3.6 % | 5.2 | 3.24 (+2.50…+4.13) | 3.24 | 0.95 | +86.8 % | 2.77 | – |
| spel | 463 | 463 | 140 | 20 | 435 | +5.2 % | +2.7 % | 14.5 | 2.26 (+1.85…+2.73) | 2.11 | 0.82 | +77.3 % | 2.61 | – |
| skugga | 1409 | 1409 | 153 | 20 | 1323 | +3.2 % | +3.8 % | 39.8 | 0.81 (+0.58…+1.05) | 0.69 | 0.83 | +65.8 % | 1.75 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1090 | +4.8 % | +4.7 % | 34.4 | -0.03 (-0.37…+0.39) | -0.12 | 0.81 | +46.0 % | 1.76 | 0.2723 / 0.2437 (592) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 306 | 1.05 (+0.36…+1.50) | +70.4 % | +4.2 % |
| blocks | **ok** | 22 | 3.91 (+2.59…+4.73) | +95.5 % | +13.5 % |
| pa | **osäker** | 32 | 0.61 (-1.71…+0.46) | +59.4 % | -7.3 % |
| points | **ok** | 700 | 1.20 (+0.70…+1.43) | +66.8 % | +1.8 % |
| pr | **ok** | 70 | 1.34 (+0.02…+2.48) | +71.4 % | +8.7 % |
| pra | **ok** | 34 | 0.93 (+0.02…+2.81) | +64.7 % | -16.4 % |
| ra | **osäker** | 90 | 0.38 (-1.15…+0.60) | +60.7 % | +10.7 % |
| rebounds | **ok** | 391 | 1.01 (+0.61…+1.39) | +70.6 % | -1.4 % |
| steals | **ok** | 36 | 4.48 (+3.15…+8.32) | +91.7 % | +48.2 % |
| threes | **ok** | 229 | 1.38 (+0.65…+1.95) | +68.8 % | +9.7 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 18 | 3.49 | -5.9 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 98 | 2.80 | +3.2 % |
| spel | borttagen | 57 | 3.07 | -14.5 % |
| spel | flyttad linje (för oss) | 42 | 4.43 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 352 | 0.24 | +5.6 % |
| skugga | borttagen | 169 | 1.02 | -4.6 % |
| skugga | flyttad linje (för oss) | 194 | 4.75 | +19.7 % |
| skugga | flyttad linje (mot oss) | 47 | -4.68 | -16.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 231 | -0.02 | -3.4 % |
| modelltest | borttagen | 145 | 0.32 | +2.4 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0386…+0.0509 | 1.05 (+0.28…+1.92) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3035 / 0.2526 (24) | +0.0064…+0.1042 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0092…+0.0492 | -0.45 (-0.85…+0.12) | 6 | -1.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0435…+0.0804 | -0.23 (-1.98…+1.32) | 1 | +86.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0069…+0.1230 | -0.08 (-0.94…+0.93) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0409…+0.0523 | 0.10 (-0.91…+0.95) | 1 | +96.0 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0016…+0.0676 | -0.33 (-0.76…+0.11) | 12 | +3.9 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0173…+0.1264 | 3.50 (+1.67…+5.15) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0112…+0.0663 | 0.11 (-0.73…+1.30) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.507, assists 0.593, threes 0.912, points 0.964, pra 0.966, rebounds 0.977, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 337 | 0.2455 | 0.2453 | 0.2782 | -0.0015…+0.0022 |
| p_modell_min | 337 | 0.2866 | 0.2453 | 0.2782 | +0.0219…+0.0615 |
| p_faktorer | 315 | 0.2456 | 0.2445 | 0.2806 | -0.0019…+0.0047 |
| p_faktorer_ra | 315 | 0.2738 | 0.2445 | 0.2806 | +0.0120…+0.0536 |
| p_betyg | 243 | 0.2425 | 0.2418 | 0.2669 | -0.0030…+0.0058 |
| p_betyg_ra | 243 | 0.2800 | 0.2418 | 0.2669 | +0.0146…+0.0705 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 17 | +20.1 % | 3.69 |
| 2.00–2.50 | 17 | -13.4 % | 2.72 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
