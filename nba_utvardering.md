# NBA – utvärdering på framåtriktad data (2026-11-19T03:04:49+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 32 | 32 | 26 | 13 | 27 | -3.8 % | -2.7 % | 4.2 | 3.14 (+2.38…+3.96) | 3.20 | 0.97 | +87.1 % | 2.61 | – |
| spel | 429 | 429 | 127 | 18 | 371 | +4.0 % | +1.9 % | 14.5 | 2.23 (+1.79…+2.71) | 2.09 | 0.81 | +78.1 % | 2.65 | – |
| skugga | 1287 | 1287 | 140 | 18 | 1103 | +2.7 % | +3.1 % | 39.8 | 0.86 (+0.64…+1.11) | 0.77 | 0.84 | +66.2 % | 1.76 | – |
| modelltest | 1107 | 1107 | 141 | 18 | 954 | +4.9 % | +4.9 % | 34.2 | -0.02 (-0.37…+0.42) | -0.12 | 0.81 | +46.1 % | 1.81 | 0.2781 / 0.2438 (456) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 281 | 1.06 (+0.37…+1.56) | +71.7 % | +6.6 % |
| blocks | **ok** | 16 | 4.16 (+2.18…+5.64) | +93.8 % | +35.4 % |
| pa | **osäker** | 20 | -0.15 (-2.09…+0.51) | +55.0 % | -2.0 % |
| points | **ok** | 668 | 1.25 (+0.75…+1.50) | +67.3 % | +0.7 % |
| pr | **osäker** | 56 | 1.16 (-0.15…+2.76) | +69.6 % | -1.6 % |
| pra | **osäker** | 31 | 0.80 (-0.10…+2.35) | +64.5 % | -11.9 % |
| ra | **osäker** | 72 | 0.42 (-1.56…+0.60) | +63.4 % | +8.9 % |
| rebounds | **ok** | 360 | 1.07 (+0.73…+1.38) | +71.0 % | -5.4 % |
| steals | **ok** | 31 | 4.48 (+2.77…+9.18) | +90.3 % | +40.0 % |
| threes | **ok** | 213 | 1.47 (+0.69…+2.18) | +69.2 % | +12.0 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 12 | 3.52 | -22.8 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 67 | 2.98 | -7.0 % |
| spel | borttagen | 55 | 2.93 | -17.6 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 263 | 0.43 | +2.4 % |
| skugga | borttagen | 152 | 1.01 | +0.7 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +15.3 % |
| skugga | flyttad linje (mot oss) | 43 | -4.83 | -4.5 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 195 | 0.01 | -14.0 % |
| modelltest | borttagen | 140 | 0.34 | +8.7 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +12.2 % |
| modelltest | flyttad linje (mot oss) | 49 | -6.25 | -26.7 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2412 / 0.2323 (70) | -0.0471…+0.0674 | 1.08 (+0.24…+1.97) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3052 / 0.2584 (11) | – | -1.71 (-3.09…-1.35) | 0 | – |
| points | **degraded** | 0.2745 / 0.2416 (138) | +0.0074…+0.0561 | -0.42 (-0.82…+0.19) | 6 | -1.3 % |
| pr | **degraded** | 0.3126 / 0.2510 (45) | +0.0416…+0.0874 | -0.13 (-1.99…+1.51) | 0 | – |
| pra | **degraded** | 0.3356 / 0.2505 (33) | +0.0015…+0.1256 | -0.11 (-0.99…+1.04) | 0 | – |
| ra | **insufficient_data** | 0.2375 / 0.2378 (29) | -0.0588…+0.0718 | 0.04 (-1.16…+0.94) | 0 | – |
| rebounds | **shadow** | 0.2880 / 0.2513 (77) | -0.0017…+0.0794 | -0.38 (-0.79…+0.07) | 8 | -18.8 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0156…+0.1371 | 3.50 (+1.81…+5.16) | 0 | – |
| threes | **shadow** | 0.2693 / 0.2431 (41) | -0.0221…+0.0754 | 0.16 (-0.69…+1.38) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.623, threes 0.852, rebounds 0.974, pra 0.978, points 0.995, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 201 | 0.2474 | 0.2465 | 0.2952 | -0.0017…+0.0037 |
| p_modell_min | 201 | 0.3071 | 0.2465 | 0.2952 | +0.0566…+0.0657 |
| p_faktorer | 179 | 0.2493 | 0.2453 | 0.3016 | +0.0018…+0.0066 |
| p_faktorer_ra | 179 | 0.2930 | 0.2453 | 0.3016 | +0.0358…+0.0804 |
| p_betyg | 107 | 0.2452 | 0.2396 | 0.2845 | +0.0045…+0.0154 |
| p_betyg_ra | 107 | 0.3071 | 0.2396 | 0.2845 | +0.0588…+0.0781 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 12 | +6.4 % | 3.74 |
| 2.00–2.50 | 13 | -17.7 % | 2.54 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
