/**
 * Propsbot – Google-arket, en sektion per sport.
 *
 * Installeras en gång: Tillägg → Apps Script → klistra in hela filen → Spara → kör byggArket().
 * Därefter finns menyn "Propsbot" i arket.
 *
 * Arkets uppbyggnad (allt uppdateras av sig självt via IMPORTDATA från botens webbsida):
 *   Översikt      – nyckeltal per sport (Fotboll, NBA, NHL) och totalt för LIVE-spelen
 *   ⚽ Fotboll     – Nyckeltal per typ · Öppna spel · Alla spel
 *   🏀 NBA         – Nyckeltal per typ · Öppna LIVE-spel · Alla spel
 *   🏒 NHL         – Nyckeltal per typ · Öppna LIVE-spel · Alla spel
 *   Parametrar    – alla regler per sport (samma som webbsidans flik)
 *   _data_*       – dolda rådataflikar (IMPORTDATA). Rör inte.
 * Gamla flikar raderas inte: de döps om till "arkiv – <namn>" och döljs.
 */

const BASE = "https://fatfockfrank888.github.io/propsbot/csv/";
const SPORTS = [
  {key: "fotboll", name: "Fotboll", tab: "⚽ Fotboll", color: "#d1fae5", main: "Live",
   note: "LIVE = spelade spel (notis). Skott på mål."},
  {key: "nba", name: "NBA", tab: "🏀 NBA", color: "#fef3c7", main: "Live", note: "LIVE = spelade spel (notis)."},
  {key: "nhl", name: "NHL", tab: "🏒 NHL", color: "#dbeafe", main: "Live", note: "LIVE = spelade spel (notis). Skott på mål."},
];
const RAW = {sammanfattning: "_data_sammanfattning", fotboll: "_data_fotboll", nba: "_data_nba", nhl: "_data_nhl",
             parametrar: "_data_parametrar"};
const OWN = ["Översikt", "Parametrar"].concat(SPORTS.map(s => s.tab)).concat(Object.values(RAW));
const HEAD_BG = "#1f2937", HEAD_FG = "#ffffff";
// CSV-kolumner: A Bokförd, B Sport, C Typ, D Avspark, E Match, F Spelare, G Marknad, H Sida, I Linje, J Bolag,
// K Odds, L Stängning, M CLV (%), N Sannolikhet, O Edge, P Insats (u), Q Status, R Utfall, S Resultat (u)

function onOpen() {
  SpreadsheetApp.getUi().createMenu("Propsbot")
    .addItem("Uppdatera data nu", "uppdatera")
    .addItem("Bygg om arket (sektioner per sport)", "byggArket")
    .addToUi();
}

function importFormula_(name) {
  // ?v= tvingar Google att hämta om filen (annars cachas IMPORTDATA i upp till en timme)
  return '=IMPORTDATA("' + BASE + name + '.csv?v=' + Date.now() + '", ",", "en_US")';
}

function uppdatera() {
  const ss = SpreadsheetApp.getActive();
  Object.entries(RAW).forEach(([file, tab]) => {
    const sh = ss.getSheetByName(tab);
    if (sh) sh.getRange("A1").setFormula(importFormula_(file));
  });
  SpreadsheetApp.flush();
  ss.toast("Data hämtad från boten.", "Propsbot", 5);
}

function byggArket() {
  const ss = SpreadsheetApp.getActive();
  // 1. Gamla flikar arkiveras (döljs, raderas aldrig).
  ss.getSheets().forEach(sh => {
    const n = sh.getName();
    if (OWN.indexOf(n) === -1 && n.indexOf("arkiv – ") !== 0) {
      let nn = "arkiv – " + n, i = 2;
      while (ss.getSheetByName(nn)) nn = "arkiv – " + n + " (" + (i++) + ")";
      sh.setName(nn);
      if (ss.getSheets().filter(x => !x.isSheetHidden()).length > 1) sh.hideSheet();
    }
  });
  // 2. Rådata
  Object.entries(RAW).forEach(([file, tab]) => {
    const sh = getOrCreate_(ss, tab);
    sh.clear();
    sh.getRange("A1").setFormula(importFormula_(file));
    sh.hideSheet();
  });
  // 3. Synliga flikar
  buildOverview_(ss);
  SPORTS.forEach(s => buildSport_(ss, s));
  buildParams_(ss);
  // 4. Ordning
  const order = ["Översikt"].concat(SPORTS.map(s => s.tab)).concat(["Parametrar"]);
  order.forEach((n, i) => { ss.setActiveSheet(ss.getSheetByName(n)); ss.moveActiveSheet(i + 1); });
  ss.setActiveSheet(ss.getSheetByName("Översikt"));
  SpreadsheetApp.flush();
  ss.toast("Arket är ombyggt: en flik per sport. Gamla flikar ligger dolda som 'arkiv – …'.", "Propsbot", 8);
}

