# NBA – utvärdering på framåtriktad data (2026-11-13T05:06:25+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 18 | +9.9 % | +6.2 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 295 | 295 | 86 | 13 | 272 | +5.7 % | +2.7 % | 14.5 | 2.33 (+2.00…+2.67) | 2.61 | 0.14 | – |
| skugga | 786 | 786 | 93 | 13 | 735 | +6.0 % | +5.8 % | 12.9 | 1.37 (+1.17…+1.60) | 1.77 | 0.18 | – |
| modelltest | 720 | 720 | 94 | 13 | 668 | +11.8 % | +11.8 % | 17.5 | 1.30 (+1.03…+1.70) | 2.02 | 0.13 | 0.2381 / 0.2354 (170) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.1901 / 0.2257 (34) | -0.0835…+0.0343 | 2.36 (+1.77…+3.12) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2360 / 0.2372 (62) | -0.0254…+0.0229 | 0.79 (+0.56…+1.16) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.2961 / 0.2490 (8) | – | 0.49 (+0.26…+0.90) | 0 | – |
| pra | **insufficient_data** | 0.2967 / 0.2282 (4) | – | 0.38 (-1.17…+2.31) | 0 | – |
| ra | **insufficient_data** | 0.1934 / 0.2417 (9) | – | 2.48 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2516 / 0.2359 (23) | -0.0514…+0.0587 | 1.24 (+0.82…+1.59) | 3 | +33.3 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.80) | 0 | – |
| threes | **insufficient_data** | 0.2823 / 0.2380 (22) | -0.0517…+0.1064 | 1.48 (+0.83…+2.55) | 7 | +42.4 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 10 | +7.0 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
