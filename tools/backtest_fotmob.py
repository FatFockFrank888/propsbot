"""Backtest: dagens spelarmodell (ESPN-logik) mot minutmedveten och xG-förstärkt variant, på FotMob-data.

Mäter sannolikheter mot utfall (Brier, log-loss, kalibrering, parad t-statistik) för skott och skott på mål
hos STARTANDE spelare. Ingen odds-data: jämför bara modellerna med verkligheten. Ingen skalning med Pinnacles
väntade mål (finns inte historiskt) -> ratio = 1 för alla modeller. Skriver bara sammanfattningar.
"""
import json, math, os, sys, time, urllib.request, urllib.error
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# Kopia av propsbot/player_model.py (nb_over, NB_SHAPE) så att skriptet inte beror på numpy/övriga paketet.
NB_SHAPE = {"shots": 6.0, "shots_on_target": 10.0}


def nb_over(mu, line, shape):
    r = shape
    p = r / (r + mu)
    k = int(math.floor(line))
    cdf = 0.0
    for i in range(k + 1):
        cdf += math.exp(math.lgamma(i + r) - math.lgamma(r) - math.lgamma(i + 1) + r * math.log(p) + i * math.log(1 - p))
    return max(0.0, 1.0 - cdf)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Referer": "https://www.fotmob.com/"}
LEAGUES = {47: "PL", 87: "LaLiga", 54: "Bundesliga", 55: "SerieA", 53: "Ligue1", 42: "CL", 73: "EL", 10216: "ECL"}
CACHE = os.environ.get("FM_CACHE", "fm_cache")
START = os.environ.get("BT_START", "2026-08-22")
SPLIT_VAL = os.environ.get("BT_VAL", "2026-10-01")
SPLIT_TEST = os.environ.get("BT_TEST", "2026-10-15")
TIME_BUDGET = float(os.environ.get("BT_BUDGET_S", "2100"))
T0 = time.time()


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503) and i < tries - 1:
                time.sleep(20 * (i + 1)); continue
            return None
        except Exception:
            time.sleep(3)
    return None


def flat_stats(groups):
    out = {}
    for g in groups or []:
        for _n, s in (g.get("stats") or {}).items():
            k = s.get("key")
            v = (s.get("stat") or {}).get("value")
            if k and isinstance(v, (int, float)):
                out[k] = float(v)
    return out


def extract(mid, meta):
    d = get(f"https://www.fotmob.com/api/data/matchDetails?matchId={mid}")
    if not d:
        return None
    c = d.get("content") or {}
    ps = c.get("playerStats") or {}
    lu = c.get("lineup") or {}
    starters = set()
    for side in ("homeTeam", "awayTeam"):
        for p in (lu.get(side) or {}).get("starters") or []:
            if p.get("id") is not None:
                starters.add(int(p["id"]))
    players = []
    for v in ps.values():
        st = flat_stats(v.get("stats"))
        mins = st.get("minutes_played")
        if not mins:
            continue
        pid = int(v.get("id"))
        players.append({"tid": int(v.get("teamId")), "pid": pid, "n": v.get("name"), "min": mins,
                        "s": (pid in starters) if starters else None, "gk": bool(v.get("isGoalkeeper")),
                        "shots": st.get("total_shots", 0.0), "sot": st.get("ShotsOnTarget", 0.0),
                        "xg": st.get("expected_goals", 0.0), "xgot": st.get("expected_goals_on_target_variant", 0.0)})
    if not players:
        return None
    return {**meta, "players": players, "have_lineup": bool(starters)}


