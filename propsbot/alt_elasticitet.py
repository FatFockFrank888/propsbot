"""Experiment 25/11: nuvarande elasticiteter mot brorsens (ELASTICITY_ALT) på avgjorda fotbollsprops.

Läser bokforing_modell_v4.json och bokforing_skugga_v4.json (fält p_raw, p_raw_alt, p_marknad, utfall).
Brier = medelkvadratfel mot utfallet (lägre = bättre, 0,25 = singla slant). Jämförelsen görs på exakt samma spel.
Körs: python -m propsbot.alt_elasticitet [rotmapp]. Skriver bara ut, ändrar inget.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FILES = ("bokforing_modell_v4.json", "bokforing_skugga_v4.json")


def load(root: Path) -> list[dict]:
    out = []
    for f in FILES:
        try:
            out += json.loads((root / f).read_text(encoding="utf-8")).get("bets", [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return out


def brier(pairs: list[tuple[float, int]]) -> float:
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def report(bets: list[dict], min_n: int = 150) -> dict:
    rows = [b for b in bets if b.get("status") in ("vunnen", "förlorad") and b.get("p_raw") is not None
            and b.get("p_raw_alt") is not None and b.get("sida", "over") == "over"]
    res = {"n": len(rows), "enough": len(rows) >= min_n}
    if not rows:
        return res
    y = [1 if b["status"] == "vunnen" else 0 for b in rows]
    for name, key in (("nuvarande", "p_raw"), ("brorsens", "p_raw_alt")):
        res[name] = {"brier": round(brier([(b[key], yy) for b, yy in zip(rows, y)]), 4),
                     "snitt_p": round(sum(b[key] for b in rows) / len(rows), 3)}
    mk = [(b["p_marknad"], yy) for b, yy in zip(rows, y) if b.get("p_marknad") is not None]
    if mk:
        res["marknad"] = {"brier": round(brier(mk), 4), "n": len(mk)}
    res["traff"] = round(sum(y) / len(y), 3)
    return res


if __name__ == "__main__":
    r = report(load(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if not r.get("enough"):
        print(f"För få avgjorda ({r['n']} < 150) – dra inga slutsatser än.")
