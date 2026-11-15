# NBA – utvärdering på framåtriktad data (2026-11-15T19:36:27+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 19 | 19 | 17 | 9 | 19 | +4.2 % | +0.5 % | 4.0 | 2.89 (+2.19…+3.47) | 2.99 | 0.95 | +84.2 % | 3.56 | – |
| spel | 349 | 349 | 101 | 15 | 323 | +4.9 % | +2.8 % | 14.5 | 2.00 (+1.55…+2.36) | 1.88 | 0.82 | +77.1 % | 2.65 | – |
| skugga | 978 | 978 | 115 | 15 | 878 | +2.2 % | +2.4 % | 27.0 | 0.83 (+0.56…+1.19) | 0.78 | 0.86 | +65.6 % | 1.70 | – |
| modelltest | 883 | 883 | 116 | 15 | 792 | +8.8 % | +8.6 % | 17.5 | -0.11 (-0.52…+0.49) | -0.16 | 0.82 | +44.6 % | 1.91 | 0.2703 / 0.2430 (294) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 220 | 0.87 (+0.14…+1.63) | +68.1 % | +2.5 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.20) | +100.0 % | +26.2 % |
| points | **ok** | 558 | 1.12 (+0.67…+1.52) | +65.8 % | -0.3 % |
| pr | **osäker** | 25 | 1.62 (-2.85…+3.10) | +70.0 % | -6.6 % |
| pra | **osäker** | 20 | 1.45 (-0.20…+3.31) | +77.8 % | -4.1 % |
| ra | **osäker** | 43 | 0.66 (-1.48…+0.79) | +71.4 % | +12.2 % |
| rebounds | **ok** | 279 | 1.06 (+0.75…+1.45) | +72.5 % | -2.1 % |
| steals | **ok** | 26 | 3.59 (+2.55…+5.67) | +88.5 % | +37.0 % |
| threes | **ok** | 161 | 1.20 (+0.40…+1.98) | +66.4 % | +15.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | borttagen | 37 | 2.74 | -26.5 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 9 | -4.69 | -9.4 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 7 | 1.32 | – |
| skugga | borttagen | 84 | 0.93 | -9.6 % |
| skugga | flyttad linje (för oss) | 157 | 4.53 | +15.1 % |
| skugga | flyttad linje (mot oss) | 35 | -6.14 | -0.2 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 3 | 0.78 | – |
| modelltest | borttagen | 90 | -0.13 | +23.3 % |
| modelltest | flyttad linje (för oss) | 97 | 4.55 | +12.9 % |
| modelltest | flyttad linje (mot oss) | 43 | -6.11 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2368 / 0.2359 (52) | -0.0637…+0.0675 | 0.82 (-0.21…+1.87) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **shadow** | 0.2675 / 0.2398 (99) | -0.0038…+0.0608 | -0.60 (-1.01…-0.01) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3262 / 0.2496 (22) | +0.0526…+0.1123 | 1.22 (-0.70…+2.89) | 0 | – |
| pra | **insufficient_data** | 0.3042 / 0.2532 (15) | -0.1133…+0.1128 | 0.51 (-1.05…+1.88) | 0 | – |
| ra | **insufficient_data** | 0.2517 / 0.2364 (19) | -0.0618…+0.1468 | 0.15 (-1.82…+1.32) | 0 | – |
| rebounds | **degraded** | 0.2799 / 0.2515 (48) | -0.0206…+0.0904 | -0.63 (-1.09…-0.23) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.97 (+1.86…+5.68) | 0 | – |
| threes | **insufficient_data** | 0.2782 / 0.2487 (29) | -0.0432…+0.0851 | -0.06 (-0.94…+1.37) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 3 marknader: assists 0.503, points 0.946, rebounds 0.986

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 39 | 0.2556 | 0.2515 | 0.3082 | – |
| p_modell_min | 39 | 0.3120 | 0.2515 | 0.3082 | – |
| p_faktorer | 17 | 0.2547 | 0.2447 | 0.3921 | – |
| p_faktorer_ra | 17 | 0.3619 | 0.2447 | 0.3921 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 3.44 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
