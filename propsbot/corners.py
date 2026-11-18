"""Hörnmodell (18/11) – körs i bakgrunden och samlar data. Inga spel, ingen notis, inte i A/B/C Tier.

Varför egen modell: Pinnacle saknar hörnor och Smarkets har nästan ingen likviditet, så hörnspelen hade
ingen referens (3 spel totalt). Unibet/Kambi har däremot gott om hörnlinjer.

Underlag: football-data.co.uk (gratis CSV, HC/AC = hörnor hemma/borta per match) för innevarande och
förra säsongen i 17 ligor. Innevarande säsong hämtas högst var 12:e timme, förra en gång (hornor_<säsong>.json i läget).

Modell per liga:
  * lagets hörnor FÖR och EMOT som kvot mot ligasnittet (hemma- och bortamatcher var för sig normerade),
    viktade med halveringstid corners_half_life_days (120 d) och krympta mot 1,0 med corners_shrink_k
    (6 matcher) – lite data = nära ligasnittet.
  * väntade hörnor: hemma = snitt_hemma × FÖR_hemmalag × EMOT_bortalag, borta = snitt_borta × FÖR_borta × EMOT_hemma.
  * fördelning: negativ binomial per lag (spridning skattad per liga, hörnor sprider sig mer än Poisson),
    totalen = faltningen av de två.
Marknader: hörnor totalt, lagens hörnor och hörnhandikapp (Kambis 3-vägs = tvåvägs halvlinjer, sides.py).

Bokföring: bokforing_hornor_test.json – ett spel per match (störst edge) med edge ≥ corners_min_edge mot
modellen och odds inom corners_odds. p_modell och p_marknad (Kambi utan marginal där båda sidor finns)
sparas för kalibrering (Brier modell mot marknad). Stängning = Unibets senaste odds före start.
Rättning: ESPN:s matchprotokoll, med football-data.co.uk som reserv.
"""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

LEAGUES = ("E0", "E1", "E2", "SP1", "SP2", "D1", "D2", "I1", "I2", "F1", "F2", "N1", "P1", "B1", "SC0", "T1", "G1")
URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
CORNER_KEYS = ("corners", "corners_home", "corners_away", "cah")
MAXN = 40


def season_codes(now: float) -> list[str]:
    d = datetime.fromtimestamp(now, timezone.utc)
    y = d.year if d.month >= 7 else d.year - 1
    return [f"{y % 100:02d}{(y + 1) % 100:02d}", f"{(y - 1) % 100:02d}{y % 100:02d}"]


def _fetch(url: str) -> str | None:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "propsbot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8-sig", errors="replace")
    except Exception:  # noqa: BLE001 – källan får aldrig stoppa skanningen; sparat underlag används
        return None


def parse_csv(txt: str, code: str) -> list[dict]:
    out = []
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            hc, ac = int(float(row["HC"])), int(float(row["AC"]))
            dt = datetime.strptime(row["Date"], "%d/%m/%Y" if len(row["Date"]) > 8 else "%d/%m/%y")
        except (KeyError, TypeError, ValueError):
            continue
        x = {"liga": code, "ts": dt.replace(tzinfo=timezone.utc).timestamp(), "hemma": row.get("HomeTeam", ""),
             "borta": row.get("AwayTeam", ""), "hc": hc, "ac": ac, "sup": None, "o25": None}
        try:   # marknadens styrka (snittodds utan marginal): favoriten tar fler hörnor
            ph, pd, pa = (1 / float(row[k]) for k in ("AvgH", "AvgD", "AvgA"))
            po, pu = 1 / float(row["Avg>2.5"]), 1 / float(row["Avg<2.5"])
            x["sup"], x["o25"] = (ph - pa) / (ph + pd + pa), po / (po + pu)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pass
        out.append(x)
    return out


