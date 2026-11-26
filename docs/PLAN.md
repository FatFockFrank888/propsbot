# PLAN – marknadsankrad residualmodell (granskning av `docs/MODEL_SPEC.md`)

2026-11-26. Ingen kod är ändrad. Planen följer Regel 2 (Mål, Kritisk diagnos, Valt upplägg + förkastade alternativ,
Risker, Byggplan) och **väntar på godkännande**. Fotbollens spelarprops har en egen plan: `docs/PLAN_FOOTBALL_PROPS.md`.
Siffrorna kommer från grenen `data` (ögonblicksbild 26/11) och testsviten (250 gröna).

## Status 2026-11-26

| Fas | Status | Filer |
|---|---|---|
| 1 Devig | klar | `propsbot/quant/devig.py`, `tests/test_quant_devig.py` |
| 2 Walk-forward | klar | `propsbot/quant/walk_forward.py`, `tests/test_quant_walk_forward.py` |
| 3 Dataset | klar | `propsbot/quant/dataset.py`, `tests/test_quant_dataset.py` |
| 4 Residual + kalibrering | klar | `propsbot/quant/residual.py`, `calibration.py`, `tests/test_quant_residual.py` |
| 5 Spridning | klar | `propsbot/quant/dispersion.py`, `tests/test_quant_dispersion.py` |
| 6 Kelly | klar, skugga i tiers (`kelly_pct`, `kelly_u`) | `propsbot/quant/kelly.py`, `tests/test_quant_kelly.py`, `tests/test_quant_shadow.py` |
| 7 Utvärdering | klar, körd på NBA | `propsbot/quant/evaluate.py`, `tools/quant_report.py`, `KVANTRAPPORT_NBA_2026-11-26.md` |
| 8 Skugginkoppling NBA (p_resid) | väntar | Rapporten visar att residualen inte slår marknaden än, så det finns inget att logga som tillför något. Görs när residualen med mål = stängning slår marknaden i ≥ 2/3 av vecken |
| 9 LightGBM | väntar | n-grind ≥ 3 000 per sport |

Ändrat kriterium i fas 4: "brusfeatures ger |medel delta_logit| < 0,02" byttes mot "< 3 standardfel för interceptet".
0,02 låg under samplingsbruset (SE ≈ 0,017 vid n = 15 000). Log-loss-villkoret står kvar.

## 0. Sammanfattning

Stora delar av specen finns redan: power-devig, negativ binomial, en marknadsankrad logit-blandning, CLV mot skarp
stängning och ¼ Kelly. Det verkliga gapet ligger inte i LightGBM. Det ligger på fyra andra ställen:

1. **Marknadens p för Kambi är ensidig och troligen för hög.** Konsensusspåret visar p 43,6 % mot utfall 37,3 %
   (n = 51, för litet för en slutsats men åt samma håll som tidigare). Att anta en hold på 7–9 % som specen gör
   räcker inte. Marginalen måste skattas.
2. **Insatsen tar inte hänsyn till oddset.** Tiers ger 1/2/3u efter edge. Mätt på 1 209 tier-spel är insatsen
   0,6 × ¼ Kelly vid odds 1,4–2, men 2,3 × ¼ Kelly vid odds 3–6,5. Vi överspelar långa odds och underspelar korta.
   Dessutom saknas matchtak sedan 18/11, och 3u = 3 % ligger över specens tak på 2–2,5 %.
3. **Det finns för lite data för en trädmodell.** NBA har cirka 1 150 avgjorda rader, men bara 623 med både `p_modell`
   och `p_marknad` och 332 med faktorfält. Fotbollens benlogg har 0 avgjorda (start 25/11). LightGBM med 10+ features
   på några hundra rader per marknad lär sig brus.
4. **Valideringen har ingen gemensam ram.** Varje modul har sin egen hållout på "nyaste 30 %"
   (`nba_kalibrering.py:40`, `benlogg.py`). Ingen delning grupperar per match, och inget test bevisar att data inte läcker.

Rekommendationen är att bygga specens struktur som ett **delpaket `propsbot/quant/`** i skuggläge:
devig → walk-forward → logit-linjär residual med offset (= `init_score`) → Platt-kalibrering → Kelly.
LightGBM och isotonisk kalibrering kommer in bakom en n-grind när datan räcker.

