# NBA – utvärdering på framåtriktad data (2026-11-12T02:01:54+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 18 | 18 | 16 | 8 | 14 | +15.3 % | +10.7 % | 4.0 | 2.65 (+1.34…+4.09) | 4.22 | 0.18 | – |
| spel | 270 | 270 | 81 | 11 | 239 | +6.9 % | +3.8 % | 14.5 | 2.26 (+1.96…+2.59) | 1.92 | 0.05 | – |
| skugga | 738 | 738 | 88 | 11 | 609 | +5.5 % | +4.8 % | 12.9 | 1.37 (+1.15…+1.64) | 2.08 | 0.11 | – |
| modelltest | 681 | 681 | 89 | 11 | 589 | +10.5 % | +10.1 % | 17.5 | 1.26 (+1.00…+1.72) | 2.40 | 0.06 | 0.2511 / 0.2393 (91) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **insufficient_data** | 0.2101 / 0.2387 (22) | -0.0969…+0.0322 | 2.29 (+1.79…+2.95) | 2 | -9.0 % |
| blocks | **insufficient_data** | 0.0628 / 0.1640 (1) | – | 1.64 (+0.32…+2.78) | 0 | – |
| points | **degraded** | 0.2563 / 0.2357 (39) | +0.0145…+0.0420 | 0.78 (+0.55…+1.14) | 4 | +0.0 % |
| pr | **insufficient_data** | – | – | 0.04 (–) | 0 | – |
| pra | **insufficient_data** | 0.0788 / 0.2256 (1) | – | 0.92 (+0.00…+3.55) | 0 | – |
| ra | **insufficient_data** | – | – | 0.00 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2714 / 0.2464 (12) | -0.0423…+0.1075 | 1.26 (+0.81…+1.69) | 2 | +3.5 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.11…+3.75) | 0 | – |
| threes | **insufficient_data** | 0.2947 / 0.2464 (12) | -0.1688…+0.1410 | 1.48 (+0.74…+2.67) | 6 | +37.5 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 6 | -9.3 % | 2.07 |
| 2.00–2.50 | 8 | +33.8 % | 3.05 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
