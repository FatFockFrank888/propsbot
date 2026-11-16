# NBA – utvärdering på framåtriktad data (2026-11-16T01:29:14+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 20 | 20 | 18 | 10 | 19 | +4.2 % | +0.5 % | 4.0 | 3.08 (+2.36…+3.77) | 3.18 | 0.95 | +85.0 % | 2.97 | – |
| spel | 357 | 357 | 104 | 15 | 329 | +4.9 % | +3.0 % | 14.5 | 2.18 (+1.69…+2.73) | 2.09 | 0.81 | +77.6 % | 2.56 | – |
| skugga | 1007 | 1007 | 115 | 15 | 904 | +1.2 % | +1.1 % | 33.1 | 0.88 (+0.61…+1.22) | 0.83 | 0.85 | +65.9 % | 1.82 | – |
| modelltest | 899 | 899 | 116 | 15 | 814 | +8.1 % | +7.6 % | 17.5 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.3 % | 1.89 | 0.2734 / 0.2451 (316) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 222 | 0.93 (+0.17…+1.58) | +69.1 % | +2.8 % |
| blocks | **ok** | 14 | 4.14 (+2.61…+5.36) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | -0.08 (–) | +50.0 % | – |
| points | **ok** | 568 | 1.18 (+0.74…+1.58) | +66.4 % | -0.3 % |
| pr | **osäker** | 29 | 1.38 (-2.26…+2.95) | +65.4 % | -1.1 % |
| pra | **osäker** | 20 | 1.09 (-0.16…+3.34) | +73.7 % | -9.1 % |
| ra | **osäker** | 50 | 0.72 (-1.16…+0.89) | +69.4 % | +5.5 % |
| rebounds | **ok** | 285 | 1.06 (+0.80…+1.43) | +71.7 % | -3.8 % |
| steals | **ok** | 27 | 4.85 (+3.09…+10.19) | +88.9 % | +37.0 % |
| threes | **ok** | 167 | 1.51 (+0.56…+2.41) | +67.9 % | +13.6 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 1 | 6.54 | – |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 10 | 8.43 | -100.0 % |
| spel | borttagen | 42 | 2.69 | -19.2 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 51 | 0.73 | -21.0 % |
| skugga | borttagen | 96 | 0.99 | -10.0 % |
| skugga | flyttad linje (för oss) | 164 | 4.62 | +13.6 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -5.8 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 34 | -0.22 | -55.8 % |
| modelltest | borttagen | 99 | 0.01 | +25.1 % |
| modelltest | flyttad linje (för oss) | 101 | 4.46 | +13.3 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -23.2 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2402 / 0.2372 (56) | -0.0570…+0.0680 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **degraded** | 0.2723 / 0.2411 (106) | +0.0012…+0.0620 | -0.61 (-0.97…-0.04) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3172 / 0.2481 (23) | +0.0337…+0.1018 | 0.91 (-1.14…+2.42) | 0 | – |
| pra | **insufficient_data** | 0.3108 / 0.2525 (18) | -0.0528…+0.1139 | 0.08 (-1.12…+1.52) | 0 | – |
| ra | **insufficient_data** | 0.2634 / 0.2408 (20) | -0.0477…+0.1480 | 0.32 (-1.62…+1.30) | 0 | – |
| rebounds | **degraded** | 0.2790 / 0.2525 (52) | -0.0177…+0.0861 | -0.59 (-1.05…-0.21) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.63) | 0 | – |
| threes | **shadow** | 0.2826 / 0.2599 (31) | -0.0460…+0.0801 | 0.12 (-0.83…+1.64) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.528, threes 0.727, points 0.983, rebounds 0.985

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 61 | 0.2642 | 0.2596 | 0.3106 | -0.0000…+0.0056 |
| p_modell_min | 61 | 0.3175 | 0.2596 | 0.3106 | +0.0532…+0.1795 |
| p_faktorer | 39 | 0.2678 | 0.2612 | 0.3484 | – |
| p_faktorer_ra | 39 | 0.3348 | 0.2612 | 0.3484 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
