# NBA – utvärdering på framåtriktad data (2026-11-18T05:23:32+00:00)

Bara bokförda prognoser (gjorda före matchen). Unika prestationer = spelare × match × marknad.

| Bokföring | Rader | Prestationer | Matcher | Dagar | Avgjorda | ROI flat | ROI modell | Max DD (u) | CLV pe skarp (95 %) | CLV pe skarp verifierad | Verifierad täckning | Slog skarp stängning | CLV pe mot Unibets stängning | Brier modell / marknad (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| live | 27 | 27 | 23 | 12 | 27 | -3.8 % | -2.7 % | 4.2 | 2.86 (+2.21…+3.62) | 2.92 | 0.96 | +85.2 % | 2.59 | – |
| spel | 391 | 391 | 116 | 17 | 368 | +4.2 % | +2.1 % | 14.5 | 2.22 (+1.75…+2.76) | 2.08 | 0.81 | +78.0 % | 2.66 | – |
| skugga | 1155 | 1155 | 128 | 17 | 1080 | +1.9 % | +2.1 % | 39.8 | 0.87 (+0.61…+1.15) | 0.81 | 0.85 | +65.8 % | 1.82 | – |
| modelltest | 1006 | 1006 | 129 | 17 | 938 | +5.3 % | +5.2 % | 34.2 | -0.03 (-0.40…+0.46) | -0.10 | 0.81 | +45.4 % | 1.86 | 0.2762 / 0.2443 (440) |

## Marknadsstatus för LIVE (marknadsbaserade spel mot skarp stängning)

| Marknad | Status | Spel | CLV pe skarp (95 %) | Slog | ROI flat |
|---|---|---|---|---|---|
| assists | **ok** | 254 | 1.00 (+0.29…+1.56) | +70.3 % | +5.2 % |
| blocks | **ok** | 15 | 3.85 (+1.84…+4.65) | +93.3 % | +26.2 % |
| pa | **osäker** | 14 | -0.74 (-2.38…+0.80) | +50.0 % | +9.0 % |
| points | **ok** | 625 | 1.19 (+0.75…+1.51) | +66.6 % | +0.5 % |
| pr | **osäker** | 45 | 1.49 (-0.26…+3.15) | +71.1 % | -3.1 % |
| pra | **osäker** | 24 | 0.63 (-0.37…+2.67) | +66.7 % | -11.9 % |
| ra | **osäker** | 61 | 0.44 (-1.69…+0.86) | +63.3 % | +5.7 % |
| rebounds | **ok** | 315 | 1.08 (+0.78…+1.44) | +71.4 % | -5.9 % |
| steals | **ok** | 30 | 4.51 (+2.68…+9.33) | +90.0 % | +40.0 % |
| threes | **ok** | 190 | 1.56 (+0.71…+2.26) | +69.2 % | +12.7 % |

## Skarp stängning per status

Verifierad = referensens notering högst 60 min före start. Flyttad linje = vår linje försvann men en närliggande fanns kvar; stängningen omräknad till vår linje. För oss = över + linjen upp / under + linjen ned (pengar på vår sida).

| Bokföring | Status | n | CLV pe skarp | ROI flat |
|---|---|---|---|---|
| live | ? | 8 | 2.77 | -22.8 % |
| live | borttagen | 1 | 1.14 | -100.0 % |
| live | flyttad linje (för oss) | 2 | 7.04 | -14.0 % |
| live | verifierad | 16 | 2.48 | +12.9 % |
| spel | ? | 38 | 3.71 | -7.7 % |
| spel | borttagen | 48 | 2.98 | -15.0 % |
| spel | flyttad linje (för oss) | 39 | 4.41 | +0.0 % |
| spel | flyttad linje (mot oss) | 10 | -4.45 | +4.0 % |
| spel | verifierad | 234 | 1.74 | +8.4 % |
| skugga | ? | 173 | 0.59 | -2.9 % |
| skugga | borttagen | 124 | 0.98 | +1.8 % |
| skugga | flyttad linje (för oss) | 170 | 4.63 | +14.5 % |
| skugga | flyttad linje (mot oss) | 41 | -4.90 | -4.5 % |
| skugga | verifierad | 625 | 0.27 | +0.0 % |
| modelltest | ? | 119 | 0.01 | -15.2 % |
| modelltest | borttagen | 124 | 0.26 | +11.3 % |
| modelltest | flyttad linje (för oss) | 106 | 4.44 | +11.6 % |
| modelltest | flyttad linje (mot oss) | 46 | -5.93 | -25.0 % |
| modelltest | verifierad | 568 | -0.45 | +10.8 % |

## Status per marknad

| Marknad | Status | Brier modell / marknad (n) | Skillnad 95 % | CLV pe (95 %) modelltest | LIVE avgjorda | LIVE ROI flat |
|---|---|---|---|---|---|---|
| assists | **shadow** | 0.2462 / 0.2331 (68) | -0.0446…+0.0694 | 1.03 (+0.13…+2.00) | 5 | -28.4 % |
| blocks | **insufficient_data** | 0.1979 / 0.2133 (4) | – | 3.37 (+1.03…+4.10) | 0 | – |
| pa | **insufficient_data** | 0.2468 / 0.2510 (9) | – | -1.94 (–) | 0 | – |
| points | **degraded** | 0.2758 / 0.2414 (135) | +0.0087…+0.0574 | -0.53 (-0.93…+0.01) | 6 | -1.3 % |
| pr | **degraded** | 0.3047 / 0.2543 (41) | +0.0262…+0.0775 | 0.68 (-0.53…+1.79) | 0 | – |
| pra | **shadow** | 0.3356 / 0.2505 (33) | -0.0015…+0.1277 | 0.11 (-0.82…+1.34) | 0 | – |
| ra | **insufficient_data** | 0.2375 / 0.2378 (29) | -0.0606…+0.0708 | 0.14 (-1.38…+1.10) | 0 | – |
| rebounds | **shadow** | 0.2831 / 0.2524 (74) | -0.0022…+0.0732 | -0.44 (-0.91…+0.03) | 8 | -18.8 % |
| steals | **insufficient_data** | 0.3281 / 0.2615 (8) | -0.0239…+0.1460 | 3.49 (+1.57…+5.29) | 0 | – |
| threes | **shadow** | 0.2691 / 0.2457 (39) | -0.0274…+0.0698 | 0.11 (-0.72…+1.41) | 8 | +24.6 % |

p för validering (max av Brier- och CLV-p) – Benjamini–Hochberg q = 0.1 över 6 marknader: assists 0.681, threes 0.803, rebounds 0.958, pra 0.973, points 0.998, pr 1.000

## Skuggmodeller (modelltest, samma spel)

| Fält | n | Brier | Brier marknad | Brier nuvarande modell | Skillnad mot marknad 95 % |
|---|---|---|---|---|---|
| p_stack | 185 | 0.2494 | 0.2480 | 0.2922 | -0.0014…+0.0037 |
| p_modell_min | 185 | 0.3029 | 0.2480 | 0.2922 | +0.0352…+0.0652 |
| p_faktorer | 163 | 0.2507 | 0.2468 | 0.2988 | +0.0001…+0.0066 |
| p_faktorer_ra | 163 | 0.2870 | 0.2468 | 0.2988 | +0.0176…+0.0734 |
| p_betyg | 91 | 0.2472 | 0.2414 | 0.2765 | +0.0043…+0.0154 |
| p_betyg_ra | 91 | 0.2964 | 0.2414 | 0.2765 | +0.0448…+0.0781 |

## LIVE per oddsintervall

| Odds | Avgjorda | ROI flat | CLV pe |
|---|---|---|---|
| 1.60–2.00 | 12 | +6.4 % | 3.57 |
| 2.00–2.50 | 13 | -17.7 % | 2.12 |
| 2.50–3.00 | 2 | +25.0 % | 3.35 |

Status-kriterier och begränsningar: se modulens docstring och GRANSKNING_NBA.md.
