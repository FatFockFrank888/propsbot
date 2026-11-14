# NBA – utvärdering på framåtriktad data (2026-11-14T03:31:48+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 329 | 329 | 93 | 13 | 283 | +5.2 % | +2.9 % | 14.5 | 2.36 (+2.04…+2.67) | 2.60 | 0.23 | – |
| skugga | 879 | 879 | 101 | 13 | 763 | +4.8 % | +4.8 % | 12.9 | 1.42 (+1.21…+1.65) | 1.79 | 0.27 | – |
| modelltest | 795 | 795 | 102 | 13 | 694 | +10.9 % | +10.8 % | 17.5 | 1.35 (+1.07…+1.72) | 1.94 | 0.22 | 0.2524 / 0.2391 (196) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2052 / 0.2289 (37) | -0.0785…+0.0540 | 2.35 (+1.81…+3.06) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2583 / 0.2400 (70) | -0.0057…+0.0499 | 0.84 (+0.59…+1.19) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3109 / 0.2497 (9) | – | 0.46 (+0.34…+0.74) | 0 | – |
| pra | **insufficient_data** | 0.3490 / 0.2462 (8) | -0.1571…+0.1999 | 1.16 (-0.48…+2.00) | 0 | – |
| ra | **insufficient_data** | 0.2006 / 0.2325 (12) | – | 1.97 (-0.23…+3.02) | 0 | – |
| rebounds | **insufficient_data** | 0.2487 / 0.2401 (26) | -0.0511…+0.0492 | 1.38 (+0.92…+1.78) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3008 / 0.2693 (5) | -0.0814…+0.1517 | 2.04 (+0.28…+3.71) | 0 | – |
| threes | **insufficient_data** | 0.2812 / 0.2459 (25) | -0.0537…+0.0943 | 1.61 (+0.89…+2.69) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 2 marknader: assists 0.266, points 0.932

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
