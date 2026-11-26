# PLAN – fotbollens spelarprops (granskning av `docs/MODEL_SPEC_FOOTBALL_PROPS.md`)

2026-11-26. Ingen kod är ändrad. Planen bygger på `docs/PLAN.md` (faserna 1–7 där: devig, walk-forward, dataset,
residual/kalibrering, spridning, Kelly, utvärdering) och **väntar på godkännande** (Regel 2).

## 0. Sammanfattning

- **Värt att ta in nu:** per-90-takt × förväntade minuter med Empirical Bayes mot positionsprior. Den största
  modellbristen i dag är att takten räknas per framträdande (`player_model.py:113`).
  Även detta: skattad NB-spridning, ¼ Kelly med korrelationstak per match, och p-baserad "manuell kontroll"-grind.
- **Finns redan:** power-devig, ensidig marginalkurva för Kambi, bekräftad-elva-grind (`lineups.py:121`,
  `lineup_required`), ett ben per spelare och familj (`decision.py:89`), domarfaktor (`referees.py`) och
  lagets väntade mål ur Pinnacle (`market.py:135`, används som ratio^elasticitet).
- **Bör vänta eller ändras:** tacklingar (stöds inte i flödena), kort (testet stängdes 20/11 utan edge), PROJECTED_XI
  (vi har ingen källa till P(start), och regeln om bekräftad elva ska stå kvar), LightGBM (0 avgjorda ben i benloggen).

## 1. Fältkarta: vad finns, och vad blir `NaN` eller proxy

| Fält | Källa i dag | Status | Fallback |
|---|---|---|---|
| Två- vs ensidiga odds | Kambi mest ensidigt "X+", ibland tvåsidigt (`line_adjust.py:177` `kambi_fair`). Pinnacle tvåsidigt för skott och SOT (`pinnacle_trusted_markets`). bet365 via OddsPapi (bara datainsamling) | Finns | Ensidig marginalkurva (`market.py:157`), kalibrerad mot utfall (`benlogg.py`) |
| Bekräftad elva | FotMob/ESPN (`lineups.py`), `lu_state == "start"` i benloggen | Finns | Ingen. Spelet stryks (`lineup_required`) |
| P(start) före elvan | Saknas | **Saknas** | Ingen (vi spelar inte före elvan) |
| Minuter per match | FotMob `minutes_played` bara i `tools/backtest_fotmob.py`. ESPN i produktionen: framträdande och start/inhopp | **Delvis** | E[min \| start] ≈ 0,35/1-vikterna i dag. Byt till FotMob-minuter (fas F1) |
| Position | FotMob (backtest). `form.py` har positionsprior men används bara av den gamla `simulator`-kedjan | **Delvis** | Lagets snitt per startspelare (dagens prior, `player_model.py:190`) |
| Skott, SOT, fouls per spelare och match | ESPN (`results.py:56` `STAT_NAMES`: skott, SOT, fouls, mål, assist) | Finns | — |
| Tacklingar per spelare | Inte i `STAT_NAMES`. "tackle" i `EXCLUDE_WORDS` (`props_text.py:9`) | **Saknas** | Probe av ESPN/FotMob-fält och Kambi-utbud krävs först |
| Kort per spelare | ESPN har troligen gula/röda. Marknaden avstängd (`props_text.py:28`) | Avstängd | — |
| Domare | UEFA-API + football-data.co.uk + transfermarkt (`referees.py`), faktor ±15 % | Finns (bara fouls) | Faktor 1,0 |
| Lagets väntade mål, 1X2, AH | Pinnacle (`team_lambdas_from_pinnacle`) | Finns | Ligasnitt |
| Motståndarens medgivna per position | Saknas (kräver positionsmärkt per-spelare-data för motståndarnas motståndare) | **Saknas** | Lagnivå: motståndarens medgivna skott/fouls (finns i fouls.py för fouls, och i backtesten M4 "motst") |
| Set-piece/straffansvar | Ingen källa | **Saknas** | Proxy: andel av lagets straffar/frisparkar ur FotMob-händelser (senare), annars `NaN` |
| Vilodagar | Lagens schema hämtas redan (`player_model.py`, ESPN team schedule) | Härledbart | `NaN` → ingen effekt |
| Hemma/borta | Finns i match-raden | Finns | — |

## 2. Konflikter och kritik av fotbollsspecen

1. **Steg A, ensidig hold 7–9 %:** vår mätning pekar på att konsensus-p ligger för högt med 7 % (43,6 % mot utfall
   37,3 %, n = 51). Marginalen ska skattas per marknad, linje och oddsnivå (marginalkurvan finns), inte antas.
   Pinnacle saknar fouls, kort och tacklingar, så där finns ingen skarp referens och ankaret blir bara Kambi.
   Residualmodellen lär sig då Kambis fel. Det är OK, men all validering måste ske mot utfall, eftersom skarp CLV saknas.
