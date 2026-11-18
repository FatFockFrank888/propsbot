# NBA – utvärdering på framåtriktad data (2026-11-18T03:55:19+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 27 | 27 | 23 | 12 | 26 | -0.1 % | +0.2 % | 4.0 | 2.86 (+2.21…+3.62) | 2.92 | 0.96 | +85.2 % | 2.59 | – |
| spel | 391 | 391 | 116 | 17 | 360 | +4.7 % | +2.9 % | 14.5 | 2.21 (+1.74…+2.76) | 2.08 | 0.81 | +77.9 % | 2.69 | – |
| skugga | 1155 | 1155 | 128 | 17 | 1045 | +2.1 % | +1.9 % | 39.8 | 0.88 (+0.62…+1.16) | 0.82 | 0.85 | +66.2 % | 1.83 | – |
| modelltest | 1006 | 1006 | 129 | 17 | 908 | +5.5 % | +5.3 % | 34.2 | -0.01 (-0.39…+0.49) | -0.09 | 0.81 | +45.5 % | 1.87 | 0.2773 / 0.2441 (410) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 254 | 0.99 (+0.30…+1.62) | +70.3 % | +4.7 % |
| blocks | **ok** | 15 | 4.14 (+2.64…+5.36) | +100.0 % | +26.2 % |
| pa | **osäker** | 14 | -0.37 (-1.74…+0.80) | +53.8 % | -15.1 % |
| points | **ok** | 625 | 1.20 (+0.74…+1.53) | +66.9 % | +1.4 % |
| pr | **osäker** | 45 | 1.42 (-0.87…+3.16) | +72.1 % | -3.7 % |
| pra | **osäker** | 24 | 0.63 (-0.39…+2.64) | +66.7 % | -11.9 % |
| ra | **osäker** | 61 | 0.45 (-1.78…+0.89) | +64.4 % | +7.7 % |
| rebounds | **ok** | 315 | 1.09 (+0.78…+1.47) | +71.7 % | -4.3 % |
| steals | **ok** | 30 | 4.51 (+2.81…+9.28) | +90.0 % | +31.8 % |
| threes | **ok** | 190 | 1.56 (+0.63…+2.27) | +68.9 % | +12.7 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 8 | 2.77 | -11.7 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 37 | 3.72 | -5.3 % |
| spel | borttagen | 47 | 2.98 | -15.0 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 163 | 0.70 | -0.2 % |
| skugga | borttagen | 124 | 0.98 | -0.2 % |
| skugga | flyttad linje (för oss) | 168 | 4.63 | +14.5 % |
| skugga | flyttad linje (mot oss) | 41 | -4.90 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 113 | 0.17 | -20.1 % |
| modelltest | borttagen | 124 | 0.26 | +11.6 % |
| modelltest | flyttad linje (för oss) | 105 | 4.40 | +11.6 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2499 / 0.2326 (64) | -0.0426…+0.0800 | 1.02 (+0.11…+2.03) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.2954 / 0.2548 (7) | – | -1.22 (–) | 0 | – |
| points | **degraded** | 0.2760 / 0.2413 (128) | +0.0070…+0.0592 | -0.52 (-0.91…+0.07) | 6 | -1.3 % |
| pr | **degraded** | 0.3077 / 0.2508 (37) | +0.0355…+0.0884 | 0.67 (-0.75…+1.83) | 0 | – |
| pra | **degraded** | 0.3470 / 0.2526 (30) | +0.0042…+0.1337 | 0.11 (-0.86…+1.29) | 0 | – |
| ra | **insufficient_data** | 0.2353 / 0.2380 (28) | -0.0657…+0.0695 | 0.14 (-1.37…+1.12) | 0 | – |
| rebounds | **shadow** | 0.2804 / 0.2543 (67) | -0.0084…+0.0732 | -0.41 (-0.89…+0.11) | 7 | -7.1 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.49 (+1.50…+5.26) | 0 | – |
| threes | **shadow** | 0.2691 / 0.2457 (39) | -0.0261…+0.0695 | 0.11 (-0.77…+1.45) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.703, threes 0.803, rebounds 0.916, pra 0.979, points 0.996, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 155 | 0.2496 | 0.2480 | 0.2984 | -0.0019…+0.0041 |
| p_modell_min | 155 | 0.3102 | 0.2480 | 0.2984 | +0.0584…+0.0715 |
| p_faktorer | 133 | 0.2518 | 0.2466 | 0.3075 | +0.0037…+0.0101 |
| p_faktorer_ra | 133 | 0.2961 | 0.2466 | 0.3075 | +0.0321…+0.1173 |
| p_betyg | 61 | 0.2447 | 0.2381 | 0.2845 | – |
| p_betyg_ra | 61 | 0.2982 | 0.2381 | 0.2845 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 11 | +16.1 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
