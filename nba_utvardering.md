# NBA – utvärdering på framåtriktad data (2026-11-16T00:58:05+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 20 | 20 | 18 | 10 | 19 | +4.2 % | +0.5 % | 4.0 | 3.08 (+2.36…+3.77) | 3.18 | 0.95 | +85.0 % | 2.97 | – |
| spel | 357 | 357 | 104 | 15 | 324 | +5.3 % | +3.3 % | 14.5 | 2.17 (+1.68…+2.70) | 2.07 | 0.81 | +77.5 % | 2.60 | – |
| skugga | 1003 | 1003 | 115 | 15 | 894 | +1.9 % | +2.0 % | 27.9 | 0.88 (+0.60…+1.21) | 0.84 | 0.86 | +66.0 % | 1.81 | – |
| modelltest | 898 | 898 | 116 | 15 | 807 | +8.5 % | +8.2 % | 17.5 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.3 % | 1.88 | 0.2717 / 0.2447 (309) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 222 | 0.93 (+0.16…+1.58) | +69.0 % | +3.4 % |
| blocks | **ok** | 14 | 4.14 (+2.61…+5.36) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | 0.76 (–) | +100.0 % | – |
| points | **ok** | 567 | 1.17 (+0.73…+1.57) | +66.4 % | -0.1 % |
| pr | **osäker** | 27 | 1.29 (-2.29…+2.95) | +65.2 % | -1.1 % |
| pra | **osäker** | 20 | 1.09 (-0.16…+3.34) | +73.7 % | -9.1 % |
| ra | **osäker** | 49 | 0.80 (-1.16…+1.18) | +70.2 % | +8.9 % |
| rebounds | **ok** | 285 | 1.08 (+0.82…+1.46) | +72.2 % | -2.8 % |
| steals | **ok** | 27 | 4.85 (+3.09…+10.19) | +88.9 % | +37.0 % |
| threes | **ok** | 167 | 1.42 (+0.56…+2.43) | +67.5 % | +14.4 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 1 | 6.54 | – |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 8 | 9.46 | – |
| spel | borttagen | 42 | 2.69 | -20.2 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | -9.4 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 42 | 0.88 | -3.1 % |
| skugga | borttagen | 95 | 1.01 | -10.3 % |
| skugga | flyttad linje (för oss) | 163 | 4.55 | +15.1 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -3.1 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 29 | -0.26 | -36.1 % |
| modelltest | borttagen | 97 | 0.02 | +26.2 % |
| modelltest | flyttad linje (för oss) | 101 | 4.46 | +13.3 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -26.8 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2403 / 0.2379 (54) | -0.0598…+0.0702 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **shadow** | 0.2704 / 0.2408 (105) | -0.0002…+0.0597 | -0.61 (-0.97…-0.04) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3172 / 0.2481 (23) | +0.0337…+0.1018 | 0.91 (-1.14…+2.42) | 0 | – |
| pra | **insufficient_data** | 0.3033 / 0.2506 (17) | -0.0735…+0.1114 | 0.08 (-1.26…+1.52) | 0 | – |
| ra | **insufficient_data** | 0.2634 / 0.2408 (20) | -0.0477…+0.1480 | 0.29 (-1.62…+1.31) | 0 | – |
| rebounds | **degraded** | 0.2774 / 0.2521 (50) | -0.0212…+0.0872 | -0.60 (-1.06…-0.23) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.63) | 0 | – |
| threes | **shadow** | 0.2781 / 0.2580 (30) | -0.0567…+0.0792 | 0.14 (-0.83…+1.72) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.521, threes 0.693, points 0.978, rebounds 0.986

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 54 | 0.2641 | 0.2593 | 0.3054 | -0.0000…+0.0070 |
| p_modell_min | 54 | 0.3111 | 0.2593 | 0.3054 | +0.0293…+0.1795 |
| p_faktorer | 32 | 0.2651 | 0.2609 | 0.3480 | – |
| p_faktorer_ra | 32 | 0.3320 | 0.2609 | 0.3480 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
