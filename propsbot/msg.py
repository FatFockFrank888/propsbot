"""Läsbara spelnotiser (Telegram/ntfy). Ren formatering – inget nätverk, lätt att testa.

Format (24/11): tydlig rubrik, match + liga, avspark i svensk tid, spelval + linje + bolag + odds,
edge / sannolikhet / rättvist odds / förväntad CLV, insats i u (1u = 1 % av kassan), kort motivering och risk.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

STHLM = ZoneInfo("Europe/Stockholm")
DAG = ["mån", "tis", "ons", "tors", "fre", "lör", "sön"]


def sv(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}".replace(".", ",") + " %"


def kickoff_sv(ts: float) -> str:
    """'tis 25/11 01:00 (svensk tid)' ur unix-sekunder."""
    t = datetime.fromtimestamp(ts, timezone.utc).astimezone(STHLM)
    return f"{DAG[t.weekday()]} {t.day}/{t.month} {t:%H:%M} (svensk tid)"


def kickoff_from_utc_text(s: str) -> str:
    """'2026-11-24 17:30' (UTC) → svensk tid."""
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T")[:19])
    except ValueError:
        return f"{s} UTC"
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return kickoff_sv(t.timestamp())


def risks(b: dict) -> list[str]:
    out = []
    rum = b.get("rum")
    if rum is not None and rum < 0.01:
        out.append("snävt rum – oddset kan snart vara under 'spela från'")
    if b.get("forv_clv_pp") is not None and b["forv_clv_pp"] < 0:
        out.append(f"förväntad CLV negativ ({b['forv_clv_pp']:+.1f} pe)".replace(".", ","))
    if b.get("edge") is not None and b["edge"] >= 0.12:
        out.append("mycket hög edge – kontrollera linje/nyhet (hög edge har historiskt slagit stängningen sämre)")
    stopp = b.get("stopp") or ""
    for part in [p for p in stopp.split("; ") if p]:
        if part.startswith(("sharp money mot", "linjejusterat", "Pinnacles linje flyttad")):
            out.append(part)
    return out[:3]


def format_bet(b: dict, *, tier: str, sport: str, who: str, spel: str, liga: str = "", ko_text: str = "",
               units_txt: str = "", unit_pct: float | None = None, upg: str = "") -> tuple[str, str]:
    """Returnerar (rubrik, brödtext). b = spelets fält: odds, bolag, edge, sannolikhet, spela_fran, rum, forv_clv_pp."""
    sp = "NBA" if sport == "nba" else "FOTBOLL"
    title = f"{tier}-TIER · {sp} · {who}: {spel}" if tier else f"{sp} · {who}: {spel}"
    lines = [f"{b['match']}" + (f" · {liga}" if liga else ""),
             f"Avspark: {ko_text}" + (f" {upg}" if upg else ""),
             f"Spela: {spel} hos {b['bolag']} @ {sv(b['odds'])}"
             + (f" (spela från {sv(b['spela_fran'])}"
                + (f", rum {b['rum'] * 100:+.1f} %".replace(".", ",") if b.get("rum") is not None else "") + ")"
                if b.get("spela_fran") else "")]
    p = b.get("sannolikhet")
    stat = [f"Edge {pct(b['edge'])}"]
    if p:
        stat.append(f"modell {pct(p)} = rättvist odds {sv(1 / p)}")
    if b.get("forv_clv_pp") is not None:
        stat.append(f"förväntad CLV {b['forv_clv_pp']:+.1f} pe".replace(".", ","))
    lines.append(" · ".join(stat))
    ins = units_txt
    if unit_pct is not None and b.get("units"):
        ins += f" ({pct(b['units'] * unit_pct, 0)} av kassan)"
    if ins:
        lines.append(f"Insats: {ins}")
    why = []
    m = build_motiv(b)
    refs = [f"{n} {pct(v)}" for n, v in (("Pinnacle", m["pin_p"]), ("Smarkets", m["smk_p"])) if v]
    if m["prognos"] is not None and m["linje"] is not None:
        refs.append(f"prognos {sv(m['prognos'], 1)} mot linje {sv(m['linje'], 1)}")
    if refs:
        lines.append("Underlag: " + ", ".join(refs))
    if b.get("clv_signal") or "CLV-signal" in (b.get("stopp") or ""):
        why.append("Pinnacle har rört sig åt vårt håll")
    if "sharp money med oss" in (b.get("stopp") or ""):
        why.append("sharp money med oss")
    if why:
        lines.append("Varför: " + ", ".join(why))
    r = risks(b)
    if r:
        lines.append("⚠️ Risk: " + "; ".join(r))
    return title, "\n".join(lines)


def build_motiv(b: dict) -> dict:
    """Strukturerad, verifierbar motivering ur spelets egna fält (24/11). Maskinläsbar och visningsvänlig."""
    p, o = b.get("sannolikhet"), b.get("odds")
    m = {"p": p, "fair_odds": round(1 / p, 3) if p else None, "odds": o, "implicit_p": round(1 / o, 4) if o else None,
         "edge": b.get("edge"), "forv_clv_pp": b.get("forv_clv_pp"), "spela_fran": b.get("spela_fran"), "rum": b.get("rum"),
         "pin_p": b.get("pin_p"), "smk_p": b.get("smk_p"), "p_modell": b.get("p_modell"), "p_marknad": b.get("p_marknad"),
         "prognos": b.get("prognos"), "linje": b.get("linje"), "pin_grans": b.get("pin_grans"), "risk": risks(b)}
    if b.get("pin_grans") is not None and b["pin_grans"] < 1000:
        m["risk"] = (m["risk"] + [f"låg Pinnacle-gräns ({b['pin_grans']:.0f}) – svag referens"])[:4]
    if b.get("status") in ("struken", "push"):
        m["risk"] = m["risk"] + [f"spelet {b['status']}"]
    return m


def motiv_text(b: dict) -> tuple[str, str, str]:
    """(fair odds, motivering, risk) som korta texter för CSV/Sheet."""
    m = build_motiv(b)
    if not m["p"] or not m["odds"]:
        return "", "", "; ".join(m["risk"])
    parts = [f"sannolikhet {pct(m['p'])} mot oddsets {pct(m['implicit_p'])} → edge {pct(b['edge'])}"
             if b.get("edge") is not None else f"sannolikhet {pct(m['p'])}"]
    refs = [f"{n} {pct(v)}" for n, v in (("Pinnacle", m["pin_p"]), ("Smarkets", m["smk_p"]), ("modell", m["p_modell"]),
                                          ("marknad", m["p_marknad"])) if v]
    if refs:
        parts.append("källor: " + ", ".join(refs))
    if m["prognos"] is not None and m["linje"] is not None:
        parts.append(f"prognos {sv(m['prognos'], 1)} mot linje {sv(m['linje'], 1)}")
    if m["forv_clv_pp"] is not None:
        parts.append(f"förväntad CLV {m['forv_clv_pp']:+.1f} pe".replace(".", ","))
    return sv(m["fair_odds"]), "; ".join(parts), "; ".join(m["risk"])
