"""Bokföring av ALLA fotbollsben med modell (inte bara de som blir spel), kalibrering mot utfall och konsensusmarginal.

Varför: dagens kedja jämför mest marknaden med sig själv, och modellens nivå ankras mot marknaden. För att veta om
modellen eller konsensusen har något värde behövs (1) alla ben, inte bara de med edge, (2) utfallen, (3) mått mot
verkligheten. Allt här är datainsamling/kalibrering i testläge: inga spel, inga notiser, inga trösklar ändras.

Flöde per skanning (anropas från spelarprops.record_hyb):
  record_all   -> loggar/uppdaterar varje ben med BEKRÄFTAD startspelare (lu_state == "start") före avspark
  finish       -> rättar mot ESPN (settle_open), flyttar avgjorda ben till benlogg_avgjorda.json (kompakt), analyserar
  analyse      -> Brier/log-loss per källa, anpassar nivåkalibrering (a + b·logit p) och konsensusens marginal

Nivåkalibrering (modell_utfallskal.json) tar nivån från UTFALL i stället för från marknaden. Startvärden (PRIOR_CAL) är
anpassade på 6 346 startande spelare ur FotMob-backtesten 26/11 (tools/backtest_fotmob.py, M0 = dagens logik); egna
avgjorda ben tar över per marknad/linje när det finns minst MIN_N och kalibreringen slår rå p på de nyaste 30 %.
Konsensusens ensidiga marginal (standard 7 %) anpassas på samma sätt (konsensus_marginal.json).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

LEG_FILE = "bokforing_ben_alla.json"
DONE_FILE = "benlogg_avgjorda.json"
CAL_FILE = "modell_utfallskal.json"
MARGIN_FILE = "konsensus_marginal.json"
MIN_N = 150
STUCK_DAYS = 5
COLS = ["key", "avspark", "marknad", "linje", "y", "p_cur", "p_hyb", "p_alt", "p_adj", "p_k", "p_cons", "n_cons",
        "parts", "odds", "p_utfall"]

# Startvärden från FotMob-backtesten (M0, alla val+test-rader). logit(p') = a + b·logit(p_rå)
PRIOR_CAL = {
    "shots_on_target|0.5": (-0.2020, 0.9306),
    "shots_on_target|1.5": (-0.2525, 0.8868),
    "shots|0.5": (-0.3501, 1.1754),
    "shots|1.5": (-0.0630, 1.2073),
    "shots|2.5+": (0.1441, 1.1356),
}
CAL: dict[str, dict] = {}     # fylls av load_cal() en gång per skanning; läses av line_adjust


def line_group(line: float) -> str:
    return "0.5" if line <= 0.5 else "1.5" if line <= 1.5 else "2.5+"


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def fit_logistic(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    """Logistisk regression y ~ a + b·x med Newton. pairs = [(x, y)]."""
    a, b = 0.0, 1.0
    for _ in range(60):
        g0 = g1 = 0.0
        h00 = h01 = h11 = 1e-6
        for x, y in pairs:
            q = _sig(a + b * x)
            w = q * (1 - q)
            g0 += q - y
            g1 += (q - y) * x
            h00 += w
            h01 += w * x
            h11 += w * x * x
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-12:
            break
        da = (h11 * g0 - h01 * g1) / det
        db = (-h01 * g0 + h00 * g1) / det
        a -= da
        b -= db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def _brier(ps: list[float], ys: list[float]) -> float:
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / max(len(ys), 1)


def _logloss(ps: list[float], ys: list[float]) -> float:
    return -sum(math.log(min(max(p if y else 1 - p, 1e-4), 1 - 1e-4)) for p, y in zip(ps, ys)) / max(len(ys), 1)


# ----------------------------------------------------------------------------- laddning
def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def load_cal(root: Path) -> dict:
    """Startvärden + egna anpassningar. Sätter modulens CAL (läses av line_adjust) och returnerar den."""
    cal = {k: {"a": a, "b": b, "src": "start (FotMob-backtest)", "n": 0} for k, (a, b) in PRIOR_CAL.items()}
    own = _read(root / CAL_FILE, {}).get("fits", {})
    for k, f in own.items():
        if isinstance(f, dict) and "a" in f and "b" in f:
            cal[k] = {"a": f["a"], "b": f["b"], "src": "egen (avgjorda ben)", "n": f.get("n", 0)}
    CAL.clear()
    CAL.update(cal)
    return cal


def consensus_margin(root: Path, settings: dict) -> float:
    default = settings.get("propline_one_sided_margin", 0.07)
    if not settings.get("consensus_margin_auto", True):
        return default
    m = _read(root / MARGIN_FILE, {})
    try:
        if m.get("n", 0) >= MIN_N and 0.0 <= float(m["m"]) <= 0.4:
            return float(m["m"])
    except (KeyError, TypeError, ValueError):
        pass
    return default


# ----------------------------------------------------------------------------- loggning
def _num(x):
    return None if x is None or x != x else x


def record_all(root: Path, rows: list, evd_by_id: dict, now: float | None = None):
    """Loggar/uppdaterar alla ben med bekräftad startspelare (r.lu_state == 'start') som har modell. Returnerar Ledger."""
    from .ledger import Ledger
    now = now or time.time()
    led = Ledger(root / LEG_FILE)
    done_keys = {r[0] for r in _read(root / DONE_FILE, {}).get("rows", [])}
    new = upd = 0
    for r in rows:
        if getattr(r, "lu_state", "okänd") != "start":
            continue
        ex = getattr(r, "extra", None) or {}
        if ex.get("p_raw_hyb") is None:
            continue
        c = r.row.decision.cand
        ev = evd_by_id.get(c.match_id, {})
        av = ev.get("commence_time")
        if not av or now >= av:
            continue
        key = f"{c.match_id}|{c.player_id}|{c.market}|{c.line}"
        if key in done_keys:
            continue
        snap = {"bokford": now, "bolag": c.best.book, "odds": c.best.odds, "stangning": c.best.odds,
                "p_cur": ex.get("p_raw_cur"), "p_hyb": ex.get("p_raw_hyb"), "p_alt": ex.get("p_raw_alt"),
                "p_adj": ex.get("p_adj"), "p_k": ex.get("p_k"), "p_cons": ex.get("p_cons"), "n_cons": ex.get("n_cons"),
                "parts": ex.get("parts"), "p_utfall": ex.get("p_mod_utfall")}
        b = led.by_key.get(key)
        if b is None:
            b = {"key": key, "id": len(led.bets) + 1, "match_id": c.match_id, "match": r.match,
                 "hemma": ev.get("home_team"), "borta": ev.get("away_team"), "avspark": av, "spelare": c.player_name,
                 "spelare_id": c.player_id, "marknad": c.market, "linje": c.line, "sida": "over", "insats_pct": 0.0,
                 "status": "öppen", "utfall": None, "resultat_enheter": None}
            led.bets.append(b)
            led.by_key[key] = b
            new += 1
        elif b.get("status") == "öppen":
            upd += 1
        else:
            continue
        b.update(snap)
    led.stats = (new, upd)
    return led


def finish(root: Path, led, client, settings: dict, diag, now: float | None = None) -> None:
    """Rättar, flyttar avgjorda ben till den kompakta filen, sparar och analyserar."""
    from .results import settle_open
    now = now or time.time()
    try:
        settle_open(led, client)
    except Exception as e:  # noqa: BLE001
        diag.log(f"Benlogg rättning: {type(e).__name__}: {str(e)[:120]}")
    done = _read(root / DONE_FILE, {"cols": COLS, "rows": []})
    seen = {r[0] for r in done.get("rows", [])}
    keep, harvested = [], 0
    for b in led.bets:
        st = b.get("status")
        if st in ("vunnen", "förlorad"):
            if b["key"] not in seen:
                done["rows"].append([b["key"], b.get("avspark"), b.get("marknad"), b.get("linje"),
                                     1 if st == "vunnen" else 0, b.get("p_cur"), b.get("p_hyb"), b.get("p_alt"),
                                     b.get("p_adj"), b.get("p_k"), b.get("p_cons"), b.get("n_cons"), b.get("parts"),
                                     b.get("odds"), b.get("p_utfall")])
                seen.add(b["key"])
                harvested += 1
        elif st == "struken":
            continue
        elif b.get("avspark") and now > b["avspark"] + STUCK_DAYS * 86400:
            continue
        else:
            keep.append(b)
    led.bets = keep
    led.by_key = {b["key"]: b for b in keep}
    done["cols"] = COLS
    try:
        led.save()
        (root / DONE_FILE).write_text(json.dumps(done, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except OSError as e:
        diag.log(f"Benlogg: kunde inte spara ({e})")
    new, upd = getattr(led, "stats", (0, 0))
    diag.log(f"Benlogg: {new} nya + {upd} uppdaterade ben (bekräftade startande), {len(led.bets)} öppna, "
             f"{harvested} nya avgjorda, {len(done['rows'])} avgjorda totalt")
    try:
        analyse(root, done, settings, diag)
    except Exception as e:  # noqa: BLE001
        diag.log(f"Benlogg analys: FEL {type(e).__name__}: {str(e)[:150]}")


# ----------------------------------------------------------------------------- analys
def _t(d: list[float]) -> float:
    n = len(d)
    if n < 3:
        return 0.0
    m = sum(d) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1)) or 1e-9
    return m / (sd / math.sqrt(n))


def analyse(root: Path, done: dict, settings: dict, diag) -> dict:
    from .consensus import p_from_parts
    rows = [dict(zip(COLS, r)) for r in done.get("rows", [])]
    out = {"groups": {}}
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["marknad"], line_group(r["linje"])), []).append(r)
    fits = {}
    for (mk, g), R in sorted(groups.items()):
        n = len(R)
        if n < 20:
            continue
        ys = [float(r["y"]) for r in R]
        txt = [f"{mk} {g}: n={n}, utfall {sum(ys) / n:.3f}"]
        base = [r for r in R if r["p_adj"] is not None and r["p_hyb"] is not None]
        if len(base) >= 20:
            yb = [float(r["y"]) for r in base]
            br_m = [(r["p_adj"] - r["y"]) ** 2 for r in base]
            br_h = [(r["p_hyb"] - r["y"]) ** 2 for r in base]
            txt.append(f"modell p {sum(r['p_hyb'] for r in base) / len(base):.3f} Brier {sum(br_h) / len(base):.4f} | "
                       f"marknad p {sum(r['p_adj'] for r in base) / len(base):.3f} Brier {sum(br_m) / len(base):.4f} | "
                       f"t(modell bättre) {_t([a - b for a, b in zip(br_m, br_h)]):+.2f}")
            kal = [r for r in base if r["p_utfall"] is not None]
            if len(kal) >= 20:
                br_u = [(r["p_utfall"] - r["y"]) ** 2 for r in kal]
                br_hk = [(r["p_hyb"] - r["y"]) ** 2 for r in kal]
                txt.append(f"utfallsankrad modell Brier {sum(br_u) / len(kal):.4f} (rå {sum(br_hk) / len(kal):.4f})")
        cons = [r for r in R if r["p_cons"] is not None and r["p_adj"] is not None]
        if len(cons) >= 20:
            bc = [(r["p_cons"] - r["y"]) ** 2 for r in cons]
            ba = [(r["p_adj"] - r["y"]) ** 2 for r in cons]
            txt.append(f"konsensus p {sum(r['p_cons'] for r in cons) / len(cons):.3f} (n={len(cons)}) Brier "
                       f"{sum(bc) / len(cons):.4f} mot marknad {sum(ba) / len(cons):.4f}, t {_t([a - b for a, b in zip(ba, bc)]):+.2f}")
        diag.log("Benlogg " + " | ".join(txt))
        # nivåkalibrering: anpassa på äldsta 70 %, pröva på nyaste 30 %
        h = [r for r in R if r["p_hyb"] is not None]
        if len(h) >= MIN_N:
            h.sort(key=lambda r: r["avspark"] or 0)
            cut = int(len(h) * 0.7)
            a_t, b_t = fit_logistic([(_logit(r["p_hyb"]), r["y"]) for r in h[:cut]])
            test = h[cut:]
            ys_t = [float(r["y"]) for r in test]
            raw = _brier([r["p_hyb"] for r in test], ys_t)
            cal = _brier([_sig(a_t + b_t * _logit(r["p_hyb"])) for r in test], ys_t)
            a, b = fit_logistic([(_logit(r["p_hyb"]), r["y"]) for r in h])
            ok = cal < raw
            diag.log(f"Benlogg nivåkalibrering {mk} {g}: a={a:+.3f} b={b:.3f} (n={len(h)}), pröva på nyaste "
                     f"{len(test)}: Brier rå {raw:.4f} -> kalibrerad {cal:.4f} {'(sparas)' if ok else '(slår inte rå, sparas inte)'}")
            if ok:
                fits[f"{mk}|{g}"] = {"a": round(a, 4), "b": round(b, 4), "n": len(h), "brier_rå_holdout": round(raw, 5),
                                     "brier_kal_holdout": round(cal, 5)}
    if fits:
        old = _read(root / CAL_FILE, {}).get("fits", {})
        old.update(fits)
        (root / CAL_FILE).write_text(json.dumps({"ts": time.time(), "fits": old}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    # konsensusens marginal
    cr = [r for r in rows if r["parts"] and r["p_cons"] is not None and "q" in (r["parts"] or "")]
    if len(cr) >= MIN_N:
        cr.sort(key=lambda r: r["avspark"] or 0)
        cut = int(len(cr) * 0.7)

        def ll(R, m):
            ps = [p_from_parts(r["parts"], m) for r in R]
            keep = [(p, r["y"]) for p, r in zip(ps, R) if p is not None]
            return _logloss([p for p, _ in keep], [y for _, y in keep]) if keep else float("inf")

        grid = [i / 100 for i in range(0, 31)]
        m_t = min(grid, key=lambda m: ll(cr[:cut], m))
        base = settings.get("propline_one_sided_margin", 0.07)
        l_new, l_old = ll(cr[cut:], m_t), ll(cr[cut:], base)
        m_all = min(grid, key=lambda m: ll(cr, m))
        ok = l_new < l_old
        diag.log(f"Benlogg konsensusmarginal: bäst {m_all:.2f} på {len(cr)} ben (antagen {base:.2f}); pröva på nyaste "
                 f"{len(cr) - cut}: log-loss {l_old:.4f} -> {l_new:.4f} med {m_t:.2f} {'(sparas)' if ok else '(slår inte antagen, sparas inte)'}")
        if ok:
            (root / MARGIN_FILE).write_text(json.dumps({"ts": time.time(), "m": m_all, "n": len(cr),
                                                        "logloss_antagen": round(l_old, 5), "logloss_ny": round(l_new, 5)},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    elif rows:
        diag.log(f"Benlogg: {len(cr)} av {MIN_N} avgjorda ben med ensidiga konsensusdelar (marginalen kalibreras vid {MIN_N})")
    return out
