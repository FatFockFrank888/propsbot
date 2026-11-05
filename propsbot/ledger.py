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


def side_suffix(side: str | None) -> str:
    """Över saknar suffix (bakåtkompatibelt med äldre nycklar), under får '|under'."""
    return "|under" if side == "under" else ""


def bet_key(r: ScanRow) -> str:
    c = r.row.decision.cand
    return f"{c.match_id}|{c.player_id}|{c.market}|{c.line}|{c.best.book}{side_suffix(c.best.side)}"


def player_key(b: dict) -> tuple:
    return (b.get("match_id"), b.get("spelare_id") or b.get("spelare"))


def mark_duplicates(bets: list[dict]) -> int:
    """Ett spel per spelare och match i varje bokföring: det först bokförda räknas,
    senare rader på samma spelare (andra linjer/marknader/sidor) markeras "dubblett" och
    räknas inte i statistiken. Raderna sparas kvar. Returnerar antal nya markeringar."""
    seen: set = set()
    n = 0
    for b in sorted(bets, key=lambda x: (x.get("bokford") or 0, x.get("id") or 0)):
        k = player_key(b)
        if k[0] is None or k[1] is None:
            continue
        if k in seen:
            if not b.get("dubblett"):
                b["dubblett"] = True
                n += 1
        else:
            seen.add(k)
            b.pop("dubblett", None)
    return n


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
        mark_duplicates(self.bets)

    @property
    def counted(self) -> list[dict]:
        """Raderna som räknas (utan dubbletter på samma spelare och match)."""
        return [b for b in self.bets if not b.get("dubblett")]

    def save(self) -> None:
        self.path.write_text(json.dumps(self.bets, ensure_ascii=False, indent=0), encoding="utf-8")

    def record(self, rows: list[ScanRow], evd_by_id: dict[str, dict], predicate=None,
               one_per_player: bool = True) -> list[dict]:
        """Bokför nya ben (standard: spelbara inom oddsramen). Returnerar de nya.
        one_per_player: högst ett ben per spelare och match i bokföringen (störst edge
        i körningen vinner; finns spelaren redan bokförd läggs inget nytt till)."""
        new = []
        cands = []
        for r in rows:
            d = r.row.decision
            ok = predicate(r) if predicate else (d.playable and d.show)
            if ok:
                cands.append(r)
        if one_per_player:
            taken = {player_key(b) for b in self.bets}
            best: dict = {}
            for r in cands:
                c = r.row.decision.cand
                pk = (c.match_id, c.player_id)
                if bet_key(r) in self.by_key or pk in taken:
                    continue
                if pk not in best or c.edge > best[pk].row.decision.cand.edge:
                    best[pk] = r
            keep = {id(x) for x in best.values()}
            cands = [r for r in cands if id(r) in keep]
        for r in cands:
            d = r.row.decision
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
                "sida": c.best.side,
                "bolag": c.best.book, "odds": c.best.odds, "sannolikhet": c.p,
                "ratt_odds": 1.0 / c.p, "edge": c.edge, "spela_fran": d.play_from,
                "insats_pct": d.stake or kelly_stake(c.p, c.best.odds, 0.25, 0.02),
                "stangning": c.best.odds, "status": "öppen", "stopp": "; ".join(d.reasons),
                "clv_signal": any("CLV-signal" in x for x in d.reasons),
                "forv_clv_pp": getattr(r, "clv_pp", None),
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
            latest[bet_key(r)] = r.row.decision.cand.best.odds
        for b in self.bets:
            if b["status"] == "öppen" and b.get("avspark") and now < b["avspark"] and b["key"] in latest:
                b["stangning"] = latest[b["key"]]

    def settle(self, bet: dict, count: int | None, played: bool) -> None:
        if not played:
            bet.update(status="struken", utfall=None, resultat_enheter=0.0)
            return
        if bet.get("sida") == "under":
            won = count is not None and count < bet["linje"]
        else:
            won = count is not None and count > bet["linje"]
        bet.update(status="vunnen" if won else "förlorad", utfall=count,
                   resultat_enheter=(bet["odds"] - 1.0) * bet["insats_pct"] if won
                   else -bet["insats_pct"])

    def summary(self) -> dict:
        bets = self.counted
        settled = [b for b in bets if b["status"] in ("vunnen", "förlorad")]
        staked = sum(b["insats_pct"] for b in settled)
        profit = sum(b["resultat_enheter"] for b in settled)
        clv = [b["odds"] / b["stangning"] - 1 for b in bets if b.get("stangning")]
        # CLV i procentenheter: stängningens implicita sannolikhet minus vid spelet (positivt = bra)
        clv_pp = [(1 / b["stangning"] - 1 / b["odds"]) * 100 for b in bets
                  if b.get("stangning") and b.get("avspark") and b["avspark"] < time.time()]
        per_book: dict[str, dict] = {}
        for b in settled:
            s = per_book.setdefault(b["bolag"], {"spel": 0, "insats": 0.0, "resultat": 0.0})
            s["spel"] += 1
            s["insats"] += b["insats_pct"]
            s["resultat"] += b["resultat_enheter"]
        return {
            "antal": len(bets), "rattade": len(settled), "dubbletter": len(self.bets) - len(bets),
            "oppna": sum(b["status"] == "öppen" for b in bets),
            "vunna": sum(b["status"] == "vunnen" for b in settled),
            "insats_pct": staked, "resultat_pct": profit,
            "roi": profit / staked if staked else None,
            "clv_snitt": sum(clv) / len(clv) if clv else None,
            "clv_pp": sum(clv_pp) / len(clv_pp) if clv_pp else None,
            "clv_antal": len(clv_pp),
            "forvantat_pct": sum(b["edge"] * b["insats_pct"] for b in settled),
            "per_bolag": per_book,
        }