---

## 1. Gap- och konfliktgranskning

| # | Specen | Vårt nuläge (fil:rad) | Bedömning | Stöder flödena det? |
|---|---|---|---|---|
| 1 | Power-devig för tvåsidiga par | `market.py:34` `devig_power` (bisektion av k i [0,5; 3]). Används för Pinnacle-par (`market.py:208`), NBA-kombinationer (`nba.py:282`) och stege-k (`line_adjust.py:57`, `min_power_k_shots` = 1,2) | **Finns.** k returneras inte, inget skydd mot odds ≤ 1, n = 1 eller summa < 1 (arb), och inget test för n > 2 | Ja för Pinnacle, DK/bet365 (OddsPapi) och tvåsidiga Kambi-linjer |
| 2 | Ensidiga priser (ingår inte i specen för de generella propsen) | `market.py:157` marginalkurva m(odds) = bas + lutning·(odds−2). `estimate_one_sided_margin` (ridge mot prior). Pinnacle ensidigt fast 1,04 (`market.py:31`). Konsensusmarginal 7 % kalibreras i `benlogg.py` | **Konflikt med specens antagande.** De flesta spelbara Kambi-priserna är ensidiga ("2+ skott"), så power-metoden går inte att använda på dem. Den antagna marginalen verkar för låg (punkt 1 i §0) | Kalibrering mot utfall finns i benloggen, men n = 0 avgjorda |
| 3 | `base_logit` = marknadens no-vig-logit | `prop_market_prob` (`market.py:197`) blandar Pinnacle och Kambi i logit med vikter. NBA-stacken `nba_minutes.py:163` = σ(a + b_m·logit p_modell + b_k·logit p_marknad) | **Finns som linjär variant.** Prior (0, 0, 1) motsvarar "lita på marknaden" (400 obs). Det är specens residualidé med en linjär modell i stället för träd | — |
| 4 | LightGBM med `init_score` | Inte installerat (`requirements.txt`: numpy, pytest, openpyxl) | **Saknas, och bör inte vara först** (§2.3) | Data: NBA cirka 330–620 rader med features, fotboll 0 |
| 5 | NB med α skattad ur residualer | Spelarprops: fast `NB_SHAPE` skott 6 / SOT 10 (`player_model.py:33`), fouls 8 (`fouls.py`), NBA `NB_R` fast per marknad (`nba.py:229`). Hörnor: r skattas ur residualer (`corners.py:140`). Mål/assist Poisson | **Delvis.** Fördelningen är diskret. Det som saknas är skattad α per marknad för spelare | Ja: ESPN-box (NBA), FotMob/ESPN (fotboll) |
| 6 | "Inte Gauss" | Gauss används bara för minuter (avkortad normal + Gauss–Hermite, `nba_minutes.py:87`) och NBA-marginal (`nba_minutes.py:57`). Kombinationer: momentmatchad NB (`nba.py:285`) | **Ingen konflikt.** Antal räknas aldrig som normalfördelade | — |
| 7 | Minuter/TOI | NBA: minuter ~ N(m, sd), utklassningsjustering, `r_conditional` som undviker dubbelräknad varians (`nba_minutes.py:81`), skuggläge. Fotboll: takt per framträdande (start 1, inhopp 0,35, `player_model.py:113`), ingen förväntad minut. Grind: bekräftad elva (`lineups.py:121`, `lineup_required` true) | **Konflikt för fotboll** (per framträdande, inte per 90 × förväntade minuter). NBA ligger före specen | Fotboll: ESPN-produktionen saknar minuter. FotMob har `minutes_played` (används bara i `tools/backtest_fotmob.py`) |
| 8 | Isotonisk på OOS-veck | Platt/logit-linjär överallt: `benlogg.py` PRIOR_CAL (a + b·logit p), `nba_kalibrering.py:129`, `fit_stack` | **Avvikelse, men vi har rätt** vid nuvarande n (§2.4) | — |
| 9 | Walk-forward, train_end < val_start < test_start | Ad hoc: "nyaste 30 %" (`nba_kalibrering.py:40`), stacken skattas och används på nästa skanning (framåtriktad), backtest med datumdelning (val 1–14/10, test 15/10+) | **Gap:** ingen gemensam delare, ingen gruppering per match/dag, ingen embargo, inget läckagetest | — |
| 10 | Log-loss + CLV | Log-loss och Brier i `benlogg.py:85-92` och `nba_eval.py`. CLV mot skarp stängning `skarp_clv.py` (Pinnacle/DK, `clv_skarp_pp`), stängningsarkiv `stangning_arkiv/*.jsonl` | **Finns.** CLV är vårt starkaste mått (styrkan bygger på det, `strength.py`) | Ja |
| 11 | EV = p·o − 1 | `decision.py:27` | **Finns** | — |
| 12 | EV-trösklar 3,5 % likvid / 6 % nisch | Tier C 4 %, B 5 %, sides 3 %, hörnor 5 %, `min_edge_all` 6 %, live 7 % (`settings.json`) | **I stort sett i linje.** Ändras inte utan CLV + ROI och ≥ 150 avgjorda (CLAUDE.md) | — |
| 13 | p_cal − p_market ≤ 0,12 | Tak i EV-enheter: `max_plausible_edge` 0,25, `tier_max_edge` 0,25, `sides_max_edge` 0,15, `live_max_edge` 0,2 | **Olika enheter.** 0,12 i p vid odds 2 motsvarar EV 0,24. Ett p-tak är mer konsekvent över oddsnivåer | — |
| 14 | ¼ Kelly, tak 2–2,5 %, matchtak | `decision.py:38` ¼ Kelly, tak 2 %, matchtak 5 % (`config.py:122-124`), men bara i den gamla kedjan/exporten. **Live**: styrka → 1–10u à 0,2 % (`strength.py`). **Tiers**: 1/2/3u à 1 % efter edge (`tiers.py:251`), inget matchtak (sedan 18/11) | **Konflikt** (§0 punkt 2). Ett ben per spelare och familj finns (`decision.py:89`, `test_one_per_player.py`) | — |
| 15 | NHL | Borttagen 12/11 | **Utgår** | — |
| 16 | Google Sheets | Sheet läser `site/csv/*.csv` från grenen `data` via IMPORTDATA (`sheet/propsbot_ark.gs:57`). Inga direkta skrivningar | Nya fält (p_resid, p_cal, kelly_u) blir nya CSV-kolumner, ingen ändring i arket behövs utom visning | Ja |

