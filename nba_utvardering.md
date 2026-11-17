# NBA – utvärdering på framåtriktad data (2026-11-17T01:50:32+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 26 | 26 | 22 | 11 | 21 | +15.3 % | +21.4 % | 4.0 | 2.83 (+2.14…+3.59) | 2.89 | 0.96 | +84.6 % | 2.56 | – |
| spel | 380 | 380 | 111 | 16 | 340 | +3.9 % | +1.9 % | 14.5 | 2.18 (+1.70…+2.75) | 2.04 | 0.81 | +77.4 % | 2.59 | – |
| skugga | 1097 | 1097 | 123 | 16 | 959 | +1.3 % | +1.3 % | 35.7 | 0.87 (+0.62…+1.17) | 0.81 | 0.85 | +66.0 % | 1.75 | – |
| modelltest | 959 | 959 | 124 | 16 | 851 | +6.8 % | +6.5 % | 22.3 | -0.06 (-0.43…+0.44) | -0.15 | 0.81 | +44.6 % | 1.81 | 0.2758 / 0.2450 (353) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 239 | 0.96 (+0.21…+1.55) | +69.2 % | +3.4 % |
| blocks | **ok** | 14 | 4.14 (+2.64…+5.24) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 7 | 0.59 (–) | +71.4 % | -2.0 % |
| points | **ok** | 608 | 1.19 (+0.71…+1.55) | +67.0 % | +0.1 % |
| pr | **osäker** | 38 | 1.55 (-0.93…+3.28) | +73.0 % | +0.7 % |
| pra | **osäker** | 24 | 0.63 (-0.39…+2.68) | +66.7 % | -13.6 % |
| ra | **osäker** | 58 | 0.40 (-2.12…+0.59) | +64.3 % | +2.6 % |
| rebounds | **ok** | 306 | 1.05 (+0.71…+1.40) | +71.0 % | -2.4 % |
| steals | **ok** | 27 | 4.85 (+3.10…+10.30) | +88.9 % | +31.8 % |
| threes | **ok** | 182 | 1.56 (+0.64…+2.30) | +68.4 % | +11.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 7 | 2.64 | +121.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 28 | 3.86 | -33.0 % |
| spel | borttagen | 47 | 2.98 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 114 | 0.55 | -11.9 % |
| skugga | borttagen | 117 | 0.99 | -5.6 % |
| skugga | flyttad linje (för oss) | 168 | 4.63 | +15.4 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 75 | -0.31 | -25.1 % |
| modelltest | borttagen | 118 | 0.26 | +17.6 % |
| modelltest | flyttad linje (för oss) | 105 | 4.40 | +11.8 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2446 / 0.2358 (59) | -0.0513…+0.0720 | 0.92 (-0.02…+1.93) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | – | – | -1.37 (–) | 0 | – |
| points | **degraded** | 0.2747 / 0.2424 (115) | +0.0022…+0.0600 | -0.56 (-0.93…-0.01) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3162 / 0.2483 (27) | +0.0447…+0.0969 | 0.81 (-0.51…+2.07) | 0 | – |
| pra | **insufficient_data** | 0.3280 / 0.2514 (25) | -0.0351…+0.1136 | 0.06 (-0.91…+1.46) | 0 | – |
| ra | **insufficient_data** | 0.2543 / 0.2423 (25) | -0.0445…+0.1009 | 0.10 (-1.67…+1.12) | 0 | – |
| rebounds | **shadow** | 0.2751 / 0.2503 (60) | -0.0141…+0.0759 | -0.51 (-1.00…-0.07) | 5 | +30.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.78…+5.75) | 0 | – |
| threes | **shadow** | 0.2838 / 0.2584 (32) | -0.0394…+0.0792 | 0.12 (-0.78…+1.42) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.591, threes 0.755, rebounds 0.970, points 0.985

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 98 | 0.2574 | 0.2538 | 0.3052 | -0.0000…+0.0042 |
| p_modell_min | 98 | 0.3139 | 0.2538 | 0.3052 | +0.0573…+0.1795 |
| p_faktorer | 76 | 0.2581 | 0.2529 | 0.3230 | – |
| p_faktorer_ra | 76 | 0.3041 | 0.2529 | 0.3230 | – |
| p_betyg | 4 | 0.2546 | 0.2392 | 0.2529 | – |
| p_betyg_ra | 4 | 0.3173 | 0.2392 | 0.2529 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.57 |
| 2.00–2.50 | 11 | -2.7 % | 2.12 |
| 2.50–3.00 | 1 | +150.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
