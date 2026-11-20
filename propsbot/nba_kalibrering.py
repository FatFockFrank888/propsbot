"""NBA: kalibreringslogg och automatisk kalibrering av spelarmodellen (20/11).

Varför: modelltestet (1 143 avgjorda till 20/11) visade att modellens sannolikhet var kraftigt överkonfident
(sa 66 %, träffade 52,5 %) och att den inte tillförde något utöver marknaden. En orsak är att modellen bara
kalibrerades på spel den SJÄLV valt – de där den avviker mest från marknaden (vinnarens förbannelse).

1. Kalibreringslogg (nba_kalibrering.json.gz)
   Varje ben som modellen räknar på loggas, inte bara de som bokas: en rad per spelare × match × marknad × linje,
   i över-orientering. Raden uppdateras vid varje skanning fram till start (sista värdena före start gäller) och
   rättas mot ESPN:s boxscore (samma rättning som bokföringarna). Kompakt format, rader äldre än LOG_DAYS tas bort.

2. Kalibrering per marknad, prövad framåt
   Tre modeller jämförs på de NYASTE avgjorda raderna (TEST_SHARE), skattade på de äldre:
     M0  marknaden som den är:                 P = p_marknad
     M1  marknaden kalibrerad:                 P = σ(a + b·logit p_marknad)
     M2  M1 + modellens avvikelser:            P = σ(a + b·logit p_marknad + c·g_modell + d·g_faktorer + e·g_betyg)
         (g = logit(delmodellens P) − logit(p_marknad), 0 när delmodellen saknas)
   En mer avancerad modell väljs bara om den slår den enklare spel för spel på testdelen: snittet av
   skillnaden i log-loss ska vara positivt med t ≥ MIN_T (parat test), och för M2 krävs minst MIN_TEST rader. Vald modell skattas sedan om på allt, med en
   ridge-prior mot "lita på marknaden" (b = 1, övriga 0). Marknader med för lite data använder den gemensamma
   skattningen (_alla).

   Resultatet sparas i nba_kalibrering_modell.json och används av NÄSTA skanning (alltid framåtriktat).
   Modelltestet bokar bara ben på marknader där M2 är vald, med den kalibrerade sannolikheten. Har modellen
   inte förtjänat vikt någonstans bokförs inga modelltestspel – men loggen fortsätter, så modellen kan
   förtjäna vikten senare (och varje ny modellversion prövas på samma sätt).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from .market import inv_logit, logit

LOG_FILE = "nba_kalibrering.json.gz"   # gzip: alla ben, ~500–1 000 per dag
MODEL_FILE = "nba_kalibrering_modell.json"
LOG_DAYS = 30
TEST_SHARE = 0.3
MIN_TEST = 150            # minsta antal avgjorda rader i testdelen för att modellen ska få vikt
MIN_MARKET = 300          # minsta antal avgjorda rader för en egen skattning per marknad
MIN_T = 2.0               # parat t-värde (log-loss per rad, testdelen) för att välja en mer avancerad modell
PRIOR_N = 400.0
BOUNDS = {"a": (-0.3, 0.3), "b": (0.7, 1.2), "c": (-0.3, 1.0), "d": (-0.3, 1.0), "e": (-0.3, 1.0)}
IDENT = {"modell": "M0", "a": 0.0, "b": 1.0, "c": 0.0, "d": 0.0, "e": 0.0}


def _clip(p: float) -> float:
    return min(max(p, 1e-3), 1 - 1e-3)


def _r(x, k=4):
    return None if x is None else round(float(x), k)


# ---------------------------------------------------------------- loggen
class KalibLog:
    def __init__(self, root: Path):
        self.path = root / LOG_FILE
        import gzip
        try:
            with gzip.open(self.path, "rt", encoding="utf-8") as fh:
                self.rows: list[dict] = json.load(fh).get("rader", [])
        except (FileNotFoundError, json.JSONDecodeError, AttributeError, OSError, EOFError):
            self.rows = []
        self.by_k = {r["k"]: r for r in self.rows}

    def upsert(self, e: dict, now: float) -> None:
        """e: mid, pid, spelare, hemma, borta, match, avspark, mk, ln, pm, pk, pf, pb, dq (P = över)."""
        if not e.get("avspark") or now >= e["avspark"]:
            return
        k = f"{e['mid']}|{e['pid']}|{e['mk']}|{e['ln']:g}"
        r = self.by_k.get(k)
        vals = {"pm": _r(e.get("pm")), "pk": _r(e["pk"]), "pf": _r(e.get("pf")), "pb": _r(e.get("pb")),
                "dq": _r(e.get("dq"), 2), "t": round(now)}
        if r is None:
            r = {"k": k, "match_id": e["mid"], "spelare": e["spelare"], "hemma": e["hemma"], "borta": e["borta"],
                 "match": e.get("match", ""), "avspark": e["avspark"], "marknad": e["mk"], "linje": e["ln"],
                 "t0": round(now), "status": "öppen"}
            self.rows.append(r)
            self.by_k[k] = r
        r.update(vals)

    def prune(self, now: float) -> None:
        cut = now - LOG_DAYS * 86400
        self.rows = [r for r in self.rows if (r.get("avspark") or 0) >= cut]
        self.by_k = {r["k"]: r for r in self.rows}

    def save(self) -> None:
        import gzip
        tmp = self.path.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=6) as fh:
            json.dump({"rader": self.rows}, fh, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(self.path)

    # settle_nba vill ha .bets och .settle(b, värde, spelade)
    @property
    def bets(self) -> list[dict]:
        return self.rows

    def settle(self, b: dict, value, played: bool = True) -> None:
        if not played or value is None:
            b["status"] = "struken"
            return
        b["utfall"] = value
        b["y"] = 1 if value > b["linje"] else 0
        b["status"] = "vunnen" if b["y"] else "förlorad"   # över-orientering: "vunnen" = över gick in


def settle(root: Path, client, now: float | None = None) -> int:
    """Rättar loggens rader mot ESPN (samma rättning som bokföringarna). Returnerar antal nya rättade."""
    from .nba import settle_nba
    lg = KalibLog(root)
    before = sum(1 for r in lg.rows if r.get("status") != "öppen")
    settle_nba(lg, client, now)
    lg.prune(now or time.time())
    lg.save()
    return sum(1 for r in lg.rows if r.get("status") != "öppen") - before


# ---------------------------------------------------------------- kalibreringen
def _features(r: dict) -> list[float]:
    lk = logit(_clip(r["pk"]))
    g = lambda k: (logit(_clip(r[k])) - lk) if r.get(k) is not None else 0.0
    return [1.0, lk, g("pm"), g("pf"), g("pb")]


def _fit(X, y, prior, cols, lam=PRIOR_N):
    from .nba_minutes import _fit_logistic
    Xs = [[x[i] for i in cols] for x in X]
    w = _fit_logistic(Xs, y, [prior[i] for i in cols], lam)
    out = dict(IDENT)
    for i, v in zip(cols, w):
        out["abcde"[i]] = v
    return {k: (min(max(v, BOUNDS[k][0]), BOUNDS[k][1]) if k in BOUNDS else v) for k, v in out.items()}


def _p(q: dict, x: list[float]) -> float:
    z = q["a"] * x[0] + q["b"] * x[1] + q["c"] * x[2] + q["d"] * x[3] + q["e"] * x[4]
    return inv_logit(z)


def _lls(q: dict, X, y) -> list[float]:
    out = []
    for x, t in zip(X, y):
        p = min(max(_p(q, x), 1e-6), 1 - 1e-6)
        out.append(-(t * math.log(p) + (1 - t) * math.log(1 - p)))
    return out


def _better(new: list[float], old: list[float]) -> tuple[bool, float]:
    """Är new bättre än old spel för spel? (parat t-test på log-loss-skillnaden)."""
    d = [o - n for n, o in zip(new, old)]
    if len(d) < 30:
        return False, 0.0
    m = sum(d) / len(d)
    sd = (sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5
    t = m / (sd / len(d) ** 0.5) if sd > 0 else 0.0
    return m > 0 and t >= MIN_T, t


def _choose(rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda r: r.get("t") or 0)
    X, y = [_features(r) for r in rows], [r["y"] for r in rows]
    cut = int(len(rows) * (1 - TEST_SHARE))
    Xtr, ytr, Xte, yte = X[:cut], y[:cut], X[cut:], y[cut:]
    prior = [0.0, 1.0, 0.0, 0.0, 0.0]
    cand = {"M0": dict(IDENT)}
    if len(Xtr) >= 50:
        cand["M1"] = _fit(Xtr, ytr, prior, [0, 1])
        cand["M2"] = _fit(Xtr, ytr, prior, [0, 1, 2, 3, 4])
    per = {k: _lls(q, Xte, yte) for k, q in cand.items()} if Xte else {}
    ll = {k: sum(v) / len(v) for k, v in per.items()} if per else {"M0": None}
    pick, t_val = "M0", {}
    if "M1" in per:
        ok, t_val["M1"] = _better(per["M1"], per["M0"])
        if ok:
            pick = "M1"
    if "M2" in per and len(Xte) >= MIN_TEST:
        ok, t_val["M2"] = _better(per["M2"], per[pick])
        if ok:
            pick = "M2"
    q = dict(IDENT) if pick == "M0" else _fit(X, y, prior, [0, 1] if pick == "M1" else [0, 1, 2, 3, 4])
    q["modell"] = pick
    q.update(n=len(rows), n_test=len(Xte), t_test={k: round(v, 2) for k, v in t_val.items()},
             logloss_test={k: (None if v is None else round(v, 5)) for k, v in ll.items()},
             vinst_mot_marknad=None if ll.get("M0") is None or ll.get(pick) is None else round(ll["M0"] - ll[pick], 5))
    return q


def fit(root: Path, now: float | None = None) -> dict:
    """Skattar om kalibreringen från loggen och sparar den. Returnerar {marknad: parametrar, "_alla": …}."""
    lg = KalibLog(root)
    done = [r for r in lg.rows if r.get("y") in (0, 1) and r.get("pk") is not None]
    out = {"uppdaterad_ts": now or time.time(), "_alla": _choose(done) if done else dict(IDENT, n=0)}
    for mk in sorted({r["marknad"] for r in done}):
        rs = [r for r in done if r["marknad"] == mk]
        if len(rs) >= MIN_MARKET:
            out[mk] = _choose(rs)
    (root / MODEL_FILE).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load(root: Path) -> dict:
    try:
        return json.loads((root / MODEL_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def params_for(params: dict, market: str) -> dict:
    return params.get(market) or params.get("_alla") or dict(IDENT)


def predict(params: dict, market: str, pk_over: float, pm_over=None, pf_over=None, pb_over=None) -> tuple[float, bool]:
    """Kalibrerad P(över) och om modellen har förtjänat vikt (M2) för marknaden."""
    q = params_for(params, market)
    p = _p(q, _features({"pk": pk_over, "pm": pm_over, "pf": pf_over, "pb": pb_over}))
    return p, q.get("modell") == "M2"


def summary(params: dict) -> str:
    parts = []
    for k, q in sorted(params.items()):
        if not isinstance(q, dict):
            continue
        g = q.get("vinst_mot_marknad")
        parts.append(f"{k} {q.get('modell')} (n {q.get('n', 0)}" + (f", test {q.get('n_test')}, vinst {g:+.4f}" if g is not None else "")
                     + (f", modellvikt {q['c']:+.2f}" if q.get("modell") == "M2" else "") + ")")
    return ", ".join(parts) or "ingen data än"
