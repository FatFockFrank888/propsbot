# NBA – utvärdering på framåtriktad data (2026-11-19T00:34:48+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 28 | 28 | 24 | 13 | 27 | -3.8 % | -2.7 % | 4.2 | 2.86 (+2.21…+3.62) | 2.92 | 0.96 | +85.2 % | 2.59 | – |
| spel | 424 | 424 | 127 | 18 | 371 | +4.0 % | +1.9 % | 14.5 | 2.22 (+1.78…+2.70) | 2.08 | 0.80 | +78.4 % | 2.73 | – |
| skugga | 1279 | 1279 | 140 | 18 | 1103 | +2.7 % | +3.1 % | 39.8 | 0.89 (+0.65…+1.15) | 0.80 | 0.84 | +66.6 % | 1.81 | – |
| modelltest | 1099 | 1099 | 141 | 18 | 954 | +4.9 % | +4.9 % | 34.2 | 0.00 (-0.36…+0.45) | -0.09 | 0.81 | +46.0 % | 1.83 | 0.2781 / 0.2438 (456) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 280 | 1.01 (+0.33…+1.55) | +71.1 % | +6.6 % |
| blocks | **ok** | 16 | 4.16 (+2.19…+5.70) | +93.8 % | +35.4 % |
| pa | **osäker** | 20 | -0.46 (-2.15…+0.86) | +56.2 % | -2.0 % |
| points | **ok** | 668 | 1.26 (+0.76…+1.53) | +67.4 % | +0.7 % |
| pr | **osäker** | 54 | 1.21 (-0.39…+2.76) | +68.6 % | -1.6 % |
| pra | **osäker** | 29 | 0.21 (-1.69…+2.30) | +61.5 % | -11.9 % |
| ra | **osäker** | 71 | 0.55 (-1.56…+0.85) | +66.2 % | +8.9 % |
| rebounds | **ok** | 354 | 1.12 (+0.79…+1.42) | +71.9 % | -5.4 % |
| steals | **ok** | 31 | 4.51 (+2.75…+9.26) | +90.0 % | +40.0 % |
| threes | **ok** | 208 | 1.48 (+0.64…+2.23) | +70.1 % | +12.0 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 8 | 2.77 | -22.8 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 50 | 3.29 | -7.0 % |
| spel | borttagen | 54 | 2.91 | -17.6 % |
| spel | flyttad linje (för oss) | 40 | 4.50 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 216 | 0.56 | +2.4 % |
| skugga | borttagen | 142 | 1.01 | +0.7 % |
| skugga | flyttad linje (för oss) | 180 | 4.72 | +15.3 % |
| skugga | flyttad linje (mot oss) | 42 | -4.99 | -4.5 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 154 | 0.14 | -14.0 % |
| modelltest | borttagen | 132 | 0.30 | +8.7 % |
| modelltest | flyttad linje (för oss) | 110 | 4.48 | +12.2 % |
| modelltest | flyttad linje (mot oss) | 48 | -6.07 | -26.7 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2412 / 0.2323 (70) | -0.0482…+0.0683 | 1.02 (+0.17…+1.95) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3052 / 0.2584 (11) | – | -1.55 (-3.09…-0.60) | 0 | – |
| points | **degraded** | 0.2745 / 0.2416 (138) | +0.0071…+0.0548 | -0.45 (-0.84…+0.14) | 6 | -1.3 % |
| pr | **degraded** | 0.3126 / 0.2510 (45) | +0.0404…+0.0853 | 0.52 (-0.77…+1.69) | 0 | – |
| pra | **degraded** | 0.3356 / 0.2505 (33) | +0.0049…+0.1277 | -0.10 (-1.09…+1.01) | 0 | – |
| ra | **insufficient_data** | 0.2375 / 0.2378 (29) | -0.0569…+0.0671 | 0.08 (-1.10…+0.98) | 0 | – |
| rebounds | **shadow** | 0.2880 / 0.2513 (77) | -0.0003…+0.0818 | -0.36 (-0.80…+0.11) | 8 | -18.8 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0167…+0.1432 | 3.49 (+1.52…+5.26) | 0 | – |
| threes | **shadow** | 0.2693 / 0.2431 (41) | -0.0207…+0.0740 | 0.13 (-0.70…+1.42) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.631, threes 0.841, rebounds 0.971, pra 0.977, points 0.995, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 201 | 0.2474 | 0.2465 | 0.2952 | -0.0017…+0.0036 |
| p_modell_min | 201 | 0.3071 | 0.2465 | 0.2952 | +0.0568…+0.0657 |
| p_faktorer | 179 | 0.2493 | 0.2453 | 0.3016 | +0.0018…+0.0066 |
| p_faktorer_ra | 179 | 0.2930 | 0.2453 | 0.3016 | +0.0358…+0.0819 |
| p_betyg | 107 | 0.2452 | 0.2396 | 0.2845 | +0.0045…+0.0154 |
| p_betyg_ra | 107 | 0.3071 | 0.2396 | 0.2845 | +0.0588…+0.0781 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 12 | +6.4 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
