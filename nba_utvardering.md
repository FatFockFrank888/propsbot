# NBA – utvärdering på framåtriktad data (2026-11-15T12:15:04+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 342 | 342 | 98 | 15 | 323 | +4.9 % | +2.8 % | 14.5 | 2.38 (+2.07…+2.69) | 2.65 | 0.26 | – |
| skugga | 940 | 940 | 112 | 15 | 878 | +2.2 % | +2.4 % | 27.0 | 1.41 (+1.21…+1.62) | 1.70 | 0.31 | – |
| modelltest | 853 | 853 | 113 | 15 | 792 | +8.8 % | +8.6 % | 17.5 | 1.38 (+1.11…+1.74) | 1.94 | 0.26 | 0.2703 / 0.2430 (294) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2368 / 0.2359 (52) | -0.0621…+0.0706 | 2.41 (+1.89…+3.06) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2675 / 0.2398 (99) | -0.0044…+0.0601 | 0.87 (+0.64…+1.22) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3262 / 0.2496 (22) | +0.0526…+0.1123 | 0.61 (+0.38…+1.03) | 0 | – |
| pra | **insufficient_data** | 0.3042 / 0.2532 (15) | -0.1133…+0.1128 | 1.18 (-0.18…+1.88) | 0 | – |
| ra | **insufficient_data** | 0.2517 / 0.2364 (19) | -0.0618…+0.1468 | 1.78 (+0.11…+2.81) | 0 | – |
| rebounds | **shadow** | 0.2799 / 0.2515 (48) | -0.0213…+0.0965 | 1.42 (+0.99…+1.83) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 1.87 (+0.29…+3.49) | 0 | – |
| threes | **insufficient_data** | 0.2782 / 0.2487 (29) | -0.0428…+0.0859 | 1.63 (+0.94…+2.67) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 3 marknader: assists 0.488, rebounds 0.854, points 0.950

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 39 | 0.2556 | 0.2515 | 0.3082 | – |
| p_modell_min | 39 | 0.3120 | 0.2515 | 0.3082 | – |
| p_faktorer | 17 | 0.2547 | 0.2447 | 0.3921 | – |
| p_faktorer_ra | 17 | 0.3619 | 0.2447 | 0.3921 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
