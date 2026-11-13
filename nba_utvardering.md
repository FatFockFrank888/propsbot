# NBA – utvärdering på framåtriktad data (2026-11-13T03:42:44+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 18 | +9.9 % | +6.2 % | 4.0 | 2.64 (+1.16…+4.05) | 3.56 | 0.26 | – |
| spel | 293 | 293 | 85 | 12 | 266 | +5.9 % | +2.9 % | 14.5 | 2.33 (+2.00…+2.67) | 2.61 | 0.14 | – |
| skugga | 783 | 783 | 92 | 12 | 725 | +5.3 % | +5.3 % | 12.9 | 1.37 (+1.17…+1.60) | 1.77 | 0.18 | – |
| modelltest | 717 | 717 | 93 | 12 | 660 | +11.7 % | +11.6 % | 17.5 | 1.30 (+1.03…+1.70) | 2.02 | 0.13 | 0.2419 / 0.2364 (162) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.1935 / 0.2273 (33) | -0.0832…+0.0429 | 2.36 (+1.77…+3.12) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2383 / 0.2373 (61) | -0.0205…+0.0229 | 0.79 (+0.56…+1.16) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.2961 / 0.2490 (8) | – | 0.49 (+0.26…+0.90) | 0 | – |
| pra | **insufficient_data** | 0.2967 / 0.2282 (4) | – | 0.38 (-1.17…+2.31) | 0 | – |
| ra | **insufficient_data** | 0.1931 / 0.2335 (7) | – | 2.48 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2578 / 0.2357 (22) | -0.0407…+0.0671 | 1.24 (+0.82…+1.59) | 3 | +33.3 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.80) | 0 | – |
| threes | **insufficient_data** | 0.2942 / 0.2476 (19) | -0.0832…+0.1156 | 1.48 (+0.83…+2.55) | 7 | +42.4 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 10 | +7.0 % | 2.77 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