def load_history(state_dir: Path, now: float, ttl_s: float = 12 * 3600, leagues=LEAGUES, log=print) -> list[dict]:
    """Hörnor per match, en kompakt fil per säsong i det sparade läget (hornor_<säsong>.json).
    Innevarande säsong hämtas högst var 12:e timme, förra säsongen en gång – skonsamt mot gratiskällan
    (arbetsflödet körs var tionde minut och sparar inte .cache_odds)."""
    import json
    rows = []
    for i, season in enumerate(season_codes(now)):
        f = state_dir / f"hornor_{season}.json"
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            d = {"hamtad": 0, "ligor": {}}
        if (i == 0 and now - d.get("hamtad", 0) > ttl_s) or (i > 0 and not d.get("ligor")):
            got = 0
            for code in leagues:
                txt = _fetch(URL.format(season=season, code=code))
                if txt:
                    d["ligor"][code] = [[x["ts"], x["hemma"], x["borta"], x["hc"], x["ac"], x["sup"], x["o25"]]
                                        for x in parse_csv(txt, code)]
                    got += 1
            if got:
                d["hamtad"] = now
                f.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            log(f"Hörnmodell: football-data.co.uk {season}: {got} av {len(leagues)} ligor hämtade")
        for code, xs in d.get("ligor", {}).items():
            rows += [{"liga": code, "ts": x[0], "hemma": x[1], "borta": x[2], "hc": x[3], "ac": x[4], "sup": x[5], "o25": x[6]}
                     for x in xs]
    return rows


# ------------------------------------------------------------------ modell
def _nb_pmf(mu: float, r: float, n: int = MAXN) -> list[float]:
    """Negativ binomial med medel mu och form r (varians mu + mu²/r)."""
    p = r / (r + mu)
    out = [p ** r]
    for k in range(1, n + 1):
        out.append(out[-1] * (k + r - 1) / k * (1 - p))
    return out


class LeagueModel:
    def __init__(self, rows: list[dict], now: float, half_life_days: float = 120, k: float = 6.0):
        self.rows = rows
        w = [0.5 ** ((now - x["ts"]) / 86400 / half_life_days) for x in rows]
        sw = sum(w) or 1.0
        self.mh = sum(wi * x["hc"] for wi, x in zip(w, rows)) / sw
        self.ma = sum(wi * x["ac"] for wi, x in zip(w, rows)) / sw
        acc: dict = {}
        for wi, x in zip(w, rows):
            for team, cf, ca, mf, ma in ((x["hemma"], x["hc"], x["ac"], self.mh, self.ma),
                                         (x["borta"], x["ac"], x["hc"], self.ma, self.mh)):
                a = acc.setdefault(team, [0.0, 0.0, 0.0])
                a[0] += wi * cf / mf
                a[1] += wi * ca / ma
                a[2] += wi
        self.att = {t: (a[0] + k) / (a[2] + k) for t, a in acc.items()}
        self.dfn = {t: (a[1] + k) / (a[2] + k) for t, a in acc.items()}
        self.n = {t: a[2] for t, a in acc.items()}
        # spridning: varians kring modellens väntevärde (per lag och match), r = μ² / (var − μ)
        res, mus = [], []
        for x in rows:
            lh, la = self.expected_raw(x["hemma"], x["borta"])
            res += [(x["hc"] - lh) ** 2, (x["ac"] - la) ** 2]
            mus += [lh, la]
        m = sum(mus) / len(mus) if mus else 5.0
        var = sum(res) / len(res) if res else m * 1.3
        self.r = max(4.0, min(60.0, m * m / max(var - m, 0.05 * m)))

    def expected_raw(self, home: str, away: str) -> tuple[float, float]:
        return (self.mh * self.att.get(home, 1.0) * self.dfn.get(away, 1.0),
                self.ma * self.att.get(away, 1.0) * self.dfn.get(home, 1.0))

    def team(self, name: str) -> str | None:
        from .sources.props_text import team_key
        k = team_key(name)
        best, br = None, 0.0
        for t in self.att:
            r = SequenceMatcher(None, k, team_key(t)).ratio()
            if r > br:
                best, br = t, r
        return best if br >= 0.75 else None

    def dist(self, home: str, away: str) -> dict | None:
        h, a = self.team(home), self.team(away)
        if not h or not a or h == a:
            return None
        lh, la = self.expected_raw(h, a)
        ph, pa = _nb_pmf(lh, self.r), _nb_pmf(la, self.r)
        return {"lh": lh, "la": la, "ph": ph, "pa": pa, "fd_hemma": h, "fd_borta": a,
                "n_hemma": self.n.get(h, 0), "n_borta": self.n.get(a, 0)}


