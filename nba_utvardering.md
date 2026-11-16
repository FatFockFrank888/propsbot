# NBA – utvärdering på framåtriktad data (2026-11-16T01:44:44+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 21 | 21 | 19 | 10 | 20 | +8.5 % | +8.6 % | 4.0 | 3.08 (+2.36…+3.77) | 3.18 | 0.95 | +85.0 % | 2.97 | – |
| spel | 358 | 358 | 105 | 15 | 331 | +4.9 % | +2.9 % | 14.5 | 2.18 (+1.69…+2.73) | 2.09 | 0.81 | +77.6 % | 2.56 | – |
| skugga | 1008 | 1008 | 115 | 15 | 911 | +1.5 % | +1.3 % | 34.3 | 0.88 (+0.61…+1.22) | 0.83 | 0.85 | +65.9 % | 1.82 | – |
| modelltest | 899 | 899 | 116 | 15 | 817 | +7.7 % | +7.3 % | 17.5 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.3 % | 1.89 | 0.2755 / 0.2452 (319) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 223 | 0.93 (+0.17…+1.58) | +69.1 % | +2.3 % |
| blocks | **ok** | 14 | 4.14 (+2.61…+5.36) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | -0.08 (–) | +50.0 % | +96.0 % |
| points | **ok** | 568 | 1.18 (+0.74…+1.58) | +66.4 % | +0.4 % |
| pr | **osäker** | 29 | 1.38 (-2.26…+2.95) | +65.4 % | -6.3 % |
| pra | **osäker** | 20 | 1.09 (-0.16…+3.34) | +73.7 % | -9.1 % |
| ra | **osäker** | 50 | 0.72 (-1.16…+0.89) | +69.4 % | +10.8 % |
| rebounds | **ok** | 287 | 1.06 (+0.80…+1.43) | +71.7 % | -4.2 % |
| steals | **ok** | 27 | 4.85 (+3.09…+10.19) | +88.9 % | +37.0 % |
| threes | **ok** | 167 | 1.51 (+0.56…+2.41) | +67.9 % | +13.6 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 1 | 6.54 | +92.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 10 | 8.43 | -36.0 % |
| spel | borttagen | 42 | 2.69 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 51 | 0.73 | -7.5 % |
| skugga | borttagen | 96 | 0.99 | -8.1 % |
| skugga | flyttad linje (för oss) | 164 | 4.62 | +14.0 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -8.3 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 34 | -0.22 | -58.9 % |
| modelltest | borttagen | 99 | 0.01 | +23.0 % |
| modelltest | flyttad linje (för oss) | 101 | 4.46 | +12.1 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -23.2 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2402 / 0.2372 (56) | -0.0570…+0.0680 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **degraded** | 0.2723 / 0.2411 (106) | +0.0012…+0.0620 | -0.61 (-0.97…-0.04) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3260 / 0.2489 (24) | +0.0567…+0.1085 | 0.91 (-1.14…+2.42) | 0 | – |
| pra | **insufficient_data** | 0.3280 / 0.2523 (20) | -0.0372…+0.1286 | 0.08 (-1.12…+1.52) | 0 | – |
| ra | **insufficient_data** | 0.2634 / 0.2408 (20) | -0.0477…+0.1480 | 0.32 (-1.62…+1.30) | 0 | – |
| rebounds | **degraded** | 0.2790 / 0.2525 (52) | -0.0177…+0.0861 | -0.59 (-1.05…-0.21) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.63) | 0 | – |
| threes | **shadow** | 0.2826 / 0.2599 (31) | -0.0460…+0.0801 | 0.12 (-0.83…+1.64) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.528, threes 0.727, points 0.983, rebounds 0.985

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 64 | 0.2638 | 0.2594 | 0.3193 | -0.0000…+0.0048 |
| p_modell_min | 64 | 0.3251 | 0.2594 | 0.3193 | +0.0573…+0.1795 |
| p_faktorer | 42 | 0.2693 | 0.2608 | 0.3591 | – |
| p_faktorer_ra | 42 | 0.3403 | 0.2608 | 0.3591 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |
| 2.50–3.00 | 0 | – | – |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
