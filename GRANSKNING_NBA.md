# Granskning av NBA-kedjan – 2026-11-11

Gren: `nba-granskning`. Ingenting är publicerat eller driftsatt; boten kör `main` tills grenen godkänns och slås ihop.
Uppdraget var skrivet för en annan bot (`nbaprops/value.py`, `calibrate.py`, `calibration.json`, `parlay.py`,
`MIN_ODDS`, `ONE_SIDED_MARGIN`). De filerna finns inte här. Principerna har tillämpats på vår egen kedja.

## 1. Kedjan (data → … → utvärdering)

| Steg | Var | Vad |
|---|---|---|
| Odds | `propsbot/nba.py` `kambi_nba_props`, `pinnacle_nba_props` | Kambi-bolagen (spelbara) och Pinnacle (referens), halvlinjer |
| Linjeflytt | `nba.py` `interpolate_pinnacle` | Pinnacles marginalfria pris på närliggande linje -> Kambis linje via negativ binomial (märks "flyttad") |
| Marknadssannolikhet | `propsbot/scan.py` `consensus`, `group_fair_prob` | marginal bort **inom varje bolags eget par** (power-metoden), median per leverantörsgrupp, logit-snitt mellan grupper; gruppen som har det bästa priset räknas inte (konsensus utan det bedömda bolaget) |
| Projektion | `propsbot/nba_model.py` `NbaModel.expected` | minuter × per-minut-takt, speltid från out/doubtful omfördelas, back-to-back, motståndets insläppta poäng |
| Fördelning | `propsbot/player_model.py` `nb_over` | negativ binomial per marknad (`NB_R`) |
| Kalibrering + blandning | `nba.py` `model_test_rows`, `coherent_blend` | nivåjustering per marknad (trimmat snitt av log-odds-gap), blandning modell/marknad i log-odds, vikt 0,3 × dq |
| Edge, insats | `propsbot/decision.py` | EV = p × odds − 1; ¼ Kelly, tak 2 %; spela från |
| LIVE-urval | `propsbot/live.py` `select_live` | marknadsedge per marknad, modelledge ≥ 5 %, ≥ 2 grupper, odds 1,40–3,00, tak |
| Bokföring | `propsbot/ledger.py` | en rad per spelare och match, stängning = senaste odds hos samma bolag och linje |
| Rättning | `nba.py` `settle_nba` | ESPN-boxscore |
| Utvärdering | `propsbot/nba_eval.py` (ny) | se avsnitt 4 |

Utgångsläge: `python -m pytest -q` -> **164 passed** (före ändringar). Efter: **174 passed**.

## 2. Verifierade buggar (rättade)

1. **Osammanhängande sannolikheter i blandningen** – `nba.py` `model_test_rows` (före rättning).
   Nivåjusteringen räknades på sidospecifika sannolikheter: över- och underradernas gap (motsatta tecken) blandades
   i samma trimmade snitt, och justeringen drogs av **lika för båda sidorna**. Reproduktion (modell P(över) 0,60,
   marknad 0,50, justering 0,30, vikt 0,3): P(över) 0,508 och P(under) 0,447, **summa 0,955**.
   Dessutom tog gapen ut varandra, vilket syns i körloggarna ("nivåavvikelse … points −0.00, rebounds +0.00"),
   så kalibreringen var i praktiken avstängd. Rättning: `coherent_blend()` räknar allt i över-orientering,
   en blandad P(över) och under = 1 − P(över); gapen tas en gång per (match, spelare, marknad, linje).
   Test: `tests/test_nba_granskning.py::test_blend_is_coherent`, `test_blend_monotone_in_line`.
   **Följd:** nivåjusteringen blir verklig (inte ≈ 0), och modellens sannolikheter kommer att ändras efter
   sammanslagning. Det är en metodändring – nya rader märks `modellversion = 2026-11-11-koherent`.
2. **Heltalslinjer räknade push som vinst** – `kambi_nba_props`. Över/under på heltal N flyttades till N − 0,5,
   vilket för över gör "exakt N" (återbetalning) till vinst. Push modelleras inte i kedjan, så heltalslinjer hoppas
   nu över (Kambi och Pinnacle) och räknas i loggen. Test: `test_kambi_integer_line_is_skipped`.
3. **Spela från kunde visa ett odds under tröskeln** – `decision.play_from_odds` och webbsidan avrundade till
   närmaste hundradel. Nu avrundas uppåt (även sides). Test: `test_play_from_rounds_up`.
