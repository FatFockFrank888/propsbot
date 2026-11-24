# Propsbot – arbetsregler

## Token- och kontextdisciplin
- Läs aldrig hela stora filer (`web/index.html` 146 kB, `propsbot/nba.py`, CSV/JSON). Grep först, läs sedan bara intervall (offset/limit).
- Delegera bred sökning/kartläggning till `scout` (Haiku, read-only). Be om <400 ord med fil:rad. Starta inte agenter för sådant du kan göra med en grep.
- Analysera CSV med små skript som skriver ut sammanfattningar, aldrig råa rader.
- Ingen omläsning av filer du just redigerat. Kör bara relevanta tester (`pytest tests/test_x.py -q`), hela sviten en gång före commit.

## Arbetsgång
1. Regel 2: före större ändringar, presentera Mål, Kritisk diagnos, Valt upplägg + förkastade alternativ, Risker, Byggplan och vänta på godkännande.
2. Var kritisk och oberoende. Försvara inte trösklar som data motsäger. Ändra inte trösklar på ROI ensamt (brus), använd CLV + ROI och minst ~150 avgjorda.
3. Inga falska notiser, inga skrivningar till skarpt Sheet/data-gren från tester. Telegram testas bara torrt.
4. `settings.json` är enda sanningen för parametrar. Uppdatera PARAMETRAR.md/README när värden ändras.
5. Commit/push bara på uppdragets gren. Ingen PR utan begäran.

## Fakta om repot
- Fotboll + NBA. NHL borttagen 12/11 (för hög p mot Kambi). Notiser: Telegram + ntfy (`propsbot/notify.py`).
- Tier-enhet: 1u = 1 % av kassan. Gamla källböcker (Live/Spel/Skugga) använde 0,2 %.
- Webb och CSV publiceras från grenen `data` (site/csv/*.csv); Sheet läser dem via IMPORTDATA (`sheet/propsbot_ark.gs`).
