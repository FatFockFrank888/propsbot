"""Domarfaktor för fouls-modellen (datainsamling, 4/11).

Vem dömer (kommande matcher):
  * UEFA:s öppna match-API (CL, EL, ECL) – domaren publiceras när den är utsedd
  * football-data.co.uk fixtures.csv – bl.a. Premier League, Championship, Skottland
Hur sträng domaren är:
  * football-data.co.uk, innevarande säsong: lagfouls (HF+AF) och kort per match per domare
  * transfermarkt-datasets (karriär fram till juli 2026): kort per match per domare, alla tävlingar
Faktor = (domarens snitt / tävlingens snitt) ^ elasticitet, krympt mot 1 efter antal matcher,
begränsad till ±15 %. Fouls-snitt används när det finns, annars kortsnitt som ersättare.
Statistiken byggs om högst en gång per vecka och sparas i referee_stats.json.
"""
from __future__ import annotations

import calendar
import csv
import gzip
import io
import json
import time
import unicodedata
import urllib.request
from pathlib import Path

from .sources.http import UA
from .sources.props_text import same_match

TM = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
FD = "https://www.football-data.co.uk/"
FD_DIVS = ("E0", "E1", "SP1", "D1", "I1", "F1", "N1", "P1", "B1", "SC0", "T1", "G1")
UEFA_COMPS = {"1": "CL", "14": "EL", "2019": "ECL"}


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _season_code(now: float) -> str:
    t = time.gmtime(now)
    y = t.tm_year if t.tm_mon >= 7 else t.tm_year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def build_stats(now: float, diag=None) -> dict:
    """{'tm': {ref: [matcher, kort]}, 'fd': {ref: [matcher, fouls, kort]}, 'snitt': {...}}"""
    out = {"byggd": now, "tm": {}, "fd": {}, "snitt": {}}
    # transfermarkt: domare per match + kort per spelare och match
    try:
        games = list(csv.DictReader(io.StringIO(gzip.decompress(_get(TM + "games.csv.gz")).decode("utf-8", "replace"))))
        ref_of = {g["game_id"]: norm(g.get("referee", "")) for g in games if g.get("referee")}
        cards: dict[str, float] = {}
        raw = gzip.decompress(_get(TM + "appearances.csv.gz", 180)).decode("utf-8", "replace")
        for a in csv.DictReader(io.StringIO(raw)):
            gid = a.get("game_id")
            if gid in ref_of:
                cards[gid] = cards.get(gid, 0.0) + float(a.get("yellow_cards") or 0) + 2 * float(a.get("red_cards") or 0)
        tm: dict[str, list] = {}
        for gid, ref in ref_of.items():
            if gid in cards:
                x = tm.setdefault(ref, [0, 0.0])
                x[0] += 1
                x[1] += cards[gid]
        out["tm"] = tm
        n = sum(v[0] for v in tm.values())
        out["snitt"]["tm_kort"] = sum(v[1] for v in tm.values()) / n if n else 4.2
    except Exception as e:
        if diag:
            diag.log(f"Domare: transfermarkt FEL {type(e).__name__}: {str(e)[:100]}")
    # football-data: innevarande säsong, fouls och kort per domare
    fd: dict[str, list] = {}
    tot_m = tot_f = tot_c = 0.0
    season = _season_code(now)
    for div in FD_DIVS:
        try:
            txt = _get(f"{FD}mmz4281/{season}/{div}.csv", 30).decode("utf-8-sig", "replace")
        except Exception:
            continue
        for r in csv.DictReader(io.StringIO(txt)):
            try:
                f = float(r["HF"]) + float(r["AF"])
                c = float(r.get("HY") or 0) + float(r.get("AY") or 0) + 2 * (float(r.get("HR") or 0) + float(r.get("AR") or 0))
            except (KeyError, ValueError):
                continue
            tot_m += 1
            tot_f += f
            tot_c += c
            ref = norm(r.get("Referee", ""))
            if ref:
                x = fd.setdefault(ref, [0, 0.0, 0.0])
                x[0] += 1
                x[1] += f
                x[2] += c
    out["fd"] = fd
    out["snitt"]["fd_fouls"] = tot_f / tot_m if tot_m else 24.0
    out["snitt"]["fd_kort"] = tot_c / tot_m if tot_m else 4.2
    if diag:
        diag.log(f"Domare: statistik byggd – transfermarkt {len(out['tm'])} domare, "
                 f"football-data {len(fd)} domare ({int(tot_m)} matcher i år)")
    return out


