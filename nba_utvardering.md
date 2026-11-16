# NBA – utvärdering på framåtriktad data (2026-11-16T03:15:08+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 21 | 21 | 19 | 10 | 20 | +8.5 % | +8.6 % | 4.0 | 3.10 (+2.37…+3.74) | 3.19 | 0.95 | +85.7 % | 3.04 | – |
| spel | 359 | 359 | 105 | 15 | 333 | +4.2 % | +2.2 % | 14.5 | 2.20 (+1.69…+2.76) | 2.10 | 0.81 | +77.7 % | 2.55 | – |
| skugga | 1008 | 1008 | 115 | 15 | 928 | +1.4 % | +1.2 % | 34.3 | 0.87 (+0.61…+1.20) | 0.83 | 0.85 | +65.9 % | 1.80 | – |
| modelltest | 900 | 900 | 116 | 15 | 828 | +7.9 % | +7.6 % | 17.5 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.2 % | 1.85 | 0.2727 / 0.2448 (330) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 223 | 0.93 (+0.16…+1.63) | +69.3 % | +3.0 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.17) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | -0.08 (–) | +50.0 % | +96.0 % |
| points | **ok** | 568 | 1.17 (+0.72…+1.56) | +66.4 % | +0.2 % |
| pr | **osäker** | 29 | 1.15 (-2.26…+2.95) | +65.5 % | -1.2 % |
| pra | **osäker** | 20 | 0.94 (-0.41…+2.90) | +70.0 % | -9.1 % |
| ra | **osäker** | 50 | 0.72 (-1.16…+0.89) | +69.4 % | +2.9 % |
| rebounds | **ok** | 288 | 1.09 (+0.81…+1.48) | +72.2 % | -3.7 % |
| steals | **ok** | 27 | 4.85 (+3.10…+10.14) | +88.9 % | +31.8 % |
| threes | **ok** | 167 | 1.51 (+0.55…+2.34) | +67.9 % | +12.9 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 2 | 5.01 | +92.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 12 | 7.77 | -61.6 % |
| spel | borttagen | 42 | 2.69 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 58 | 0.75 | -5.3 % |
| skugga | borttagen | 99 | 0.90 | -8.1 % |
| skugga | flyttad linje (för oss) | 164 | 4.62 | +14.6 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -10.7 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 39 | -0.21 | -27.8 % |
| modelltest | borttagen | 103 | 0.05 | +23.0 % |
| modelltest | flyttad linje (för oss) | 102 | 4.41 | +12.9 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -23.2 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2436 / 0.2364 (58) | -0.0527…+0.0703 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **shadow** | 0.2677 / 0.2406 (111) | -0.0009…+0.0558 | -0.60 (-0.97…-0.04) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3260 / 0.2489 (24) | +0.0567…+0.1085 | 0.70 (-1.19…+2.26) | 0 | – |
| pra | **insufficient_data** | 0.3280 / 0.2523 (20) | -0.0372…+0.1286 | -0.11 (-1.22…+1.49) | 0 | – |
| ra | **insufficient_data** | 0.2650 / 0.2415 (21) | -0.0436…+0.1398 | 0.26 (-1.62…+1.28) | 0 | – |
| rebounds | **shadow** | 0.2687 / 0.2520 (55) | -0.0288…+0.0758 | -0.53 (-1.02…-0.06) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.76) | 0 | – |
| threes | **shadow** | 0.2826 / 0.2599 (31) | -0.0468…+0.0793 | 0.12 (-0.84…+1.64) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.575, threes 0.719, rebounds 0.954, points 0.975

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 75 | 0.2593 | 0.2555 | 0.3003 | -0.0000…+0.0042 |
| p_modell_min | 75 | 0.3067 | 0.2555 | 0.3003 | +0.0412…+0.1795 |
| p_faktorer | 53 | 0.2600 | 0.2549 | 0.3240 | – |
| p_faktorer_ra | 53 | 0.3104 | 0.2549 | 0.3240 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |
| 2.50–3.00 | 0 | – | 3.49 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
