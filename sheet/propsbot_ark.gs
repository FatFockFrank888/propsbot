/**
 * Propsbot – Google-arket.
 *
 * Installeras en gång: Tillägg → Apps Script → markera allt i filen och ersätt med hela den här filen → Spara →
 * välj byggArket och tryck Kör. Därefter finns menyn "Propsbot" i arket.
 *
 * Arkets uppbyggnad (allt uppdateras av sig självt via IMPORTDATA från botens webbsida):
 *   Översikt      – nyckeltalskort för det vi spelar (A + B Tier), tabeller per nivå och sport, resultatkurva
 *   📊 Statistik   – kurvor och uppdelningar: marknad, odds, edge, insats, sport, sida, bolag, vecka
 *   ⚽ Fotboll     – nyckeltal för sporten · öppna A/B-spel · senaste avgjorda · alla bokföringar · alla spel
 *   🏀 NBA         – samma
 *   Parametrar    – alla regler per sport (samma som webbsidans flik)
 *   _data_*       – dolda rådataflikar (IMPORTDATA). Rör inte.
 * Gamla flikar raderas inte: de döps om till "arkiv – <namn>" och döljs.
 */

const BASE = "https://fatfockfrank888.github.io/propsbot/csv/";
const SPORTS = [
  {key: "fotboll", name: "Fotboll", tab: "⚽ Fotboll"},
  {key: "nba", name: "NBA", tab: "🏀 NBA"},
];
const STATS_TAB = "📊 Statistik";
const RAW = {sammanfattning: "_data_sammanfattning", fotboll: "_data_fotboll", nba: "_data_nba",
             parametrar: "_data_parametrar", tier_nyckeltal: "_data_tier_nyckeltal", tier_stats: "_data_tier_stats",
             tier_kurva: "_data_tier_kurva", tier_vecka: "_data_tier_vecka"};
const OWN = ["Översikt", STATS_TAB, "Parametrar"].concat(SPORTS.map(s => s.tab)).concat(Object.values(RAW));

// ------------------------------------------------------------------ utseende
const FONT = "Roboto";
const INK = "#111827", MUTED = "#6b7280", LINE = "#e5e7eb", CARD = "#f8fafc", HEAD = "#f1f5f9", BANNER = "#0f172a";
const POS = "#15803d", NEG = "#b91c1c";
// Nivåernas färger: samma i tabeller (ljus ton) och diagram (full färg). A+B = det vi spelar (skiffer).
const TIER = {
  "A+B":    {color: "#334155", tint: "#e2e8f0"},
  "A Tier": {color: "#2a78d6", tint: "#dbeafe"},
  "B Tier": {color: "#eb6834", tint: "#ffedd5"},
  "C Tier": {color: "#1baf7a", tint: "#d1fae5"},
};
const NCOL = 18;   // innehållet ligger i kolumn B–S (A är marginal)
const F = {
  int: "0", u: '+0.0"u";-0.0"u";0.0"u"', u2: '+0.00"u";-0.00"u";0.00"u"', units: '0"u"',
  pct: '0.0" %"', spct: '+0.0" %";-0.0" %";0.0" %"', clv: '+0.00" %";-0.00" %";0.00" %"',
  frac: "0.0%", odds: "0.00", line: "0.0", dt: "d mmm hh:mm",
};
const TIER_NOTE = "A och B Tier spelas (notis) · C Tier är bara bokföring · flat 1–3u, 1u = 1 % av kassan";

function onOpen() {
  SpreadsheetApp.getUi().createMenu("Propsbot")
    .addItem("Uppdatera data nu", "uppdatera")
    .addItem("Bygg om arket", "byggArket")
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
    if (sh) retry_(() => sh.getRange("A1").setFormula(importFormula_(file)));
  });
  try { retry_(() => SpreadsheetApp.flush()); } catch (e) { /* Google räknar fortfarande om – datan kommer ändå */ }
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
    retry_(() => { sh.clear(); sh.getRange("A1").setFormula(importFormula_(file)); });
    sh.hideSheet();
  });
  // 3. Synliga flikar (varje flik byggs om från grunden, så ett nytt försök är ofarligt)
  retry_(() => buildOverview_(ss));
  retry_(() => buildStats_(ss));
  SPORTS.forEach(s => retry_(() => buildSport_(ss, s)));
  retry_(() => buildParams_(ss));
  // 4. Ordning
  const order = ["Översikt", STATS_TAB].concat(SPORTS.map(s => s.tab)).concat(["Parametrar"]);
  order.forEach((n, i) => { ss.setActiveSheet(ss.getSheetByName(n)); ss.moveActiveSheet(i + 1); });
  ss.setActiveSheet(ss.getSheetByName("Översikt"));
  try { SpreadsheetApp.flush(); } catch (e) { /* omräkningen fortsätter i bakgrunden */ }
  ss.toast("Arket är ombyggt. Gamla flikar ligger dolda som 'arkiv – …'.", "Propsbot", 8);
}

