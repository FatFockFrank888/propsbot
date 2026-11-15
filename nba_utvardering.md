# NBA – utvärdering på framåtriktad data (2026-11-15T03:51:10+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 341 | 341 | 97 | 14 | 316 | +5.3 % | +3.3 % | 14.5 | 2.38 (+2.07…+2.69) | 2.65 | 0.26 | – |
| skugga | 923 | 923 | 106 | 14 | 848 | +2.4 % | +2.7 % | 23.9 | 1.41 (+1.21…+1.62) | 1.70 | 0.31 | – |
| modelltest | 838 | 838 | 107 | 14 | 761 | +9.3 % | +9.2 % | 17.5 | 1.38 (+1.11…+1.74) | 1.94 | 0.26 | 0.2630 / 0.2412 (263) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2397 / 0.2342 (46) | -0.0673…+0.0825 | 2.41 (+1.89…+3.06) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2686 / 0.2399 (90) | -0.0080…+0.0624 | 0.87 (+0.64…+1.22) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3168 / 0.2507 (18) | +0.0432…+0.0970 | 0.61 (+0.37…+1.03) | 0 | – |
| pra | **insufficient_data** | 0.3042 / 0.2532 (15) | -0.1133…+0.1128 | 1.18 (-0.18…+1.93) | 0 | – |
| ra | **insufficient_data** | 0.2211 / 0.2304 (17) | -0.0875…+0.0527 | 1.78 (+0.11…+2.81) | 0 | – |
| rebounds | **shadow** | 0.2435 / 0.2411 (40) | -0.0325…+0.0424 | 1.42 (+1.00…+1.84) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3008 / 0.2693 (5) | -0.0814…+0.1378 | 1.87 (+0.28…+3.45) | 0 | – |
| threes | **insufficient_data** | 0.2820 / 0.2504 (28) | -0.0441…+0.0894 | 1.63 (+0.92…+2.69) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 3 marknader: assists 0.528, rebounds 0.548, points 0.935

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 8 | 0.2230 | 0.2282 | 0.2127 | – |
| p_modell_min | 8 | 0.2279 | 0.2282 | 0.2127 | – |
| p_faktorer | 2 | 0.1992 | 0.2072 | 0.2472 | – |
| p_faktorer_ra | 2 | 0.1426 | 0.2072 | 0.2472 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
