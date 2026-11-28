# NBA – utvärdering på framåtriktad data (2026-11-28T07:34:10+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 53 | 53 | 46 | 21 | 53 | -2.7 % | -0.0 % | 5.7 | 2.98 (+2.29…+3.72) | 2.92 | 0.92 | +84.9 % | 2.53 | – |
| spel | 558 | 558 | 185 | 27 | 533 | +4.7 % | +3.7 % | 14.5 | 2.25 (+1.90…+2.64) | 2.15 | 0.83 | +77.8 % | 2.58 | – |
| skugga | 1693 | 1693 | 199 | 27 | 1617 | +1.1 % | +0.9 % | 39.8 | 0.87 (+0.67…+1.07) | 0.75 | 0.83 | +66.6 % | 1.73 | – |
| modelltest | 1151 | 1151 | 150 | 21 | 1093 | +4.7 % | +4.6 % | 34.4 | -0.03 (-0.37…+0.39) | -0.12 | 0.81 | +45.9 % | 1.76 | 0.2724 / 0.2437 (595) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 377 | 1.23 (+0.61…+1.66) | +71.9 % | +2.1 % |
| blocks | **ok** | 23 | 3.97 (+2.72…+4.88) | +95.7 % | +22.9 % |
| pa | **osäker** | 55 | 0.68 (-1.18…+0.83) | +61.8 % | +0.5 % |
| points | **ok** | 810 | 1.24 (+0.73…+1.47) | +67.7 % | -0.4 % |
| pr | **ok** | 100 | 1.48 (+0.87…+2.66) | +73.0 % | -2.2 % |
| pra | **ok** | 45 | 1.13 (+0.28…+2.54) | +68.9 % | -28.3 % |
| ra | **osäker** | 129 | 0.45 (-0.86…+0.84) | +62.2 % | +11.5 % |
| rebounds | **ok** | 458 | 0.99 (+0.64…+1.31) | +70.4 % | -2.2 % |
| steals | **ok** | 49 | 4.25 (+3.18…+6.91) | +93.9 % | +41.7 % |
| threes | **ok** | 258 | 1.32 (+0.63…+1.79) | +68.4 % | +8.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 31 | 2.89 | -3.5 % |
| live | borttagen | 4 | 3.62 | -53.5 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 173 | 2.53 | +8.6 % |
| spel | borttagen | 69 | 2.79 | -21.8 % |
| spel | flyttad linje (för oss) | 47 | 4.57 | +1.1 % |
| spel | flyttad linje (mot oss) | 12 | -3.98 | -13.3 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 558 | 0.40 | -0.2 % |
| skugga | borttagen | 207 | 1.19 | -5.0 % |
| skugga | flyttad linje (för oss) | 224 | 4.72 | +16.0 % |
| skugga | flyttad linje (mot oss) | 54 | -4.72 | -15.6 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 232 | -0.03 | -3.0 % |
| modelltest | borttagen | 146 | 0.30 | +0.5 % |
| modelltest | flyttad linje (för oss) | 112 | 4.43 | +13.5 % |
| modelltest | flyttad linje (mot oss) | 50 | -6.18 | -24.9 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2383 / 0.2315 (94) | -0.0369…+0.0519 | 1.05 (+0.20…+1.88) | 11 | -31.5 % |
| blocks | **insufficient_data** | 0.1919 / 0.2085 (5) | -0.1012…+0.0132 | 3.39 (+1.65…+4.04) | 0 | – |
| pa | **insufficient_data** | 0.3044 / 0.2521 (25) | +0.0090…+0.0948 | -1.44 (-2.22…-0.88) | 1 | +110.0 % |
| points | **shadow** | 0.2612 / 0.2412 (166) | -0.0099…+0.0480 | -0.46 (-0.87…+0.16) | 11 | -12.3 % |
| pr | **degraded** | 0.3142 / 0.2545 (61) | +0.0430…+0.0784 | -0.23 (-1.85…+1.29) | 2 | -7.0 % |
| pra | **shadow** | 0.3242 / 0.2511 (44) | -0.0057…+0.1251 | -0.08 (-0.95…+0.87) | 1 | -100.0 % |
| ra | **shadow** | 0.2432 / 0.2430 (39) | -0.0420…+0.0547 | 0.10 (-0.91…+0.96) | 2 | +100.5 % |
| rebounds | **degraded** | 0.2792 / 0.2488 (102) | +0.0020…+0.0683 | -0.33 (-0.80…+0.11) | 15 | -3.0 % |
| steals | **insufficient_data** | 0.3038 / 0.2473 (9) | -0.0177…+0.1280 | 3.50 (+1.73…+5.21) | 0 | – |
| threes | **shadow** | 0.2720 / 0.2446 (50) | -0.0145…+0.0655 | 0.11 (-0.73…+1.26) | 10 | +18.5 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 7 marknader: ra 0.513, assists 0.633, threes 0.908, points 0.969, pra 0.970, rebounds 0.986, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 340 | 0.2454 | 0.2453 | 0.2782 | -0.0015…+0.0021 |
| p_modell_min | 340 | 0.2871 | 0.2453 | 0.2782 | +0.0228…+0.0620 |
| p_faktorer | 318 | 0.2455 | 0.2445 | 0.2807 | -0.0020…+0.0049 |
| p_faktorer_ra | 318 | 0.2734 | 0.2445 | 0.2807 | +0.0127…+0.0529 |
| p_betyg | 246 | 0.2426 | 0.2418 | 0.2671 | -0.0030…+0.0059 |
| p_betyg_ra | 246 | 0.2806 | 0.2418 | 0.2671 | +0.0154…+0.0732 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 24 | +8.0 % | 3.76 |
| 2.00–2.50 | 25 | -7.5 % | 2.25 |
| 2.50–3.00 | 4 | -37.5 % | 2.83 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
