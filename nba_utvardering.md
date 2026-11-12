# NBA – utvärdering på framåtriktad data (2026-11-12T15:40:06+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 18 | 18 | 16 | 8 | 18 | +9.9 % | +6.2 % | 4.0 | 2.78 (+1.35…+4.17) | 4.45 | 0.22 | – |
| spel | 285 | 285 | 85 | 12 | 256 | +6.1 % | +3.3 % | 14.5 | 2.24 (+1.93…+2.56) | 1.71 | 0.07 | – |
| skugga | 768 | 768 | 92 | 12 | 703 | +4.6 % | +4.5 % | 12.9 | 1.36 (+1.15…+1.60) | 1.87 | 0.13 | – |
| modelltest | 702 | 702 | 93 | 12 | 644 | +11.2 % | +11.0 % | 17.5 | 1.28 (+1.00…+1.68) | 2.23 | 0.09 | 0.2420 / 0.2371 (146) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.1780 / 0.2267 (31) | -0.0978…+0.0156 | 2.37 (+1.79…+3.15) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **shadow** | 0.2416 / 0.2364 (56) | -0.0171…+0.0319 | 0.79 (+0.55…+1.18) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3000 / 0.2568 (6) | – | 0.34 (–) | 0 | – |
| pra | **insufficient_data** | 0.2967 / 0.2282 (4) | – | 0.92 (+0.00…+3.55) | 0 | – |
| ra | **insufficient_data** | 0.1290 / 0.2805 (2) | – | -0.23 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2634 / 0.2339 (21) | -0.0163…+0.0767 | 1.24 (+0.80…+1.60) | 3 | +33.3 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.75) | 0 | – |
| threes | **insufficient_data** | 0.3011 / 0.2518 (18) | -0.0817…+0.1204 | 1.46 (+0.74…+2.58) | 7 | +42.4 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 2.45 |
| 2.00–2.50 | 10 | +7.0 % | 3.05 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