4. **Saknad spelare blev "struken" direkt** – `settle_nba`. Namnskillnad eller ofullständig boxscore är inte DNP.
   Nu väntar rättningen 48 h, därefter struken med `struken_orsak`. DNP enligt ESPN märks också.
   Test: `test_missing_player_is_not_auto_void`.
5. **Stängning utan tidpunkt** – `ledger.update_closing`. Stängningsoddset initieras till spelets eget odds; utan
   senare notering blev CLV 0 och räknades som täckt. Nu loggas `stangning_ts`; utvärderingen skiljer verifierad
   stängning från legacy.

## 3. Statistiska svagheter och antaganden (inte rättade – kräver data eller beslut)

* **Ensidiga marknader:** `fair_prob_one_sided` använder en antagen marginal m(odds) (`config.MarketConfig.one_sided_margin`),
  och Pinnacle ensidigt antas ha 3–4 % marginal. Det är antaganden, inte observerade priser. Sådana rader märks
  ("ingen Pinnacle/tvåsidig källa – högre edgekrav") och LIVE kräver minst 2 grupper och modellstöd.
* **Linjeflytt** (`interpolate_pinnacle`) är modellbaserad (fast `NB_R`). Märkta rader ("flyttad") är undantagna
  från nivåjusteringen men inte från LIVE.
* **Minuter och omfördelning:** speltid från out/doubtful fördelas proportionellt (× 0,8), questionable × 0,9 –
  heuristik utan egen validering. Ingen startspelarstatus, ingen modell för minutvarians.
* **Fördelning:** negativ binomial med fast form per marknad; ingen korrelation mellan statistikslag (PRA = summa
  av väntevärden, fördelad som NB med egen form).
* **Ingen parameterosäkerhet:** beslutet använder en punktsannolikhet. Ett intervall kräver bootstrap över
  spelarens matcher – inte implementerat (se avsnitt 6).
* **Kombos:** parlays byggs bara över olika matcher hos samma bolag (inga produkter av olika bolags bästa priser),
  under antagandet om oberoende mellan matcher. Bara data – inga notiser, ingen insats.

## 4. Utvärdering (ny: `propsbot/nba_eval.py`)

Bara bokförda prognoser (gjorda före matchen) – inget skenbart backtest med dagens information.
Avduplicering: en prestation = spelare × match × marknad (alternativa linjer och bolag räknas en gång).
Osäkerhet: block-bootstrap över speldagar (amerikansk tid), fast seed. Brier/log loss: modell och marknad på
**samma** spel. Kör: `python -m propsbot.nba_eval <lägesmapp>` (skriver `nba_utvardering.json/.md`); körs även
efter varje NBA-skanning, och status per marknad används av nästa skanning.

Läge 2026-11-11 (data-grenen, 10 speldagar, före rättningen av blandningen):

| Bokföring | Avgjorda | ROI flat | CLV pe legacy (95 %) | Brier modell / marknad (n) |
|---|---|---|---|---|
| LIVE | 14 | +15,3 % | +2,31 (+0,94…+4,09) | – |
| Spel (regler) | 229 | +4,9 % | +2,28 (+1,96…+2,62) | – |
| Skugga | 586 | +5,0 % | +1,29 (+1,10…+1,53) | – |
| Modelltest | 578 | +10,6 % | +1,19 (+0,95…+1,57) | 0,2416 / 0,2385 (80) |

Tolkning: **modellen slår inte marknaden** (Brier 0,2416 mot 0,2385 på 80 spel, skillnaden inte signifikant).
CLV är positiv men "legacy" – utan stängningstid. Status per marknad: points = shadow, övriga = insufficient_data.
Ingen marknad är validated. Positiv ROI på 10 dagar bevisar ingenting.

Status-kriterier (konventioner, inte garantier): insufficient_data < 30 unika avgjorda prestationer med både
modell och marknad; degraded = modellens Brier signifikant sämre än marknadens eller CLV signifikant negativ
(verifierad stängning går före legacy); validated = Brier signifikant bättre OCH CLV signifikant positiv;
annars shadow. **Degraded blockerar LIVE** för marknaden (`live_block_degraded`, standard på). Shadow och
insufficient_data påverkar inte LIVE-reglerna från 4/11 – de visas som osäkra.

## 5. Vad som inte går att rekonstruera