// ------------------------------------------------------------------ byggstenar
function getOrCreate_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function retry_(fn) {
  for (let i = 0; i < 4; i++) {
    try { return fn(); } catch (e) {
      if (i === 3) throw e;
      try { SpreadsheetApp.flush(); } catch (e2) { /* ignorera */ }
      Utilities.sleep(3000 * (i + 1));
    }
  }
}

/** Tömmer fliken helt och ger den grundutseendet: inga rutnät, ett typsnitt, marginal i kolumn A. */
function prep_(ss, name, fixedRows) {
  const sh = getOrCreate_(ss, name);
  sh.showSheet();
  sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns()).breakApart();
  sh.clear();
  sh.clearConditionalFormatRules();
  sh.getCharts().forEach(c => sh.removeChart(c));
  sh.getBandings().forEach(b => b.remove());
  sh.setFrozenRows(0);
  if (sh.getMaxColumns() < NCOL + 1) sh.insertColumnsAfter(sh.getMaxColumns(), NCOL + 1 - sh.getMaxColumns());
  if (fixedRows !== false) sh.setRowHeights(1, sh.getMaxRows(), 22);
  sh.setHiddenGridlines(true);
  const all = sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns());
  all.setFontFamily(FONT).setFontSize(10).setFontColor(INK).setVerticalAlignment("middle");
  sh.setColumnWidth(1, 20);
  sh.setColumnWidths(2, NCOL, 96);
  return sh;
}

function banner_(sh, title, subFormula) {
  sh.setRowHeight(1, 52);
  sh.getRange(1, 1, 1, NCOL + 1).setBackground(BANNER);
  sh.getRange(1, 2).setValue(title).setFontSize(20).setFontWeight("bold").setFontColor("#ffffff");
  sh.getRange(2, 1, 1, NCOL + 1).setBackground(BANNER);
  sh.setRowHeight(2, 26);
  const sub = sh.getRange(2, 2);
  if (subFormula.charAt(0) === "=") sub.setFormula(subFormula); else sub.setValue(subFormula);
  sub.setFontColor("#cbd5e1").setFontSize(10);
  return 4;
}

/** Rubrik med tunn linje under, valfri förklaring. Returnerar raden där innehållet börjar. */
function heading_(sh, row, title, sub) {
  sh.setRowHeight(row, 30);
  sh.getRange(row, 2).setValue(title).setFontSize(14).setFontWeight("bold");
  sh.getRange(row, 2, 1, NCOL).setBorder(null, null, true, null, null, null, LINE, SpreadsheetApp.BorderStyle.SOLID);
  if (!sub) return row + 1;
  sh.getRange(row + 1, 2).setValue(sub).setFontColor(MUTED).setFontSize(9);
  return row + 2;
}

/** Nyckeltalskort: liten etikett, stort värde, grå undertext. 2 kolumner brett, 3 rader högt. */
function card_(sh, row, col, label, valueFormula, fmt, subFormula, accent) {
  const box = sh.getRange(row, col, 3, 2).setBackground(CARD);
  box.setBorder(true, true, true, true, null, null, LINE, SpreadsheetApp.BorderStyle.SOLID);
  sh.getRange(row, col, 3, 1).setBorder(null, true, null, null, null, null, accent || TIER["A+B"].color,
    SpreadsheetApp.BorderStyle.SOLID_THICK);
  sh.getRange(row, col, 1, 2).merge().setValue(label.toUpperCase()).setFontSize(8).setFontWeight("bold")
    .setFontColor(MUTED);
  const v = sh.getRange(row + 1, col, 1, 2).merge();
  v.setFormula(valueFormula).setNumberFormat(fmt).setFontSize(20).setFontWeight("bold").setHorizontalAlignment("left");
  const s = sh.getRange(row + 2, col, 1, 2).merge().setFontSize(9).setFontColor(MUTED);
  if (subFormula && subFormula.charAt(0) === "=") s.setFormula(subFormula); else s.setValue(subFormula || "");
  return v;
}

