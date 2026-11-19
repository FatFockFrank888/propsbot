# NBA – utvärdering på framåtriktad data (2026-11-19T05:13:13+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 32 | 32 | 26 | 13 | 31 | -3.7 % | -5.1 % | 5.2 | 3.25 (+2.39…+4.16) | 3.32 | 0.97 | +87.5 % | 2.46 | – |
| spel | 429 | 429 | 127 | 18 | 402 | +3.7 % | +1.4 % | 14.5 | 2.23 (+1.79…+2.71) | 2.09 | 0.81 | +78.1 % | 2.65 | – |
| skugga | 1287 | 1287 | 140 | 18 | 1199 | +3.4 % | +3.7 % | 39.8 | 0.86 (+0.64…+1.11) | 0.77 | 0.84 | +66.2 % | 1.76 | – |
| modelltest | 1107 | 1107 | 141 | 18 | 1030 | +4.7 % | +4.6 % | 34.2 | -0.02 (-0.36…+0.43) | -0.12 | 0.81 | +46.1 % | 1.81 | 0.2753 / 0.2444 (532) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 281 | 1.06 (+0.34…+1.56) | +71.7 % | +5.7 % |
| blocks | **ok** | 16 | 4.16 (+2.21…+5.62) | +93.8 % | +26.3 % |
| pa | **osäker** | 20 | -0.15 (-2.09…+0.51) | +55.0 % | -8.4 % |
| points | **ok** | 668 | 1.25 (+0.74…+1.51) | +67.3 % | +2.5 % |
| pr | **osäker** | 56 | 1.16 (-0.11…+2.81) | +69.6 % | +3.4 % |
| pra | **osäker** | 31 | 0.80 (-0.11…+2.36) | +64.5 % | -26.0 % |
| ra | **osäker** | 72 | 0.42 (-1.48…+0.59) | +63.4 % | +14.1 % |
| rebounds | **ok** | 360 | 1.08 (+0.77…+1.38) | +71.1 % | -4.5 % |
| steals | **ok** | 31 | 4.48 (+2.78…+9.36) | +90.3 % | +40.0 % |
| threes | **ok** | 213 | 1.47 (+0.70…+2.13) | +69.2 % | +11.3 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 13 | 3.77 | -16.2 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 67 | 2.98 | -5.7 % |
| spel | borttagen | 55 | 2.93 | -17.1 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 263 | 0.43 | +6.7 % |
| skugga | borttagen | 152 | 1.01 | -3.1 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +18.4 % |
| skugga | flyttad linje (mot oss) | 43 | -4.83 | -9.0 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 195 | 0.01 | -6.9 % |
| modelltest | borttagen | 140 | 0.34 | +2.3 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 49 | -6.25 | -23.3 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2412 / 0.2322 (84) | -0.0389…+0.0576 | 1.08 (+0.22…+1.95) | 6 | -40.3 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3203 / 0.2545 (18) | +0.0406…+0.0956 | -1.71 (-3.09…-1.35) | 0 | – |
| points | **shadow** | 0.2636 / 0.2406 (152) | -0.0078…+0.0498 | -0.42 (-0.85…+0.18) | 6 | -1.3 % |
| pr | **degraded** | 0.3081 / 0.2521 (53) | +0.0362…+0.0795 | -0.13 (-1.90…+1.52) | 0 | – |
| pra | **degraded** | 0.3521 / 0.2533 (37) | +0.0304…+0.1416 | -0.11 (-1.03…+1.05) | 1 | -100.0 % |
| ra | **shadow** | 0.2357 / 0.2426 (35) | -0.0569…+0.0496 | 0.04 (-1.15…+0.95) | 0 | – |
| rebounds | **degraded** | 0.2826 / 0.2509 (94) | +0.0020…+0.0694 | -0.38 (-0.80…+0.06) | 9 | -5.6 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0087…+0.1420 | 3.50 (+1.82…+5.17) | 0 | – |
| threes | **shadow** | 0.2726 / 0.2466 (47) | -0.0142…+0.0655 | 0.16 (-0.67…+1.36) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.584, assists 0.636, threes 0.887, points 0.950, rebounds 0.980, pra 0.995, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 277 | 0.2473 | 0.2469 | 0.2853 | -0.0014…+0.0027 |
| p_modell_min | 277 | 0.2948 | 0.2469 | 0.2853 | +0.0292…+0.0637 |
| p_faktorer | 255 | 0.2481 | 0.2460 | 0.2889 | -0.0010…+0.0057 |
| p_faktorer_ra | 255 | 0.2837 | 0.2460 | 0.2889 | +0.0233…+0.0633 |
| p_betyg | 183 | 0.2447 | 0.2430 | 0.2739 | -0.0028…+0.0068 |
| p_betyg_ra | 183 | 0.2903 | 0.2430 | 0.2739 | +0.0198…+0.0776 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 14 | +4.6 % | 3.74 |
| 2.00–2.50 | 15 | -15.3 % | 2.81 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
