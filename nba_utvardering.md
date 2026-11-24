# NBA – utvärdering på framåtriktad data (2026-11-24T01:27:27+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 45 | 45 | 38 | 18 | 43 | +5.8 % | +6.8 % | 5.2 | 3.08 (+2.34…+3.90) | 3.03 | 0.91 | +86.7 % | 2.46 | – |
| spel | 501 | 501 | 161 | 23 | 465 | +4.5 % | +2.7 % | 14.5 | 2.22 (+1.85…+2.66) | 2.11 | 0.82 | +77.4 % | 2.51 | – |
| skugga | 1546 | 1546 | 175 | 23 | 1413 | +2.3 % | +2.4 % | 39.8 | 0.83 (+0.63…+1.06) | 0.70 | 0.83 | +66.0 % | 1.71 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1091 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.36…+0.41) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (593) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 335 | 1.10 (+0.49…+1.51) | +71.3 % | +4.0 % |
| blocks | **ok** | 23 | 3.97 (+2.70…+4.81) | +95.7 % | +22.9 % |
| pa | **osäker** | 42 | 0.77 (-1.64…+1.14) | +61.9 % | +2.4 % |
| points | **ok** | 758 | 1.25 (+0.74…+1.46) | +67.6 % | -0.5 % |
| pr | **ok** | 84 | 1.25 (+0.07…+2.24) | +70.4 % | +11.2 % |
| pra | **osäker** | 38 | 0.81 (-0.22…+2.40) | +64.9 % | -15.5 % |
| ra | **osäker** | 114 | 0.38 (-1.06…+0.72) | +60.7 % | +9.5 % |
| rebounds | **ok** | 418 | 0.95 (+0.55…+1.30) | +69.8 % | -1.1 % |
| steals | **ok** | 42 | 4.48 (+3.27…+7.79) | +92.7 % | +39.3 % |
| threes | **ok** | 238 | 1.36 (+0.62…+1.86) | +68.7 % | +8.5 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 23 | 3.05 | +8.3 % |
| live | borttagen | 4 | 3.62 | -38.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 129 | 2.64 | +2.6 % |
| spel | borttagen | 61 | 2.88 | -18.5 % |
| spel | flyttad linje (för oss) | 43 | 4.28 | +6.4 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 443 | 0.31 | +2.7 % |
| skugga | borttagen | 188 | 1.12 | -4.5 % |
| skugga | flyttad linje (för oss) | 202 | 4.72 | +17.7 % |
| skugga | flyttad linje (mot oss) | 48 | -4.66 | -14.6 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 232 | -0.03 | -3.4 % |
| modelltest | borttagen | 146 | 0.30 | +1.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0391…+0.0500 | 1.05 (+0.25…+1.92) | 8 | -33.1 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0931 | -1.44 (-2.23…-0.88) | 0 | – |
| points | **shadow** | 0.2611 / 0.2412 (164) | -0.0103…+0.0479 | -0.46 (-0.86…+0.13) | 9 | -12.7 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0433…+0.0799 | -0.23 (-1.90…+1.24) | 1 | +86.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0030…+0.1242 | -0.08 (-0.93…+0.93) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0453…+0.0568 | 0.10 (-0.90…+0.92) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0014…+0.0683 | -0.33 (-0.75…+0.08) | 13 | +11.9 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0212…+0.1246 | 3.50 (+1.75…+5.18) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0102…+0.0659 | 0.11 (-0.73…+1.28) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.471, assists 0.612, threes 0.911, points 0.965, pra 0.972, rebounds 0.983, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 338 | 0.2455 | 0.2453 | 0.2783 | -0.0014…+0.0022 |
| p_modell_min | 338 | 0.2871 | 0.2453 | 0.2783 | +0.0230…+0.0619 |
| p_faktorer | 316 | 0.2456 | 0.2445 | 0.2807 | -0.0019…+0.0049 |
| p_faktorer_ra | 316 | 0.2735 | 0.2445 | 0.2807 | +0.0118…+0.0525 |
| p_betyg | 244 | 0.2426 | 0.2418 | 0.2671 | -0.0028…+0.0062 |
| p_betyg_ra | 244 | 0.2810 | 0.2418 | 0.2671 | +0.0155…+0.0731 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 19 | +27.0 % | 3.66 |
| 2.00–2.50 | 21 | -10.2 % | 2.45 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
