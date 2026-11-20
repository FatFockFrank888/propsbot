# NBA – utvärdering på framåtriktad data (2026-11-20T01:10:16+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 34 | 34 | 28 | 14 | 32 | -0.4 % | +0.5 % | 5.2 | 3.36 (+2.53…+4.23) | 3.36 | 0.94 | +88.2 % | 2.47 | – |
| spel | 440 | 440 | 131 | 19 | 409 | +3.7 % | +1.5 % | 14.5 | 2.25 (+1.83…+2.73) | 2.10 | 0.81 | +77.9 % | 2.61 | – |
| skugga | 1339 | 1339 | 144 | 19 | 1227 | +3.5 % | +4.0 % | 39.8 | 0.82 (+0.57…+1.07) | 0.72 | 0.83 | +65.8 % | 1.72 | – |
| modelltest | 1141 | 1141 | 145 | 19 | 1050 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.38) | -0.13 | 0.82 | +46.0 % | 1.75 | 0.2742 / 0.2441 (552) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 287 | 1.05 (+0.35…+1.53) | +71.3 % | +5.2 % |
| blocks | **ok** | 19 | 3.96 (+2.37…+5.12) | +94.7 % | +26.3 % |
| pa | **osäker** | 23 | -0.01 (-1.84…+0.81) | +56.5 % | -8.4 % |
| points | **ok** | 681 | 1.19 (+0.69…+1.48) | +66.9 % | +2.5 % |
| pr | **osäker** | 65 | 1.24 (-0.25…+2.47) | +69.2 % | +5.9 % |
| pra | **osäker** | 33 | 0.69 (-0.24…+2.08) | +63.6 % | -26.0 % |
| ra | **osäker** | 78 | 0.28 (-1.42…+0.46) | +61.0 % | +13.0 % |
| rebounds | **ok** | 376 | 1.10 (+0.82…+1.41) | +71.4 % | -3.7 % |
| steals | **ok** | 33 | 4.51 (+2.99…+8.62) | +90.9 % | +40.9 % |
| threes | **ok** | 218 | 1.39 (+0.57…+1.95) | +68.5 % | +10.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 14 | 3.84 | -7.1 % |
| live | borttagen | 2 | 3.27 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 75 | 2.93 | -4.3 % |
| spel | borttagen | 56 | 2.98 | -17.1 % |
| spel | flyttad linje (för oss) | 41 | 4.55 | +4.6 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 304 | 0.31 | +6.9 % |
| skugga | borttagen | 161 | 1.01 | -3.9 % |
| skugga | flyttad linje (för oss) | 182 | 4.73 | +18.4 % |
| skugga | flyttad linje (mot oss) | 45 | -4.69 | -9.0 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 225 | -0.06 | -6.2 % |
| modelltest | borttagen | 142 | 0.36 | +3.0 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -23.3 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2407 / 0.2312 (87) | -0.0375…+0.0572 | 1.06 (+0.24…+1.93) | 6 | -40.3 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3114 / 0.2542 (19) | +0.0406…+0.0715 | -1.52 (-2.40…-0.91) | 0 | – |
| points | **shadow** | 0.2621 / 0.2410 (157) | -0.0109…+0.0495 | -0.45 (-0.86…+0.15) | 6 | -1.3 % |
| pr | **degraded** | 0.3112 / 0.2536 (55) | +0.0409…+0.0799 | -0.23 (-1.92…+1.32) | 0 | – |
| pra | **degraded** | 0.3451 / 0.2534 (38) | +0.0218…+0.1299 | -0.00 (-0.84…+0.99) | 1 | -100.0 % |
| ra | **shadow** | 0.2357 / 0.2426 (35) | -0.0574…+0.0534 | -0.01 (-1.03…+0.86) | 0 | – |
| rebounds | **degraded** | 0.2821 / 0.2503 (100) | +0.0038…+0.0720 | -0.35 (-0.78…+0.08) | 10 | +5.2 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0141…+0.1280 | 3.50 (+1.71…+5.15) | 0 | – |
| threes | **shadow** | 0.2733 / 0.2454 (48) | -0.0147…+0.0665 | 0.11 (-0.73…+1.25) | 9 | +31.7 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.518, assists 0.648, threes 0.907, points 0.971, rebounds 0.982, pra 0.993, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 297 | 0.2465 | 0.2462 | 0.2824 | -0.0014…+0.0027 |
| p_modell_min | 297 | 0.2922 | 0.2462 | 0.2824 | +0.0280…+0.0637 |
| p_faktorer | 275 | 0.2470 | 0.2453 | 0.2855 | -0.0012…+0.0056 |
| p_faktorer_ra | 275 | 0.2796 | 0.2453 | 0.2855 | +0.0179…+0.0633 |
| p_betyg | 203 | 0.2436 | 0.2423 | 0.2708 | -0.0029…+0.0068 |
| p_betyg_ra | 203 | 0.2854 | 0.2423 | 0.2708 | +0.0167…+0.0776 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 14 | +4.6 % | 3.85 |
| 2.00–2.50 | 16 | -8.0 % | 2.81 |
| 2.50–3.00 | 2 | +25.0 % | 3.81 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
