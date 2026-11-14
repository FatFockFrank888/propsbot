# NBA – utvärdering på framåtriktad data (2026-11-14T15:36:08+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 334 | 334 | 96 | 14 | 312 | +5.4 % | +3.5 % | 14.5 | 2.36 (+2.04…+2.67) | 2.60 | 0.23 | – |
| skugga | 890 | 890 | 105 | 14 | 840 | +3.1 % | +3.4 % | 19.6 | 1.42 (+1.21…+1.65) | 1.79 | 0.27 | – |
| modelltest | 813 | 813 | 107 | 14 | 754 | +9.1 % | +8.9 % | 17.5 | 1.35 (+1.07…+1.72) | 1.94 | 0.22 | 0.2649 / 0.2418 (256) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2430 / 0.2359 (45) | -0.0732…+0.0903 | 2.35 (+1.81…+3.06) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2717 / 0.2404 (88) | -0.0020…+0.0627 | 0.84 (+0.59…+1.19) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3168 / 0.2507 (18) | +0.0432…+0.0970 | 0.46 (+0.34…+0.74) | 0 | – |
| pra | **insufficient_data** | 0.3306 / 0.2532 (12) | -0.1571…+0.1243 | 1.16 (-0.48…+2.06) | 0 | – |
| ra | **insufficient_data** | 0.2109 / 0.2327 (16) | -0.1515…+0.0085 | 1.97 (-0.23…+3.02) | 0 | – |
| rebounds | **shadow** | 0.2435 / 0.2411 (40) | -0.0333…+0.0465 | 1.38 (+0.92…+1.80) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3008 / 0.2693 (5) | -0.0814…+0.1517 | 2.04 (+0.31…+3.71) | 0 | – |
| threes | **insufficient_data** | 0.2820 / 0.2504 (28) | -0.0435…+0.0911 | 1.61 (+0.92…+2.67) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 3 marknader: rebounds 0.547, assists 0.555, points 0.959

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 1 | 0.2820 | 0.2820 | 0.3672 | – |
| p_modell_min | 1 | 0.4614 | 0.2820 | 0.3672 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
