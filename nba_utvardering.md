# NBA – utvärdering på framåtriktad data (2026-11-16T05:08:13+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 21 | 21 | 19 | 10 | 20 | +8.5 % | +8.6 % | 4.0 | 3.10 (+2.37…+3.74) | 3.19 | 0.95 | +85.7 % | 3.04 | – |
| spel | 362 | 362 | 107 | 16 | 338 | +3.8 % | +2.0 % | 14.5 | 2.20 (+1.69…+2.76) | 2.10 | 0.81 | +77.7 % | 2.55 | – |
| skugga | 1014 | 1014 | 118 | 16 | 950 | +1.1 % | +1.0 % | 34.6 | 0.87 (+0.61…+1.20) | 0.83 | 0.85 | +65.9 % | 1.80 | – |
| modelltest | 906 | 906 | 118 | 16 | 842 | +7.2 % | +7.0 % | 18.3 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.2 % | 1.85 | 0.2740 / 0.2449 (344) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 227 | 0.93 (+0.16…+1.63) | +69.3 % | +3.0 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.17) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | -0.08 (–) | +50.0 % | -2.0 % |
| points | **ok** | 572 | 1.17 (+0.72…+1.56) | +66.4 % | +0.3 % |
| pr | **osäker** | 29 | 1.15 (-2.26…+2.95) | +65.5 % | -5.3 % |
| pra | **osäker** | 21 | 0.94 (-0.41…+2.90) | +70.0 % | -9.1 % |
| ra | **osäker** | 50 | 0.72 (-1.16…+0.89) | +69.4 % | +2.6 % |
| rebounds | **ok** | 288 | 1.09 (+0.81…+1.48) | +72.2 % | -3.9 % |
| steals | **ok** | 27 | 4.85 (+3.10…+10.14) | +88.9 % | +31.8 % |
| threes | **ok** | 167 | 1.51 (+0.55…+2.34) | +67.9 % | +11.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 2 | 5.01 | +92.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 12 | 7.77 | -44.6 % |
| spel | borttagen | 42 | 2.69 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 58 | 0.75 | -17.8 % |
| skugga | borttagen | 99 | 0.90 | -5.5 % |
| skugga | flyttad linje (för oss) | 164 | 4.62 | +15.4 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 39 | -0.21 | -31.4 % |
| modelltest | borttagen | 103 | 0.05 | +23.1 % |
| modelltest | flyttad linje (för oss) | 102 | 4.41 | +12.9 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2446 / 0.2358 (59) | -0.0515…+0.0712 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **degraded** | 0.2731 / 0.2416 (114) | +0.0027…+0.0588 | -0.60 (-0.97…-0.04) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3341 / 0.2493 (25) | +0.0618…+0.1264 | 0.70 (-1.19…+2.26) | 0 | – |
| pra | **insufficient_data** | 0.3066 / 0.2513 (22) | -0.0372…+0.0998 | -0.11 (-1.22…+1.49) | 0 | – |
| ra | **insufficient_data** | 0.2419 / 0.2411 (24) | -0.0618…+0.0840 | 0.26 (-1.62…+1.28) | 0 | – |
| rebounds | **shadow** | 0.2768 / 0.2517 (58) | -0.0149…+0.0781 | -0.53 (-1.02…-0.06) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.76) | 0 | – |
| threes | **shadow** | 0.2838 / 0.2584 (32) | -0.0383…+0.0804 | 0.12 (-0.84…+1.64) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.592, threes 0.757, rebounds 0.954, points 0.987

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 89 | 0.2573 | 0.2541 | 0.3011 | -0.0000…+0.0042 |
| p_modell_min | 89 | 0.3098 | 0.2541 | 0.3011 | +0.0518…+0.1795 |
| p_faktorer | 67 | 0.2590 | 0.2532 | 0.3200 | – |
| p_faktorer_ra | 67 | 0.3125 | 0.2532 | 0.3200 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |
| 2.50–3.00 | 0 | – | 3.49 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
