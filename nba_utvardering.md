# NBA – utvärdering på framåtriktad data (2026-11-17T03:30:33+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 26 | 26 | 22 | 11 | 22 | +10.0 % | +15.1 % | 4.0 | 2.83 (+2.14…+3.59) | 2.89 | 0.96 | +84.6 % | 2.56 | – |
| spel | 380 | 380 | 111 | 16 | 346 | +4.0 % | +2.1 % | 14.5 | 2.18 (+1.70…+2.75) | 2.04 | 0.81 | +77.4 % | 2.59 | – |
| skugga | 1097 | 1097 | 123 | 16 | 987 | +1.9 % | +1.8 % | 35.7 | 0.88 (+0.63…+1.18) | 0.82 | 0.85 | +66.0 % | 1.77 | – |
| modelltest | 959 | 959 | 124 | 16 | 870 | +6.3 % | +5.9 % | 25.4 | -0.05 (-0.42…+0.47) | -0.14 | 0.81 | +44.8 % | 1.81 | 0.2776 / 0.2453 (372) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 239 | 0.96 (+0.17…+1.59) | +69.2 % | +4.2 % |
| blocks | **ok** | 14 | 4.14 (+2.64…+5.27) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 7 | 0.59 (–) | +71.4 % | -2.0 % |
| points | **ok** | 608 | 1.19 (+0.71…+1.57) | +67.0 % | +0.5 % |
| pr | **osäker** | 38 | 1.65 (-0.93…+3.51) | +73.7 % | +3.2 % |
| pra | **osäker** | 24 | 0.63 (-0.36…+2.72) | +66.7 % | -13.6 % |
| ra | **osäker** | 58 | 0.38 (-2.04…+0.71) | +63.2 % | +2.5 % |
| rebounds | **ok** | 306 | 1.05 (+0.72…+1.39) | +70.9 % | -4.1 % |
| steals | **ok** | 27 | 4.85 (+3.13…+10.36) | +88.9 % | +31.8 % |
| threes | **ok** | 182 | 1.57 (+0.66…+2.25) | +68.9 % | +14.2 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 7 | 2.64 | +47.3 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 28 | 3.86 | -27.5 % |
| spel | borttagen | 47 | 2.98 | -16.8 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 123 | 0.58 | -0.5 % |
| skugga | borttagen | 119 | 1.05 | -5.8 % |
| skugga | flyttad linje (för oss) | 168 | 4.63 | +15.2 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 78 | -0.21 | -26.4 % |
| modelltest | borttagen | 120 | 0.30 | +16.3 % |
| modelltest | flyttad linje (för oss) | 105 | 4.40 | +12.7 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2471 / 0.2357 (60) | -0.0499…+0.0752 | 0.92 (-0.06…+1.96) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3254 / 0.2582 (3) | – | -1.37 (–) | 0 | – |
| points | **degraded** | 0.2793 / 0.2428 (117) | +0.0074…+0.0672 | -0.55 (-0.94…+0.01) | 5 | +18.4 % |
| pr | **degraded** | 0.3128 / 0.2500 (31) | +0.0397…+0.0897 | 0.92 (-0.61…+2.17) | 0 | – |
| pra | **insufficient_data** | 0.3330 / 0.2517 (26) | -0.0131…+0.1212 | 0.11 (-0.96…+1.44) | 0 | – |
| ra | **insufficient_data** | 0.2470 / 0.2410 (26) | -0.0591…+0.0867 | 0.11 (-1.56…+1.12) | 0 | – |
| rebounds | **shadow** | 0.2788 / 0.2520 (63) | -0.0096…+0.0780 | -0.51 (-1.02…-0.07) | 6 | +8.3 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.97 (+1.81…+5.62) | 0 | – |
| threes | **shadow** | 0.2716 / 0.2539 (36) | -0.0421…+0.0698 | 0.12 (-0.74…+1.45) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 5 marknader: assists 0.645, threes 0.692, rebounds 0.967, points 0.996, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 117 | 0.2562 | 0.2533 | 0.3059 | -0.0004…+0.0041 |
| p_modell_min | 117 | 0.3160 | 0.2533 | 0.3059 | +0.0584…+0.0815 |
| p_faktorer | 95 | 0.2581 | 0.2525 | 0.3204 | +0.0037…+0.0101 |
| p_faktorer_ra | 95 | 0.3067 | 0.2525 | 0.3204 | +0.0321…+0.1173 |
| p_betyg | 23 | 0.2583 | 0.2488 | 0.3000 | – |
| p_betyg_ra | 23 | 0.3151 | 0.2488 | 0.3000 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.57 |
| 2.00–2.50 | 12 | -10.8 % | 2.12 |
| 2.50–3.00 | 1 | +150.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