/**
 * Tabell från en QUERY: rubrikrad i ljusgrått, randiga rader, format per kolumn.
 * formats: {kolumnindex (0 = första): talformat}. Returnerar raden efter tabellens reserverade yta.
 */
function table_(sh, row, formula, ncols, nrows, formats, opts) {
  opts = opts || {};
  const need = row + nrows + 2;
  if (sh.getMaxRows() < need) sh.insertRowsAfter(sh.getMaxRows(), need - sh.getMaxRows());
  sh.getRange(row, 2).setFormula(formula);
  const head = sh.getRange(row, 2, 1, ncols);
  head.setBackground(HEAD).setFontWeight("bold").setFontColor("#374151").setFontSize(9).setWrap(true)
    .setBorder(null, null, true, null, null, null, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID);
  sh.setRowHeight(row, 30);
  const body = sh.getRange(row + 1, 2, nrows, ncols);
  const band = body.applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  band.setFirstRowColor("#ffffff").setSecondRowColor(CARD);
  Object.entries(formats || {}).forEach(([i, f]) => sh.getRange(row + 1, 2 + Number(i), nrows, 1).setNumberFormat(f));
  (opts.results || []).forEach(i => resultColors_(sh.getRange(row + 1, 2 + i, nrows, 1)));
  (opts.tiers || []).forEach(i => tierColors_(sh.getRange(row + 1, 2 + i, nrows, 1)));
  (opts.status || []).forEach(i => statusColors_(sh.getRange(row + 1, 2 + i, nrows, 1)));
  return row + nrows + 2;
}

function addRules_(sh, rules) {
  sh.setConditionalFormatRules(sh.getConditionalFormatRules().concat(rules));
}

function resultColors_(range) {
  const sh = range.getSheet();
  addRules_(sh, [
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setFontColor(POS).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0).setFontColor(NEG).setRanges([range]).build()]);
}

function tierColors_(range) {
  addRules_(range.getSheet(), Object.entries(TIER).map(([name, t]) =>
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo(name).setBackground(t.tint).setBold(true)
      .setRanges([range]).build()));
}

function statusColors_(range) {
  addRules_(range.getSheet(), [
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("vunnen").setFontColor(POS).setBold(true)
      .setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("förlorad").setFontColor(NEG).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo("öppen").setFontColor("#2563eb").setRanges([range]).build()]);
}

function q_(tab, cols, sql, empty) {
  return "=IFERROR(QUERY('" + tab + "'!" + cols + ", \"" + sql + "\", 1), \"" + (empty || "(inget än)") + "\")";
}

/** Ett värde ur tier_nyckeltal (kolumn col) för sport och nivå. Tomt eller saknas = "–". */
function nk_(sport, lvl, col) {
  const t = "'" + RAW.tier_nyckeltal + "'!";
  return "IFERROR(LET(v, INDEX(FILTER(" + t + col + ":" + col + ", " + t + "A:A=\"" + sport + "\", " + t +
    "B:B=\"" + lvl + "\"), 1), IF(v=\"\", \"–\", v)), \"–\")";
}

/** Sex kort för A + B Tier (sport = "Alla", "Fotboll" eller "NBA"). Returnerar raden efter korten. */
function kpiCards_(sh, row, sport) {
  const c = TIER["A+B"].color;
  const cards = [
    ["Resultat", "=" + nk_(sport, "A+B", "H"), F.u, '="på "&TEXT(' + nk_(sport, "A+B", "G") + ', "0.0")&"u insats"'],
    ["ROI", "=" + nk_(sport, "A+B", "I"), F.spct, "avkastning på insatsen"],
    ["Träffprocent", "=" + nk_(sport, "A+B", "F"), F.pct, '=' + nk_(sport, "A+B", "E") + '&" vunna av "&' + nk_(sport, "A+B", "D")],
    ["Snitt-CLV", "=" + nk_(sport, "A+B", "J"), F.clv, "mot stängningsoddset"],
    ["Avgjorda spel", "=" + nk_(sport, "A+B", "D"), F.int, '=' + nk_(sport, "A+B", "K") + '&" öppna just nu"'],
    ["Senaste 7 dagarna", "=" + nk_(sport, "A+B", "L"), F.u, "resultat (avspark)"],
  ];
  sh.setRowHeight(row, 20); sh.setRowHeight(row + 1, 38); sh.setRowHeight(row + 2, 20);
  cards.forEach(([label, f, fmt, sub], i) => {
    const v = card_(sh, row, 2 + i * 3, label, f, fmt, sub, c);
    if (fmt !== F.int && fmt !== F.pct) resultColors_(v);
  });
  return row + 4;
}

