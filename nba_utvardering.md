# NBA – utvärdering på framåtriktad data (2026-11-17T05:09:14+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 26 | 26 | 22 | 11 | 26 | -0.1 % | +0.2 % | 4.0 | 2.83 (+2.14…+3.59) | 2.89 | 0.96 | +84.6 % | 2.56 | – |
| spel | 381 | 381 | 112 | 17 | 360 | +4.7 % | +2.9 % | 14.5 | 2.18 (+1.70…+2.75) | 2.04 | 0.81 | +77.4 % | 2.59 | – |
| skugga | 1100 | 1100 | 124 | 17 | 1034 | +1.5 % | +1.3 % | 39.8 | 0.88 (+0.63…+1.18) | 0.82 | 0.85 | +66.0 % | 1.77 | – |
| modelltest | 962 | 962 | 125 | 17 | 903 | +5.5 % | +5.3 % | 34.2 | -0.05 (-0.42…+0.47) | -0.14 | 0.81 | +44.8 % | 1.81 | 0.2782 / 0.2444 (405) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 240 | 0.96 (+0.17…+1.59) | +69.2 % | +4.7 % |
| blocks | **ok** | 14 | 4.14 (+2.64…+5.27) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 7 | 0.59 (–) | +71.4 % | -15.1 % |
| points | **ok** | 608 | 1.19 (+0.71…+1.57) | +67.0 % | +1.1 % |
| pr | **osäker** | 38 | 1.65 (-0.93…+3.51) | +73.7 % | -6.2 % |
| pra | **osäker** | 24 | 0.63 (-0.36…+2.72) | +66.7 % | -11.9 % |
| ra | **osäker** | 59 | 0.38 (-2.04…+0.71) | +63.2 % | +6.2 % |
| rebounds | **ok** | 307 | 1.05 (+0.72…+1.39) | +70.9 % | -5.0 % |
| steals | **ok** | 27 | 4.85 (+3.13…+10.36) | +88.9 % | +31.8 % |
| threes | **ok** | 183 | 1.57 (+0.66…+2.25) | +68.9 % | +12.3 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 7 | 2.64 | -11.7 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 28 | 3.86 | -5.3 % |
| spel | borttagen | 47 | 2.98 | -15.0 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 123 | 0.58 | -5.9 % |
| skugga | borttagen | 119 | 1.05 | +0.0 % |
| skugga | flyttad linje (för oss) | 168 | 4.63 | +14.5 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 78 | -0.21 | -21.8 % |
| modelltest | borttagen | 120 | 0.30 | +12.1 % |
| modelltest | flyttad linje (för oss) | 105 | 4.40 | +11.6 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2499 / 0.2326 (64) | -0.0435…+0.0779 | 0.92 (-0.06…+1.96) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.2954 / 0.2548 (7) | – | -1.37 (–) | 0 | – |
| points | **degraded** | 0.2761 / 0.2416 (126) | +0.0076…+0.0605 | -0.55 (-0.94…+0.01) | 6 | -1.3 % |
| pr | **degraded** | 0.3152 / 0.2532 (36) | +0.0442…+0.0884 | 0.92 (-0.61…+2.17) | 0 | – |
| pra | **insufficient_data** | 0.3447 / 0.2526 (29) | +0.0086…+0.1350 | 0.11 (-0.96…+1.44) | 0 | – |
| ra | **insufficient_data** | 0.2415 / 0.2399 (27) | -0.0628…+0.0765 | 0.11 (-1.56…+1.12) | 0 | – |
| rebounds | **shadow** | 0.2804 / 0.2543 (67) | -0.0086…+0.0723 | -0.51 (-1.02…-0.07) | 7 | -7.1 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.97 (+1.81…+5.62) | 0 | – |
| threes | **shadow** | 0.2691 / 0.2457 (39) | -0.0305…+0.0706 | 0.12 (-0.74…+1.45) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 5 marknader: assists 0.715, threes 0.793, rebounds 0.967, points 0.997, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 150 | 0.2509 | 0.2492 | 0.3013 | -0.0018…+0.0041 |
| p_modell_min | 150 | 0.3133 | 0.2492 | 0.3013 | +0.0584…+0.0736 |
| p_faktorer | 128 | 0.2534 | 0.2479 | 0.3112 | +0.0037…+0.0101 |
| p_faktorer_ra | 128 | 0.2992 | 0.2479 | 0.3112 | +0.0321…+0.1173 |
| p_betyg | 56 | 0.2471 | 0.2404 | 0.2911 | – |
| p_betyg_ra | 56 | 0.3009 | 0.2404 | 0.2911 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 11 | +16.1 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
