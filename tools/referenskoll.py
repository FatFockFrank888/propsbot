"""Referenskoll: har NBA-spelen fortfarande Pinnacle/DraftKings som skarp referens vid stängning?

Read-only. Skriver bara en sammanfattning, ingen notis, inga skrivningar till Sheet/data-gren.

Läser tiers.json (spelen) och diagnos_nba/diagnos.txt (källornas status) från grenen `data`
(`git show <ref>:<fil>`) eller från lokala filer. Täckning per bokföringsdag (UTC):
  pin   andel spel med pin_stang_p
  dk    andel spel med dk_stang_p
  minst andel spel med minst en av dem
Flaggar en dag bara om den har minst --min-n spel och `minst` ligger under --floor, så att
halvfärdiga dagar inte ger falsklarm. Fälten loggas först från 14/11, äldre spel räknas inte.
FanDuel loggas inte separat (bara DK), så FD-bortfall syns inte här.

Exempel:
  python tools/referenskoll.py                       # läser origin/data
  python tools/referenskoll.py --ref FETCH_HEAD --days 10
  python tools/referenskoll.py --tiers tiers.json --diag diagnos.txt

Utgångskod 0 = ingen flagga, 1 = minst en flagga.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

FIRST_LOGGED_DAY = "2026-11-14"   # pin_stang_p/dk_stang_p loggas först från detta datum


def read_ref(ref: str, path: str) -> str:
    out = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git show {ref}:{path} misslyckades: {out.stderr.strip()[:200]}")
    return out.stdout


def coverage_by_day(bets: list[dict], sport: str = "nba") -> dict[str, dict]:
    days: dict[str, dict] = defaultdict(lambda: {"n": 0, "pin": 0, "dk": 0, "minst": 0})
    for b in bets:
        if b.get("sport") != sport:
            continue
        try:
            day = datetime.fromtimestamp(float(b.get("bokford") or 0), tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        if day < FIRST_LOGGED_DAY:
            continue
        pin = b.get("pin_stang_p") is not None
        dk = b.get("dk_stang_p") is not None
        d = days[day]
        d["n"] += 1
        d["pin"] += pin
        d["dk"] += dk
        d["minst"] += pin or dk
    return dict(days)


def source_status(diag_text: str) -> list[tuple[str, str, bool]]:
    """(källa, rad, ok). Läser statusrader ur NBA-diagnosen."""
    res: list[tuple[str, str, bool]] = []
    lines = diag_text.splitlines()

    def find(pat: str) -> str | None:
        return next((ln.strip() for ln in lines if re.search(pat, ln)), None)

    espn = find(r"DraftKings via ESPN")
    if espn is None:
        res.append(("DK via ESPN", "ingen rad i diagnosen", False))
    else:
        m = re.search(r"(\d+) matcher, (\d+) spelarodds", espn)
        ok = bool(m) and int(m.group(1)) > 0 and int(m.group(2)) > 0 and "FEL" not in espn
        res.append(("DK via ESPN", espn, ok))
    dkfd = find(r"^\s*DK/FD")
    if dkfd is None:
        res.append(("DK/FD (The Odds API)", "ingen rad i diagnosen", False))
    else:
        m = re.search(r"krediter kvar (\d+)", dkfd)
        ok = "FEL" not in dkfd and (not m or int(m.group(1)) > 0)
        res.append(("DK/FD (The Odds API)", dkfd, ok))
    sgo = find(r"SportsGameOdds")
    if sgo is not None:
        res.append(("SportsGameOdds", sgo, "FEL" not in sgo and "vilar" not in sgo))
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="origin/data", help="git-ref med data (standard origin/data)")
    ap.add_argument("--tiers", help="lokal tiers.json (annars git show <ref>:tiers.json)")
    ap.add_argument("--diag", help="lokal diagnos.txt (annars git show <ref>:diagnos_nba/diagnos.txt)")
    ap.add_argument("--days", type=int, default=7, help="antal senaste dagar att visa")
    ap.add_argument("--floor", type=float, default=0.70, help="lägsta andel med minst en av Pin/DK")
    ap.add_argument("--min-n", type=int, default=30, help="minsta antal spel för att en dag ska kunna flaggas")
    a = ap.parse_args()

    tiers_raw = open(a.tiers, encoding="utf-8").read() if a.tiers else read_ref(a.ref, "tiers.json")
    bets = json.loads(tiers_raw).get("bets", [])
    days = coverage_by_day(bets)
    flags: list[str] = []

    print(f"NBA tier-spel, referenstäckning vid stängning (golv {a.floor:.0%}, flagga först vid n ≥ {a.min_n})")
    print(f"{'dag':<11}{'n':>4}{'Pin':>7}{'DK':>7}{'minst en':>10}")
    for day in sorted(days)[-a.days:]:
        d = days[day]
        n = d["n"]
        mark = ""
        if n >= a.min_n and d["minst"] / n < a.floor:
            mark = "  <-- FLAGGA"
            flags.append(f"{day}: bara {d['minst'] / n:.0%} med Pin/DK (n={n})")
        elif n < a.min_n:
            mark = "  (för få spel för flagga)"
        print(f"{day:<11}{n:>4}{d['pin'] / n:>7.0%}{d['dk'] / n:>7.0%}{d['minst'] / n:>10.0%}{mark}")
    tot = sum(d["n"] for d in days.values())
    if tot:
        print(f"{'totalt':<11}{tot:>4}{sum(d['pin'] for d in days.values()) / tot:>7.0%}"
              f"{sum(d['dk'] for d in days.values()) / tot:>7.0%}{sum(d['minst'] for d in days.values()) / tot:>10.0%}")

    diag_raw = (open(a.diag, encoding="utf-8").read() if a.diag
                else read_ref(a.ref, "diagnos_nba/diagnos.txt"))
    print("\nKällstatus (senaste NBA-skanningen):")
    for name, line, ok in source_status(diag_raw):
        print(f"  [{'OK ' if ok else 'OBS'}] {name}: {line}")
        if not ok and name != "SportsGameOdds":
            flags.append(f"{name}: {line}")

    print("\nObs: FanDuel loggas inte separat (bara DK). Äldre spel än 14/11 saknar fälten och räknas inte.")
    if flags:
        print("\nFLAGGOR:")
        for f in flags:
            print("  -", f)
        return 1
    print("\nInga flaggor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
