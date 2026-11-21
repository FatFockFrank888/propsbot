# NBA – utvärdering på framåtriktad data (2026-11-21T03:43:38+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 38 | 38 | 32 | 15 | 35 | +2.0 % | +3.8 % | 5.2 | 3.24 (+2.50…+4.13) | 3.24 | 0.95 | +86.8 % | 2.77 | – |
| spel | 463 | 463 | 140 | 20 | 424 | +4.6 % | +2.4 % | 14.5 | 2.26 (+1.85…+2.73) | 2.11 | 0.82 | +77.3 % | 2.61 | – |
| skugga | 1409 | 1409 | 153 | 20 | 1283 | +3.6 % | +4.3 % | 39.8 | 0.81 (+0.58…+1.05) | 0.69 | 0.83 | +65.8 % | 1.75 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1085 | +4.9 % | +4.9 % | 34.4 | -0.03 (-0.37…+0.39) | -0.12 | 0.81 | +46.0 % | 1.76 | 0.2714 / 0.2437 (587) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 306 | 1.05 (+0.37…+1.49) | +70.4 % | +4.8 % |
| blocks | **ok** | 22 | 3.91 (+2.52…+4.78) | +95.5 % | +9.4 % |
| pa | **osäker** | 32 | 0.61 (-1.68…+0.46) | +59.4 % | -12.8 % |
| points | **ok** | 700 | 1.20 (+0.72…+1.45) | +66.8 % | +1.9 % |
| pr | **osäker** | 70 | 1.34 (-0.02…+2.40) | +71.4 % | +8.1 % |
| pra | **ok** | 34 | 0.93 (+0.06…+2.83) | +64.7 % | -19.6 % |
| ra | **osäker** | 90 | 0.38 (-1.16…+0.58) | +60.7 % | +16.0 % |
| rebounds | **ok** | 391 | 1.01 (+0.57…+1.39) | +70.6 % | -2.5 % |
| steals | **ok** | 36 | 4.48 (+3.06…+8.25) | +91.7 % | +48.2 % |
| threes | **ok** | 229 | 1.38 (+0.64…+1.96) | +68.8 % | +11.5 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 18 | 3.49 | -6.4 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 98 | 2.80 | +1.0 % |
| spel | borttagen | 57 | 3.07 | -14.5 % |
| spel | flyttad linje (för oss) | 42 | 4.43 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 352 | 0.24 | +6.5 % |
| skugga | borttagen | 169 | 1.02 | -1.5 % |
| skugga | flyttad linje (för oss) | 194 | 4.75 | +18.8 % |
| skugga | flyttad linje (mot oss) | 47 | -4.68 | -13.1 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 231 | -0.02 | -3.1 % |
| modelltest | borttagen | 145 | 0.32 | +2.8 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2402 / 0.2314 (92) | -0.0373…+0.0534 | 1.05 (+0.28…+1.92) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.2930 / 0.2521 (23) | -0.0079…+0.0695 | -1.44 (-2.22…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0092…+0.0492 | -0.45 (-0.85…+0.12) | 6 | -1.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0435…+0.0804 | -0.23 (-1.98…+1.32) | 1 | +86.0 % |
| pra | **shadow** | 0.3191 / 0.2506 (43) | -0.0130…+0.1179 | -0.08 (-0.93…+0.90) | 1 | -100.0 % |
| ra | **shadow** | 0.2371 / 0.2427 (38) | -0.0475…+0.0496 | 0.10 (-0.92…+0.96) | 1 | +96.0 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0018…+0.0659 | -0.33 (-0.75…+0.10) | 10 | +5.2 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0150…+0.1332 | 3.50 (+1.69…+5.14) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0128…+0.0632 | 0.11 (-0.68…+1.28) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.375, assists 0.627, threes 0.916, pra 0.954, points 0.964, rebounds 0.984, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 332 | 0.2456 | 0.2452 | 0.2768 | -0.0012…+0.0024 |
| p_modell_min | 332 | 0.2851 | 0.2452 | 0.2768 | +0.0196…+0.0603 |
| p_faktorer | 310 | 0.2453 | 0.2444 | 0.2791 | -0.0022…+0.0044 |
| p_faktorer_ra | 310 | 0.2730 | 0.2444 | 0.2791 | +0.0110…+0.0531 |
| p_betyg | 238 | 0.2419 | 0.2416 | 0.2647 | -0.0039…+0.0054 |
| p_betyg_ra | 238 | 0.2774 | 0.2416 | 0.2647 | +0.0081…+0.0655 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 16 | +15.4 % | 3.69 |
| 2.00–2.50 | 16 | -8.0 % | 2.72 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
