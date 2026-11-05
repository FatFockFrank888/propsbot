"""Den sammanslagna webbsidan (GitHub Pages): en sida, tre sporter.

Fotboll och NBA skriver redan site/data.json och site/nba/data.json. Här läggs NHL till i
samma format (site/nhl/data.json), alla parametrar skrivs till site/parametrar.json och
den gemensamma sidan web/index.html kopieras in. Gamla adresser (nba/, nhl/) skickas vidare.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

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


def nhl_data(root: Path) -> dict:
    from nhl.bot_settings import BotSettings
    from nhl.ledger import LEDGERS
    from nhl.site_export import ledger_sv
    d = root / "nhl"
    s = BotSettings.load()
    from .ledger import mark_duplicates

    def counted(xs: list[dict]) -> list[dict]:   # ett spel per spelare och match i varje bokföring
        mark_duplicates(xs)
        return [b for b in xs if not b.get("dubblett")]
    led = {name: counted([ledger_sv(b, s.unit_pct) for b in _load(d / fname, [])]) for name, fname in LEDGERS.items()}
    tests = counted(_load(d / "nhl_test_marknader.json", []))
    radar = _load(d / "radar.json", {})
    by_new = lambda xs: sorted(xs, key=lambda b: -(b.get("bokford") or 0))
    return {
        "sport": "NHL", "live_enabled": s.live_on, "live": True,
        "uppdaterad_ts": radar.get("uppdaterad_ts") or time.time(),
        "uppdaterad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "radar": radar.get("radar", []),
        "bokforing": by_new(led["live"]), "sammanfattning": _summary(led["live"]),
        "spel_data": by_new(led["bokforing"]),
        "skuggspel": by_new(led["skugga"]), "skuggspel_sammanfattning": _summary(led["skugga"]),
        "modelltest": by_new(led["modelltest"]), "modelltest_sammanfattning": _summary(led["modelltest"]),
        "test_marknader": by_new(tests), "test_sammanfattning": _summary(tests),
    }


def build_site(root: Path, settings_path: Path) -> None:
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    try:
        (site / "nhl").mkdir(exist_ok=True)
        (site / "nhl" / "data.json").write_text(json.dumps(nhl_data(root), ensure_ascii=False), encoding="utf-8")
    except Exception as e:  # NHL-delen får aldrig stoppa sidan
        print(f"Webbsidan: NHL-data saknas ({type(e).__name__}: {e})")
    import csv
    from .params import all_params
    params = all_params(settings_path)
    (site / "parametrar.json").write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
    (site / "csv").mkdir(exist_ok=True)
    with open(site / "csv" / "parametrar.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Sport", "Parameter", "Värde", "Förklaring"])
        for sport, rows in params.items():
            w.writerows([sport, r["namn"], r["varde"], r["forklaring"]] for r in rows)
    shutil.copy(WEB / "index.html", site / "index.html")
    for sport, name in (("nba", "NBA"), ("nhl", "NHL")):
        (site / sport).mkdir(exist_ok=True)
        (site / sport / "index.html").write_text(REDIRECT.format(sport=sport, name=name), encoding="utf-8")
