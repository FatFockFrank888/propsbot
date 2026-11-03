"""Fouls (Player's fouls conceded) – datainsamling, inga notiser (3/11).

Kambi (Unibet, ATG, Svenska Spel …) har fler fouls-linjer än skott på mål, och ingen
skarp aktör (Pinnacle har inga fouls-props). Edgen kan därför bara komma från en egen
modell, så allt bokförs som test i bokforing_fouls_test.json och rättas mot ESPN.

Modell per spelare (de senaste n matcherna, nyare väger tyngre):
  takt   = fouls per framträdande, krympt mot lagets snitt per spelare (prior_apps)
  motst. = motståndarlagets dragna fouls per match / ligasnittet (dribblande lag drar mer),
           elasticitet 0,5, begränsad till 0,8–1,25
  väntat = takt × motst.-faktor;  P(över linje) från negativ binomial (form 8)
Sannolikheten gäller givet att spelaren spelar (annars stryks spelet).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from .config import Config
from .decision import Candidate, evaluate
from .player_model import _num, nb_over
from .results import BASE
from .pipeline import Row
from .scan import ScanRow
from .sources.props_text import name_key, same_person

NB_SHAPE = 8.0
LEAGUE_FS = 11.5          # ungefärligt snitt dragna fouls per lag och match (topp-5-ligor)


class FoulsStore:
    """Permanent cache: per match och lag, spelarnas fouls (gjorda) och lagets dragna fouls."""

    def __init__(self, client, cache_dir: Path):
        self.c = client
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.fetched = 0

    def match(self, league: str, event_id: str) -> dict | None:
        f = self.dir / f"{league}_{event_id}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        raw = self.c.get(f"{BASE}/{league}/summary", {"event": event_id}, ttl=86400)
        if not raw:
            return None
        out = {"teams": {}, "drawn": {}}
        for team in raw.get("rosters", []) or []:
            tid = str((team.get("team") or {}).get("id", ""))
            ps, drawn = [], 0.0
            for e in team.get("roster", []) or []:
                st = {}
                for s in e.get("stats", []) or []:
                    st[s.get("name") or s.get("abbreviation")] = _num(s.get("value", s.get("displayValue")))
                started = bool(e.get("starter"))
                if not (started or e.get("subbedIn") or st.get("appearances", 0) > 0):
                    continue
                fc = next((st[k] for k in ("foulsCommitted", "fouls", "FC") if k in st), None)
                drawn += next((st[k] for k in ("foulsSuffered", "FA") if k in st), 0.0)
                if fc is None:
                    continue
                ps.append({"n": (e.get("athlete") or {}).get("displayName", ""), "s": started, "fc": fc})
            out["teams"][tid] = ps
            out["drawn"][tid] = drawn
        if any(out["teams"].values()):
            f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            self.fetched += 1
        return out


def team_rates(pm, store: FoulsStore, league: str, team_id: str, before: float,
               n: int = 8, hl: float = 5.0, prior: float = 3.0, sub_w: float = 0.35):
    """-> ({name_key: (namn, takt, viktade framträdanden, starter)}, lagets dragna fouls/match)."""
    sched = pm.c.get(f"{BASE}/{league}/teams/{team_id}/schedule", ttl=6 * 3600) or {}
    done = []
    for ev in sched.get("events", []) or []:
        comp = (ev.get("competitions") or [{}])[0]
        stt = (comp.get("status") or ev.get("status") or {}).get("type", {})
        try:
            from .player_model import _ts
            st = _ts(ev["date"])
        except (KeyError, ValueError):
            continue
        if stt.get("completed") and st < before:
            done.append((st, str(ev["id"])))
    done.sort(reverse=True)
    acc, drawn, wsum = {}, 0.0, 0.0
    for age, (_, eid) in enumerate(done[:n]):
        ex = store.match(league, eid)
        if not ex or team_id not in ex.get("teams", {}):
            continue
        w_age = 0.5 ** (age / hl)
        drawn += w_age * ex["drawn"].get(team_id, 0.0)
        wsum += w_age
        for p in ex["teams"][team_id]:
            a = acc.setdefault(name_key(p["n"]), {"name": p["n"], "apps": 0.0, "fc": 0.0, "starts": 0})
            a["apps"] += w_age * (1.0 if p["s"] else sub_w)
            a["fc"] += w_age * p["fc"]
            a["starts"] += int(p["s"])
    if not acc or wsum == 0:
        return {}, None
    team_avg = sum(a["fc"] for a in acc.values()) / wsum / 11.0
    rates = {k: (a["name"], (a["fc"] + team_avg * prior) / (a["apps"] + prior), a["apps"], a["starts"])
             for k, a in acc.items()}
    return rates, drawn / wsum


def evaluate_fouls(evd: dict, quotes: list, names: dict, pm, store: FoulsStore, settings: dict,
                   cfg: Config, now: float, diag) -> list[ScanRow]:
    fq = [q for q in quotes if q.market == "fouls" and q.book in set(settings["playable_books"])]
    if not fq:
        return []
    hit = pm.find_upcoming(evd["home_team"], evd["away_team"], evd["commence_time"])
    if not hit:
        return []
    lg, _eid, hid, aid, _ = hit
    rh, dh = team_rates(pm, store, lg, hid, evd["commence_time"])
    ra, da = team_rates(pm, store, lg, aid, evd["commence_time"])
    if not rh and not ra:
        return []
    el = settings.get("fouls_opp_elasticity", 0.5)
    opp = lambda d: 1.0 if d is None else min(1.25, max(0.8, (d / LEAGUE_FS) ** el))
    model = {}
    for rates, mult in ((rh, opp(da)), (ra, opp(dh))):      # hemmaspelare möter bortalagets dragna fouls
        for k, (nm, rate, apps, starts) in rates.items():
            if apps >= settings.get("fouls_min_apps", 2.5) and starts >= 2:
                model[k] = (rate * mult, nm)
    ko = float(evd["commence_time"])
    best: dict = {}
    for q in fq:
        if q.side != "over":
            continue
        k = (q.player_id, q.line)
        if k not in best or q.odds > best[k].odds:
            best[k] = q
    out = []
    import dataclasses
    dcfg = dataclasses.replace(cfg.decision, min_edge_by_market=dict(cfg.decision.min_edge_by_market,
                                                                     fouls=settings.get("fouls_min_edge", 0.05)))
    for (pid, line), q in best.items():
        mk = pid if pid in model else next((m for m in model if same_person(m, pid)), None)
        if not mk:
            continue
        mu, nm = model[mk]
        p = nb_over(mu, line, NB_SHAPE)
        if not 0.02 < p < 0.98:
            continue
        cand = Candidate(evd["id"], pid, names.get(pid, nm), "fouls", line, p, q, None, now, True, (ko - now) / 60)
        d = evaluate(cand, dcfg)
        d.reasons.append(f"fouls-modell: väntat {mu:.2f}")
        out.append(ScanRow("fotboll", f"{evd['home_team']} – {evd['away_team']}",
                           time.strftime("%Y-%m-%d %H:%M", time.gmtime(ko)), Row(d, p, float("nan"), 1.0), 1,
                           expected=mu))
    return out


def run(root: Path, data: list, pm, settings: dict, cfg: Config, diag) -> None:
    """Utvärdera fouls för alla matcher, bokför i testbokföringen och rätta."""
    from .clv_signal import final_rules, taken_players
    from .ledger import Ledger
    from .results import settle_open
    from .sources.http import JsonClient
    store = FoulsStore(pm.c, root / "espn_fouls")
    rows = []
    for evd, quotes, names in data:
        try:
            rows += evaluate_fouls(evd, quotes, names, pm, store, settings, cfg, time.time(), diag)
        except Exception as e:     # testmarknad – får aldrig stoppa skanningen
            diag.lines.append(f"  fouls {evd.get('home_team')}: FEL {type(e).__name__}: {e}")
    lg = Ledger(root / "bokforing_fouls_test.json")
    final_rules(rows, settings, None, "", taken_players(lg))
    new = lg.record(rows, {evd["id"]: evd for evd, _, _ in data})
    lg.update_closing(rows, time.time())
    try:
        settle_open(lg, JsonClient(root / ".cache_odds", ttl_s=900))
    except Exception as e:
        diag.log(f"Fouls-rättning: {type(e).__name__}: {e}")
    lg.save()
    es = sorted((r.row.decision.cand.edge for r in rows), reverse=True)[:3]
    diag.log(f"Fouls (test): {len(rows)} ben med modell, {sum(r.row.decision.playable for r in rows)} klarar kraven, "
             f"{len(new)} nya bokförda, bästa edge {', '.join(f'{e:+.1%}' for e in es) or '–'}, "
             f"{store.fetched} nya ESPN-matcher")
