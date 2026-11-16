"""Arkiv med skarpa stängningsodds (Pinnacle och DraftKings) för ALLA NBA-spelarlinjer (16/11).

Syfte: ett eget backtest-underlag. Historikfilerna rensas efter två dygn och skarp-CLV sparas bara på
bokförda spel. Här sparas varje linje som Pinnacle eller DraftKings har tvåsidigt, oavsett om vi spelade.

Under dagen (stang_pending.json):  senaste notering per (match, spelare, marknad, linje, bolag):
    marginalfri P(över) inom bolagets EGET över/under-par (proportionell avmarginalisering),
    råodds för över och under, tid för noteringen.
När matchen startat flyttas raderna till stangning_arkiv/nba-ÅÅÅÅ-MM.jsonl (en JSON per rad, bara tillägg)
med minuter mellan sista notering och avspark – en gammal notering märks, den presenteras inte som exakt
stängning. Interpolerade/flyttade Pinnacle-linjer arkiveras inte: bara noteringar bolaget faktiskt visade.
Arkivet skrivs aldrig om i efterhand.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

BOOKS = {"pinnacle": "pinnacle", "us_draftkings": "draftkings", "draftkings": "draftkings"}
PENDING = "stang_pending.json"
ARCHIVE_DIR = "stangning_arkiv"


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def observe(pending: dict, evd: dict, quotes: list, names: dict, now: float) -> int:
    """Uppdatera senaste noteringen för matchens Pinnacle/DK-linjer. Anropas före interpolering."""
    pairs: dict[tuple, dict] = {}
    for q in quotes:
        book = BOOKS.get(q.book)
        if not book or q.odds <= 1.0 or q.side not in ("over", "under"):
            continue
        pairs.setdefault((q.player_id, q.market, q.line, book), {})[q.side] = (q.odds, q.ts or now)
    m = pending.setdefault(evd["id"], {"match": f"{evd['home_team']} – {evd['away_team']}",
                                       "avspark": float(evd["commence_time"]), "rader": {}})
    n = 0
    for (pid, mk, ln, book), sides in pairs.items():
        if "over" not in sides or "under" not in sides:
            continue          # ensidiga noteringar arkiveras inte (marginalen kan inte mätas)
        (oo, to), (ou, tu) = sides["over"], sides["under"]
        io, iu = 1.0 / oo, 1.0 / ou
        m["rader"][f"{pid}|{mk}|{ln}|{book}"] = {
            "spelare_id": pid, "spelare": names.get(pid, pid), "marknad": mk, "linje": ln, "bolag": book,
            "p_over": round(io / (io + iu), 4), "marginal": round(io + iu - 1.0, 4),
            "odds_over": oo, "odds_under": ou, "ts": max(to, tu)}
        n += 1
    return n


def freeze(root: Path, pending: dict, now: float) -> int:
    """Matcher som startat: skriv raderna till månadsarkivet och ta bort dem ur pending."""
    out = 0
    adir = root / ARCHIVE_DIR
    for mid in [k for k, v in pending.items() if v.get("avspark", now) <= now]:
        m = pending.pop(mid)
        ko = m["avspark"]
        if not m["rader"]:
            continue
        adir.mkdir(exist_ok=True)
        f = adir / f"nba-{time.strftime('%Y-%m', time.gmtime(ko))}.jsonl"
        with f.open("a", encoding="utf-8") as fh:
            for r in m["rader"].values():
                fh.write(json.dumps({"match_id": mid, "match": m["match"], "avspark": ko, **r,
                                     "min_fore_start": round((ko - r["ts"]) / 60, 1)}, ensure_ascii=False) + "\n")
                out += 1
    return out


def run(root: Path, per: dict, now: float, diag) -> None:
    """Hela steget: notera alla matcher i skanningen och frys de som startat."""
    p = root / PENDING
    pending = _load(p)
    n = sum(observe(pending, evd, qs, names, now) for evd, qs, names in per.values())
    frozen = freeze(root, pending, now)
    # skräp: matcher som aldrig fick avspark-tid passerad men är äldre än två dygn
    for k in [k for k, v in pending.items() if now - v.get("avspark", now) > 2 * 86400]:
        pending.pop(k)
    p.write_text(json.dumps(pending), encoding="utf-8")
    diag.log(f"Stängningsarkiv (Pinnacle/DK): {n} tvåsidiga linjer noterade, {frozen} rader arkiverade")
