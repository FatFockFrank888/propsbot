# NBA – utvärdering på framåtriktad data (2026-11-18T07:13:14+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 27 | 27 | 23 | 12 | 27 | -3.8 % | -2.7 % | 4.2 | 2.86 (+2.21…+3.62) | 2.92 | 0.96 | +85.2 % | 2.59 | – |
| spel | 391 | 391 | 116 | 17 | 369 | +4.5 % | +2.4 % | 14.5 | 2.22 (+1.75…+2.76) | 2.08 | 0.81 | +78.0 % | 2.66 | – |
| skugga | 1158 | 1158 | 131 | 18 | 1091 | +2.4 % | +2.7 % | 39.8 | 0.87 (+0.61…+1.15) | 0.81 | 0.85 | +65.8 % | 1.82 | – |
| modelltest | 1009 | 1009 | 131 | 18 | 946 | +5.0 % | +5.0 % | 34.2 | -0.03 (-0.40…+0.46) | -0.10 | 0.81 | +45.4 % | 1.86 | 0.2777 / 0.2439 (448) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 255 | 1.00 (+0.29…+1.59) | +70.3 % | +6.5 % |
| blocks | **ok** | 15 | 3.85 (+1.90…+4.68) | +93.3 % | +26.2 % |
| pa | **osäker** | 14 | -0.74 (-2.38…+0.80) | +50.0 % | +5.5 % |
| points | **ok** | 626 | 1.19 (+0.73…+1.53) | +66.6 % | +0.6 % |
| pr | **osäker** | 45 | 1.49 (-0.39…+3.14) | +71.1 % | -1.1 % |
| pra | **osäker** | 24 | 0.63 (-0.40…+2.68) | +66.7 % | -11.9 % |
| ra | **osäker** | 61 | 0.44 (-1.65…+0.86) | +63.3 % | +7.5 % |
| rebounds | **ok** | 315 | 1.08 (+0.78…+1.44) | +71.4 % | -5.7 % |
| steals | **ok** | 30 | 4.51 (+2.74…+9.31) | +90.0 % | +40.0 % |
| threes | **ok** | 191 | 1.56 (+0.69…+2.30) | +69.2 % | +13.2 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 8 | 2.77 | -22.8 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 38 | 3.71 | -4.4 % |
| spel | borttagen | 48 | 2.98 | -15.0 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 173 | 0.59 | +1.6 % |
| skugga | borttagen | 124 | 0.98 | +0.7 % |
| skugga | flyttad linje (för oss) | 170 | 4.63 | +14.5 % |
| skugga | flyttad linje (mot oss) | 41 | -4.90 | -4.5 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 119 | 0.01 | -14.3 % |
| modelltest | borttagen | 124 | 0.26 | +8.7 % |
| modelltest | flyttad linje (för oss) | 106 | 4.44 | +11.6 % |
| modelltest | flyttad linje (mot oss) | 46 | -5.93 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2441 / 0.2332 (69) | -0.0472…+0.0682 | 1.03 (+0.13…+2.00) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.2468 / 0.2510 (9) | – | -1.94 (–) | 0 | – |
| points | **degraded** | 0.2743 / 0.2413 (136) | +0.0074…+0.0560 | -0.53 (-0.93…+0.01) | 6 | -1.3 % |
| pr | **degraded** | 0.3140 / 0.2535 (43) | +0.0401…+0.0855 | 0.68 (-0.53…+1.79) | 0 | – |
| pra | **shadow** | 0.3356 / 0.2505 (33) | -0.0015…+0.1277 | 0.11 (-0.82…+1.34) | 0 | – |
| ra | **insufficient_data** | 0.2375 / 0.2378 (29) | -0.0606…+0.0708 | 0.14 (-1.38…+1.10) | 0 | – |
| rebounds | **shadow** | 0.2908 / 0.2516 (76) | -0.0003…+0.0871 | -0.44 (-0.91…+0.03) | 8 | -18.8 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0239…+0.1460 | 3.49 (+1.57…+5.29) | 0 | – |
| threes | **shadow** | 0.2693 / 0.2431 (41) | -0.0227…+0.0731 | 0.11 (-0.72…+1.41) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.653, threes 0.842, rebounds 0.969, pra 0.973, points 0.998, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 193 | 0.2480 | 0.2469 | 0.2950 | -0.0016…+0.0037 |
| p_modell_min | 193 | 0.3067 | 0.2469 | 0.2950 | +0.0541…+0.0652 |
| p_faktorer | 171 | 0.2499 | 0.2456 | 0.3016 | +0.0021…+0.0066 |
| p_faktorer_ra | 171 | 0.2904 | 0.2456 | 0.3016 | +0.0305…+0.0792 |
| p_betyg | 99 | 0.2459 | 0.2398 | 0.2832 | +0.0055…+0.0154 |
| p_betyg_ra | 99 | 0.3038 | 0.2398 | 0.2832 | +0.0588…+0.0781 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 12 | +6.4 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
