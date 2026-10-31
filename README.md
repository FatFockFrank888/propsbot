# propsbot – player props för fotboll

Skott, skott på mål, mål och assist per spelare. Sannolikheterna gäller **givet
att spelaren spelar** (annars stryks spelet).

## Kedjan

```
startelva/minuter ─┐
Pinnacle 1X2+total ─┼─> lagvolym per skottyp (volymfaktor + matchup) ─> matchsimulator
motståndarprofil ──┘                                                     (10 000 matcher)
                                                                               │
Pinnacle props (tvåsidigt) ─┐                                          modellens p
Kambi-bolagen (en röst) ────┴─> marknadens p ──> blandning i log-odds ──> nivåkalibrering
                                                                               │
                                     bästa spelbara odds ──> edge / spela från / insats / tak
```

| Fil | Innehåll |
|---|---|
| `propsbot/config.py` | **Alla parametrar** (halveringstider, krympning, vikter, k = 200, edge, oddsgränser, insatser) |
| `propsbot/form.py` | Dagsform: viktade snitt i spelade minuter, krympning mot positionsprior, rollbyte, lag- och motståndarprofiler |
| `propsbot/volume.py` | Pinnacles väntade mål → lagets skott per typ. Matchup (lågt block → distans/nick, hög backlinje → kontring), domare, väder, tak ±18 % |
| `propsbot/simulator.py` | Minut-för-minut-simulering: byten, rött kort, ställningseffekter, straffordning, assist, målvakt. Kalibreras mot Pinnacles mål |
| `propsbot/market.py` | Marginalborttagning (power/Shin), Pinnacle → λ, Unibets ensidiga marginal m(odds), skattning av m mot Pinnacle, konsensus |
| `propsbot/kambi.py` | Hittar bolag med samma leverantör, Kambis huvudpris (median), eftersläpning per bolag, eftersläpande priser |
| `propsbot/blend.py` | Modellvikt (startelva, Pinnacle, oenighet, marknad), nivåkalibrering, klustrat standardfel per match |
| `propsbot/decision.py` | Edge ≥ 2 % (4 % mål/assist), odds ≥ 1,40, visas ≥ 1,60, spela från, ¼ Kelly, ett ben per spelare och familj, tak per match, stoppregler |
| `propsbot/store.py` | SQLite-logg: beräkningar, stängning, utfall → CLV och kalibrering |
| `propsbot/sources/` | Inläsning. `json_source.py` läser formatet i `examples/match.json` |

## Snabbstart på Windows

1. Packa upp zip-filen (högerklicka → Extrahera alla).
2. Dubbelklicka på **start.bat**. Den installerar det som behövs och börjar bevaka oddsen.
3. Installera appen **ntfy** på mobilen och prenumerera på kanalnamnet som visas överst i fönstret.
   Varje nytt spelbart ben ger en notis som plingar.

Källor (gratis, inga krediter): Kambis öppna flöde (Unibet, Paf, ATG, LeoVegas, Svenska Spel …)
och Pinnacles gästflöde som skarp referens. The Odds API är avstängt som standard
(`use_the_odds_api`). William Hill, onexbet och Pinnacle används bara som jämförelse,
aldrig som spelbolag (`excluded_books`).

Om något inte fungerar: innehållet i `diagnos\diagnos.txt` visar vilken källa som felar,
och råsvar sparas i `diagnos\` så att tolkningen kan rättas.

### Inställningar (`settings.json`)

| Nyckel | Betydelse |
|---|---|
| `sports` | Ligor (The Odds API-nycklar, t.ex. `soccer_epl`) |
| `hours_ahead` | Hur långt fram matcher hämtas |
| `prop_markets` | `player_shots_on_target`, `player_shots`, `player_goal_scorer_anytime`, `player_assists` |
| `regions` / `bookmakers` | Region (`eu`, `uk`) eller en lista med bolag (max 10 = en region i kostnad) |
| `playable_books` | Bolag ni kan spela hos. Tom = alla utom Pinnacle |
| `kambi_hint_prefixes` | Bolagsnamn som räknas som samma Kambi-grupp (gruppering sker även automatiskt) |
| `max_events_per_run` | Tak för antal matcher per körning (skyddar krediterna) |
| `bankroll` | Bankrulle i kronor, för insatskolumnen |

**Krediter:** varje match kostar (antal marknader × antal regioner). Fyra prop-marknader i en region = 4 krediter per match. Svar cachas i 4 minuter.

**Läge just nu:** utan spelardata jämförs bästa pris mot en marknadskonsensus från de *andra* bolagsgrupperna (Pinnacle väger tyngst, Kambi räknas som en röst). Utan Pinnacle eller tvåsidigt pris i konsensus höjs edgekravet med 3 procentenheter. När spelardata kopplas in tar simulatorn över.

## Kör (utvecklare)

```bash
pip install -r requirements.txt
python3 examples/make_example.py       # påhittad exempelmatch
python3 -m propsbot demo examples/match.json
python3 -m propsbot skanna          # kräver ODDS_API_KEY
python3 -m propsbot bolag
python3 -m pytest -q
```

## Det som saknas (kräver era konton/nycklar)

1. **The Odds API-kopplingen** (`sources/the_odds_api.py`) är skriven och testad mot API:ets dokumenterade format, men ännu inte mot riktiga anrop.
2. **Händelsedata-adapter** (skott med position/typ, xG, xA, minuter, startelvor) → `PlayerMatchRow`/`TeamMatchRow`.
3. **Avräkningsdefinitioner**: träna på samma källa som bolaget avräknar efter (blockerade skott, assist).
4. **Walk-forward-backtest** för att trimma parametrarna i `config.py` på log loss och CLV.
