# NBA – utvärdering på framåtriktad data (2026-11-11T12:02:35+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 15 | 15 | 14 | 8 | 14 | +15.3 % | +10.7 % | 4.0 | 2.31 (+0.94…+4.09) | – | 0.00 | – |
| spel | 253 | 253 | 75 | 11 | 239 | +6.9 % | +3.8 % | 14.5 | 2.28 (+1.96…+2.62) | – | 0.00 | – |
| skugga | 655 | 655 | 81 | 11 | 609 | +5.5 % | +4.8 % | 12.9 | 1.29 (+1.10…+1.53) | – | 0.00 | – |
| modelltest | 629 | 629 | 81 | 11 | 589 | +10.5 % | +10.1 % | 17.5 | 1.19 (+0.95…+1.57) | – | 0.00 | 0.2511 / 0.2393 (91) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **insufficient_data** | 0.2101 / 0.2387 (22) | -0.0969…+0.0322 | 2.10 (+1.62…+2.59) | 2 | -9.0 % |
| blocks | **insufficient_data** | 0.0628 / 0.1640 (1) | – | 0.50 (–) | 0 | – |
| points | **degraded** | 0.2563 / 0.2357 (39) | +0.0145…+0.0420 | 0.74 (+0.51…+1.10) | 4 | +0.0 % |
| pr | **insufficient_data** | – | – | 0.26 (–) | 0 | – |
| pra | **insufficient_data** | 0.0788 / 0.2256 (1) | – | 2.31 (–) | 0 | – |
| ra | **insufficient_data** | – | – | – (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2714 / 0.2464 (12) | -0.0423…+0.1075 | 1.18 (+0.71…+1.52) | 2 | +3.5 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.91) | 0 | – |
| threes | **insufficient_data** | 0.2947 / 0.2464 (12) | -0.1688…+0.1410 | 1.34 (+0.64…+2.41) | 6 | +37.5 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 6 | -9.3 % | 1.24 |
| 2.00–2.50 | 8 | +33.8 % | 3.11 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
