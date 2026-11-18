# Arbetssätt för Claude i det här projektet

## Modellval: rätt modell till rätt uppgift

Vi använder **Haiku, Sonnet och Opus** i allt arbete och kör varje uppgift på den modell som passar bäst.
Det gäller både huvudsessionen och underagenter (välj modell med `model` när en agent startas).

| Modell | Används till | Exempel |
|---|---|---|
| **Haiku** | Snabba, enkla och mekaniska uppgifter | Söka i filer, läsa loggar, formatera data, byta namn, små textändringar, sammanfatta en fil |
| **Sonnet** | Vanligt utvecklingsarbete och analys | Ny funktion, buggrättning, tester, Apps Script, CSV-tolkning, dokumentation |
| **Opus** | Svåra och avgörande uppgifter | Arkitektur och planering, modell- och statistikdesign, djupa granskningar, felsökning som andra modeller fastnat på |

Tumregel: börja så billigt och snabbt som uppgiften tillåter, gå uppåt när den kräver mer omdöme.
Allt som rör pengar, modellens sannolikheter eller data vi inte får förlora granskas med Opus innan det går live.