2. **Steg B, `PROJECTED_XI`:** ingen källa, och regeln "bekräftad elva" har varit avgörande för oss. Föreslås bara som
   logg (skugga), aldrig spel. Lägg också till två fall specen missar: **inhopp** (Kambi: spelet står om spelaren hoppar
   in, och p ska då bygga på inhoppsminuter) och **voidregeln** (spelar inte = ogiltigt, så p ska vara villkorad på
   att spelaren spelar).
3. **Steg C, EB-formeln** är rätt i princip, men:
   - Minutvikterna ska avta per **match** och inte per minut (`form.py:64` avtar per 90 minuter, vilket ger
     inhoppare ett för långt minne).
   - Förra säsongens 30 % behöver justeras för lag- eller ligabyte. Annars bär en spelare med sig fel nivå efter en
     övergång. Använd ligafaktor eller nollställ.
   - Positionspriorn per liga och roll kräver positioner. Utan FotMob blir det lagets snitt (dagens lösning).
   - M_prior 450/630 är rimliga startvärden och ska skattas (fas F3, maximal marginallikelihood på historiken).
4. **Steg D:** "favorit → fler skott för anfallare" fångas redan av ratio^elasticitet (backtest 26/11: motståndare +
   hemmaplan ger t 2–7 men bara cirka 0,002 i Brier). Ta in motståndare och hemmaplan som features, men förvänta
   ingen stor vinst. Positionsfördelad motståndarstatistik är dyr och brusig: vänta tills grundmodellen visar CLV.
5. **Steg E:** featuren `logit(p_count) − base_logit` är bra (det är vår stack), men LightGBM på 0 avgjorda ben
   fungerar inte. Linjär residual med offset först (PLAN.md fas 4), isotonisk bara vid n ≥ 2 000.
   Om p_count räknas med minutblandning måste κ vara villkorad (jfr `nba_minutes.r_conditional`), annars dubbelräknas
   spridningen.
6. **§3, insats:** 4 % och 6 % stämmer med tier C/B (4 / 5 %). Korrelationsregeln (0,65×, 3,5 % per match) är bättre än
   i dag (inget matchtak i tiers sedan 18/11). Specen missar korrelation mellan **motståndare** (två lag i samma
   match delar matchtempo): ta med dem i samma matchtak. Stale-line-grinden 0,14 i p tas in som "manuell kontroll".
7. **Marknadsurval:** börja med skott och SOT (data, skarp referens, tvåsidiga Pinnacle-linjer). Fouls stannar i
   skugga (pågående datainsamling). Kort är avstängda. Tacklingar kräver en probe först.

## 3. Valt upplägg, förkastade alternativ, risker

- **Valt:** `propsbot/quant/fb_minutes.py`, `fb_rates.py` och `fb_context.py` som rena funktioner. En skuggmodell
  `p_fb2` bokförs i `bokforing_ben_alla.json` bredvid `p_cur/p_hyb/p_alt` och jämförs i `benlogg.analyse`.
  Inga notiser och inga spel.
- **Förkastat:**
  - Att väcka `form.py`/`simulator.py` (den gamla kedjan, andra dataklasser, ingen produktion).
  - PROJECTED_XI-spel.
  - Tacklingar och kort i första omgången.
- **Risker:** FotMob-minuter kan saknas eller ha annan namnmatchning än ESPN (befintlig `same_person`). Positionsetiketter
  skiljer mellan källor (mappa till CB/FB/DM-CM/AM-W/ST). Litet n per liga.

## 4. Byggplan

Förutsättning: faserna 1, 2, 3, 4 och 6 i `docs/PLAN.md` är klara.

### F0: Probe av fält (inga modelländringar)
- Utöka `propsbot/probe.py` med en torr kontroll som listar statistiknamn i ESPN:s och FotMobs spelarstatistik
  (minuter, position, tacklingar, kort) och Kambi-etiketter som innehåller "tackle".
- **Test `tests/test_probe_fields.py`** (fixturer, inget nät):
  - PASS om parsern hittar `minutes_played`, `position` och `tackles` i en FotMob-fixtur.
  - PASS om en saknad nyckel ger `None` utan undantag.

### F1: Minuter och elvagrind (`propsbot/quant/fb_minutes.py`)
- `status(lineup, player) -> CONFIRMED_XI | BENCH | DOUBTFUL | UNKNOWN`.
- `expected_minutes(history, status)`: E[min | start] med avtagande vikter per match, eller E[min | inhopp] om
  spelaren startar på bänken (bara för logg).
- `gate(status) -> (spelbar: bool, ev_extra: float, kelly_mult: float)`.
- **Tester `tests/test_quant_fb_minutes.py`:**
  - PASS om BENCH och DOUBTFUL ger `stake == 0.0` genom `kelly.portfolio`.
  - PASS om UNKNOWN ger `spelbar False` (som `lineup_required` i dag).
  - PASS om CONFIRMED_XI för en spelare som alltid spelar 90 minuter ger E ≈ 90 ± 1.
  - PASS om en spelare som byts ut vid 60 minuter i 5 av 5 matcher ger E ≈ 60 ± 2.
  - PASS om E[min] ligger i [0, 95].
  - PASS om en tom historik ger positionsmedel (`NaN`-säkert).

