# NBA – utvärdering på framåtriktad data (2026-11-14T01:20:57+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 326 | 326 | 93 | 13 | 278 | +4.8 % | +2.3 % | 14.5 | 2.38 (+2.06…+2.72) | 2.78 | 0.19 | – |
| skugga | 874 | 874 | 101 | 13 | 747 | +5.1 % | +4.8 % | 12.9 | 1.44 (+1.22…+1.70) | 1.94 | 0.23 | – |
| modelltest | 794 | 794 | 102 | 13 | 679 | +11.2 % | +11.1 % | 17.5 | 1.34 (+1.07…+1.72) | 2.02 | 0.18 | 0.2458 / 0.2368 (181) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.1992 / 0.2277 (35) | -0.0839…+0.0508 | 2.37 (+1.80…+3.17) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2522 / 0.2395 (65) | -0.0108…+0.0406 | 0.82 (+0.59…+1.17) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3109 / 0.2497 (9) | – | 0.32 (-0.33…+0.74) | 0 | – |
| pra | **insufficient_data** | 0.2572 / 0.2359 (5) | -0.1674…+0.1403 | 0.88 (-0.48…+2.03) | 0 | – |
| ra | **insufficient_data** | 0.2006 / 0.2325 (12) | – | 2.33 (-0.23…+3.02) | 0 | – |
| rebounds | **insufficient_data** | 0.2535 / 0.2394 (24) | -0.0480…+0.0580 | 1.32 (+0.91…+1.70) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 2.04 (+0.31…+3.67) | 0 | – |
| threes | **insufficient_data** | 0.2809 / 0.2379 (23) | -0.0505…+0.1032 | 1.61 (+0.92…+2.68) | 7 | +42.4 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