function nkFormats_() {
  // tabellen: Nivå, Spel, Avgjorda, Vunna, Träff, Insats, Resultat, ROI, CLV, Öppna, 7 d
  return {1: F.int, 2: F.int, 3: F.int, 4: F.pct, 5: '0.0"u"', 6: F.u, 7: F.spct, 8: F.clv, 9: F.int, 10: F.u};
}

function lineChart_(sh, row, col, width, height) {
  const src = SpreadsheetApp.getActive().getSheetByName(RAW.tier_kurva);
  const chart = sh.newChart().setChartType(Charts.ChartType.LINE)
    .addRange(src.getRange("A1:E2000"))
    .setNumHeaders(1)
    .setHiddenDimensionStrategy(Charts.ChartHiddenDimensionStrategy.SHOW_BOTH)
    .setPosition(row, col, 0, 0)
    .setOption("title", "Ackumulerat resultat (u) per nivå")
    .setOption("titleTextStyle", {color: INK, fontSize: 13, bold: true})
    .setOption("fontName", FONT)
    .setOption("width", width).setOption("height", height)
    .setOption("colors", ["A+B", "A Tier", "B Tier", "C Tier"].map(n => TIER[n].color))
    .setOption("series", {0: {lineWidth: 3}, 1: {lineWidth: 2}, 2: {lineWidth: 2}, 3: {lineWidth: 2, lineDashStyle: [4, 3]}})
    .setOption("legend", {position: "top", textStyle: {color: MUTED}})
    .setOption("hAxis", {textStyle: {color: MUTED}, gridlines: {color: "transparent"}, format: "d MMM"})
    .setOption("vAxis", {textStyle: {color: MUTED}, gridlines: {color: "#eef0f3"}, baselineColor: "#9ca3af",
                         format: "+0.0;-0.0;0"})
    .setOption("chartArea", {left: 60, top: 50, width: "88%", height: "72%"})
    .setOption("backgroundColor", "#ffffff")
    .build();
  sh.insertChart(chart);
}

function weekChart_(sh, row, col, width, height) {
  const src = SpreadsheetApp.getActive().getSheetByName(RAW.tier_vecka);
  const chart = sh.newChart().setChartType(Charts.ChartType.COLUMN)
    .addRange(src.getRange("A1:D500"))
    .setNumHeaders(1)
    .setHiddenDimensionStrategy(Charts.ChartHiddenDimensionStrategy.SHOW_BOTH)
    .setPosition(row, col, 0, 0)
    .setOption("title", "Resultat (u) per vecka och nivå")
    .setOption("titleTextStyle", {color: INK, fontSize: 13, bold: true})
    .setOption("fontName", FONT)
    .setOption("width", width).setOption("height", height)
    .setOption("colors", ["A Tier", "B Tier", "C Tier"].map(n => TIER[n].color))
    .setOption("legend", {position: "top", textStyle: {color: MUTED}})
    .setOption("bar", {groupWidth: "70%"})
    .setOption("hAxis", {textStyle: {color: MUTED}})
    .setOption("vAxis", {textStyle: {color: MUTED}, gridlines: {color: "#eef0f3"}, baselineColor: "#9ca3af",
                         format: "+0.0;-0.0;0"})
    .setOption("chartArea", {left: 60, top: 50, width: "88%", height: "70%"})
    .setOption("backgroundColor", "#ffffff")
    .build();
  sh.insertChart(chart);
}