def load_stats(root: Path, diag=None) -> dict:
    p = root / "referee_stats.json"
    now = time.time()
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
        if now - st.get("byggd", 0) < 7 * 86400:
            return st
    except (OSError, json.JSONDecodeError):
        pass
    st = build_stats(now, diag)
    if st["tm"] or st["fd"]:
        p.write_text(json.dumps(st), encoding="utf-8")
    return st


def upcoming(now: float, hours: float = 72, diag=None) -> list[tuple[str, str, float, str]]:
    """[(hemma, borta, avspark, domare)] från UEFA och football-data fixtures.csv."""
    out = []
    fmt = "%Y-%m-%d"
    for cid in UEFA_COMPS:
        url = (f"https://match.uefa.com/v5/matches?competitionId={cid}&fromDate={time.strftime(fmt, time.gmtime(now))}"
               f"&toDate={time.strftime(fmt, time.gmtime(now + hours * 3600))}&order=ASC&offset=0&limit=100")
        try:
            ms = json.loads(_get(url, 25))
        except Exception:
            continue
        for m in ms:
            refs = [r for r in (m.get("referees") or []) if (r.get("role") or "").upper() == "REFEREE"]
            if not refs:
                continue
            nm = ((refs[0].get("person") or {}).get("translations") or {}).get("name", {}).get("EN")
            ko = (m.get("kickOffTime") or {}).get("dateTime")
            try:
                ts = calendar.timegm(time.strptime(ko[:19], "%Y-%m-%dT%H:%M:%S"))
            except (TypeError, ValueError):
                continue
            out.append(((m.get("homeTeam") or {}).get("internationalName", ""),
                        (m.get("awayTeam") or {}).get("internationalName", ""), ts, nm or ""))
    try:
        txt = _get(FD + "fixtures.csv", 25).decode("utf-8-sig", "replace")
        for r in csv.DictReader(io.StringIO(txt)):
            if not r.get("Referee"):
                continue
            try:
                d = time.strptime(f"{r['Date']} {r.get('Time') or '15:00'}", "%d/%m/%Y %H:%M")
            except (KeyError, ValueError):
                continue
            # football-data anger brittisk lokal tid; ±1 h spelar ingen roll för matchningen
            out.append((r.get("HomeTeam", ""), r.get("AwayTeam", ""), calendar.timegm(d), r["Referee"]))
    except Exception:
        pass
    if diag:
        diag.log(f"Domare: {len(out)} kommande matcher med utsedd domare (UEFA + football-data)")
    return out


def _match_ref(stats_tbl: dict, name: str):
    k = norm(name)
    if k in stats_tbl:
        return stats_tbl[k]
    parts = k.split()
    if not parts:
        return None
    # "M. Oliver" / "Michael Oliver" – efternamn + initial
    last, ini = parts[-1], parts[0][0]
    hits = [v for kk, v in stats_tbl.items() if kk.split() and kk.split()[-1] == last and kk[0] == ini]
    return hits[0] if len(hits) == 1 else None


def factor(stats: dict, referee: str, prior: float = 10.0) -> tuple[float, str]:
    """Multiplikator för spelarnas väntade fouls, och en förklaring."""
    if not referee:
        return 1.0, ""
    fd = _match_ref(stats.get("fd", {}), referee)
    if fd and fd[0] >= 3:
        n, f = fd[0], fd[1]
        avg = stats["snitt"].get("fd_fouls", 24.0)
        ratio = (f + avg * prior) / (n + prior) / avg
        mult = ratio ** 0.8
        src = f"{referee}: {f / n:.1f} fouls/match i år ({n} m)"
    else:
        tm = _match_ref(stats.get("tm", {}), referee)
        if not tm or tm[0] < 5:
            return 1.0, f"{referee}: för lite data"
        n, c = tm[0], tm[1]
        avg = stats["snitt"].get("tm_kort", 4.2)
        ratio = (c + avg * prior) / (n + prior) / avg
        mult = ratio ** 0.4                     # kort är bara en ersättare för fouls
        src = f"{referee}: {c / n:.1f} kort/match ({n} m, karriär)"
    mult = min(1.15, max(0.85, mult))
    return mult, f"{src} → ×{mult:.2f}"


def referee_for(evd: dict, ups: list) -> str:
    for h, a, ts, ref in ups:
        if same_match(evd["home_team"], evd["away_team"], float(evd["commence_time"]), h, a, ts, max_dt_s=4 * 3600):
            return ref
    return ""