def p_side(d: dict, key: tuple) -> float | None:
    """Sannolikheten för (marknad, linje, sida) ur modellens fördelningar."""
    mk, line, side = key
    ph, pa = d["ph"], d["pa"]
    if mk in ("corners_home", "corners_away"):
        pm = ph if mk == "corners_home" else pa
        over = sum(p for k, p in enumerate(pm) if k > line)
        return over if side == "over" else sum(p for k, p in enumerate(pm) if k < line)
    if mk == "corners":
        tot = [0.0] * (2 * MAXN + 1)
        for i, x in enumerate(ph):
            for j, y in enumerate(pa):
                tot[i + j] += x * y
        return sum(p for k, p in enumerate(tot) if (k > line if side == "over" else k < line))
    if mk == "cah":   # halvlinjer: hemma + linje > borta
        s = 0.0
        for i, x in enumerate(ph):
            for j, y in enumerate(pa):
                if (side == "home" and i + line > j) or (side == "away" and j + line > i):
                    s += x * y
        return s
    return None


class OddsModel:
    """Marknadens förväntan ur 1X2 och över/under 2,5 (log-linjär, ligaintercept, nivå rättad per liga) och
    lagens egna hörnor UTÖVER vad oddsen säger (residual, krympt) med vikt GAMMA. Holdout 45 dagar, 17 ligor:
    Brier 0,2227 mot 0,2258 för bara lagdata (LeagueModel) och 0,2235 för bara odds."""
    GAMMA = 0.5

    def __init__(self, rows: list[dict], now: float, half_life_days: float = 120, k: float = 6.0):
        import numpy as np
        tr = [x for x in rows if x.get("sup") is not None]
        self.ligs = sorted({x["liga"] for x in tr})
        self.idx = {lg: i for i, lg in enumerate(self.ligs)}
        A = np.array([self._x(x) for x in tr])
        self.bh = np.linalg.lstsq(A, np.array([np.log(x["hc"] + 0.5) for x in tr]), rcond=None)[0]
        self.ba = np.linalg.lstsq(A, np.array([np.log(x["ac"] + 0.5) for x in tr]), rcond=None)[0]
        sm: dict = {}
        for x in tr:
            eh, ea = self._raw(x["liga"], x["sup"], x["o25"])
            a = sm.setdefault(x["liga"], [0.0, 0.0, 0.0, 0.0])
            a[0] += x["hc"]; a[1] += eh; a[2] += x["ac"]; a[3] += ea
        self.corr = {lg: (a[0] / a[1], a[2] / a[3]) for lg, a in sm.items()}
        acc: dict = {}
        for x in tr:
            w = 0.5 ** ((now - x["ts"]) / 86400 / half_life_days)
            eh, ea = self.market(x["liga"], x["sup"], x["o25"])
            for t, cf, ca, ef, eo in ((x["hemma"], x["hc"], x["ac"], eh, ea), (x["borta"], x["ac"], x["hc"], ea, eh)):
                a = acc.setdefault((x["liga"], t), [0.0, 0.0, 0.0])
                a[0] += w * cf / ef
                a[1] += w * ca / eo
                a[2] += w
        self.att = {t: (a[0] + k) / (a[2] + k) for t, a in acc.items()}
        self.dfn = {t: (a[1] + k) / (a[2] + k) for t, a in acc.items()}

    def _x(self, x: dict) -> list:
        v = [0.0] * len(self.ligs)
        v[self.idx[x["liga"]]] = 1.0
        return v + [x["sup"], x["o25"] - 0.5]

    def _raw(self, liga: str, sup: float, o25: float) -> tuple[float, float]:
        import math
        v = self._x({"liga": liga, "sup": sup, "o25": o25})
        return (max(0.5, math.exp(sum(a * b for a, b in zip(v, self.bh))) - 0.5),
                max(0.5, math.exp(sum(a * b for a, b in zip(v, self.ba))) - 0.5))

    def market(self, liga: str, sup: float, o25: float) -> tuple[float, float]:
        eh, ea = self._raw(liga, sup, o25)
        ch, ca = self.corr.get(liga, (1.0, 1.0))
        return eh * ch, ea * ca

    def expected(self, liga: str, h: str, a: str, sup: float, o25: float) -> tuple[float, float]:
        eh, ea = self.market(liga, sup, o25)
        g = self.GAMMA
        return (eh * (self.att.get((liga, h), 1.0) * self.dfn.get((liga, a), 1.0)) ** g,
                ea * (self.att.get((liga, a), 1.0) * self.dfn.get((liga, h), 1.0)) ** g)


