"""Parlays (kombinationsspel) med 2–3 ben och egen bokföring.

Regler:
- Benen kommer från OLIKA matcher (ben i samma match hänger ihop och kan inte
  multipliceras som oberoende) och från SAMMA bolag (en kupong läggs hos ett bolag).
- Varje ben måste ha positiv edge av minst parlay_min_leg_edge och odds 1,40–6,00.
- Parlayns sannolikhet = produkten av benens sannolikheter, odds = produkten av odds.
- Insats = ¼ Kelly på parlayn, högst parlay_max_stake (lägre tak än singlar).
- Rättning: ett förlorat ben = förlorad parlay. Strukna ben tas bort och oddset
  räknas om på resterande ben.
"""
from __future__ import annotations

import itertools
import json
import math
import time
from pathlib import Path

from .decision import kelly_stake
from .ledger import Ledger, bet_key
from .scan import ScanRow


def leg_from_row(r: ScanRow, evd_by_id: dict) -> dict:
    c = r.row.decision.cand
    ev = evd_by_id.get(c.match_id, {})
    return {"key": bet_key(r), "match_id": c.match_id, "match": r.match,
            "hemma": ev.get("home_team"), "borta": ev.get("away_team"),
            "avspark": ev.get("commence_time"), "spelare": c.player_name,
            "spelare_id": c.player_id, "marknad": c.market, "linje": c.line, "sida": c.best.side,
            "bolag": c.best.book, "odds": c.best.odds, "sannolikhet": c.p, "edge": c.edge,
            "insats_pct": 0.0, "status": "öppen", "utfall": None, "resultat_enheter": None}


def suggest(rows: list[ScanRow], evd_by_id: dict, settings: dict) -> list[dict]:
    min_edge = settings.get("parlay_min_leg_edge", 0.02)
    max_legs = min(3, settings.get("parlay_max_legs", 3))
    top_k = settings.get("parlay_pool_per_book", 8)
    max_odds = settings.get("parlay_max_odds", 40.0)
    cap = settings.get("parlay_max_stake", 0.005)
    by_book: dict[str, dict[str, ScanRow]] = {}
    for r in rows:
        d = r.row.decision
        c = d.cand
        if not d.show or c.edge < min_edge:
            continue
        if any(x.startswith(("oddset har fallit", "redan ett spel")) for x in d.reasons):
            continue
        best_in_match = by_book.setdefault(c.best.book, {})
        cur = best_in_match.get(c.match_id)
        if cur is None or c.edge > cur.row.decision.cand.edge:
            best_in_match[c.match_id] = r          # bästa benet per match och bolag
    out = []
    for book, per_match in by_book.items():
        pool = sorted(per_match.values(), key=lambda r: -r.row.decision.cand.edge)[:top_k]
        for n in range(2, max_legs + 1):
            for combo in itertools.combinations(pool, n):
                p = math.prod(r.row.decision.cand.p for r in combo)
                odds = math.prod(r.row.decision.cand.best.odds for r in combo)
                if odds > max_odds:
                    continue
                ev = p * odds - 1
                stake = kelly_stake(p, odds, 0.25, cap)
                if ev <= 0 or stake <= 0:
                    continue
                legs = [leg_from_row(r, evd_by_id) for r in combo]
                out.append({"key": book + "||" + "||".join(sorted(l["key"] for l in legs)),
                            "bolag": book, "ben": legs, "antal_ben": n, "odds": odds,
                            "sannolikhet": p, "ev": ev, "insats_pct": stake})
    out.sort(key=lambda x: -x["ev"] * x["insats_pct"])   # mest väntad vinst först
    picked, used = [], set()
    for x in out:                                           # spridning: inget ben i >2 förslag
        keys = [l["key"] for l in x["ben"]]
        if sum(k in used for k in keys) > 1:
            continue
        picked.append(x)
        used.update(keys)
        if len(picked) >= settings.get("parlay_max_suggestions", 5):
            break
    return picked


class ParlayLedger:
    def __init__(self, path: Path):
        self.path = path
        self.items: list[dict] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        self.keys = {x["key"] for x in self.items}

    def record(self, suggestions: list[dict]) -> list[dict]:
        new = []
        open_legs = {l["key"] for x in self.items if x["status"] == "öppen" for l in x["ben"]}
        for s in suggestions:
            # Bokför bara parlays vars ben inte redan ligger i en öppen parlay,
            # så att samma ben inte bokförs om och om igen i nya kombinationer.
            if s["key"] in self.keys or any(l["key"] in open_legs for l in s["ben"]):
                continue
            open_legs.update(l["key"] for l in s["ben"])
            item = dict(s, id=len(self.items) + 1, bokford=time.time(), status="öppen",
                        resultat_enheter=None, slutodds=None)
            self.items.append(item)
            self.keys.add(s["key"])
            new.append(item)
        return new

    def legs_ledger(self) -> Ledger:
        """Alla öppna ben som en Ledger, så att samma rättning som för singlar kan användas."""
        lg = Ledger(self.path.with_suffix(".tmp_unused"))
        lg.bets = [l for x in self.items if x["status"] == "öppen" for l in x["ben"]
                   if l["status"] == "öppen"]
        for l in lg.bets:
            l["insats_pct"] = 1.0       # bara för att rättningen ska fungera
        return lg

    def update_status(self) -> None:
        for x in self.items:
            if x["status"] != "öppen":
                continue
            st = [l["status"] for l in x["ben"]]
            if "förlorad" in st:
                x.update(status="förlorad", resultat_enheter=-x["insats_pct"])
            elif "öppen" not in st:
                live = [l for l in x["ben"] if l["status"] == "vunnen"]
                if not live:
                    x.update(status="struken", resultat_enheter=0.0, slutodds=1.0)
                else:
                    o = math.prod(l["odds"] for l in live)
                    x.update(status="vunnen", slutodds=o, resultat_enheter=(o - 1) * x["insats_pct"])

    def save(self) -> None:
        self.path.write_text(json.dumps(self.items, ensure_ascii=False), encoding="utf-8")

    def summary(self) -> dict:
        done = [x for x in self.items if x["status"] in ("vunnen", "förlorad")]
        staked = sum(x["insats_pct"] for x in done)
        res = sum(x["resultat_enheter"] for x in done)
        return {"antal": len(self.items), "rattade": len(done),
                "oppna": sum(x["status"] == "öppen" for x in self.items),
                "vunna": sum(x["status"] == "vunnen" for x in done),
                "insats_pct": staked, "resultat_pct": res, "roi": res / staked if staked else None}