* Historiska indata (boxscores vid prognostillfället, skadelistan, oddsnoteringar per tid) sparas inte som
  snapshots. Ett walk-forward-backtest av råmodellen (träning → kalibrering → test) kan därför inte göras utan
  att läcka dagens information. Ersättning: framåtriktad shadow-utvärdering (ovan), från och med nu med
  modellversion och prognostid på varje rad.
* Modellens och marknadens sannolikheter finns på bokförda rader först från 2026-11-07 (80 avgjorda hittills).
* Stängningstid finns från 2026-11-11.

## 6. Kvarstående databehov och nästa steg

1. ~2–4 veckor till för status per marknad med meningsfull säkerhet (≥ 30 prestationer per marknad).
2. Spara indata-snapshots per prognos (spelarens matchlogg-hash, skadestatus, minuter) – krävs för riktig
   walk-forward-kalibrering och för att jämföra kandidatmodeller mot nuvarande version.
3. Parameterosäkerhet: bootstrap över spelarens senaste matcher -> intervall för P och EV; konservativ
   beslutssannolikhet (t.ex. nedre kvartil) jämförd mot punktprognos i shadow innan den får styra.
4. Push-modellering om heltalslinjer ska användas (P(vinst), P(push), P(förlust) och EV = p_vinst·(odds−1) − p_förlust).
5. Modellen ska inte få större vikt förrän Brier-skillnaden mot marknaden är signifikant negativ.

## 7. SportsGameOdds och Cloudflare

* SportsGameOdds kräver konto och API-nyckel (gratisnivån är begränsad). Inte integrerad – nyckeln måste skapas
  av ägaren och läggas som GitHub-hemlighet. Det är också en betald tjänst, vilket tidigare valts bort.
* Körningarna använder inga Claude-tokens: boten körs på GitHub Actions. En Cloudflare Worker kan inte köra
  Python-skanningen (~15 min); den kunde bara ersätta schemaläggningen, som redan fungerar.

## 8. Kommandon

```
python -m pytest -q
python -m pytest -q tests/test_nba_granskning.py
python -m propsbot.nba_eval <mapp med nba_*.json>
```

## 9. Tillägg 2026-11-14 (gren `modellforbattringar`)

Efter en jämförelse med en extern modellbeskrivning. Det som redan fanns (devig power/Shin per bolag, CLV,
¼ Kelly med tak, tak per match) är oförändrat.

1. **Graduering tål upprepad prövning** (`graduation.py`). "t ≥ 1 vid varje skanning" uppgraderar till slut en
   marknad utan CLV av slump. Nu en tidsoberoende gräns (Robbins normalblandning, α 0,10 delat på 2 marknader):
   t ≥ 3,7 vid 50 spel, 3,0 vid 500. Sides (redan uppgraderad, t 6,8) påverkas inte.
2. **Benjamini–Hochberg på status per marknad** (`nba_eval.py`). "validated" kräver dessutom att marknaden klarar
   BH (FDR 0,10) över alla prövade marknader; p = max av ensidiga bootstrap-p för Brier och CLV.
3. **Skuggfält på modelltestrader** (`nba_minutes.py`) – styr INTE LIVE, utvärderas under "Skuggmodeller":
   * `p_modell_min`: minuter som fördelning (spelarens egen spridning, Gauss–Hermite) med r krympt så att
     genomsnittlig varians är oförändrad, plus utklassningsrisk ur Pinnacles spread (hämtas i samma anrop).
   * `p_stack`: inlärd blandning σ(a + b_m·logit p_modell + b_k·logit p_marknad) per marknad, ridge mot
     "lita på marknaden" (400 obs), skattad på avgjorda rader och använd först nästa skanning (`nba_stack.json`).
     Med dagens 181 rader blir b_m ≈ 0,05–0,1, alltså nästan bara marknaden – som Brier-jämförelsen säger.
   Varför inte direkt i LIVE: modellkravet (modelledge ≥ 5 %) var det starkaste filtret i 4/11-analysen. Med en
   vikt nära 0 blir modelledgen ≈ marknadsedgen och kravet slutar filtrera. Det beslutet ska tas på data.
4. **Sides 1X2, devig-artefakt?** Kontrollerat på 420 avgjorda 1X2-rader (spel + skugga): edge hemma 2,8 %,
   borta 3,3 %, och utfall mot Pinnacles p ligger inom brus för alla sidor och oddsband. Ingen ändring.
   Råpriserna sparas inte, så Shin mot power kan inte räknas om i efterhand.
