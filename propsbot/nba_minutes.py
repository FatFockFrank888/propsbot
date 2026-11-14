"""NBA: speltid som fördelning och inlärd blandning modell/marknad (bägge i skuggläge).

1. Minuter som fördelning
   Modellen räknar i dag väntat antal = minuter × takt per minut, och fördelningen är en negativ binomial med
   fast form r per marknad (NB_R). r fångar då ALL spridning, även den som kommer från att speltiden varierar.
   Det ger samma spridning för en stabil startare (36 ± 3 min) som för en rotationsspelare (18 ± 8 min).

   Här blandas NB över minutscenarier i stället: minuter ~ Normal(m, sd), avkortad till [0, 48], med
   Gauss–Hermite-punkter. För att inte räkna minutvariansen två gånger krymps r till r_villkorad så att
   GENOMSNITTLIG varians blir oförändrad:

       Var = μ + μ²/r  =  μ + μ²·(1/r_v + cv²)      (cv = sd/m för minuterna)
       1/r_v = 1/r − medel(cv²)                      (medel över skanningens spelare)

   Utklassning (blowout): ur Pinnacles spread fås P(|marginal| > 15) med marginal ~ Normal(−spread, 12,5).
   Utöver ligasnittet (spread 0 -> 0,23) tappar startare (≥ 26 min) ~ 6 min i en utklassning och bänken
   får tillbaka samma minuter i proportion till sin speltid (lagets minuter är oförändrade). Siffrorna är
   heuristik – därför skuggläge: p_modell_min bokförs och jämförs i nba_eval innan något får styra.

2. Inlärd blandning (stackning)
   I stället för en fast modellvikt (0,3 × dq) skattas per marknad

       P(över) = σ(a + b_m · logit(p_modell) + b_k · logit(p_marknad))

   på AVGJORDA modelltestrader (bara det som bokfördes före matchen), med en ridge-prior mot (0, 0, 1) –
   dvs. "lita på marknaden" – värd STACK_PRIOR_N (400) observationer, och gränser STACK_BOUNDS. Med litet underlag blir det marknaden; modellen
   får vikt bara när den mätbart tillför något, och b_m < 1 krymper en övermodig modell (Platt-lutning).
   Parametrarna skattas om varje skanning och används på NÄSTA skannings prognoser, så p_stack är alltid
   framåtriktad. Bokförs som p_stack (skugga) – påverkar inte LIVE.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .market import inv_logit, logit
from .player_model import nb_over

MARGIN_SD = 12.5          # NBA: slutmarginalens spridning kring spreaden
BLOWOUT = 15.0            # |marginal| över detta = utklassning
BLOWOUT_MIN_LOSS = 6.0    # minuter en startare tappar i en utklassning
STARTER_MIN = 26.0
MAX_MIN = 48.0
# Gauss–Hermite (sannolikhetsform): punkter i standardavvikelser och vikter (summa 1)
_GH = [(-2.651961, 0.000548), (-1.673552, 0.030757), (-0.816288, 0.240123), (0.0, 0.457142),
       (0.816288, 0.240123), (1.673552, 0.030757), (2.651961, 0.000548)]
STACK_PRIOR_N = 400.0
STACK_BOUNDS = {"a": (-0.3, 0.3), "b_modell": (-0.2, 1.0), "b_marknad": (0.7, 1.2)}
STACK_FILE = "nba_stack.json"


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def p_blowout(spread_home: float | None) -> float:
    """P(|marginal| > 15). spread_home = hemmalagets spread (−5,5 = hemmafavorit med 5,5)."""
    mu = -(spread_home or 0.0)
    return (1.0 - _phi((BLOWOUT - mu) / MARGIN_SD)) + _phi((-BLOWOUT - mu) / MARGIN_SD)


BASE_BLOWOUT = p_blowout(0.0)


def blowout_minutes(players: dict[str, float], spread_home: float | None) -> dict[str, float]:
    """Spelarnas väntade minuter efter utklassningsrisk utöver ligasnittet. Lagets summa är oförändrad."""
    if spread_home is None:
        return dict(players)
    extra = p_blowout(spread_home) - BASE_BLOWOUT
    starters = {k: m for k, m in players.items() if m >= STARTER_MIN}
    bench = {k: m for k, m in players.items() if m < STARTER_MIN}
    lost = {k: min(m, extra * BLOWOUT_MIN_LOSS) for k in starters for m in (starters[k],)}
    tot_lost, bm = sum(lost.values()), sum(bench.values()) or 1.0
    out = {}
    for k, m in players.items():
        out[k] = m - lost[k] if k in lost else min(MAX_MIN, m + tot_lost * m / bm)
    return out


def r_conditional(r: float, mean_cv2: float) -> float:
    """Form r givet minuterna, så att genomsnittlig varians är oförändrad. Högst halva spridningen tas bort."""
    inv = max(0.5 / r, 1.0 / r - mean_cv2)
    return 1.0 / inv


def nb_over_minutes(rate: float, m: float, sd: float, line: float, r_cond: float) -> float:
    """P(antal > line) när minuter ~ Normal(m, sd) avkortad till [0, 48] och antal | minuter ~ NB(rate·min, r_v)."""
    if sd <= 0.05 or m <= 0:
        return nb_over(max(rate * m, 1e-6), line, r_cond)
    p = wsum = 0.0
    for z, w in _GH:
        mins = min(MAX_MIN, max(0.0, m + z * sd))
        if mins <= 0:
            wsum += w          # 0 minuter -> 0 i statistik -> aldrig över (line ≥ 0,5)
            continue
        p += w * nb_over(rate * mins, line, r_cond)
        wsum += w
    return p / wsum if wsum else 0.0


# ------------------------------------------------------------------ stackning
def _fit_logistic(X: list[list[float]], y: list[int], prior: list[float], lam: float, iters: int = 30) -> list[float]:
    """Ridge-logistisk regression mot prior (Newton). Utan numpy-beroende i signaturen."""
    import numpy as np
    Xa, ya, b0 = np.array(X, float), np.array(y, float), np.array(prior, float)
    b = b0.copy()
    # lam = priorns värde i antal observationer: skalas med varje kolumns informationsinnehåll per observation
    # (0,25·x²), annars blir priorn för log-odds-kolumner (små tal) mycket starkare än avsett.
    L = np.diag(lam * np.maximum(0.25 * (Xa ** 2).mean(axis=0), 1e-3)) if len(Xa) else lam * np.eye(len(prior))
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(Xa @ b)))
        g = Xa.T @ (ya - p) - L @ (b - b0)
        H = (Xa * (p * (1 - p))[:, None]).T @ Xa + L
        step = np.linalg.solve(H, g)
        b = b + step
        if float(np.abs(step).max()) < 1e-8:
            break
    return [float(v) for v in b]


def _over_rows(bets: list[dict]) -> dict[str, list[tuple[float, float, int]]]:
    """Avgjorda modelltestrader -> per marknad (logit p_modell över, logit p_marknad över, y över).
    En rad per prestation (spelare × match × marknad × linje)."""
    seen, out = set(), {}
    for b in sorted(bets, key=lambda b: b.get("bokford") or 0):
        if b.get("status") not in ("vunnen", "förlorad") or b.get("p_modell") is None or b.get("p_marknad") is None:
            continue
        k = (b.get("match_id"), b.get("spelare_id"), b.get("marknad"), b.get("linje"))
        if k in seen:
            continue
        seen.add(k)
        under = b.get("sida") == "under"
        y = 1 if b["status"] == "vunnen" else 0
        pm, pk = b["p_modell"], b["p_marknad"]
        if under:
            pm, pk, y = 1 - pm, 1 - pk, 1 - y
        out.setdefault(b.get("marknad"), []).append((logit(pm), logit(pk), y))
    return out


def fit_stack(bets: list[dict], prior_n: float = STACK_PRIOR_N) -> dict:
    """Per marknad: {"a", "b_modell", "b_marknad", "n"}; "_alla" = gemensam skattning (prior för marknaderna)."""
    rows = _over_rows(bets)
    allr = [r for rs in rows.values() for r in rs]
    res = {}
    base = [0.0, 0.0, 1.0]
    if allr:
        base = _fit_logistic([[1.0, a, b] for a, b, _ in allr], [y for *_, y in allr], base, prior_n)
    res["_alla"] = {"a": base[0], "b_modell": base[1], "b_marknad": base[2], "n": len(allr)}
    for mk, rs in rows.items():
        # marknadens prior = gemensamma skattningen krympt halvvägs mot "lita på marknaden"
        pr = [0.5 * base[0], 0.5 * base[1], 0.5 * base[2] + 0.5]
        b = _fit_logistic([[1.0, a, c] for a, c, _ in rs], [y for *_, y in rs], pr, prior_n)
        res[mk] = {"a": b[0], "b_modell": b[1], "b_marknad": b[2], "n": len(rs)}
    return {k: _clip(v) for k, v in res.items()}


def _clip(q: dict) -> dict:
    return {k: (min(max(v, STACK_BOUNDS[k][0]), STACK_BOUNDS[k][1]) if k in STACK_BOUNDS else v) for k, v in q.items()}


def stack_p(params: dict, market: str, p_model_over: float, p_market_over: float) -> float:
    q = _clip(params.get(market) or params.get("_alla") or {"a": 0.0, "b_modell": 0.0, "b_marknad": 1.0})
    return inv_logit(q["a"] + q["b_modell"] * logit(p_model_over) + q["b_marknad"] * logit(p_market_over))


def load_stack(root: Path) -> dict:
    try:
        return json.loads((root / STACK_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_stack(root: Path, bets: list[dict]) -> dict:
    params = fit_stack(bets)
    (root / STACK_FILE).write_text(json.dumps(params, ensure_ascii=False, indent=1), encoding="utf-8")
    return params