### F2: Per-90 med Empirical Bayes (`propsbot/quant/fb_rates.py`)
- `shrunk_rate(minutes, counts, prior_rate, m_prior, half_life_matches=13, prev_season_weight=0.3)`.
- `lambda_base = rate90 · E[min] / 90`.
- **Tester `tests/test_quant_fb_rates.py`:**
  - PASS om en spelare med 90 minuter och 3 skott ligger inom 15 % av priorn (låg-minut → prior).
  - PASS om en spelare med 3 000 minuter ligger inom 5 % av sin råa takt (hög-minut → egen takt).
  - PASS om avståndet till priorn minskar monotont med minuterna (egenskapstest).
  - PASS om `m_prior = 0` ger den råa takten och `m_prior → ∞` ger priorn.
  - PASS om äldre matcher väger mindre (halveringstid på 13 matcher ger vikt 0,5 ± 0,01 vid ålder 13).
  - PASS om förra säsongens vikt är 0,3.
  - PASS om lag- eller ligabyte nollställer förra säsongens bidrag.

### F3: Spridning och anker (`propsbot/quant/dispersion.py` från PLAN fas 5)
- κ per stat (skott, SOT, fouls) skattat walk-forward. Om minutblandning används: villkorad κ.
- **Tester:**
  - PASS om simulerade data med κ = 6 ger κ̂ inom ±15 %.
  - PASS om `p_count` med fasta minuter är identisk med `player_model.nb_over`.

### F4: Matchkontext (`propsbot/quant/fb_context.py`)
- `team_goal_factor` (finns, återanvänd `team_lambdas_from_pinnacle`), `opp_factor` på lagnivå, `ref_factor`
  (återanvänd `referees`, bara fouls), `rest_days`, `is_home`. Alla klipps och ger 1,0 eller `NaN` vid saknad data.
- **Tester `tests/test_quant_fb_context.py`:**
  - PASS om alla faktorer ligger i sina klippintervall.
  - PASS om saknad domare ger 1,0.
  - PASS om vilodagar räknas från senaste match före avspark (aldrig efter: läckagetest med en framtida match i
    schemat).

### F5: Skuggmodell `p_fb2` och residual
- I `spelarprops.record_hyb` och `benlogg.record_all`: räkna `p_fb2` (EB-takt × minuter × kontext → NB) och, när
  `benlogg` har ≥ 150 avgjorda per marknad, `p_fb2_resid` (PLAN fas 4, offset = marknadens logit, feature
  `logit(p_fb2) − base_logit`). Ingen påverkan på spel.
- **Tester `tests/test_quant_fb_shadow.py`:**
  - PASS om de befintliga fälten `p_cur`/`p_hyb` och spelbeslut är oförändrade.
  - PASS om `p_fb2` finns för rader med bekräftad startspelare och saknas för övriga.
  - PASS om ingenting skrivs utanför `tmp_path`.
  - PASS om ingen notis skickas.

### F6: Insats med korrelation (`propsbot/quant/kelly.py`, PLAN fas 6)
- Lägg till lineup-grind, motståndare i samma matchtak och p-tak 0,14 som ger `MANUAL_REVIEW`.
- **Tester `tests/test_quant_fb_staking.py`:**
  - PASS om skott och SOT för samma spelare och match ger att bara högsta EV får insats.
  - PASS om två lagkamrater ger andra insatsen 0,65× den fristående.
  - PASS om tre ben (två lag) ger matchsumman ≤ 3,5 %.
  - PASS om varje ben är ≤ 2 %.
  - PASS om `p_cal − p_market = 0,15` ger status `MANUAL_REVIEW` och insats 0.
  - PASS om EV under 4 % (skott/SOT) eller 6 % (fouls) ger 0.

### F7: Utvärdering och beslut
- `tools/quant_report.py --sport fotboll`: log-loss, Brier och kalibreringskurva per marknad och linje för
  `p_cur`, `p_hyb`, `p_fb2`, marknad och konsensus. CLV mot Pinnacle för skott och SOT.
- Beslutsregel (förslag): `p_fb2` får ersätta `p_hyb` i skuggan när den slår den på log-loss med parad t > 2 vid
  ≥ 150 avgjorda. Den får styra spel först vid CLV > 0 (95 % CI) och ett separat godkännande.
- **Test:** PASS om rapporten bara skriver sammanfattningar (inga rader per spelare) och om den kastar vid tom indata.

**Uppskattad ordning:** F0 → F1 → F2 → F3/F4 → F5 → F6 → F7. F0–F2 ger mest värde per insats.
