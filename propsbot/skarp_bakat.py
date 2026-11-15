"""Bakåträkning av skarp stängnings-CLV ur datagrenens historik.

Varje körning sparar sitt läge i grenen "data", bl.a. historikfilerna med referensens
(Pinnacle/DK-konsensus) senaste sannolikhet per linje och tid. Historiken rensas efter två dygn,
men git har kvar varje version. Det här skriptet går igenom alla versioner och tar, för varje
bokfört spel, den sista noteringen FÖRE avspark = skarp stängning.

Körs för hand (behöver hela datagrenens historik):
    git fetch origin data
    python -m propsbot.skarp_bakat [ref=origin/data] [ut=propsbot/skarp_stangning_bakat.json]

Resultatet (linjenyckel -> [p, ts], alla linjer för spelare/marknader som bokförts) läses in av boten vid varje körning (apply_backfill) och
fylls i på spel som saknar skarp stängning eller har en äldre notering. Idempotent.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HIST_FILES = ("pinnacle_historik.json", "nba_historik.json")
LEDGERS = ("nba_bokforing_v2.json", "nba_skugga_v2.json", "nba_modelltest.json", "nba_live.json",
           "bokforing_v3.json", "bokforing_skugga_v4.json", "bokforing_modell_v4.json",
           "bokforing_kort_test.json", "bokforing_fouls_test.json")
BACKFILL = Path(__file__).with_name("skarp_stangning_bakat.json")


def _git(*a: str) -> str:
    return subprocess.run(["git", *a], check=True, capture_output=True, text=True).stdout


def _show_many(specs: list[str]) -> list[bytes | None]:
    """git cat-file --batch: innehållet för många <commit>:<fil> på en gång."""
    p = subprocess.run(["git", "cat-file", "--batch"], input="\n".join(specs).encode() + b"\n",
                       capture_output=True, check=True)
    out, i, res = p.stdout, 0, []
    for _ in specs:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if len(head) >= 2 and head[1] == b"missing":
            res.append(None)
            i = nl + 1
            continue
        size = int(head[2])
        res.append(out[nl + 1: nl + 1 + size])
        i = nl + 1 + size + 1
    return res


def build(ref: str = "origin/data") -> dict[str, list]:
    from .skarp_clv import line_key_bet
    # avspark per spelare/marknad (alla linjer och sidor behövs för flyttade linjer)
    kickoff: dict[str, float] = {}
    for f in LEDGERS:
        raw = _show_many([f"{ref}:{f}"])[0]
        for b in (json.loads(raw) if raw else []):
            if b.get("avspark") and b.get("match_id"):
                kickoff["|".join(line_key_bet(b).split("|")[:3])] = float(b["avspark"])
    commits = _git("rev-list", "--reverse", ref).split()
    best: dict[str, list] = {}
    for f in HIST_FILES:
        blobs = _show_many([f"{c}:{f}" for c in commits])
        for raw in blobs:
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for k, h in d.items():
                ko = kickoff.get("|".join(k.split("|")[:3]))
                if ko is None or len(h) < 4 or h[2] is None or h[3] >= ko:
                    continue
                if k not in best or h[3] > best[k][1]:
                    best[k] = [h[2], h[3]]
    return best


def apply_backfill(ledger, path: Path = BACKFILL) -> int:
    """Fyll i skarp stängning från bakåträkningen (bara där den är nyare än det som finns)."""
    try:
        bf = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    from .skarp_clv import apply_moved, update
    hist_like = {k: [None, None, v[0], v[1]] for k, v in bf.items()}
    n = update(ledger, hist_like, 0.0, None, source="bakåt")
    apply_moved(ledger, hist_like)
    return n


def main(argv: list[str]) -> None:
    ref = argv[0] if argv else "origin/data"
    out = Path(argv[1]) if len(argv) > 1 else BACKFILL
    best = build(ref)
    out.write_text(json.dumps(best, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"{len(best)} linjer med skarp stängning -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
