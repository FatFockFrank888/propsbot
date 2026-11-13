# NBA – utvärdering på framåtriktad data (2026-11-13T18:30:37+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 315 | 315 | 92 | 13 | 278 | +4.8 % | +2.3 % | 14.5 | 2.33 (+2.00…+2.67) | 2.61 | 0.14 | – |
| skugga | 851 | 851 | 101 | 13 | 747 | +5.1 % | +4.8 % | 12.9 | 1.37 (+1.17…+1.60) | 1.77 | 0.18 | – |
| modelltest | 774 | 774 | 102 | 13 | 679 | +11.2 % | +11.1 % | 17.5 | 1.30 (+1.03…+1.70) | 2.02 | 0.13 | 0.2458 / 0.2368 (181) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.1992 / 0.2277 (35) | -0.0827…+0.0464 | 2.36 (+1.77…+3.12) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2522 / 0.2395 (65) | -0.0113…+0.0417 | 0.79 (+0.56…+1.16) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3109 / 0.2497 (9) | – | 0.49 (+0.26…+0.90) | 0 | – |
| pra | **insufficient_data** | 0.2572 / 0.2359 (5) | -0.1674…+0.1403 | 0.38 (-1.17…+2.31) | 0 | – |
| ra | **insufficient_data** | 0.2006 / 0.2325 (12) | – | 2.48 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2535 / 0.2394 (24) | -0.0480…+0.0580 | 1.24 (+0.82…+1.58) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.75) | 0 | – |
| threes | **insufficient_data** | 0.2809 / 0.2379 (23) | -0.0505…+0.1032 | 1.48 (+0.80…+2.49) | 7 | +42.4 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 11 | -2.7 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
