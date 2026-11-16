# NBA – utvärdering på framåtriktad data (2026-11-16T03:54:46+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 21 | 21 | 19 | 10 | 20 | +8.5 % | +8.6 % | 4.0 | 3.10 (+2.37…+3.74) | 3.19 | 0.95 | +85.7 % | 3.04 | – |
| spel | 360 | 360 | 106 | 16 | 336 | +4.4 % | +2.5 % | 14.5 | 2.20 (+1.69…+2.76) | 2.10 | 0.81 | +77.7 % | 2.55 | – |
| skugga | 1011 | 1011 | 116 | 16 | 940 | +1.4 % | +1.2 % | 34.3 | 0.87 (+0.61…+1.20) | 0.83 | 0.85 | +65.9 % | 1.80 | – |
| modelltest | 904 | 904 | 117 | 16 | 835 | +7.4 % | +7.1 % | 17.5 | -0.09 (-0.48…+0.44) | -0.15 | 0.82 | +44.2 % | 1.85 | 0.2735 / 0.2447 (337) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 224 | 0.93 (+0.16…+1.63) | +69.3 % | +3.5 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.17) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 2 | -0.08 (–) | +50.0 % | +96.0 % |
| points | **ok** | 570 | 1.17 (+0.72…+1.56) | +66.4 % | +0.1 % |
| pr | **osäker** | 29 | 1.15 (-2.26…+2.95) | +65.5 % | -1.2 % |
| pra | **osäker** | 21 | 0.94 (-0.41…+2.90) | +70.0 % | -9.1 % |
| ra | **osäker** | 50 | 0.72 (-1.16…+0.89) | +69.4 % | +2.5 % |
| rebounds | **ok** | 288 | 1.09 (+0.81…+1.48) | +72.2 % | -3.5 % |
| steals | **ok** | 27 | 4.85 (+3.10…+10.14) | +88.9 % | +31.8 % |
| threes | **ok** | 167 | 1.51 (+0.55…+2.34) | +67.9 % | +11.8 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 2 | 5.01 | +92.0 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 12 | 7.77 | -30.8 % |
| spel | borttagen | 42 | 2.69 | -22.3 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 58 | 0.75 | -14.2 % |
| skugga | borttagen | 99 | 0.90 | -6.9 % |
| skugga | flyttad linje (för oss) | 164 | 4.62 | +15.4 % |
| skugga | flyttad linje (mot oss) | 40 | -4.97 | -6.9 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 39 | -0.21 | -33.6 % |
| modelltest | borttagen | 103 | 0.05 | +24.1 % |
| modelltest | flyttad linje (för oss) | 102 | 4.41 | +12.9 % |
| modelltest | flyttad linje (mot oss) | 45 | -5.91 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2446 / 0.2358 (59) | -0.0515…+0.0712 | 0.84 (-0.13…+1.88) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **degraded** | 0.2699 / 0.2410 (112) | +0.0009…+0.0567 | -0.60 (-0.97…-0.04) | 5 | +18.4 % |
| pr | **insufficient_data** | 0.3341 / 0.2493 (25) | +0.0618…+0.1264 | 0.70 (-1.19…+2.26) | 0 | – |
| pra | **insufficient_data** | 0.3158 / 0.2509 (21) | -0.0372…+0.1123 | -0.11 (-1.22…+1.49) | 0 | – |
| ra | **insufficient_data** | 0.2546 / 0.2409 (22) | -0.0477…+0.1126 | 0.26 (-1.62…+1.28) | 0 | – |
| rebounds | **shadow** | 0.2723 / 0.2518 (57) | -0.0201…+0.0760 | -0.53 (-1.02…-0.06) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0375…+0.1597 | 3.97 (+1.83…+5.76) | 0 | – |
| threes | **shadow** | 0.2826 / 0.2599 (31) | -0.0468…+0.0793 | 0.12 (-0.84…+1.64) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 4 marknader: assists 0.592, threes 0.719, rebounds 0.954, points 0.981

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 82 | 0.2580 | 0.2544 | 0.3015 | -0.0000…+0.0042 |
| p_modell_min | 82 | 0.3134 | 0.2544 | 0.3015 | +0.0573…+0.1795 |
| p_faktorer | 60 | 0.2591 | 0.2535 | 0.3228 | – |
| p_faktorer_ra | 60 | 0.3148 | 0.2535 | 0.3228 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 9 | +22.3 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |
| 2.50–3.00 | 0 | – | 3.49 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
