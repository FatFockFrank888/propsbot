"""Bokföring av spel: registrera, följ stängningsodds (CLV) och rätta efter matchen.

Varje spelbart ben bokförs första gången det dyker upp (en gång per match,
spelare, marknad, linje och bolag). Fram till avspark uppdateras senaste odds
hos samma bolag, så att stängningsoddset blir kvar -> CLV.
Efter matchen rättas spelet mot spelarstatistik (results.py).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .decision import kelly_stake
from .scan import ScanRow


def bet_key(r: ScanRow) -> str:
    c = r.row.decision.cand
    return f"{c.match_id}|{c.player_id}|{c.market}|{c.line}|{c.best.book}"


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.bets: list[dict] = []
        if path.exists():
            try:
                self.bets = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.bets = []
        self.by_key = {b["key"]: b for b in self.bets}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.bets, ensure_ascii=False, indent=0), encoding="utf-8")

    def record(self, rows: list[ScanRow], evd_by_id: dict[str, dict], predicate=None) -> list[dict]:
        """Bokför nya ben (standard: spelbara inom oddsramen). Returnerar de nya."""
        new = []
        for r in rows:
            d = r.row.decision
            ok = predicate(r) if predicate else (d.playable and d.show)
            if not ok:
                continue
            k = bet_key(r)
            if k in self.by_key:
                continue
            c = d.cand
            ev = evd_by_id.get(c.match_id, {})
            b = {
                "key": k, "id": len(self.bets) + 1, "bokford": time.time(),
                "match_id": c.match_id, "match": r.match, "hemma": ev.get("home_team"),
                "borta": ev.get("away_team"), "liga": ev.get("league", ""),
                "avspark": ev.get("commence_time"), "spelare": c.player_name,
                "spelare_id": c.player_id, "marknad": c.market, "linje": c.line,
                "bolag": c.best.book, "odds": c.best.odds, "sannolikhet": c.p,
                "ratt_odds": 1.0 / c.p, "edge": c.edge, "spela_fran": d.play_from,
                "insats_pct": d.stake or kelly_stake(c.p, c.best.odds, 0.25, 0.02),
                "stangning": c.best.odds, "status": "öppen", "stopp": "; ".join(d.reasons),
                "utfall": None, "resultat_enheter": None,
            }
            self.bets.append(b)
            self.by_key[k] = b
            new.append(b)
        return new

    def update_closing(self, rows: list[ScanRow], now: float) -> None:
        """Senaste odds före avspark hos samma bolag = stängningsodds."""
        latest = {}
        for r in rows:
            c = r.row.decision.cand
            latest[f"{c.match_id}|{c.player_id}|{c.market}|{c.line}|{c.best.book}"] = c.best.odds
        for b in self.bets:
            if b["status"] == "öppen" and b.get("avspark") and now < b["avspark"] and b["key"] in latest:
                b["stangning"] = latest[b["key"]]

    def settle(self, bet: dict, count: int | None, played: bool) -> None:
        if not played:
            bet.update(status="struken", utfall=None, resultat_enheter=0.0)
            return
        won = count is not None and count > bet["linje"]
        bet.update(status="vunnen" if won else "förlorad", utfall=count,
                   resultat_enheter=(bet["odds"] - 1.0) * bet["insats_pct"] if won
                   else -bet["insats_pct"])

    def summary(self) -> dict:
        settled = [b for b in self.bets if b["status"] in ("vunnen", "förlorad")]
        staked = sum(b["insats_pct"] for b in settled)
        profit = sum(b["resultat_enheter"] for b in settled)
        clv = [b["odds"] / b["stangning"] - 1 for b in self.bets if b.get("stangning")]
        # CLV i procentenheter: stängningens implicita sannolikhet minus vid spelet (positivt = bra)
        clv_pp = [(1 / b["stangning"] - 1 / b["odds"]) * 100 for b in self.bets
                  if b.get("stangning") and b.get("avspark") and b["avspark"] < time.time()]
        per_book: dict[str, dict] = {}
        for b in settled:
            s = per_book.setdefault(b["bolag"], {"spel": 0, "insats": 0.0, "resultat": 0.0})
            s["spel"] += 1
            s["insats"] += b["insats_pct"]
            s["resultat"] += b["resultat_enheter"]
        return {
            "antal": len(self.bets), "rattade": len(settled),
            "oppna": sum(b["status"] == "öppen" for b in self.bets),
            "vunna": sum(b["status"] == "vunnen" for b in settled),
            "insats_pct": staked, "resultat_pct": profit,
            "roi": profit / staked if staked else None,
            "clv_snitt": sum(clv) / len(clv) if clv else None,
            "clv_pp": sum(clv_pp) / len(clv_pp) if clv_pp else None,
            "clv_antal": len(clv_pp),
            "forvantat_pct": sum(b["edge"] * b["insats_pct"] for b in settled),
            "per_bolag": per_book,
        }
