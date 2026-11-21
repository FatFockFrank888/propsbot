# NBA – utvärdering på framåtriktad data (2026-11-21T00:56:52+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 38 | 38 | 32 | 15 | 34 | -0.8 % | +0.4 % | 5.2 | 3.45 (+2.65…+4.30) | 3.46 | 0.94 | +88.9 % | 2.53 | – |
| spel | 460 | 460 | 140 | 20 | 420 | +4.1 % | +2.0 % | 14.5 | 2.30 (+1.88…+2.80) | 2.15 | 0.82 | +78.3 % | 2.66 | – |
| skugga | 1408 | 1408 | 153 | 20 | 1275 | +3.5 % | +4.0 % | 39.8 | 0.79 (+0.55…+1.04) | 0.69 | 0.83 | +65.8 % | 1.70 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1083 | +4.7 % | +4.7 % | 34.4 | -0.03 (-0.37…+0.38) | -0.12 | 0.82 | +46.0 % | 1.77 | 0.2719 / 0.2436 (585) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 306 | 1.08 (+0.36…+1.53) | +71.6 % | +3.6 % |
| blocks | **ok** | 21 | 3.93 (+2.39…+4.88) | +95.0 % | +15.4 % |
| pa | **osäker** | 31 | -0.09 (-1.68…+0.55) | +57.7 % | -12.8 % |
| points | **ok** | 700 | 1.20 (+0.71…+1.46) | +66.7 % | +1.8 % |
| pr | **osäker** | 70 | 1.26 (-0.21…+2.40) | +70.1 % | +9.9 % |
| pra | **osäker** | 34 | 0.69 (-0.21…+2.07) | +63.6 % | -19.6 % |
| ra | **osäker** | 90 | 0.40 (-1.25…+0.75) | +60.5 % | +14.2 % |
| rebounds | **ok** | 390 | 1.05 (+0.66…+1.39) | +71.5 % | -2.5 % |
| steals | **ok** | 36 | 4.49 (+3.05…+8.38) | +91.2 % | +45.7 % |
| threes | **ok** | 228 | 1.39 (+0.63…+2.01) | +68.9 % | +11.7 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 16 | 3.98 | -13.7 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 86 | 3.05 | -2.2 % |
| spel | borttagen | 57 | 3.07 | -14.5 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 329 | 0.24 | +6.3 % |
| skugga | borttagen | 166 | 1.02 | -1.5 % |
| skugga | flyttad linje (för oss) | 183 | 4.75 | +18.4 % |
| skugga | flyttad linje (mot oss) | 46 | -4.72 | -13.1 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 231 | -0.02 | -4.1 % |
| modelltest | borttagen | 144 | 0.31 | +2.8 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2408 / 0.2307 (91) | -0.0354…+0.0565 | 1.05 (+0.27…+1.86) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.2930 / 0.2521 (23) | -0.0079…+0.0669 | -1.56 (-2.40…-1.05) | 0 | – |
| points | **shadow** | 0.2622 / 0.2413 (163) | -0.0083…+0.0497 | -0.45 (-0.87…+0.15) | 6 | -1.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0807 | -0.23 (-1.82…+1.28) | 1 | +86.0 % |
| pra | **shadow** | 0.3191 / 0.2506 (43) | -0.0125…+0.1174 | -0.08 (-0.92…+0.90) | 1 | -100.0 % |
| ra | **shadow** | 0.2371 / 0.2427 (38) | -0.0492…+0.0477 | 0.10 (-0.92…+0.94) | 0 | – |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0027…+0.0680 | -0.33 (-0.76…+0.11) | 10 | +5.2 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0177…+0.1280 | 3.50 (+1.74…+5.09) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0106…+0.0622 | 0.11 (-0.70…+1.23) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.398, assists 0.672, threes 0.914, pra 0.955, points 0.969, rebounds 0.979, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 330 | 0.2454 | 0.2451 | 0.2776 | -0.0012…+0.0024 |
| p_modell_min | 330 | 0.2863 | 0.2451 | 0.2776 | +0.0225…+0.0617 |
| p_faktorer | 308 | 0.2453 | 0.2443 | 0.2800 | -0.0020…+0.0046 |
| p_faktorer_ra | 308 | 0.2736 | 0.2443 | 0.2800 | +0.0129…+0.0553 |
| p_betyg | 236 | 0.2420 | 0.2414 | 0.2657 | -0.0033…+0.0060 |
| p_betyg_ra | 236 | 0.2786 | 0.2414 | 0.2657 | +0.0130…+0.0690 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 15 | +10.1 % | 4.00 |
| 2.00–2.50 | 16 | -8.0 % | 2.86 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