**Specens krav som flödena inte stöder i dag:**
- Tvåsidiga priser för de flesta spelbara Kambi-props (bara ensidiga "X+").
- Projekterade elvor med P(start) (vi har bara bekräftade elvor från FotMob/ESPN nära avspark).
- Minuter per spelare och match i produktionsflödet för fotboll (bara i backtestverktyget).
- Positionsfördelad motståndarstatistik (kräver per-spelare-data för motståndarnas motståndare).
- Hörnfeatures som korsningar och blockerade skott (football-data.co.uk har bara skott, skott på mål och hörnor).
- Set-piece-ansvar (ingen källa).
- Tillräcklig historik för LightGBM.

---

## 2. Kritik av specen (det vi bör ändra före bygget)

1. **Fel sport.** NHL utgår. NBA, där minutmodellen, faktorerna och stacken redan finns, saknas. Specens "TOI" motsvaras
   av NBA-minuter, och den delen är redan byggd i skuggläge.
2. **Vilken marknad är ankaret?** Specen säger "marknadens p" men skiljer inte mellan den skarpa referensen
   (Pinnacle/DK) och det spelbara bolaget (Kambi). Ankaret ska vara den **skarpaste tillgängliga p vid bokningstillfället**,
   med källan som feature. Edgen mäts mot det spelbara priset. Med Kambi som ankare lär sig modellen Kambis fel, vilket
   är vår edge, men då blir ensidig marginal (§1 rad 2) den kritiska punkten.
3. **Målvariabeln.** Utfallet (över/under) är mycket brusigt: en Brier-skillnad på 0,002 kräver tusentals rader.
   **Skarp stängning (logit p_close − logit p_open) som extra mål** ger mycket mer information per rad, och vi har
   stängningar för nästan alla rader (`skarp_stang_p` 1 158 av 1 214 i NBA). Rekommendation: träna residualen mot
   stängningen först och utvärdera mot utfall och CLV.