def collect():
    os.makedirs(CACHE, exist_ok=True)
    out = {}
    for f in os.listdir(CACHE):
        if f.endswith(".json"):
            try:
                x = json.load(open(os.path.join(CACHE, f)))
                out[x["id"]] = x
            except Exception:
                pass
    print("cache: matcher", len(out), flush=True)
    day = datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.now(timezone.utc) - timedelta(days=1)
    fetched = skipped = 0
    while day <= end and time.time() - T0 < TIME_BUDGET:
        ds = day.strftime("%Y%m%d")
        mkey = os.path.join(CACHE, f"_day_{ds}.txt")
        if os.path.exists(mkey):
            day += timedelta(days=1); continue
        d = get(f"https://www.fotmob.com/api/data/matches?date={ds}")
        time.sleep(0.4)
        if d is None:
            print("matches misslyckades", ds, flush=True); day += timedelta(days=1); continue
        for lg in d.get("leagues", []):
            if lg.get("primaryId") not in LEAGUES:
                continue
            for m in lg.get("matches", []):
                st = m.get("status") or {}
                if not st.get("finished") or int(m["id"]) in out:
                    continue
                try:
                    ts = datetime.fromisoformat(st["utcTime"].replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue
                meta = {"id": int(m["id"]), "ts": ts, "lg": lg.get("primaryId"),
                        "h": int((m.get("home") or {}).get("id")), "a": int((m.get("away") or {}).get("id"))}
                x = extract(m["id"], meta)
                time.sleep(0.5)
                if x:
                    out[x["id"]] = x
                    json.dump(x, open(os.path.join(CACHE, f"{x['id']}.json"), "w"))
                    fetched += 1
                else:
                    skipped += 1
        if day.date() < (datetime.now(timezone.utc) - timedelta(days=2)).date():
            open(mkey, "w").write("1")
        day += timedelta(days=1)
    print(f"hämtade {fetched} nya, {skipped} utan data, totalt {len(out)}; tid {time.time()-T0:.0f}s", flush=True)
    return sorted(out.values(), key=lambda x: x["ts"])


# ----------------------------------------------------------------------------- modeller
N, HL, PRIOR, SUB_W = 8, 5.0, 3.0, 0.35


def started(p, m):
    return p["s"] if p["s"] is not None else p["min"] >= 60


def team_hist(matches_by_team, tid, ts):
    h = [m for m in matches_by_team[tid] if m["ts"] < ts]
    return h[-N:][::-1]          # senaste först


def build(hist, tid):
    """Aggregat per spelare ur lagets senaste matcher. Returnerar (acc, tot_w, n_matches)."""
    acc = {}
    tot_w = 0.0
    for age, m in enumerate(hist):
        w_age = 0.5 ** (age / HL)
        tot_w += w_age
        for p in (q for q in m["players"] if q["tid"] == tid):
            a = acc.setdefault(p["pid"], {"apps": 0.0, "starts": 0, "n": 0, "ex": 0.0, "mins": [], "wm": [],
                                          **{k: 0.0 for k in ("shots", "sot", "xg", "xgot")}})
            s = started(p, m)
            a["apps"] += w_age * (1.0 if s else SUB_W)
            a["starts"] += int(s)
            a["n"] += 1
            a["ex"] += w_age * p["min"] / 90.0
            if s:
                a["mins"].append(p["min"]); a["wm"].append(w_age)
            for k in ("shots", "sot", "xg", "xgot"):
                a[k] += w_age * p[k]
    return acc, tot_w


def predictions(hist, tid, conv, ctx=None):
    """pid -> dict(modell -> {marknad: mu}) för spelare med apps >= 2 (som produktionen)."""
    acc, tot_w = build(hist, tid)
    if not acc or tot_w <= 0:
        return {}
    ks = ("shots", "sot", "xg", "xgot")
    team_pa = {k: sum(a[k] for a in acc.values()) / tot_w / 11.0 for k in ks}            # per start-spelare (M0)
    tot_ex = sum(a["ex"] for a in acc.values()) or 1.0
    team_90 = {k: sum(a[k] for a in acc.values()) / tot_ex for k in ks}                    # per spelare-90 (M1/M2)
    out = {}
    for pid, a in acc.items():
        if a["apps"] < 2.0:
            continue
        r0 = {k: (a[k] + team_pa[k] * PRIOR) / (a["apps"] + PRIOR) for k in ks}             # M0 = produktionsmodellen
        r90 = {k: (a[k] + team_90[k] * PRIOR) / (a["ex"] + PRIOR) for k in ks}
        em = (sum(m * w for m, w in zip(a["mins"], a["wm"])) / sum(a["wm"])) if a["wm"] else 70.0
        em = min(90.0, max(30.0, em))
        f = em / 90.0
        mods = {"M0_nuvarande": {"shots": r0["shots"], "sot": r0["sot"]},
                "M3_lagsnitt": {"shots": team_pa["shots"], "sot": team_pa["sot"]},
                "M1_minuter": {"shots": r90["shots"] * f, "sot": r90["sot"] * f}}
        for b in (0.25, 0.5):
            mods[f"M2_xG_b{b}"] = {"shots": ((1 - b) * r90["shots"] + b * r90["xg"] * conv["shots_per_xg"]) * f,
                                   "sot": ((1 - b) * r90["sot"] + b * r90["xgot"] * conv["sot_per_xgot"]) * f}
        if ctx:
            for e in (0.5, 1.0):
                mods[f"M4_motst_e{e}"] = {mk: r0[mk] * (ctx["fdef"][mk] ** e) * (ctx["g"][mk] if ctx["home"] else 1.0 / ctx["g"][mk])
                                          for mk in ("shots", "sot")}
        out[pid] = mods
    return out


# ----------------------------------------------------------------------------- utvärdering
LINES = {"sot": (0.5, 1.5), "shots": (0.5, 1.5, 2.5)}


def evaluate(matches):
    by_team = defaultdict(list)
    for m in matches:
        by_team[m["h"]].append(m); by_team[m["a"]].append(m)
    tot = {k: sum(p[k] for m in matches for p in m["players"]) for k in ("shots", "sot", "xg", "xgot")}
    conv = {"shots_per_xg": tot["shots"] / max(tot["xg"], 1e-9), "sot_per_xgot": tot["sot"] / max(tot["xgot"], 1e-9)}
    print(f"konvertering: skott per xG {conv['shots_per_xg']:.2f}, skott på mål per xGOT {conv['sot_per_xgot']:.2f}", flush=True)
    tt = {}
    for m in matches:
        d = {m["h"]: {"shots": 0.0, "sot": 0.0}, m["a"]: {"shots": 0.0, "sot": 0.0}}
        for p in m["players"]:
            if p["tid"] in d:
                d[p["tid"]]["shots"] += p["shots"]; d[p["tid"]]["sot"] += p["sot"]
        tt[m["id"]] = d
    rows = []   # (split, marknad, linje, y, {modell: p})
    n_lineup = sum(1 for m in matches if m.get("have_lineup"))
    print(f"matcher {len(matches)}, med startelva i data {n_lineup}", flush=True)
    for m in matches:
        split = "test" if m["ts"] >= datetime.strptime(SPLIT_TEST, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() else (
            "val" if m["ts"] >= datetime.strptime(SPLIT_VAL, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() else None)
        if not split:
            continue
        for tid in (m["h"], m["a"]):
            hist = team_hist(by_team, tid, m["ts"])
            if len(hist) < 4:
                continue
            opp = m["a"] if tid == m["h"] else m["h"]
            prior = [x for x in matches if x["ts"] < m["ts"]]
            ctx = None
            if len(prior) > 100:
                ctx = {"home": tid == m["h"], "fdef": {}, "g": {}}
                oh = team_hist(by_team, opp, m["ts"])
                for mk in ("shots", "sot"):
                    lg = sum(tt[x["id"]][x["h"]][mk] + tt[x["id"]][x["a"]][mk] for x in prior) / (2 * len(prior))
                    hm = sum(tt[x["id"]][x["h"]][mk] for x in prior) / len(prior)
                    aw = sum(tt[x["id"]][x["a"]][mk] for x in prior) / len(prior)
                    num = den = 0.0
                    for age, x in enumerate(oh):
                        w = 0.5 ** (age / HL)
                        other = x["a"] if opp == x["h"] else x["h"]
                        num += w * tt[x["id"]][other][mk]; den += w
                    ctx["fdef"][mk] = ((num + 3.0 * lg) / (den + 3.0)) / max(lg, 1e-9)
                    ctx["g"][mk] = math.sqrt(hm / max(aw, 1e-9))
            pr = predictions(hist, tid, conv, ctx)
            for p in m["players"]:
                if p["tid"] != tid or p["gk"] or not started(p, m) or p["pid"] not in pr:
                    continue
                for mk, y_val in (("sot", p["sot"]), ("shots", p["shots"])):
                    for line in LINES[mk]:
                        ps = {name: nb_over(max(mu[mk], 1e-6), line, NB_SHAPE["shots_on_target" if mk == "sot" else "shots"])
                              for name, mu in pr[p["pid"]].items()}
                        rows.append((split, mk, line, 1.0 if y_val > line else 0.0, ps))
    return rows


def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _fit_cal(pairs):
    a, b = 0.0, 1.0
    for _ in range(60):          # Newton-iterationer för logistisk regression på (logit p) -> y
        g = [0.0, 0.0]; H = [[1e-6, 0.0], [0.0, 1e-6]]
        for x, y in pairs:
            q = 1 / (1 + math.exp(-(a + b * x)))
            w = q * (1 - q)
            g[0] += q - y; g[1] += (q - y) * x
            H[0][0] += w; H[0][1] += w * x; H[1][0] += w * x; H[1][1] += w * x * x
        det = H[0][0] * H[1][1] - H[0][1] * H[1][0]
        if abs(det) < 1e-12:
            break
        da = (H[1][1] * g[0] - H[0][1] * g[1]) / det
        db = (-H[1][0] * g[0] + H[0][0] * g[1]) / det
        a -= da; b -= db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def add_calibrated(rows, names=("M0_nuvarande", "M4_motst_e1.0", "M4_motst_e0.5")):
    cal = {}
    for mk in ("sot", "shots"):
        for line in LINES[mk]:
            val = [r for r in rows if r[0] == "val" and r[1] == mk and r[2] == line]
            for nm in names:
                if len(val) >= 200 and all(nm in r[4] for r in val):
                    cal[(mk, line, nm)] = _fit_cal([(_logit(r[4][nm]), r[3]) for r in val])
    for (mk, line, nm), (a, b) in sorted(cal.items()):
        print(f"kalibrering fit [val] {nm} {mk}>{line}: a={a:+.3f} b={b:.3f}")
    for r in rows:
        if r[0] != "test":
            continue
        for nm in names:
            c = cal.get((r[1], r[2], nm))
            if c and nm in r[4]:
                r[4][nm.split("_")[0] + "kal_" + nm.split("_", 1)[1]] = 1 / (1 + math.exp(-(c[0] + c[1] * _logit(r[4][nm]))))
    return rows


def report(rows):
    models = sorted({k for r in rows for k in r[4]})
    for split in ("val", "test"):
        for mk in ("sot", "shots"):
            for line in LINES[mk]:
                R = [r for r in rows if r[0] == split and r[1] == mk and r[2] == line]
                if len(R) < 30:
                    continue
                models = sorted(k for k in {k for r in R for k in r[4]} if all(k in r[4] for r in R))
                n = len(R)
                obs = sum(r[3] for r in R) / n
                print(f"\n[{split}] {mk} över {line}: n={n}, utfall {obs:.3f}")
                base = {mname: [(r[4][mname] - r[3]) ** 2 for r in R] for mname in models}
                for mname in models:
                    b = sum(base[mname]) / n
                    ll = -sum(math.log(max(min(r[4][mname], 1 - 1e-4), 1e-4)) if r[3] else math.log(max(min(1 - r[4][mname], 1 - 1e-4), 1e-4)) for r in R) / n
                    mp = sum(r[4][mname] for r in R) / n
                    d = [a - c for a, c in zip(base["M0_nuvarande"], base[mname])]
                    md = sum(d) / n
                    sd = math.sqrt(sum((x - md) ** 2 for x in d) / max(n - 1, 1)) or 1e-9
                    t = md / (sd / math.sqrt(n)) if mname != "M0_nuvarande" else 0.0
                    print(f"   {mname:14s} medel-p {mp:.3f}  Brier {b:.4f}  logloss {ll:.4f}  t mot M0 {t:+.2f}")
    # kalibrering för test, sot 0.5 och shots 1.5
    for mk, line in (("sot", 0.5), ("sot", 1.5), ("shots", 1.5)):
        R = [r for r in rows if r[0] == "test" and r[1] == mk and r[2] == line]
        if len(R) < 100:
            continue
        for mname in ("M0_nuvarande", "M4_motst_e1.0", "M4kal_motst_e1.0"):
            if not all(mname in r[4] for r in R):
                continue
            R2 = sorted(R, key=lambda r: r[4][mname])
            q = len(R2) // 5
            cells = []
            for i in range(5):
                part = R2[i * q:(i + 1) * q if i < 4 else len(R2)]
                cells.append(f"{sum(r[4][mname] for r in part)/len(part):.2f}->{sum(r[3] for r in part)/len(part):.2f}")
            print(f"\nkalibrering [test] {mk} >{line} {mname}: " + "  ".join(cells))


if __name__ == "__main__":
    matches = collect()
    if len(matches) < 50:
        print("för lite data"); sys.exit(0)
    rows = evaluate(matches)
    print("utvärderingsrader:", len(rows), flush=True)
    rows = add_calibrated(rows)
    report(rows)
