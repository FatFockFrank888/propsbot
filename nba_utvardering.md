# NBA – utvärdering på framåtriktad data (2026-11-18T04:03:46+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 27 | 27 | 23 | 12 | 26 | -0.1 % | +0.2 % | 4.0 | 2.86 (+2.21…+3.62) | 2.92 | 0.96 | +85.2 % | 2.59 | – |
| spel | 391 | 391 | 116 | 17 | 363 | +4.5 % | +2.6 % | 14.5 | 2.22 (+1.75…+2.76) | 2.08 | 0.81 | +78.0 % | 2.66 | – |
| skugga | 1155 | 1155 | 128 | 17 | 1058 | +2.0 % | +1.9 % | 39.8 | 0.87 (+0.61…+1.15) | 0.81 | 0.85 | +65.8 % | 1.82 | – |
| modelltest | 1006 | 1006 | 129 | 17 | 917 | +5.6 % | +5.4 % | 34.2 | -0.03 (-0.40…+0.46) | -0.10 | 0.81 | +45.4 % | 1.86 | 0.2766 / 0.2441 (419) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 254 | 1.00 (+0.31…+1.57) | +70.3 % | +5.3 % |
| blocks | **ok** | 15 | 3.85 (+1.82…+4.53) | +93.3 % | +26.2 % |
| pa | **osäker** | 14 | -0.74 (-2.38…+0.80) | +50.0 % | -11.0 % |
| points | **ok** | 625 | 1.19 (+0.75…+1.50) | +66.6 % | +1.0 % |
| pr | **osäker** | 45 | 1.49 (-0.53…+3.05) | +71.1 % | -3.3 % |
| pra | **osäker** | 24 | 0.63 (-0.37…+2.60) | +66.7 % | -11.9 % |
| ra | **osäker** | 61 | 0.44 (-1.80…+0.86) | +63.3 % | +5.7 % |
| rebounds | **ok** | 315 | 1.08 (+0.77…+1.44) | +71.4 % | -4.6 % |
| steals | **ok** | 30 | 4.51 (+2.81…+9.24) | +90.0 % | +31.8 % |
| threes | **ok** | 190 | 1.56 (+0.70…+2.29) | +69.2 % | +12.9 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 8 | 2.77 | -11.7 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 38 | 3.71 | -6.6 % |
| spel | borttagen | 48 | 2.98 | -15.0 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 173 | 0.59 | -0.3 % |
| skugga | borttagen | 124 | 0.98 | -1.4 % |
| skugga | flyttad linje (för oss) | 170 | 4.63 | +14.5 % |
| skugga | flyttad linje (mot oss) | 41 | -4.90 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 119 | 0.01 | -15.9 % |
| modelltest | borttagen | 124 | 0.26 | +10.2 % |
| modelltest | flyttad linje (för oss) | 106 | 4.44 | +11.6 % |
| modelltest | flyttad linje (mot oss) | 46 | -5.93 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2468 / 0.2336 (66) | -0.0477…+0.0702 | 1.03 (+0.13…+2.00) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.2954 / 0.2548 (7) | – | -1.94 (–) | 0 | – |
| points | **degraded** | 0.2753 / 0.2412 (130) | +0.0073…+0.0580 | -0.53 (-0.93…+0.01) | 6 | -1.3 % |
| pr | **degraded** | 0.3061 / 0.2521 (39) | +0.0326…+0.0818 | 0.68 (-0.53…+1.79) | 0 | – |
| pra | **degraded** | 0.3470 / 0.2526 (30) | +0.0217…+0.1364 | 0.11 (-0.85…+1.29) | 0 | – |
| ra | **insufficient_data** | 0.2353 / 0.2380 (28) | -0.0657…+0.0707 | 0.14 (-1.39…+1.12) | 0 | – |
| rebounds | **shadow** | 0.2810 / 0.2530 (70) | -0.0044…+0.0720 | -0.44 (-0.92…+0.03) | 7 | -7.1 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1564 | 3.49 (+1.59…+5.24) | 0 | – |
| threes | **shadow** | 0.2691 / 0.2457 (39) | -0.0285…+0.0700 | 0.11 (-0.78…+1.39) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.679, threes 0.799, rebounds 0.944, pra 0.978, points 0.997, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 164 | 0.2494 | 0.2479 | 0.2953 | -0.0017…+0.0037 |
| p_modell_min | 164 | 0.3078 | 0.2479 | 0.2953 | +0.0489…+0.0652 |
| p_faktorer | 142 | 0.2507 | 0.2465 | 0.3034 | -0.0012…+0.0066 |
| p_faktorer_ra | 142 | 0.2904 | 0.2465 | 0.3034 | +0.0194…+0.0938 |
| p_betyg | 70 | 0.2454 | 0.2392 | 0.2792 | +0.0038…+0.0154 |
| p_betyg_ra | 70 | 0.2973 | 0.2392 | 0.2792 | +0.0448…+0.0781 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 11 | +16.1 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