4. **Isotonisk regression vid litet n** ger trappsteg. Platåer och kanter skapar falska edges precis där p hoppar.
   Platt/logit-linjär med prior är bättre under ungefär 2 000 rader per marknad. Isotonisk bara bakom en n-grind.
   Kalibrera inte två gånger: ett lager räcker.
5. **Dubbelräknad spridning.** α skattad på råa antal innehåller redan minutvariansen. Om man sedan blandar över
   minutscenarier räknas den två gånger. Vi löser det med `r_conditional`. Specen måste säga det.
6. **Läckage som specen inte nämner.** (a) `p_market` måste vara priset vid prognostillfället, aldrig stängningen.
   (b) Flera rader per spelare och match (linjer/marknader) är korrelerade och måste ligga i samma veck (gruppera per
   `match_id`). (c) Rullande features (`traff_l5` m.fl.) ska ha `prognos_ts` < avspark. Det bokförs redan och ska testas.
7. **Push och void.** Heltalslinjer (hörnor, AH, vissa NBA-linjer) har push-sannolikhet. Kambi gör spelarprops
   ogiltiga om spelaren inte spelar. p ska alltså vara villkorad på att spelaren spelar, och EV ska räknas på
   (vinst, förlust, push).
8. **Kelly med osäkert p.** ¼ Kelly förutsätter ett kalibrerat p. Konsensus-p är bevisat för högt (§0). Kelly på ett
   för högt p överspelar systematiskt. Krymp först (p_cal), sätt insats sedan. Korrelerade ben (samma match)
   behöver gemensamt tak, se fotbollsspecen (0,65× och 3,5 %).
9. **Ett outliertak i p-enheter** (0,12) är bättre än våra EV-tak, men ska vara en grind ("manuell kontroll"), inte
   en tyst bortfiltrering. Annars missar vi skadenyheter, det enda fall där stora avvikelser är riktiga.
10. **Strukturen.** Toppnivåmappar (`features/`, `models/` …) krockar med paketet `propsbot/` och `propsbot/models.py`
    (dataklasser). Använd `propsbot/quant/` i stället.

---

## 3. Valt upplägg och förkastade alternativ

**Valt:** `propsbot/quant/` med rena funktioner (bara numpy), fullt testade, som **kopplas in i skuggläge**. De loggar
nya fält i befintliga bokföringar (`nba_modelltest.json`, `bokforing_ben_alla.json`) och påverkar inte LIVE eller
notiser. Befintliga funktioner (`devig_power`, `kelly_stake`, `nb_over`) flyttas inte. `quant` återanvänder dem, så
inget i produktionen byter beteende förrän ett separat godkännande.

**Förkastat:**
- *LightGBM direkt i LIVE:* för lite data, och nytt beroende i Windows-körningen (`start.bat`). Kommer som valfritt
  skuggsteg (fas 6) bakom importgrind och n-grind.
- *Skriva om `market.py`/`decision.py` till specens mappar:* stor diff utan ny funktion och risk för regressioner
  i 250 tester.
- *Isotonisk som standard:* se §2.4.
- *Ändra tier-trösklar nu:* CLAUDE.md kräver CLV + ROI och ≥ 150 avgjorda. Fas 5 loggar bara Kelly-förslaget bredvid.

## 4. Risker

- **Överanpassning på små n.** Motverkas med prior mot marknaden, n-grindar och gruppvis walk-forward.
- **Skuggfält som läcker in i LIVE.** Test som säkrar att `stake`/`units` är oförändrade när `quant` är påslaget.
- **Skrivningar till skarp data från tester.** Alla tester på `tmp_path`, inga nätanrop (CLAUDE.md regel 3).
- **Prestanda.** Gauss–Hermite × NB per rad är redan billigt. LightGBM-inferens bara i skugga.
- **Parameterdrift.** Nya parametrar i `settings.json`, PARAMETRAR.md och README uppdateras i samma commit (regel 4).

---

## 5. Byggplan (isolerade, testbara faser)

Varje fas är en egen commit på `claude/nifty-turing-femqsu`. "Klar" betyder att fasens tester är gröna och att hela
sviten är grön en gång före commit.

