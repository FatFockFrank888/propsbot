# NBA – utvärdering på framåtriktad data (2026-11-19T04:11:57+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 32 | 32 | 26 | 13 | 27 | -3.8 % | -2.7 % | 4.2 | 3.25 (+2.39…+4.16) | 3.32 | 0.97 | +87.5 % | 2.46 | – |
| spel | 429 | 429 | 127 | 18 | 390 | +3.4 % | +1.0 % | 14.5 | 2.23 (+1.79…+2.71) | 2.09 | 0.81 | +78.1 % | 2.65 | – |
| skugga | 1287 | 1287 | 140 | 18 | 1169 | +4.0 % | +4.4 % | 39.8 | 0.86 (+0.64…+1.11) | 0.77 | 0.84 | +66.2 % | 1.76 | – |
| modelltest | 1107 | 1107 | 141 | 18 | 1000 | +5.4 % | +5.3 % | 34.2 | -0.02 (-0.36…+0.43) | -0.12 | 0.81 | +46.1 % | 1.81 | 0.2741 / 0.2438 (502) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 281 | 1.06 (+0.34…+1.56) | +71.7 % | +7.0 % |
| blocks | **ok** | 16 | 4.16 (+2.21…+5.62) | +93.8 % | +26.3 % |
| pa | **osäker** | 20 | -0.15 (-2.09…+0.51) | +55.0 % | -14.3 % |
| points | **ok** | 668 | 1.25 (+0.74…+1.51) | +67.3 % | +2.2 % |
| pr | **osäker** | 56 | 1.16 (-0.11…+2.81) | +69.6 % | +5.6 % |
| pra | **osäker** | 31 | 0.80 (-0.11…+2.36) | +64.5 % | -18.7 % |
| ra | **osäker** | 72 | 0.42 (-1.48…+0.59) | +63.4 % | +14.8 % |
| rebounds | **ok** | 360 | 1.08 (+0.77…+1.38) | +71.1 % | -5.1 % |
| steals | **ok** | 31 | 4.48 (+2.78…+9.36) | +90.3 % | +40.0 % |
| threes | **ok** | 213 | 1.47 (+0.70…+2.13) | +69.2 % | +13.2 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 13 | 3.77 | -22.8 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 67 | 2.98 | -6.3 % |
| spel | borttagen | 55 | 2.93 | -19.5 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +2.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 263 | 0.43 | +8.8 % |
| skugga | borttagen | 152 | 1.01 | -1.8 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +18.4 % |
| skugga | flyttad linje (mot oss) | 43 | -4.83 | -6.8 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 195 | 0.01 | -4.9 % |
| modelltest | borttagen | 140 | 0.34 | +4.9 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +12.7 % |
| modelltest | flyttad linje (mot oss) | 49 | -6.25 | -25.8 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2360 / 0.2326 (80) | -0.0453…+0.0558 | 1.08 (+0.22…+1.95) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3192 / 0.2571 (16) | +0.0406…+0.0958 | -1.71 (-3.09…-1.35) | 0 | – |
| points | **shadow** | 0.2672 / 0.2407 (146) | -0.0030…+0.0507 | -0.42 (-0.85…+0.18) | 6 | -1.3 % |
| pr | **degraded** | 0.3028 / 0.2496 (47) | +0.0223…+0.0795 | -0.13 (-1.90…+1.52) | 0 | – |
| pra | **degraded** | 0.3440 / 0.2524 (35) | +0.0204…+0.1336 | -0.11 (-1.03…+1.05) | 0 | – |
| ra | **shadow** | 0.2392 / 0.2435 (34) | -0.0563…+0.0534 | 0.04 (-1.15…+0.95) | 0 | – |
| rebounds | **degraded** | 0.2835 / 0.2497 (88) | +0.0022…+0.0718 | -0.38 (-0.80…+0.06) | 8 | -18.8 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0087…+0.1420 | 3.50 (+1.82…+5.17) | 0 | – |
| threes | **shadow** | 0.2686 / 0.2446 (44) | -0.0197…+0.0664 | 0.16 (-0.67…+1.36) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: assists 0.548, ra 0.584, threes 0.840, points 0.964, rebounds 0.980, pra 0.991, pr 0.999

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 247 | 0.2467 | 0.2460 | 0.2839 | -0.0014…+0.0028 |
| p_modell_min | 247 | 0.2950 | 0.2460 | 0.2839 | +0.0250…+0.0637 |
| p_faktorer | 225 | 0.2476 | 0.2450 | 0.2879 | -0.0005…+0.0057 |
| p_faktorer_ra | 225 | 0.2858 | 0.2450 | 0.2879 | +0.0259…+0.0633 |
| p_betyg | 153 | 0.2432 | 0.2409 | 0.2695 | -0.0037…+0.0068 |
| p_betyg_ra | 153 | 0.2923 | 0.2409 | 0.2695 | +0.0157…+0.0776 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 12 | +6.4 % | 3.74 |
| 2.00–2.50 | 13 | -17.7 % | 2.81 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
