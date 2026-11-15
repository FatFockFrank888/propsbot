# NBA – utvärdering på framåtriktad data (2026-11-15T23:22:10+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 20 | 20 | 18 | 10 | 19 | +4.2 % | +0.5 % | 4.0 | 3.08 (+2.36…+3.77) | 3.18 | 0.95 | +85.0 % | 2.97 | – |
| spel | 355 | 355 | 103 | 15 | 323 | +4.9 % | +2.8 % | 14.5 | 2.11 (+1.66…+2.55) | 2.00 | 0.81 | +77.3 % | 2.64 | – |
| skugga | 998 | 998 | 115 | 15 | 885 | +2.0 % | +2.1 % | 27.0 | 0.84 (+0.58…+1.17) | 0.80 | 0.85 | +65.7 % | 1.77 | – |
| modelltest | 892 | 892 | 116 | 15 | 798 | +8.7 % | +8.5 % | 17.5 | -0.08 (-0.48…+0.45) | -0.14 | 0.82 | +44.4 % | 1.91 | 0.2702 / 0.2433 (300) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 222 | 0.91 (+0.12…+1.61) | +68.8 % | +2.9 % |
| blocks | **ok** | 14 | 4.14 (+2.62…+5.27) | +100.0 % | +26.2 % |
| pa | **insufficient_data** | 1 | 0.76 (–) | +100.0 % | – |
| points | **ok** | 566 | 1.16 (+0.73…+1.60) | +66.2 % | -0.1 % |
| pr | **osäker** | 25 | 1.29 (-2.29…+2.95) | +65.2 % | -6.6 % |
| pra | **osäker** | 20 | 1.09 (-0.19…+3.23) | +73.7 % | -4.1 % |
| ra | **osäker** | 48 | 0.76 (-1.16…+1.07) | +68.9 % | +8.9 % |
| rebounds | **ok** | 283 | 1.05 (+0.80…+1.43) | +72.0 % | -2.9 % |
| steals | **ok** | 27 | 4.85 (+3.08…+10.23) | +88.9 % | +37.0 % |
| threes | **ok** | 167 | 1.16 (+0.35…+1.82) | +66.5 % | +15.1 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 1 | 6.54 | – |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 5 | 9.97 | – |
| spel | borttagen | 42 | 2.69 | -26.5 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | -9.4 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 34 | 0.66 | -16.6 % |
| skugga | borttagen | 94 | 0.99 | -9.6 % |
| skugga | flyttad linje (för oss) | 161 | 4.57 | +15.1 % |
| skugga | flyttad linje (mot oss) | 39 | -5.69 | -0.2 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 24 | 0.03 | -35.3 % |
| modelltest | borttagen | 96 | 0.02 | +24.6 % |
| modelltest | flyttad linje (för oss) | 101 | 4.46 | +13.6 % |
| modelltest | flyttad linje (mot oss) | 44 | -6.02 | -26.8 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2368 / 0.2359 (52) | -0.0647…+0.0717 | 0.86 (-0.12…+1.89) | 4 | -54.5 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| points | **shadow** | 0.2626 / 0.2393 (102) | -0.0103…+0.0547 | -0.60 (-0.97…-0.02) | 4 | +0.0 % |
| pr | **insufficient_data** | 0.3262 / 0.2496 (22) | +0.0526…+0.1123 | 1.07 (-0.73…+2.50) | 0 | – |
| pra | **insufficient_data** | 0.3134 / 0.2522 (16) | -0.0721…+0.1252 | 0.23 (-1.07…+1.56) | 0 | – |
| ra | **insufficient_data** | 0.2634 / 0.2408 (20) | -0.0477…+0.1480 | 0.28 (-1.62…+1.37) | 0 | – |
| rebounds | **degraded** | 0.2812 / 0.2529 (49) | -0.0190…+0.0916 | -0.62 (-1.05…-0.25) | 4 | -0.0 % |
| steals | **insufficient_data** | 0.3103 / 0.2511 (6) | -0.0368…+0.1597 | 3.97 (+1.78…+5.75) | 0 | – |
| threes | **insufficient_data** | 0.2782 / 0.2487 (29) | -0.0450…+0.0877 | 0.14 (-0.82…+1.74) | 7 | +42.4 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 3 marknader: assists 0.498, points 0.955, rebounds 0.990

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 45 | 0.2568 | 0.2527 | 0.3024 | -0.0000…+0.0050 |
| p_modell_min | 45 | 0.3093 | 0.2527 | 0.3024 | +0.0320…+0.1795 |
| p_faktorer | 23 | 0.2562 | 0.2486 | 0.3588 | – |
| p_faktorer_ra | 23 | 0.3442 | 0.2486 | 0.3588 | – |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 8 | +13.6 % | 3.78 |
| 2.00–2.50 | 11 | -2.7 % | 2.50 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
