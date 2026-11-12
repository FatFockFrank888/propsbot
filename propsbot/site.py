"""Den sammanslagna webbsidan (GitHub Pages): en sida, fotboll och NBA.

Fotboll och NBA skriver redan site/data.json och site/nba/data.json. Här skrivs alla parametrar
till site/parametrar.json och den gemensamma sidan web/index.html kopieras in. Gamla adressen nba/ skickas vidare.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .ledger import rensa_nan as _rensa_nan

WEB = Path(__file__).resolve().parent.parent / "web"

REDIRECT = """<!DOCTYPE html><html lang="sv"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=../#{sport}"><title>Propsbot</title></head>
<body><a href="../#{sport}">Propsbot – {name}</a></body></html>"""


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _summary(bets: list[dict]) -> dict:
    """Samma nycklar som fotbollens/NBA:s Ledger.summary() (andelar av bankrullen)."""
    done = [b for b in bets if b.get("status") in ("vunnen", "förlorad", "push")]
    st = sum(b.get("insats_pct") or 0 for b in done)
    res = sum(b.get("resultat_enheter") or 0 for b in done)
    per: dict[str, dict] = {}
    for b in done:
        x = per.setdefault(b.get("bolag") or "?", {"spel": 0, "insats": 0.0, "resultat": 0.0})
        x["spel"] += 1
        x["insats"] += b.get("insats_pct") or 0
        x["resultat"] += b.get("resultat_enheter") or 0
    now = time.time()
    clv = [(1 / b["stangning"] - 1 / b["odds"]) * 100 for b in bets
           if b.get("stangning") and b.get("odds") and b.get("avspark") and b["avspark"] < now]
    return {"antal": len(bets), "rattade": len(done), "oppna": sum(b.get("status") == "öppen" for b in bets),
            "vunna": sum(b.get("status") == "vunnen" for b in done), "insats_pct": st, "resultat_pct": res,
            "roi": res / st if st else None, "per_bolag": per,
            "clv_pp": sum(clv) / len(clv) if clv else None, "clv_antal": len(clv)}


def build_site(root: Path, settings_path: Path) -> None:
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    import csv
    from .params import all_params
    params = all_params(settings_path)
    (site / "parametrar.json").write_text(
        json.dumps(_rensa_nan(params), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    (site / "csv").mkdir(exist_ok=True)
    with open(site / "csv" / "parametrar.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Sport", "Parameter", "Värde", "Förklaring"])
        for sport, rows in params.items():
            w.writerows([sport, r["namn"], r["varde"], r["forklaring"]] for r in rows)
    shutil.copy(WEB / "index.html", site / "index.html")
    for f in ("apple-touch-icon.png", "icon-512.png", "manifest.json"):   # hemskärmsikon (iPhone/Android)
        if (WEB / f).exists():
            shutil.copy(WEB / f, site / f)
    for sport, name in (("nba", "NBA"),):
        (site / sport).mkdir(exist_ok=True)
        (site / sport / "index.html").write_text(REDIRECT.format(sport=sport, name=name), encoding="utf-8")
