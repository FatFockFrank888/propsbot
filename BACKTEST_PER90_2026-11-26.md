# Backtest F1–F2: per 90 med Empirical Bayes mot per framträdande, 2026-11-26

Data: ESPN summary för 548 ligamatcher (PL, LaLiga, Bundesliga, Serie A, Ligue 1), 14/8–26/11.
Prognoser för startande utespelare från 15/9; Platt skattad 15/9–15/10, test 16/10–26/11 (5 020 per linje).
Verktyg: `tools/backtest_per90.py` (rullande tillstånd, varje prognos ser bara tidigare matcher; läckagetest i
`tests/test_backtest_per90.py`).

- **M0** = dagens `player_model`: takt per framträdande (start 1, inhopp 0,35), senaste 8 lagmatcherna,
  halveringstid 5, krympt mot lagets snitt per startspelare (3 framträdanden).
- **M1** = F1–F2: takt per 90 ur ESPN-minuter, halveringstid 13 spelarmatcher, krympt mot ligans
  positionssnitt (CB, FB, DM/CM, AM/W, ST) med 450 (skott, fouls) / 630 (SOT) minuter, × E[min | start] / 90.
- Samma NB-form (skott 6, SOT 10, fouls 8), ingen matchkontext i någon av dem.

## Resultat

| Marknad | n test | utfall | M0 rå | M0 Platt | M1 rå | M1 Platt | Δ (M1−M0, Platt) | 95 % CI |
|---|---|---|---|---|---|---|---|---|
| fouls > 0.5 | 5020 | 60.9% | 0.6600 | 0.6579 | 0.6562 | 0.6572 | -0.0007 | -0.0021 … +0.0009 |
| fouls > 1.5 | 5020 | 26.3% | 0.5679 | 0.5638 | 0.5618 | 0.5618 | -0.0021 | -0.0039 … -0.0002 |
| shots > 0.5 | 5020 | 58.8% | 0.6309 | 0.6237 | 0.6069 | 0.6059 | -0.0178 | -0.0243 … -0.0110 |
| shots > 1.5 | 5020 | 29.8% | 0.5382 | 0.5367 | 0.5143 | 0.5166 | -0.0201 | -0.0264 … -0.0137 |
| shots > 2.5 | 5020 | 15.6% | 0.3686 | 0.3691 | 0.3538 | 0.3545 | -0.0146 | -0.0198 … -0.0094 |
| shots_on_target > 0.5 | 5020 | 29.1% | 0.5652 | 0.5630 | 0.5470 | 0.5453 | -0.0177 | -0.0236 … -0.0118 |
| shots_on_target > 1.5 | 5020 | 8.1% | 0.2500 | 0.2537 | 0.2378 | 0.2388 | -0.0149 | -0.0198 … -0.0102 |

Negativt Δ = per 90-modellen bättre. CI per match (bootstrap).
## Robusthet (Δ log-loss M1 − M0 efter Platt; ordning: fouls 0,5 / 1,5, skott 0,5 / 1,5 / 2,5, SOT 0,5 / 1,5)

| Variant | fouls | skott | SOT |
|---|---|---|---|
| M_prior 225 | −0,0003 / −0,0015 | −0,0165 / −0,0193 / −0,0147 | −0,0136 / −0,0126 |
| M_prior 450 (skott) / 630 (SOT), standard | −0,0007 / −0,0021 | −0,0178 / −0,0201 / −0,0146 | −0,0177 / −0,0149 |
| M_prior 900 | −0,0001 / −0,0016 | −0,0154 / −0,0162 / −0,0107 | −0,0177 / −0,0145 |
| M_prior 1 800 | +0,0023 / +0,0008 | −0,0109 / −0,0096 / −0,0048 | −0,0159 / −0,0126 |
| Bara historisk position (inte dagens elva) | −0,0007 / −0,0019 | −0,0148 / −0,0173 / −0,0127 | −0,0142 / −0,0125 |
| E[min] = 90 (utan minutmodellen) | +0,0007 / −0,0013 | −0,0175 / −0,0200 / −0,0142 | −0,0175 / −0,0146 |

## Tolkning

1. **Per 90 med positionsprior är klart bättre än dagens modell** för skott och SOT: 0,015–0,020 lägre log-loss,
   alla intervall under 0. Det är cirka tio gånger större än motståndar-/hemmaeffekten i backtesten 26/11 (0,002).
2. Vinsten kommer från **takten per 90 och positionspriorn**. Dagens prior (lagets snitt per startspelare) drar en
   anfallare och en mittback mot samma värde. Förväntade minuter tillför lite för startspelare, eftersom de flesta
   spelar 75–90, men hjälper fouls något.
3. M_prior 450 (skott) / 630 (SOT) ligger nära optimum, så specens värden står sig. Vinsten består med enbart
   historisk position (−15 %), så den beror inte på att dagens position är känd.
4. **Det här är mot utfall, inte mot marknaden.** Produktionens sannolikhet ankras mot Kambi/Pinnacle, så om modellen
   ger edge mot Unibet är fortfarande obevisat. Nästa steg (F5) är att bokföra `p_fb2` bredvid `p_cur`/`p_hyb` i
   benloggen (skugga) och mäta mot marknad och CLV vid ≥ 150 avgjorda.
5. Förbehåll: M0 ser här bara ligamatcher (produktionen även cuper/Europa), och rött kort syns inte i ESPN:s
   bytesrader (räknas som 90 min).