### Fas 1: Devig (`propsbot/quant/devig.py`)
- `power(odds) -> (probs, k)`, `proportional`, `shin` (tunna lager över `market.py`), `one_sided(odds, margin_curve)`,
  `base_logit(p, eps=1e-4)`.
- Inmatning valideras: odds ≤ 1 eller tom lista ger `ValueError`, n = 1 kräver ensidig väg.
- **Tester `tests/test_quant_devig.py`:**
  - PASS om `sum(power(o)) == 1 ± 1e-9` för 1 000 slumpade par och trippel (marginal −2 % … +15 %).
  - PASS om k > 1 vid positiv marginal och k < 1 vid negativ (arb).
  - PASS om lika odds ger lika p.
  - PASS om power ger lägre p än proportionell för outsidern (favorit/outsider-effekten).
  - PASS om `(1/o1)^k + (1/o2)^k = 1 ± 1e-9` för returnerat k.
  - PASS om `base_logit(0)`/`(1)` är ändliga (klippning).
  - FAIL-skydd: `power([1.0, 2.0])` kastar.

### Fas 2: Walk-forward (`propsbot/quant/walk_forward.py`)
- `splits(rows, ts_key="avspark", group_key="match_id", n_folds, min_train, embargo_h=6, expanding=True)` ger index.
- `assert_no_leak(rows, split, feature_ts_key="prognos_ts")`.
- **Tester `tests/test_quant_walk_forward.py`:**
  - PASS om `max(ts[train]) < min(ts[val]) < min(ts[test])` i varje veck.
  - PASS om inget `match_id` finns i två delar.
  - PASS om embargot håller: inga träningsrader inom 6 h före val-start.
  - PASS om expanderande träning växer monotont.
  - PASS om `assert_no_leak` larmar på en konstruerad rad med `prognos_ts > avspark` och på en rad där
    `p_market` är tagen efter `prognos_ts`.
  - PASS om oordnad indata ger samma veck som sorterad.

### Fas 3: Datasetbyggare (`propsbot/quant/dataset.py`)
- Läser befintliga bokföringar (sökväg som argument, **aldrig** git eller nät) och ger enhetliga rader:
  `ts, match_id, sport, marknad, linje, sida, odds, p_market, p_market_src, p_model, p_close, y, features{…}`.
  Saknade features blir `NaN`.
- **Tester `tests/test_quant_dataset.py`** (fixtur i `tests/fixtures/quant_ledger_small.json`, cirka 30 rader):
  - PASS om strukna och oavgjorda rader inte får `y`.
  - PASS om `p_close` aldrig används som `p_market`.
  - PASS om saknade fält blir `NaN` utan undantag.
  - PASS om under-rader får `y = 1 − y_over` och `p = 1 − p_over`.

### Fas 4: Kalibrering och residual (`propsbot/quant/calibration.py`, `propsbot/quant/residual.py`)
- `residual.fit(X, y, offset=base_logit, l2, prior)`: logistisk regression med offset, alltså specens `init_score`
  men linjär. Ger delta_logit. `NaN` hanteras med medelimputation och en saknad-flagga.
- Valfritt mål: `target="close"` (regression på logit p_close − base_logit).
- `calibration.platt_fit/apply` (a + b·logit p, ridge mot (0, 1)) och `isotonic_fit` (pool-adjacent-violators i numpy)
  med `min_n=2000`, annars `NotEnoughData`.
- **Tester `tests/test_quant_residual.py`, `tests/test_quant_calibration.py`:**
  - PASS om residualen ger exakt `p_market` (±1e-9) utan features.
  - PASS om brusfeatures ger |medel delta_logit| < 0,02 och log-loss OOS ≥ marknaden − 0,001.
  - PASS om en syntetisk signal (y beror på x1) ger OOS log-loss lägre än marknaden.
  - PASS om Platt återfinner kända (a, b) ±0,05 på 20 000 syntetiska rader.
  - PASS om isotonisk är monoton och kastar vid n < `min_n`.
  - PASS om kalibreringen bara ser träningsveckets index (mock som registrerar index).

### Fas 5: Spridning (`propsbot/quant/dispersion.py`)
- `fit_nb_r(mu_hat, y, prior_r, prior_n)`: momentmetod/ML på walk-forward-residualer per marknad.
  Ger r för skugg-p (ersätter **inte** `NB_SHAPE`/`NB_R` i LIVE).
