# NBA – utvärdering på framåtriktad data (2026-11-12T03:58:43+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe legacy (95 %) | CLV pe verifierad | Verifierad täckning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 18 | 18 | 16 | 8 | 17 | +6.3 % | +2.2 % | 4.0 | 2.78 (+1.35…+4.17) | 4.45 | 0.22 | – |
| spel | 271 | 271 | 81 | 11 | 247 | +6.9 % | +3.9 % | 14.5 | 2.24 (+1.93…+2.56) | 1.71 | 0.07 | – |
| skugga | 739 | 739 | 88 | 11 | 638 | +4.8 % | +4.7 % | 12.9 | 1.36 (+1.15…+1.60) | 1.87 | 0.13 | – |
| modelltest | 681 | 681 | 89 | 11 | 606 | +10.6 % | +10.4 % | 17.5 | 1.28 (+1.00…+1.68) | 2.23 | 0.09 | 0.2478 / 0.2377 (108) |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **insufficient_data** | 0.1990 / 0.2384 (25) | -0.1055…+0.0193 | 2.37 (+1.79…+3.15) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.0628 / 0.1640 (1) | – | 1.63 (+0.32…+2.39) | 0 | – |
| points | **degraded** | 0.2532 / 0.2353 (43) | +0.0085…+0.0324 | 0.79 (+0.55…+1.18) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.2803 / 0.2480 (3) | – | 0.34 (–) | 0 | – |
| pra | **insufficient_data** | 0.0788 / 0.2256 (1) | – | 0.92 (+0.00…+3.55) | 0 | – |
| ra | **insufficient_data** | – | – | -0.23 (–) | 0 | – |
| rebounds | **insufficient_data** | 0.2636 / 0.2350 (16) | -0.0218…+0.0830 | 1.24 (+0.80…+1.60) | 3 | +33.3 % |
| steals | **insufficient_data** | 0.3250 / 0.2582 (4) | -0.0535…+0.2201 | 1.96 (+0.10…+3.75) | 0 | – |
| threes | **insufficient_data** | 0.2936 / 0.2442 (15) | -0.0945…+0.1204 | 1.46 (+0.74…+2.58) | 6 | +37.5 % |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 7 | +5.3 % | 2.45 |
| 2.00–2.50 | 10 | +7.0 % | 3.05 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