class Models:
    def __init__(self, rows: list[dict], now: float, half_life_days: float = 120, k: float = 6.0):
        by: dict = {}
        for x in rows:
            by.setdefault(x["liga"], []).append(x)
        self.leagues = {c: LeagueModel(rs, now, half_life_days, k) for c, rs in by.items() if len(rs) >= 30}
        self.rows = rows
        try:
            self.odds = OddsModel([x for x in rows if x["liga"] in self.leagues], now, half_life_days, k)
        except Exception:  # noqa: BLE001 – för lite odds i underlaget: bara lagdata
            self.odds = None

    def dist(self, home: str, away: str, sup: float | None = None, o25: float | None = None
             ) -> tuple[str, dict] | tuple[None, None]:
        """Med marknadens styrka (sup = p_hemma − p_borta, o25 = p över 2,5 mål, Pinnacle) används OddsModel,
        annars bara lagens hörnor (LeagueModel)."""
        for code, m in self.leagues.items():
            d = m.dist(home, away)
            if not d:
                continue
            if self.odds is not None and sup is not None and o25 is not None and code in self.odds.idx:
                lh, la = self.odds.expected(code, d["fd_hemma"], d["fd_borta"], sup, o25)
                d.update(lh=lh, la=la, ph=_nb_pmf(lh, m.r), pa=_nb_pmf(la, m.r), metod="odds+lag")
            else:
                d["metod"] = "lag"
            return code, d
        return None, None

    def result(self, home: str, away: str, ko: float) -> tuple[int, int] | None:
        """Reserv för rättningen: hörnorna ur football-data.co.uk."""
        from .sources.props_text import same_match
        for x in self.rows:
            if abs(x["ts"] - ko) < 2 * 86400 and same_match(home, away, ko, x["hemma"], x["borta"], x["ts"], 2 * 86400):
                return x["hc"], x["ac"]
        return None


def _market_strength(pin: dict) -> tuple[float | None, float | None]:
    """Pinnacle utan marginal (sides.pinnacle_main): sup = p_hemma − p_borta, o25 = p(över 2,5 mål)."""
    try:
        sup = pin[("1x2", 0.0, "home")][0] - pin[("1x2", 0.0, "away")][0]
    except (KeyError, TypeError, IndexError):
        return None, None
    o = pin.get(("total", 2.5, "over"))
    if o is None:     # närmaste linje: grov omräkning med ±0,12 per halvt mål
        tl = sorted((k[1], v[0]) for k, v in pin.items() if k[0] == "total" and k[2] == "over")
        if not tl:
            return sup, 0.5
        ln, p = min(tl, key=lambda t: abs(t[0] - 2.5))
        return sup, max(0.05, min(0.95, p + (ln - 2.5) * 0.24))
    return sup, o[0]


def _devig(km: dict, key: tuple) -> float | None:
    mk, line, side = key
    if mk == "cah":          # Kambis 3-vägs handikapp: sidorna är inte varandras komplement (krysset saknas)
        return None
    okey = (mk, line, {"over": "under", "under": "over"}[side])
    if key in km and okey in km:
        a, b = 1 / km[key], 1 / km[okey]
        return a / (a + b)
    return None


