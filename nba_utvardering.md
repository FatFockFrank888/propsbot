# NBA – utvärdering på framåtriktad data (2026-11-17T00:30:37+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 25 | 25 | 21 | 11 | 21 | +15.3 % | +21.4 % | 4.0 | 2.77 (+1.98…+3.59) | 2.84 | 0.96 | +84.0 % | 2.79 | – |
| spel | 378 | 378 | 111 | 16 | 340 | +3.9 % | +1.9 % | 14.5 | 2.13 (+1.61…+2.70) | 2.04 | 0.82 | +77.0 % | 2.56 | – |
| skugga | 1095 | 1095 | 123 | 16 | 959 | +1.3 % | +1.3 % | 35.7 | 0.85 (+0.60…+1.16) | 0.80 | 0.85 | +65.6 % | 1.75 | – |
| modelltest | 957 | 957 | 124 | 16 | 851 | +6.8 % | +6.5 % | 22.3 | -0.09 (-0.46…+0.41) | -0.16 | 0.81 | +44.2 % | 1.82 | 0.2758 / 0.2450 (353) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 237 | 0.89 (+0.15…+1.55) | +68.7 % | +3.4 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.14) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 7 | 0.75 (–) | +80.0 % | -2.0 % |
| points | **ok** | 606 | 1.15 (+0.71…+1.57) | +66.2 % | +0.1 % |
| pr | **osäker** | 38 | 1.55 (-0.93…+3.28) | +73.0 % | +0.7 % |
| pra | **osäker** | 24 | 0.87 (-0.46…+2.87) | +68.2 % | -13.6 % |
| ra | **osäker** | 58 | 0.36 (-2.49…+0.64) | +64.2 % | +2.6 % |
| rebounds | **ok** | 306 | 1.02 (+0.61…+1.39) | +70.7 % | -2.4 % |
| steals | **ok** | 27 | 4.85 (+3.09…+10.17) | +88.9 % | +31.8 % |
| threes | **ok** | 181 | 1.56 (+0.66…+2.32) | +68.6 % | +11.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 6 | 2.39 | +121.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 25 | 3.99 | -33.0 % |
| spel | borttagen | 44 | 2.63 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 102 | 0.44 | -11.9 % |
| skugga | borttagen | 108 | 0.89 | -5.6 % |
| skugga | flyttad linje (för oss) | 167 | 4.65 | +15.4 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 64 | -0.45 | -25.1 % |
| modelltest | borttagen | 110 | 0.05 | +17.6 % |
| modelltest | flyttad linje (för oss) | 105 | 4.40 | +11.8 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2446 / 0.2358 (59) | -0.0513…+0.0720 | 0.83 (-0.18…+1.90) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | – | – | -2.05 (–) | 0 | – |
| points | **degraded** | 0.2747 / 0.2424 (115) | +0.0027…+0.0603 | -0.61 (-0.97…-0.05) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3162 / 0.2483 (27) | +0.0441…+0.0970 | 0.86 (-0.61…+2.15) | 0 | – |
| pra | **insufficient_data** | 0.3280 / 0.2514 (25) | -0.0372…+0.1139 | -0.05 (-1.07…+1.42) | 0 | – |
| ra | **insufficient_data** | 0.2543 / 0.2423 (25) | -0.0477…+0.1032 | 0.11 (-1.87…+1.15) | 0 | – |
| rebounds | **shadow** | 0.2751 / 0.2503 (60) | -0.0155…+0.0759 | -0.50 (-0.96…-0.06) | 5 | +30.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.97 (+1.86…+5.63) | 0 | – |
| threes | **shadow** | 0.2838 / 0.2584 (32) | -0.0386…+0.0782 | 0.09 (-0.82…+1.45) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.591, threes 0.758, rebounds 0.965, points 0.986

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
| 1.60–2.00 | 9 | +22.3 % | 3.51 |
| 2.00–2.50 | 11 | -2.7 % | 2.12 |
| 2.50–3.00 | 1 | +150.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
