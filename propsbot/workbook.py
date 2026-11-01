"""Excel-bokföring: alla spel från båda botarna i en arbetsbok med formler.

Flikar:
  Översikt          – nyckeltal (formler mot 'Alla spel')
  Alla spel         – en rad per spel (Excel-tabell med filter), CLV/resultat/intervall som formler
  Per marknad, Per bolag, Per sida, Per oddsintervall, Per sannolikhet, Per edge,
  Per typ, Per sport, Per CLV-signal, Per vecka – sammanställningar med COUNTIFS/SUMIFS
  Förklaring        – kolumner, units och CLV

1u = 0,2 % av bankrullen. CLV = stängningens implicita sannolikhet minus vår (procentenheter).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

UNIT = 0.002
FONT = "Arial"
MK = {"shots": "Skott", "shots_on_target": "Skott på mål", "goal": "Mål", "assist": "Assist",
      "points": "Poäng", "rebounds": "Returer", "assists": "Assist (NBA)", "threes": "Trepoängare",
      "steals": "Steals", "blocks": "Blocks", "pra": "PRA", "pr": "Poäng + returer", "ra": "Returer + assist"}

LEDGERS = [  # (fil, sport, typ)
    ("bokforing_v2.json", "Fotboll", "Live"), ("bokforing_skugga_v3.json", "Fotboll", "Skugga"),
    ("bokforing_modell_v3.json", "Fotboll", "Modelltest"), ("parlays_v2.json", "Fotboll", "Parlay"),
    ("nba_bokforing_v2.json", "NBA", "Live"), ("nba_skugga_v2.json", "NBA", "Skugga"),
    ("nba_modelltest.json", "NBA", "Modelltest"), ("nba_parlays_v2.json", "NBA", "Parlay"),
]

HEAD = ["Bokförd", "Sport", "Typ", "Avspark", "Match", "Spelare", "Marknad", "Sida", "Linje", "Bolag",
        "Odds", "Stängning", "CLV (pe)", "Sannolikhet", "Edge", "Insats (u)", "CLV-signal", "Status",
        "Utfall", "Resultat (u)", "Oddsintervall", "Sannolikhetsintervall", "Edgeintervall", "Vecka"]
COL = {h: get_column_letter(i + 1) for i, h in enumerate(HEAD)}


def _dt(ts):
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None) if ts else None


def _rows(root: Path) -> list[list]:
    out = []
    for fname, sport, typ in LEDGERS:
        f = root / fname
        if not f.exists():
            continue
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for b in items:
            if typ == "Parlay":
                legs = b.get("ben", [])
                spelare = " + ".join(f"{l['spelare']} {MK.get(l['marknad'], l['marknad']).lower()} "
                                     f"{'under' if l.get('sida') == 'under' else 'över'} {l['linje']:g}" for l in legs)
                avs = max((l.get("avspark") or 0) for l in legs) if legs else None
                row = [_dt(b.get("bokford")), sport, typ, _dt(avs), " | ".join(l["match"] for l in legs), spelare,
                       f"Parlay {b.get('antal_ben')} ben", "", None, b.get("bolag"), b.get("slutodds") or b.get("odds"),
                       None, None, b.get("sannolikhet"), b.get("ev"), (b.get("insats_pct") or 0) / UNIT, "nej",
                       b.get("status"), None]
            else:
                done = b.get("avspark") and b["avspark"] < datetime.now(timezone.utc).timestamp()
                row = [_dt(b.get("bokford")), sport, typ, _dt(b.get("avspark")), b.get("match"), b.get("spelare"),
                       MK.get(b.get("marknad"), b.get("marknad")),
                       "Under" if b.get("sida") == "under" else "Över", b.get("linje"), b.get("bolag"),
                       b.get("odds"), b.get("stangning") if done else None, None, b.get("sannolikhet"), b.get("edge"),
                       (b.get("insats_pct") or 0) / UNIT, "ja" if b.get("clv_signal") else "nej",
                       b.get("status"), b.get("utfall")]
            out.append(row)
    out.sort(key=lambda r: r[0] or datetime.min, reverse=True)
    return out


def build(root: Path, path: Path) -> int:
    rows = _rows(root)
    wb = Workbook()
    base = Font(name=FONT, size=10)
    bold = Font(name=FONT, size=10, bold=True)
    head_font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F2937")
    thin = Border(bottom=Side(style="thin", color="D1D5DB"))
    green = Font(name=FONT, size=10, color="15803D")
    red = Font(name=FONT, size=10, color="B91C1C")

    # ------------------------------------------------------------ spelblad
    def write_sheet(ws, rows, table_name):
        ws.append(HEAD)
        n = max(len(rows), 1)
        last = n + 1
        for i, r in enumerate(rows, start=2):
            c = COL
            ws.append(r + [None] * (len(HEAD) - len(r)))
            ws[f"{c['CLV (pe)']}{i}"] = f'=IF({c["Stängning"]}{i}="","",(1/{c["Stängning"]}{i}-1/{c["Odds"]}{i})*100)'
            ws[f"{c['Resultat (u)']}{i}"] = (
                f'=IF({c["Status"]}{i}="vunnen",({c["Odds"]}{i}-1)*{c["Insats (u)"]}{i},'
                f'IF({c["Status"]}{i}="förlorad",-{c["Insats (u)"]}{i},IF({c["Status"]}{i}="struken",0,"")))')
            ws[f"{c['Oddsintervall']}{i}"] = (
                f'=LOOKUP({c["Odds"]}{i},{{1,1.6,2,2.5,3,4,6}},'
                f'{{"1,00–1,59","1,60–1,99","2,00–2,49","2,50–2,99","3,00–3,99","4,00–5,99","6,00+"}})')
            ws[f"{c['Sannolikhetsintervall']}{i}"] = (
                f'=LOOKUP({c["Sannolikhet"]}{i}*100,{{0,30,40,50,60,70}},'
                f'{{"under 30 %","30–39 %","40–49 %","50–59 %","60–69 %","70 %+"}})')
            ws[f"{c['Edgeintervall']}{i}"] = (
                f'=LOOKUP({c["Edge"]}{i}*100,{{-100,0,2,4,6,10}},'
                f'{{"under 0 %","0–1,9 %","2–3,9 %","4–5,9 %","6–9,9 %","10 %+"}})')
            ws[f"{c['Vecka']}{i}"] = f'=YEAR({c["Bokförd"]}{i})&" v"&TEXT(WEEKNUM({c["Bokförd"]}{i},21),"00")'
        if not rows:
            ws.append(["(inga spel bokförda än)"])
        fmt = {"Bokförd": "yyyy-mm-dd hh:mm", "Avspark": "yyyy-mm-dd hh:mm", "Odds": "0.00", "Stängning": "0.00",
               "CLV (pe)": '+0.00;-0.00;0.00', "Sannolikhet": "0.0%", "Edge": "0.0%", "Insats (u)": '0.0"u"',
               "Resultat (u)": '+0.00"u";-0.00"u";0.00"u"', "Linje": "0.0"}
        widths = {"Bokförd": 16, "Avspark": 16, "Match": 34, "Spelare": 34, "Marknad": 16, "Bolag": 12,
                  "Status": 10, "Oddsintervall": 13, "Sannolikhetsintervall": 15, "Edgeintervall": 12, "Vecka": 10}
        for h, col in COL.items():
            ws.column_dimensions[col].width = widths.get(h, 11)
            for cell in ws[col][1:last]:
                cell.font = base
                if h in fmt:
                    cell.number_format = fmt[h]
        for cell in ws[1]:
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "A2"
        if rows:
            tab = Table(displayName=table_name, ref=f"A1:{get_column_letter(len(HEAD))}{last}")
            tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
            ws.add_table(tab)
        for h in ("CLV (pe)", "Resultat (u)"):
            rng = f"{COL[h]}2:{COL[h]}{last}"
            ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], font=green))
            ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], font=red))
        return last

    def kpi_box(ws, last):
        """Nyckeltal till höger om tabellen, med formler mot bladets egna kolumner."""
        def r(h):
            return f"${COL[h]}$2:${COL[h]}${last}"
        box = [
            ("Spel", f"=COUNTA({r('Status')})", "0"),
            ("Rättade", f'=COUNTIF({r("Status")},"vunnen")+COUNTIF({r("Status")},"förlorad")', "0"),
            ("Öppna", f'=COUNTIF({r("Status")},"öppen")', "0"),
            ("Träff", f'=IF(AA3=0,"",COUNTIF({r("Status")},"vunnen")/AA3)', "0.0%"),
            ("Insats rättade (u)", f'=SUMIFS({r("Insats (u)")},{r("Status")},"vunnen")+SUMIFS({r("Insats (u)")},{r("Status")},"förlorad")', '0.0"u"'),
            ("Resultat (u)", f"=SUM({r('Resultat (u)')})", '+0.00"u";-0.00"u";0.00"u"'),
            ("ROI", '=IF(AA6=0,"",AA7/AA6)', "0.0%"),
            ("Snitt-CLV (pe)", f'=IFERROR(AVERAGE({r("CLV (pe)")}),"")', '+0.00;-0.00;0.00'),
            ("Slog stängningen", f'=IFERROR(COUNTIF({r("CLV (pe)")},">0")/COUNT({r("CLV (pe)")}),"")', "0.0%"),
        ]
        ws["Z1"], ws["AA1"] = "Nyckeltal", ""
        ws["Z1"].font, ws["Z1"].fill = head_font, head_fill
        ws["AA1"].fill = head_fill
        for i, (k, f, nfm) in enumerate(box, start=2):
            ws[f"Z{i}"], ws[f"AA{i}"] = k, f
            ws[f"Z{i}"].font, ws[f"AA{i}"].font = base, bold
            ws[f"AA{i}"].number_format = nfm
        ws.column_dimensions["Z"].width = 20
        ws.column_dimensions["AA"].width = 12

    ws = wb.active
    ws.title = "Alla spel"
    last = write_sheet(ws, rows, "AllaSpel")
    kpi_box(ws, last)
    for title, tname, pick in (
            ("NBA", "NBA", lambda r: r[1] == "NBA" and r[2] != "Parlay"),
            ("Fotboll", "Fotboll", lambda r: r[1] == "Fotboll" and r[2] != "Parlay"),
            ("Parlays", "Parlays", lambda r: r[2] == "Parlay")):
        sub = [r for r in rows if pick(r)]
        w = wb.create_sheet(title)
        kpi_box(w, write_sheet(w, sub, tname))

    def R(h):  # absolut område i 'Alla spel'
        return f"'Alla spel'!${COL[h]}$2:${COL[h]}${last}"

    # ------------------------------------------------------------ sammanställningar
    def group_sheet(title: str, field: str, values: list[str]):
        g = wb.create_sheet(title)
        cols = ["Grupp", "Spel", "Rättade", "Vunna", "Träff", "Insats (u)", "Resultat (u)", "ROI",
                "Snitt-CLV (pe)", "Slog stängningen", "Snitt edge"]
        g.append(cols)
        for j, v in enumerate(values, start=2):
            k = f"$A{j}"
            g.append([v])
            g[f"B{j}"] = f"=COUNTIFS({R(field)},{k})"
            g[f"C{j}"] = f'=COUNTIFS({R(field)},{k},{R("Status")},"vunnen")+COUNTIFS({R(field)},{k},{R("Status")},"förlorad")'
            g[f"D{j}"] = f'=COUNTIFS({R(field)},{k},{R("Status")},"vunnen")'
            g[f"E{j}"] = f'=IF(C{j}=0,"",D{j}/C{j})'
            g[f"F{j}"] = (f'=SUMIFS({R("Insats (u)")},{R(field)},{k},{R("Status")},"vunnen")'
                          f'+SUMIFS({R("Insats (u)")},{R(field)},{k},{R("Status")},"förlorad")')
            g[f"G{j}"] = f"=SUMIFS({R('Resultat (u)')},{R(field)},{k})"
            g[f"H{j}"] = f'=IF(F{j}=0,"",G{j}/F{j})'
            g[f"I{j}"] = f'=IFERROR(AVERAGEIFS({R("CLV (pe)")},{R(field)},{k}),"")'
            g[f"J{j}"] = (f'=IFERROR(COUNTIFS({R(field)},{k},{R("CLV (pe)")},">0")/'
                          f'COUNTIFS({R(field)},{k},{R("CLV (pe)")},">-1000"),"")')
            g[f"K{j}"] = f'=IFERROR(AVERAGEIFS({R("Edge")},{R(field)},{k}),"")'
        end = len(values) + 1
        tot = end + 1
        g[f"A{tot}"] = "Totalt"
        for col in "BCDFG":
            g[f"{col}{tot}"] = f"=SUM({col}2:{col}{end})"
        g[f"E{tot}"] = f'=IF(C{tot}=0,"",D{tot}/C{tot})'
        g[f"H{tot}"] = f'=IF(F{tot}=0,"",G{tot}/F{tot})'
        g[f"I{tot}"] = f'=IFERROR(AVERAGE({R("CLV (pe)")}),"")'
        g[f"J{tot}"] = f'=IFERROR(COUNTIF({R("CLV (pe)")},">0")/COUNT({R("CLV (pe)")}),"")'
        g[f"K{tot}"] = f'=IFERROR(AVERAGE({R("Edge")}),"")'
        nf = {"E": "0.0%", "F": '0.0"u"', "G": '+0.00"u";-0.00"u";0.00"u"', "H": "0.0%",
              "I": '+0.00;-0.00;0.00', "J": "0.0%", "K": "0.0%"}
        for row in g.iter_rows(min_row=2, max_row=tot):
            for cell in row:
                cell.font = bold if cell.row == tot else base
                cell.border = thin
                if cell.column_letter in nf:
                    cell.number_format = nf[cell.column_letter]
        for cell in g[1]:
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
        g.column_dimensions["A"].width = 26
        for col in "BCDEFGHIJK":
            g.column_dimensions[col].width = 13
        g.freeze_panes = "B2"
        for col in "GI":
            rng = f"{col}2:{col}{tot}"
            g.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], font=green))
            g.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], font=red))
        g[f"A{tot + 2}"] = ("Rättade = vunna + förlorade (strukna och öppna räknas inte). "
                            "Slog stängningen = andel spel med CLV > 0. CLV-krav: snitt ≥ 1,0 pe.")
        g[f"A{tot + 2}"].font = Font(name=FONT, size=9, italic=True, color="6B7280")

    def uniq(idx, order=None):
        vals = sorted({r[idx] for r in rows if r[idx] not in (None, "")}, key=str)
        if order:
            vals = [v for v in order if v in vals] + [v for v in vals if v not in order]
        return vals or ["–"]

    odds_b = ["1,00–1,59", "1,60–1,99", "2,00–2,49", "2,50–2,99", "3,00–3,99", "4,00–5,99", "6,00+"]
    prob_b = ["under 30 %", "30–39 %", "40–49 %", "50–59 %", "60–69 %", "70 %+"]
    edge_b = ["under 0 %", "0–1,9 %", "2–3,9 %", "4–5,9 %", "6–9,9 %", "10 %+"]
    weeks = sorted({f"{r[0].isocalendar()[0]} v{r[0].isocalendar()[1]:02d}" for r in rows if r[0]}) or ["–"]
    group_sheet("Per marknad", "Marknad", uniq(HEAD.index("Marknad")))
    group_sheet("Per bolag", "Bolag", uniq(HEAD.index("Bolag")))
    group_sheet("Per sida", "Sida", ["Över", "Under"])
    group_sheet("Per oddsintervall", "Oddsintervall", odds_b)
    group_sheet("Per sannolikhet", "Sannolikhetsintervall", prob_b)
    group_sheet("Per edge", "Edgeintervall", edge_b)
    group_sheet("Per typ", "Typ", ["Live", "Skugga", "Modelltest", "Parlay"])
    group_sheet("Per sport", "Sport", ["Fotboll", "NBA"])
    group_sheet("Per CLV-signal", "CLV-signal", ["ja", "nej"])
    group_sheet("Per vecka", "Vecka", weeks)

    # ------------------------------------------------------------ Översikt
    o = wb.create_sheet("Översikt", 0)
    o["A1"] = "propsbot – bokföring"
    o["A1"].font = Font(name=FONT, size=16, bold=True)
    o["A2"] = f"Uppdaterad {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · 1u = 0,2 % av bankrullen"
    o["A2"].font = Font(name=FONT, size=9, color="6B7280")
    kpis = [
        ("Bokförda spel", f"=COUNTA({R('Status')})", "0"),
        ("Varav live", f'=COUNTIFS({R("Typ")},"Live")', "0"),
        ("Rättade (vunna + förlorade)", f'=COUNTIF({R("Status")},"vunnen")+COUNTIF({R("Status")},"förlorad")', "0"),
        ("Öppna", f'=COUNTIF({R("Status")},"öppen")', "0"),
        ("Träffprocent", '=IF(B6=0,"",COUNTIF(' + R("Status") + ',"vunnen")/B6)', "0.0%"),
        ("Insats rättade (u)", f'=SUMIFS({R("Insats (u)")},{R("Status")},"vunnen")+SUMIFS({R("Insats (u)")},{R("Status")},"förlorad")', '0.0"u"'),
        ("Resultat (u)", f"=SUM({R('Resultat (u)')})", '+0.00"u";-0.00"u";0.00"u"'),
        ("ROI", '=IF(B9=0,"",B10/B9)', "0.0%"),
        ("Snitt-CLV (pe) – krav ≥ 1,0", f'=IFERROR(AVERAGE({R("CLV (pe)")}),"")', '+0.00;-0.00;0.00'),
        ("Slog stängningen", f'=IFERROR(COUNTIF({R("CLV (pe)")},">0")/COUNT({R("CLV (pe)")}),"")', "0.0%"),
        ("Spel med CLV-mätning", f"=COUNT({R('CLV (pe)')})", "0"),
        ("Snitt edge vid spel", f'=IFERROR(AVERAGE({R("Edge")}),"")', "0.0%"),
    ]
    for i, (k, f, nfmt) in enumerate(kpis, start=4):
        o[f"A{i}"], o[f"B{i}"] = k, f
        o[f"A{i}"].font = base
        o[f"B{i}"].font = bold
        o[f"B{i}"].number_format = nfmt
        o[f"A{i}"].border = o[f"B{i}"].border = thin
    o.column_dimensions["A"].width = 34
    o.column_dimensions["B"].width = 16
    o["A18"] = "Live = spel som skickats som notis. Skugga = stoppade av reglerna. Modelltest = modellens val (ingen notis)."
    o["A19"] = "Filtrera i fliken 'Alla spel' (pilarna i rubrikraden). Övriga flikar sammanställer per grupp."
    for c in ("A18", "A19"):
        o[c].font = Font(name=FONT, size=9, italic=True, color="6B7280")

    # ------------------------------------------------------------ Förklaring
    e = wb.create_sheet("Förklaring")
    expl = [
        ("Kolumn", "Betydelse"),
        ("Typ", "Live = notifierat spel. Skugga = minst 2 % edge men stoppat av en regel. Modelltest = spelarmodellens val. Parlay = kombinationsspel."),
        ("Odds", "Bästa pris hos våra spelbolag när spelet bokfördes."),
        ("Stängning", "Senaste pris hos samma bolag före avspark (visas efter avspark)."),
        ("CLV (pe)", "Stängningens implicita sannolikhet minus vår, i procentenheter. Positivt = vi fick bättre pris än stängningen."),
        ("Sannolikhet / Edge", "Bottens rättvisa sannolikhet (Pinnacle-baserad) och edge = sannolikhet × odds − 1."),
        ("Insats (u)", "Units 1–10. 1u = 0,2 % av bankrullen, 10u = taket 2 %. ¼ Kelly efter EV."),
        ("Resultat (u)", "Vunnen: (odds − 1) × insats. Förlorad: −insats. Struken: 0."),
        ("CLV-signal", "ja = släppt från 1 % edge eftersom Pinnacle rört sig åt vårt håll."),
        ("Krav", "Snitt-CLV ≥ 1,0 pe över många spel visar att boten slår marknaden. ROI stabiliseras först efter flera hundra spel."),
    ]
    for r_ in expl:
        e.append(list(r_))
    for row in e.iter_rows():
        for cell in row:
            cell.font = bold if cell.row == 1 else base
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    e.column_dimensions["A"].width = 20
    e.column_dimensions["B"].width = 100

    wb.calculation.fullCalcOnLoad = True
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return len(rows)
