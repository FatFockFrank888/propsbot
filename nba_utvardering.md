# NBA – utvärdering på framåtriktad data (2026-11-20T16:21:59+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 34 | 34 | 28 | 14 | 34 | -0.8 % | +0.4 % | 5.2 | 3.36 (+2.53…+4.23) | 3.36 | 0.94 | +88.2 % | 2.47 | – |
| spel | 447 | 447 | 138 | 20 | 420 | +4.1 % | +2.0 % | 14.5 | 2.26 (+1.85…+2.73) | 2.11 | 0.81 | +78.0 % | 2.59 | – |
| skugga | 1380 | 1380 | 153 | 20 | 1275 | +3.5 % | +4.0 % | 39.8 | 0.82 (+0.57…+1.07) | 0.72 | 0.83 | +65.8 % | 1.72 | – |
| modelltest | 1149 | 1149 | 149 | 20 | 1083 | +4.7 % | +4.7 % | 34.4 | -0.03 (-0.36…+0.39) | -0.13 | 0.82 | +46.1 % | 1.75 | 0.2719 / 0.2436 (585) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 298 | 1.05 (+0.38…+1.55) | +71.3 % | +3.6 % |
| blocks | **ok** | 20 | 3.96 (+2.40…+5.07) | +94.7 % | +15.4 % |
| pa | **osäker** | 26 | -0.01 (-1.71…+0.81) | +56.5 % | -12.8 % |
| points | **ok** | 691 | 1.19 (+0.68…+1.44) | +66.9 % | +1.8 % |
| pr | **osäker** | 67 | 1.24 (-0.21…+2.40) | +69.2 % | +9.9 % |
| pra | **osäker** | 33 | 0.69 (-0.16…+2.09) | +63.6 % | -19.6 % |
| ra | **osäker** | 84 | 0.28 (-1.45…+0.45) | +61.0 % | +14.2 % |
| rebounds | **ok** | 382 | 1.12 (+0.81…+1.46) | +71.5 % | -2.5 % |
| steals | **ok** | 33 | 4.51 (+2.98…+8.62) | +90.9 % | +45.7 % |
| threes | **ok** | 227 | 1.39 (+0.62…+1.99) | +68.5 % | +11.7 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 14 | 3.84 | -13.7 % |
| live | borttagen | 2 | 3.27 | -7.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 77 | 2.98 | -2.2 % |
| spel | borttagen | 56 | 2.98 | -14.5 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 304 | 0.31 | +6.3 % |
| skugga | borttagen | 161 | 1.01 | -1.5 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +18.4 % |
| skugga | flyttad linje (mot oss) | 45 | -4.69 | -13.1 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 226 | -0.04 | -4.1 % |
| modelltest | borttagen | 142 | 0.36 | +2.8 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2408 / 0.2307 (91) | -0.0348…+0.0549 | 1.06 (+0.26…+1.92) | 7 | -48.9 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.2930 / 0.2521 (23) | -0.0079…+0.0669 | -1.52 (-2.40…-0.91) | 0 | – |
| points | **shadow** | 0.2622 / 0.2413 (163) | -0.0086…+0.0495 | -0.45 (-0.87…+0.14) | 6 | -1.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0801 | -0.23 (-1.87…+1.27) | 1 | +86.0 % |
| pra | **shadow** | 0.3191 / 0.2506 (43) | -0.0079…+0.1205 | -0.00 (-0.84…+1.02) | 1 | -100.0 % |
| ra | **shadow** | 0.2371 / 0.2427 (38) | -0.0492…+0.0467 | -0.01 (-1.08…+0.86) | 0 | – |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0018…+0.0678 | -0.33 (-0.76…+0.11) | 10 | +5.2 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0174…+0.1289 | 3.50 (+1.66…+5.14) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0124…+0.0629 | 0.11 (-0.72…+1.25) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.538, assists 0.662, threes 0.919, pra 0.960, points 0.970, rebounds 0.984, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 330 | 0.2454 | 0.2451 | 0.2776 | -0.0012…+0.0024 |
| p_modell_min | 330 | 0.2863 | 0.2451 | 0.2776 | +0.0218…+0.0617 |
| p_faktorer | 308 | 0.2453 | 0.2443 | 0.2800 | -0.0018…+0.0047 |
| p_faktorer_ra | 308 | 0.2736 | 0.2443 | 0.2800 | +0.0122…+0.0547 |
| p_betyg | 236 | 0.2420 | 0.2414 | 0.2657 | -0.0033…+0.0060 |
| p_betyg_ra | 236 | 0.2786 | 0.2414 | 0.2657 | +0.0130…+0.0707 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 15 | +10.1 % | 3.85 |
| 2.00–2.50 | 16 | -8.0 % | 2.81 |
| 2.50–3.00 | 3 | -16.7 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
