# NBA – utvärdering på framåtriktad data (2026-11-19T16:50:04+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 32 | 32 | 26 | 13 | 32 | -0.4 % | +0.5 % | 5.2 | 3.25 (+2.39…+4.16) | 3.32 | 0.97 | +87.5 % | 2.46 | – |
| spel | 431 | 431 | 129 | 19 | 409 | +3.7 % | +1.5 % | 14.5 | 2.23 (+1.79…+2.71) | 2.09 | 0.81 | +78.1 % | 2.65 | – |
| skugga | 1314 | 1314 | 144 | 19 | 1227 | +3.5 % | +4.0 % | 39.8 | 0.86 (+0.64…+1.11) | 0.77 | 0.84 | +66.2 % | 1.76 | – |
| modelltest | 1122 | 1122 | 145 | 19 | 1050 | +4.7 % | +4.6 % | 34.4 | -0.02 (-0.36…+0.43) | -0.12 | 0.81 | +46.1 % | 1.81 | 0.2742 / 0.2441 (552) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 283 | 1.06 (+0.36…+1.58) | +71.7 % | +5.2 % |
| blocks | **ok** | 16 | 4.16 (+2.25…+5.55) | +93.8 % | +26.3 % |
| pa | **osäker** | 22 | -0.15 (-2.09…+0.51) | +55.0 % | -8.4 % |
| points | **ok** | 674 | 1.25 (+0.75…+1.51) | +67.3 % | +2.5 % |
| pr | **osäker** | 60 | 1.16 (-0.12…+2.74) | +69.6 % | +5.9 % |
| pra | **osäker** | 32 | 0.80 (-0.10…+2.30) | +64.5 % | -26.0 % |
| ra | **osäker** | 76 | 0.42 (-1.45…+0.64) | +63.4 % | +13.0 % |
| rebounds | **ok** | 366 | 1.08 (+0.77…+1.39) | +71.1 % | -3.7 % |
| steals | **ok** | 31 | 4.48 (+2.75…+9.02) | +90.3 % | +40.9 % |
| threes | **ok** | 217 | 1.47 (+0.67…+2.10) | +69.2 % | +10.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 13 | 3.77 | -7.1 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 67 | 2.98 | -4.3 % |
| spel | borttagen | 55 | 2.93 | -17.1 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 263 | 0.43 | +6.9 % |
| skugga | borttagen | 152 | 1.01 | -3.9 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +18.4 % |
| skugga | flyttad linje (mot oss) | 43 | -4.83 | -9.0 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 195 | 0.01 | -6.2 % |
| modelltest | borttagen | 140 | 0.34 | +3.0 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 49 | -6.25 | -23.3 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2407 / 0.2312 (87) | -0.0380…+0.0572 | 1.08 (+0.22…+1.95) | 6 | -40.3 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.3114 / 0.2542 (19) | +0.0406…+0.0715 | -1.71 (-3.09…-1.35) | 0 | – |
| points | **shadow** | 0.2621 / 0.2410 (157) | -0.0097…+0.0497 | -0.42 (-0.85…+0.18) | 6 | -1.3 % |
| pr | **degraded** | 0.3112 / 0.2536 (55) | +0.0398…+0.0795 | -0.13 (-1.90…+1.52) | 0 | – |
| pra | **degraded** | 0.3451 / 0.2534 (38) | +0.0274…+0.1297 | -0.11 (-1.03…+1.05) | 1 | -100.0 % |
| ra | **shadow** | 0.2357 / 0.2426 (35) | -0.0569…+0.0496 | 0.04 (-1.15…+0.95) | 0 | – |
| rebounds | **degraded** | 0.2821 / 0.2503 (100) | +0.0033…+0.0688 | -0.38 (-0.80…+0.06) | 10 | +5.2 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0167…+0.1243 | 3.50 (+1.82…+5.15) | 0 | – |
| threes | **shadow** | 0.2733 / 0.2454 (48) | -0.0123…+0.0686 | 0.16 (-0.68…+1.29) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.584, assists 0.649, threes 0.907, points 0.950, rebounds 0.985, pra 0.994, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 297 | 0.2465 | 0.2462 | 0.2824 | -0.0014…+0.0027 |
| p_modell_min | 297 | 0.2922 | 0.2462 | 0.2824 | +0.0276…+0.0637 |
| p_faktorer | 275 | 0.2470 | 0.2453 | 0.2855 | -0.0014…+0.0057 |
| p_faktorer_ra | 275 | 0.2796 | 0.2453 | 0.2855 | +0.0179…+0.0633 |
| p_betyg | 203 | 0.2436 | 0.2423 | 0.2708 | -0.0029…+0.0068 |
| p_betyg_ra | 203 | 0.2854 | 0.2423 | 0.2708 | +0.0167…+0.0776 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 14 | +4.6 % | 3.74 |
| 2.00–2.50 | 16 | -8.0 % | 2.81 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