function getOrCreate_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function retry_(fn) {
  for (let i = 0; i < 4; i++) {
    try { return fn(); } catch (e) {
      if (i === 3) throw e;
      SpreadsheetApp.flush(); Utilities.sleep(3000 * (i + 1));
    }
  }
}

function reset_(sh) {
  retry_(() => sh.clear());
  sh.clearConditionalFormatRules();
  sh.getCharts().forEach(c => sh.removeChart(c));
  sh.setFrozenRows(0);
  sh.showSheet();
}

function section_(sh, row, title, sub, color) {
  const r = sh.getRange(row, 1, 1, 12);
  r.merge().setValue(title).setFontWeight("bold").setFontSize(13).setBackground(color || "#e5e7eb");
  if (sub) sh.getRange(row + 1, 1).setValue(sub).setFontColor("#6b7280").setFontStyle("italic");
  return row + (sub ? 2 : 1);
}

function headerRow_(sh, row, n) {
  sh.getRange(row, 1, 1, n).setFontWeight("bold").setBackground(HEAD_BG).setFontColor(HEAD_FG);
}

function q_(tab, sql) {
  return "=IFERROR(QUERY('" + tab + "'!A:S, \"" + sql + "\", 1), \"(inget än)\")";
}

// ------------------------------------------------------------------ Översikt
function buildOverview_(ss) {
  const sh = getOrCreate_(ss, "Översikt");
  reset_(sh);
  sh.getRange("A1").setValue("Propsbot – översikt").setFontSize(18).setFontWeight("bold");
  sh.getRange("A2").setFormula('="Senast uppdaterad (UTC): "&IFERROR(TEXT(INDEX(\'' + RAW.sammanfattning + '\'!L:L, 2), "yyyy-mm-dd hh:mm"), "–")')
    .setFontColor("#6b7280");
  sh.getRange("A3").setValue("1u = 0,2 % av bankrullen. CLV i procentenheter (positivt = vi slog stängningsoddset). " +
    "Webbsida: https://fatfockfrank888.github.io/propsbot/").setFontColor("#6b7280");
  let row = 5;
  const cols = ["Sport", "Typ", "Spel", "Avgjorda", "Vunna", "Träff %", "Insats (u)", "Resultat (u)", "ROI %", "Snitt-CLV %", "Öppna"];
  row = section_(sh, row, "Huvudsiffror per sport", "LIVE-spelen (de som skickas som notis) för varje sport.");
  sh.getRange(row, 1, 1, cols.length).setValues([cols]);
  headerRow_(sh, row, cols.length);
  SPORTS.forEach((s, i) => {
    const r = row + 1 + i;
    sh.getRange(r, 1).setFormula("=IFERROR(QUERY('" + RAW.sammanfattning + "'!A:K, \"select A,B,C,D,E,F,G,H,I,J,K where A='" +
      s.name + "' and B='" + s.main + "'\", 0), {\"" + s.name + "\",\"" + s.main + "\",0,0,0,\"\",0,0,\"\",\"\",0})");
    sh.getRange(r, 1, 1, cols.length).setBackground(s.color);
  });
  const tot = row + 1 + SPORTS.length;
  sh.getRange(tot, 1, 1, 2).setValues([["Totalt", "huvudrader"]]).setFontWeight("bold");
  ["C", "D", "E", "G", "H", "K"].forEach(c =>
    sh.getRange(c + tot).setFormula("=SUM(" + c + (row + 1) + ":" + c + (tot - 1) + ")").setFontWeight("bold"));
  sh.getRange("F" + tot).setFormula("=IF(D" + tot + ">0, ROUND(100*E" + tot + "/D" + tot + ", 1), \"\")");
  sh.getRange("I" + tot).setFormula("=IF(G" + tot + ">0, ROUND(100*H" + tot + "/G" + tot + ", 1), \"\")");
  row = tot + 2;

  row = section_(sh, row, "Alla bokföringar", "Live = spelat · Spel = klarar reglerna (data) · Skugga = stoppat av en regel · " +
    "Modelltest = egna modellen · Fouls-/Kort-/NHL-test = nya marknader (data) · Parlay = kombinationer (data)");
  sh.getRange(row, 1).setFormula("=IFERROR(QUERY('" + RAW.sammanfattning + "'!A:K, \"select A,B,C,D,E,F,G,H,I,J,K\", 1), \"(inget än)\")");
  headerRow_(sh, row, cols.length);
  sh.setFrozenRows(0);
  sh.setColumnWidths(1, 11, 105);
  sh.setColumnWidth(2, 110);
  sh.getRange("A5:K200").setNumberFormat("General");
  ["C", "D", "E", "K"].forEach(c => sh.getRange(c + "5:" + c + "200").setNumberFormat("0"));
  ["F", "G", "H", "I"].forEach(c => sh.getRange(c + "5:" + c + "200").setNumberFormat("0.0"));
  sh.getRange("J5:J200").setNumberFormat("0.00");
  addResultColors_(sh, "H6:H200");
  addResultColors_(sh, "J6:J200");
}