// ------------------------------------------------------------------ Översikt
function buildOverview_(ss) {
  const sh = prep_(ss, "Översikt");
  let row = banner_(sh, "Propsbot",
    '="Uppdaterad " & IFERROR(TEXT(INDEX(\'' + RAW.sammanfattning + '\'!L:L, 2), "d mmm hh:mm") & " (UTC)", "–") & "   ·   ' +
    TIER_NOTE + '"');
  // Villkor för SportScores gratis-API (resultat för mindre ligor): länken ska synas.
  sh.getRange(2, 14).setFormula('=HYPERLINK("https://sportscore.com/", "Powered by SportScore")')
    .setFontColor("#cbd5e1").setFontSize(9).setHorizontalAlignment("right");

  row = heading_(sh, row, "Det vi spelar – A + B Tier", "Alla sporter. Gröna siffror = vinst, röda = förlust.");
  row = kpiCards_(sh, row, "Alla");

  row = heading_(sh, row, "Per nivå", "A + B = summan av det vi spelar. C Tier visar om kraven för A och B är för skarpa.");
  row = table_(sh, row, q_(RAW.tier_nyckeltal, "A:L", "select B,C,D,E,F,G,H,I,J,K,L where A='Alla' " +
    "label B 'Nivå', G 'Insats (u)', L 'Senaste 7 d'"), 11, 4, nkFormats_(), {results: [6, 7, 8, 10], tiers: [0]});

  row = heading_(sh, row, "Per sport och nivå");
  row = table_(sh, row, q_(RAW.tier_nyckeltal, "A:L", "select A,B,C,D,E,F,G,H,I,J,K,L where A<>'Alla' " +
    "label B 'Nivå', G 'Insats (u)', L 'Senaste 7 d'"), 12, 8,
    {2: F.int, 3: F.int, 4: F.int, 5: F.pct, 6: '0.0"u"', 7: F.u, 8: F.spct, 9: F.clv, 10: F.int, 11: F.u},
    {results: [7, 8, 9, 11], tiers: [1]});

  row = heading_(sh, row, "Utveckling", "Mer statistik i fliken " + STATS_TAB + ".");
  lineChart_(sh, row, 2, 1100, 340);
  row += 17;

  row = heading_(sh, row, "Alla bokföringar (data)",
    "A/B/C Tier = nivåerna · Live = gamla LIVE-spelen · Spel = klarar reglerna · Skugga = stoppat av en regel · " +
    "Modelltest = egna modellen · testmarknader (fouls, hörnor). Övriga typer än Tier: 1u = 0,2 % av kassan.");
  table_(sh, row, q_(RAW.sammanfattning, "A:K", "select A,B,C,D,E,F,G,H,I,J,K"), 11, 40,
    {2: F.int, 3: F.int, 4: F.int, 5: F.pct, 6: '0.0"u"', 7: F.u, 8: F.spct, 9: F.clv, 10: F.int},
    {results: [7, 8, 9], tiers: [1]});
  sh.setColumnWidth(2, 110);
}

// ------------------------------------------------------------------ Statistik
function buildStats_(ss) {
  const sh = prep_(ss, STATS_TAB);
  let row = banner_(sh, "📊 Statistik", "A, B och C Tier uppdelat på allt som går att mäta   ·   " + TIER_NOTE);

  row = heading_(sh, row, "Resultat över tid");
  lineChart_(sh, row, 2, 1100, 340);
  row += 17;
  weekChart_(sh, row, 2, 1100, 300);
  row += 16;

  row = heading_(sh, row, "Uppdelningar",
    "Vänstra delen = A + B (det vi spelar). Till höger resultat och ROI för varje nivå var för sig. " +
    "ROI på få spel säger lite – titta på antal avgjorda.");
  const dims = [["Marknad", 20], ["Odds", 8], ["Edge", 6], ["Insats", 4], ["Sport", 3], ["Sida", 6], ["Bolag", 8],
                ["Vecka", 60]];
  const fm = {1: F.int, 2: F.int, 3: F.pct, 4: '0.0"u"', 5: F.u, 6: F.spct, 7: F.clv,
              8: F.int, 9: F.u, 10: F.spct, 11: F.int, 12: F.u, 13: F.spct, 14: F.int, 15: F.u, 16: F.spct};
  dims.forEach(([dim, n]) => {
    sh.getRange(row, 2).setValue(dim).setFontWeight("bold").setFontSize(11);
    // grupprubriker ovanför tabellen
    [["A + B Tier", 3, 7, "A+B"], ["A Tier", 10, 3, "A Tier"], ["B Tier", 13, 3, "B Tier"], ["C Tier", 16, 3, "C Tier"]]
      .forEach(([t, c, w, k]) => sh.getRange(row, c, 1, w).merge().setValue(t).setHorizontalAlignment("center")
        .setFontWeight("bold").setFontSize(9).setBackground(TIER[k].tint));
    row = table_(sh, row + 1, q_(RAW.tier_stats, "A:R",
      "select B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R where A='" + dim + "' limit " + n + " label B '" + dim + "', " +
      "C 'Spel', J 'Spel', K 'Res (u)', L 'ROI', M 'Spel', N 'Res (u)', O 'ROI', P 'Spel', Q 'Res (u)', R 'ROI'"),
      17, n, fm, {results: [5, 6, 7, 9, 10, 12, 13, 15, 16]});
  });
  sh.setColumnWidth(2, 150);
  [3, 4, 10, 13, 16].forEach(c => sh.setColumnWidth(c, 70));
}

