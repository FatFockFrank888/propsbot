# NBA – utvärdering på framåtriktad data (2026-11-17T00:13:40+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 25 | 25 | 21 | 11 | 21 | +15.3 % | +21.4 % | 4.0 | 3.18 (+2.47…+3.85) | 3.28 | 0.95 | +86.4 % | 3.36 | – |
| spel | 378 | 378 | 111 | 16 | 340 | +3.9 % | +1.9 % | 14.5 | 2.16 (+1.66…+2.75) | 2.08 | 0.81 | +77.3 % | 2.56 | – |
| skugga | 1094 | 1094 | 123 | 16 | 959 | +1.3 % | +1.3 % | 35.7 | 0.84 (+0.56…+1.15) | 0.79 | 0.85 | +65.4 % | 1.80 | – |
| modelltest | 955 | 955 | 124 | 16 | 851 | +6.8 % | +6.5 % | 22.3 | -0.09 (-0.47…+0.43) | -0.15 | 0.82 | +44.2 % | 1.85 | 0.2758 / 0.2450 (353) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 237 | 0.86 (+0.12…+1.52) | +68.1 % | +3.4 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.14) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 7 | -0.08 (–) | +50.0 % | -2.0 % |
| points | **ok** | 606 | 1.16 (+0.74…+1.57) | +66.0 % | +0.1 % |
| pr | **osäker** | 37 | 1.46 (-0.93…+3.69) | +70.6 % | +0.7 % |
| pra | **osäker** | 24 | 0.94 (-0.46…+2.86) | +70.0 % | -13.6 % |
| ra | **osäker** | 58 | 0.55 (-1.71…+0.71) | +66.7 % | +2.6 % |
| rebounds | **ok** | 306 | 1.06 (+0.75…+1.41) | +71.5 % | -2.4 % |
| steals | **ok** | 27 | 4.85 (+3.12…+10.18) | +88.9 % | +31.8 % |
| threes | **ok** | 181 | 1.40 (+0.42…+2.14) | +67.9 % | +11.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 3 | 5.00 | +121.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 17 | 5.70 | -33.0 % |
| spel | borttagen | 43 | 2.61 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 82 | 0.15 | -11.9 % |
| skugga | borttagen | 101 | 0.86 | -5.6 % |
| skugga | flyttad linje (för oss) | 167 | 4.65 | +15.4 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 53 | -0.30 | -25.1 % |
| modelltest | borttagen | 107 | -0.01 | +17.6 % |
| modelltest | flyttad linje (för oss) | 104 | 4.42 | +11.8 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2446 / 0.2358 (59) | -0.0513…+0.0720 | 0.83 (-0.18…+1.90) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | – | – | -1.28 (–) | 0 | – |
| points | **degraded** | 0.2747 / 0.2424 (115) | +0.0027…+0.0603 | -0.60 (-0.96…-0.03) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3162 / 0.2483 (27) | +0.0441…+0.1007 | 0.82 (-0.69…+2.25) | 0 | – |
| pra | **insufficient_data** | 0.3280 / 0.2514 (25) | -0.0341…+0.1144 | -0.12 (-1.17…+1.42) | 0 | – |
| ra | **insufficient_data** | 0.2543 / 0.2423 (25) | -0.0445…+0.0955 | 0.11 (-1.76…+1.15) | 0 | – |
| rebounds | **shadow** | 0.2751 / 0.2503 (60) | -0.0153…+0.0759 | -0.53 (-0.99…-0.08) | 5 | +30.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.97 (+1.81…+5.68) | 0 | – |
| threes | **shadow** | 0.2838 / 0.2584 (32) | -0.0386…+0.0794 | 0.11 (-0.81…+1.55) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.591, threes 0.760, rebounds 0.966, points 0.986

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
| 1.60–2.00 | 9 | +22.3 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.70 |
| 2.50–3.00 | 1 | +150.0 % | 3.49 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