// ------------------------------------------------------------------ Sportflikar
function buildSport_(ss, s) {
  const sh = getOrCreate_(ss, s.tab);
  reset_(sh);
  const raw = RAW[s.key];
  sh.getRange("A1").setValue(s.tab).setFontSize(18).setFontWeight("bold");
  sh.getRange("A2").setValue(s.note).setFontColor("#6b7280");
  let row = 4;

  row = section_(sh, row, "1. Nyckeltal per typ", null, s.color);
  sh.getRange(row, 1).setFormula("=IFERROR(QUERY('" + RAW.sammanfattning + "'!A:K, \"select B,C,D,E,F,G,H,I,J,K where A='" +
    s.name + "'\", 1), \"(inget än)\")");
  headerRow_(sh, row, 10);
  addResultColors_(sh, "G" + (row + 1) + ":G" + (row + 9));
  addResultColors_(sh, "I" + (row + 1) + ":I" + (row + 9));
  row += 11;

  const openTitle = s.main === "Live" ? "2. Öppna LIVE-spel (det vi spelar)" : "2. Öppna regelspel (data)";
  row = section_(sh, row, openTitle, "Spela till lägst oddset i notisen. Sorterat på start.", s.color);
  sh.getRange(row, 1).setFormula(q_(raw, "select D,E,F,G,H,I,J,K,O,P where C='" + s.main + "' and Q='öppen' order by D limit 20 label D 'Start'"));
  headerRow_(sh, row, 10);
  row += 22;

  row = section_(sh, row, "3. Avgjorda " + (s.main === "Live" ? "LIVE-spel" : "regelspel"), "Senaste först.", s.color);
  sh.getRange(row, 1).setFormula(q_(raw, "select D,F,G,H,I,J,K,L,M,Q,R,S where C='" + s.main +
    "' and Q<>'öppen' order by D desc limit 300 label D 'Start'"));
  headerRow_(sh, row, 12);
  addResultColors_(sh, "L" + (row + 1) + ":L" + (row + 300));
  addResultColors_(sh, "I" + (row + 1) + ":I" + (row + 300));
  row += 302;

  row = section_(sh, row, "4. Alla spel (alla typer)", "Live, Spel, Skugga, Modelltest och testmarknader. Filtrera med Data → Skapa ett filter.", s.color);
  sh.getRange(row, 1).setFormula(q_(raw, "select A,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S order by A desc"));
  headerRow_(sh, row, 18);
  sh.setColumnWidths(1, 18, 95);
  sh.setColumnWidth(2, 150);
  sh.setColumnWidth(3, 170);
}

// ------------------------------------------------------------------ Parametrar
function buildParams_(ss) {
  const sh = getOrCreate_(ss, "Parametrar");
  reset_(sh);
  sh.getRange("A1").setValue("Parametrar – alla regler per sport").setFontSize(18).setFontWeight("bold");
  sh.getRange("A2").setValue("Hämtas från de värden boten använder just nu.").setFontColor("#6b7280");
  let row = 4;
  ["Gemensamt"].concat(SPORTS.map(s => s.name)).forEach((name, i) => {
    const s = SPORTS.find(x => x.name === name);
    row = section_(sh, row, name, null, s ? s.color : "#e5e7eb");
    sh.getRange(row, 1).setFormula("=IFERROR(QUERY('" + RAW.parametrar + "'!A:D, \"select B,C,D where A='" + name + "'\", 1), \"\")");
    headerRow_(sh, row, 3);
    row += 22;
  });
  sh.setColumnWidth(1, 260);
  sh.setColumnWidth(2, 260);
  sh.setColumnWidth(3, 620);
  sh.getRange("C:C").setWrap(true);
}

function addResultColors_(sh, a1) {
  const range = sh.getRange(a1);
  const rules = sh.getConditionalFormatRules();
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setFontColor("#15803d").setRanges([range]).build());
  rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0).setFontColor("#b91c1c").setRanges([range]).build());
  sh.setConditionalFormatRules(rules);
}