// ------------------------------------------------------------------ Sportflikar
function buildSport_(ss, s) {
  const sh = prep_(ss, s.tab);
  const raw = RAW[s.key];
  let row = banner_(sh, s.tab, TIER_NOTE);

  row = heading_(sh, row, "Det vi spelar – A + B Tier");
  row = kpiCards_(sh, row, s.name);

  row = heading_(sh, row, "Per nivå");
  row = table_(sh, row, q_(RAW.tier_nyckeltal, "A:L", "select B,C,D,E,F,G,H,I,J,K,L where A='" + s.name + "' " +
    "label B 'Nivå', G 'Insats (u)', L 'Senaste 7 d'"), 11, 4, nkFormats_(), {results: [6, 7, 8, 10], tiers: [0]});

  row = heading_(sh, row, "Öppna A och B Tier-spel",
    "Spela till lägst oddset i notisen. Tomt = inget öppet A/B-spel just nu (du får en notis när något klarar kraven).");
  row = table_(sh, row, q_(raw, "A:S", "select C,D,E,F,G,H,I,J,K,O,P where (C='A Tier' or C='B Tier') " +
    "and Q='öppen' order by D limit 20 label C 'Tier', D 'Start', O 'Edge', P 'Insats'",
    "(inga öppna A/B Tier-spel just nu)"), 11, 20,
    {1: F.dt, 6: F.line, 8: F.odds, 9: F.frac, 10: F.units}, {tiers: [0]});

  row = heading_(sh, row, "Senaste avgjorda A, B och C Tier-spel", "De 30 senaste.");
  row = table_(sh, row, q_(raw, "A:S", "select C,D,E,F,G,H,I,K,L,M,P,Q,S where " +
    "(C='A Tier' or C='B Tier' or C='C Tier') and Q<>'öppen' order by D desc limit 30 " +
    "label C 'Tier', D 'Start', M 'CLV', P 'Insats', S 'Resultat'", "(inga avgjorda Tier-spel än)"), 13, 30,
    {1: F.dt, 6: F.line, 7: F.odds, 8: F.odds, 9: F.clv, 10: F.units, 12: F.u2},
    {tiers: [0], results: [9, 12], status: [11]});

  row = heading_(sh, row, "Alla bokföringar per typ (data)",
    "Övriga typer än Tier: 1u = 0,2 % av kassan. Live = gamla LIVE-spelen · Spel = klarar reglerna · Skugga = stoppat av en regel.");
  row = table_(sh, row, q_(RAW.sammanfattning, "A:K", "select B,C,D,E,F,G,H,I,J,K where A='" + s.name + "' limit 16"),
    10, 16, {1: F.int, 2: F.int, 3: F.int, 4: F.pct, 5: '0.0"u"', 6: F.u, 7: F.spct, 8: F.clv, 9: F.int},
    {results: [6, 7, 8], tiers: [0]});

  row = heading_(sh, row, "Alla spel (alla typer, senaste först)", "Filtrera med Data → Skapa ett filter.");
  table_(sh, row, q_(raw, "A:S", "select A,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S order by A desc"), 18, 3000,
    {0: F.dt, 2: F.dt, 7: F.line, 9: F.odds, 10: F.odds, 11: F.clv, 12: F.frac, 13: F.frac, 17: F.u2},
    {tiers: [1], results: [11, 17], status: [15]});

  sh.setColumnWidth(2, 80);
  sh.setColumnWidth(4, 200);
  sh.setColumnWidth(5, 160);
}

// ------------------------------------------------------------------ Parametrar
function buildParams_(ss) {
  const sh = prep_(ss, "Parametrar", false);   // radhöjd efter innehåll (långa förklaringar)
  let row = banner_(sh, "Parametrar", "Alla regler per sport – hämtas från de värden boten använder just nu.");
  ["Gemensamt"].concat(SPORTS.map(s => s.name)).forEach(name => {
    row = heading_(sh, row, name);
    row = table_(sh, row, "=IFERROR(QUERY('" + RAW.parametrar + "'!A:D, \"select B,C,D where A='" + name + "'\", 1), \"\")",
      3, 24, {});
  });
  sh.setColumnWidth(2, 240);
  sh.setColumnWidth(3, 240);
  sh.setColumnWidth(4, 640);
  sh.getRange("B:D").setWrap(true).setVerticalAlignment("top");
}