def run(root: Path, data: list, settings: dict, diag) -> dict:
    """data: [(evd, ...)] med evd['kambi_main'] (sides.py). Bokför hörnmodellens testspel och rättar."""
    from .ledger import Ledger
    from .sides import _ceil2, espn_scores, label, settle
    from .sources.http import JsonClient
    now = time.time()
    s = settings
    rows = load_history(root, now, log=diag.log)
    models = Models(rows, now, s.get("corners_half_life_days", 120), s.get("corners_shrink_k", 6.0))
    lg = Ledger(root / "bokforing_hornor_test.json")
    playable = set(s.get("playable_books", []))
    lo, hi = s.get("corners_odds", [1.40, 6.50])
    min_e = s.get("corners_min_edge", 0.05)
    max_e = s.get("corners_max_edge", 0.25)
    n_match = n_lines = 0
    new, latest, top = [], {}, []
    for evd, *_ in data:
        km = evd.get("kambi_main") or {}
        if any(w in f"{evd['home_team']} {evd['away_team']} {evd.get('league', '')}".lower()
               for w in ("(w)", "women", "dam", "u19", "u21", "u23", "reserves", " ii")):
            continue          # underlaget är herrarnas A-lag
        if not km or not (0 < evd["commence_time"] - now <= s.get("sides_max_hours", 24) * 3600):
            continue
        sup, o25 = _market_strength(evd.get("pin_main") or {})
        code, d = models.dist(evd["home_team"], evd["away_team"], sup, o25)
        if d is None:
            continue
        n_match += 1
        cands = []
        for book, prices in km.items():
            if book not in playable:
                continue
            for key, odds in prices.items():
                if key[0] not in CORNER_KEYS:
                    continue
                p = p_side(d, key)
                if p is None or p <= 0:
                    continue
                n_lines += 1
                edge = p * odds - 1
                latest[f"{evd['id']}|{key[0]}|{key[1]:g}|{key[2]}|{book}"] = odds
                cands.append((edge, key, odds, book, p, _devig(prices, key)))
        cands.sort(key=lambda t: -t[0])
        if cands:
            top.append((cands[0][0], evd, cands[0]))
        ok = [c for c in cands if min_e <= c[0] <= max_e and lo <= c[2] <= hi]
        if not ok or any(b.get("match_id") == evd["id"] for b in lg.bets):
            continue
        edge, key, odds, book, p, pmk = ok[0]
        mk, line, side = key
        who, txt = label(mk, line, side, evd["home_team"], evd["away_team"])
        b = {"key": f"{evd['id']}|{mk}|{line:g}|{side}|{book}", "id": len(lg.bets) + 1, "bokford": now,
             "match_id": evd["id"], "match": f"{evd['home_team']} – {evd['away_team']}", "hemma": evd["home_team"],
             "borta": evd["away_team"], "liga": evd.get("league", ""), "fd_liga": code, "avspark": evd["commence_time"],
             "spelare": who, "spelare_id": "hörnor", "marknad": mk, "linje": line, "sida": side, "spel_text": txt,
             "bolag": book, "odds": odds, "sannolikhet": p, "ratt_odds": 1 / p, "edge": edge,
             "spela_fran": _ceil2((1 + min_e) / p), "insats_pct": 0.01, "stangning": odds,
             "p_modell": p, "p_marknad": pmk, "vantat_hemma": round(d["lh"], 2), "vantat_borta": round(d["la"], 2),
             "underlag_matcher": [round(d["n_hemma"], 1), round(d["n_borta"], 1)],
             "status": "öppen", "stopp": f"hörnmodell ({d['metod']}): väntat {d['lh']:.1f}–{d['la']:.1f} ({code})", "metod": d["metod"],
             "utfall": None, "resultat_enheter": None}
        lg.bets.append(b)
        lg.by_key[b["key"]] = b
        new.append(b)
    for b in lg.bets:   # stängning = Unibets senaste odds före start
        if b["status"] == "öppen" and now < b["avspark"] and b["key"] in latest:
            b["stangning"] = latest[b["key"]]
            b["stangning_ts"] = now
    try:
        scores = espn_scores(lg.bets, JsonClient(root / ".cache_odds", ttl_s=900), now)
        for b in lg.bets:   # reserv: football-data.co.uk
            if b["status"] == "öppen" and ("corners", b["match_id"]) not in scores and now > b["avspark"] + 3 * 3600:
                r = models.result(b["hemma"], b["borta"], b["avspark"])
                if r:
                    scores[("corners", b["match_id"])] = r
                    scores.setdefault(b["match_id"], (0, 0))   # settle kräver match-nyckeln
        for line in settle(lg, scores):
            diag.lines.append("  hörnor " + line)
    except Exception as e:  # noqa: BLE001
        diag.log(f"Hörnmodell rättning: FEL {type(e).__name__}: {e}")
    lg.save()
    top.sort(key=lambda t: -t[0])
    diag.log(f"Hörnmodell (test): {len(rows)} matcher i underlaget ({len(models.leagues)} ligor), {n_match} matcher med modell, "
             f"{n_lines} Kambi-linjer, {len(new)} nya testspel; bästa edge "
             + ", ".join(f"{e:+.1%} ({ev['home_team']} {label(*c[1], ev['home_team'], ev['away_team'])[1]} @ {c[2]:.2f})"
                         for e, ev, c in top[:3]))
    return {"ledger": lg, "new": new, "models": models}


def calibration(bets: list[dict]) -> dict:
    """Brier för modellen mot Kambis pris utan marginal på avgjorda testspel."""
    xs = [(b["p_modell"], b["p_marknad"], 1 if b["status"] == "vunnen" else 0) for b in bets
          if b.get("status") in ("vunnen", "förlorad") and b.get("p_modell") is not None and b.get("p_marknad") is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "brier_modell": sum((p - y) ** 2 for p, _, y in xs) / len(xs),
            "brier_marknad": sum((q - y) ** 2 for _, q, y in xs) / len(xs)}