- **Tester `tests/test_quant_dispersion.py`:**
  - PASS om simulerad NB(μ, r = 8) med n = 5 000 ger r̂ inom ±15 %.
  - PASS om Poisson-data ger r̂ ≥ 50 (klipps till taket).
  - PASS om litet n ger r̂ nära prior.
  - PASS om `nb_over` med r → ∞ närmar sig `poisson_over` (±1e-3).

### Fas 6: Insats (`propsbot/quant/kelly.py`)
- `stake(p, odds, frac=0.25, cap=0.02)`, `portfolio(bets, per_match_cap=0.035, corr_mult=0.65, one_per_player=True)`,
  `units(stake, unit=0.01)`.
- Loggas som `kelly_u` bredvid tiers `units` (skugga). Ingen ändring av `tiers.units_for` utan nytt godkännande.
- **Tester `tests/test_quant_kelly.py`:**
  - PASS om EV ≤ 0 ger 0,0.
  - PASS om p = 0 eller odds ≤ 1 ger 0,0.
  - PASS om insatsen aldrig överstiger `cap` (egenskapstest över ett rutnät).
  - PASS om ¼ Kelly vid p = 0,55, odds 2,0 blir 0,025 och klipps till 0,02.
  - PASS om samma spelare ger att bara högsta EV behålls.
  - PASS om summan per match är ≤ 3,5 % och andra benet skalas 0,65.
  - PASS om `stake` matchar `decision.kelly_stake` för samma indata (ingen drift mellan kedjorna).

### Fas 7: Utvärdering och befordringsregel (`propsbot/quant/evaluate.py`, `tools/quant_report.py`)
- Per veck och marknad: log-loss, Brier, ECE, CLV-pp (mot `skarp_stang_p`) och ROI för marknad, modell, residual
  och kalibrerad. Rapporten skrivs som markdown (sammanfattning, inga råa rader).
- Befordringsregel (förslag, beslutas separat): ≥ 150 avgjorda, CLV-medel > 0 med 95 % CI över 0, log-loss bättre
  än marknaden i ≥ 2/3 av vecken.
- **Tester `tests/test_quant_evaluate.py`:**
  - PASS om log-loss och Brier matchar handräknade värden på 4 rader.
  - PASS om CLV-pp matchar `skarp_clv.clv_pp` för samma rad.
  - PASS om befordringsregeln returnerar False vid n = 149.

### Fas 8: Skugginkoppling (NBA först)
- `nba.py` och `nba_eval.py`: beräkna `p_resid`, `p_cal`, `kelly_u` när `settings["quant_shadow"]` är true
  (standard false). Fälten skrivs till `nba_modelltest.json` och som nya kolumner i `site/csv/nba.csv`.
  Arket visar dem i en ny dold kolumn.
- **Tester `tests/test_quant_shadow.py`:**
  - PASS om `odds`, `edge`, `units` och `stake` är identiska med och utan `quant_shadow`.
  - PASS om de nya CSV-kolumnerna finns.
  - PASS om ingen fil utanför `tmp_path` skrivs (monkeypatch på `Path.write_text`/`open`).
  - PASS om ingen notis skickas (mock av `notify`).

### Fas 9 (valfri, n-grind): LightGBM i skugga
- `propsbot/quant/residual_gbm.py`. Importen är valfri: utan `lightgbm` hoppas fasen över. `init_score=base_logit`,
  `num_leaves ≤ 7`, `min_data_in_leaf ≥ 100`, `learning_rate 0.02`, tidigt stopp på val-vecket och monotona
  begränsningar för (p_model − p_market).
  Körs bara när det finns ≥ 3 000 avgjorda per sport.
- **Tester:**
  - `pytest.importorskip("lightgbm")`.
  - PASS om noll träd ger `p_market`.
  - PASS om brusdata ger OOS log-loss ≥ marknaden − 0,001.
  - PASS om utfallet är deterministiskt med fast seed.

**Ordning och beroenden:** 1 → 2 → 3 → (4, 5, 6 parallellt) → 7 → 8 → 9. Fotbollsplanen återanvänder faserna 1–7.
