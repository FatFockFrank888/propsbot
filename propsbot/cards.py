"""Kort ("To Get a Card": gult eller rött) – datainsamling, inga notiser (4/11).

Kambi (Unibet, ATG, Svenska Spel …) har "To Get a Card" för ~27 spelare per match, bara ja-sidan.
Ingen skarp aktör har spelarkort, så edgen kan bara komma från en egen modell. Allt bokförs som
test i bokforing_kort_test.json och rättas mot ESPN (gula + röda kort).

Modell per spelare (senaste n matcherna, nyare väger tyngre):
  takt    = kort per framträdande (inhoppare väger 0,35), krympt mot lagets snitt per spelare
  motst.  = motståndarlagets dragna fouls per match / ligasnittet (fler fouls -> fler kort),
            elasticitet 0,5, begränsad till 0,8–1,25
  domare  = samma stränghetsfaktor som fouls (±15 %)
  P(kort) = 1 − exp(−takt × motst. × domare)        (Poisson, minst ett kort)
Sannolikheten gäller givet att spelaren spelar (annars stryks spelet).
"""
from __future__ import annotations

import dataclasses
import json
import math
import time
from pathlib import Path

from .config import Config
from .decision import Candidate, evaluate
from .player_model import _num
from .pipeline import Row
from .results import BASE
from .scan import ScanRow
from .sources.props_text import name_key, same_person

LEAGUE_FS = 11.5          # ungefärligt snitt dragna fouls per lag och match


class CardsStore:
    """Permanent cache per match: spelarnas kort (gula + röda) och lagens dragna fouls."""

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
                drawn += next((st[k] for k in ("foulsSuffered", "FA") if k in st), 0.0)
                yc = next((st[k] for k in ("yellowCards", "YC") if k in st), None)
                rc = next((st[k] for k in ("redCards", "RC") if k in st), None)
                if yc is None and rc is None:
                    continue
                ps.append({"n": (e.get("athlete") or {}).get("displayName", ""), "s": started,
                           "c": (yc or 0.0) + (rc or 0.0)})
            out["teams"][tid] = ps
            out["drawn"][tid] = drawn
        if any(out["teams"].values()):
            f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            self.fetched += 1
        return out


def team_rates(pm, store: CardsStore, league: str, team_id: str, before: float,
               n: int = 10, hl: float = 6.0, prior: float = 4.0, sub_w: float = 0.35):
    """-> ({name_key: (namn, kort per match, viktade framträdanden, starter)}, lagets dragna fouls/match)."""
    from .player_model import _ts
    sched = pm.c.get(f"{BASE}/{league}/teams/{team_id}/schedule", ttl=6 * 3600) or {}
    done = []
    for ev in sched.get("events", []) or []:
        comp = (ev.get("competitions") or [{}])[0]
        stt = (comp.get("status") or ev.get("status") or {}).get("type", {})
        try:
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
        w = 0.5 ** (age / hl)
        drawn += w * ex["drawn"].get(team_id, 0.0)
        wsum += w
        for p in ex["teams"][team_id]:
            a = acc.setdefault(name_key(p["n"]), {"name": p["n"], "apps": 0.0, "c": 0.0, "starts": 0})
            a["apps"] += w * (1.0 if p["s"] else sub_w)
            a["c"] += w * p["c"]
            a["starts"] += int(p["s"])
    if not acc or wsum == 0:
        return {}, None
    team_avg = sum(a["c"] for a in acc.values()) / wsum / 11.0
    rates = {k: (a["name"], (a["c"] + team_avg * prior) / (a["apps"] + prior), a["apps"], a["starts"])
             for k, a in acc.items()}
    return rates, drawn / wsum


def evaluate_cards(evd: dict, quotes: list, names: dict, pm, store: CardsStore, settings: dict,
                   cfg: Config, now: float, ref_mult: float = 1.0, ref_note: str = "") -> list[ScanRow]:
    cq = [q for q in quotes if q.market == "cards" and q.side == "over" and q.book in set(settings["playable_books"])]
    if not cq:
        return []
    hit = pm.find_upcoming(evd["home_team"], evd["away_team"], evd["commence_time"])
    if not hit:
        return []
    lg, _eid, hid, aid, _ = hit
    rh, dh = team_rates(pm, store, lg, hid, evd["commence_time"])
    ra, da = team_rates(pm, store, lg, aid, evd["commence_time"])
    if not rh and not ra:
        return []
    el = settings.get("cards_opp_elasticity", 0.5)
    opp = lambda d: 1.0 if d is None else min(1.25, max(0.8, (d / LEAGUE_FS) ** el))
    model = {}
    for rates, mult in ((rh, opp(da)), (ra, opp(dh))):
        for k, (nm, rate, apps, starts) in rates.items():
            if apps >= settings.get("cards_min_apps", 3.0) and starts >= 2:
                model[k] = (rate * mult * ref_mult, nm)
    best: dict = {}
    for q in cq:
        if q.player_id not in best or q.odds > best[q.player_id].odds:
            best[q.player_id] = q
    dcfg = dataclasses.replace(cfg.decision, min_edge_by_market=dict(cfg.decision.min_edge_by_market,
                                                                     cards=settings.get("cards_min_edge", 0.05)))
    ko = float(evd["commence_time"])
    out = []
    for pid, q in best.items():
        mk = pid if pid in model else next((m for m in model if same_person(m, pid)), None)
        if not mk:
            continue
        mu, nm = model[mk]
        p = 1.0 - math.exp(-mu)
        if not 0.02 < p < 0.9:
            continue
        cand = Candidate(evd["id"], pid, names.get(pid, nm), "cards", 0.5, p, q, None, q.ts, True, (ko - now) / 60)
        d = evaluate(cand, dcfg)
        d.reasons.append(f"kort-modell: {mu:.2f} kort/match" + (f"; domare {ref_note}" if ref_note else ""))
        if d.cand.edge > settings.get("max_plausible_edge", 0.25):
            d.playable, d.stake = False, 0.0
            d.reasons.append(f"edge över {settings.get('max_plausible_edge', 0.25):.0%} – orimligt, modellen saknar troligen info")
        out.append(ScanRow("fotboll", f"{evd['home_team']} – {evd['away_team']}",
                           time.strftime("%Y-%m-%d %H:%M", time.gmtime(ko)), Row(d, p, float("nan"), 1.0), 1,
                           expected=mu))
    return out


def run(root: Path, data: list, pm, settings: dict, cfg: Config, diag, ref_stats=None, ups=None) -> None:
    """Utvärdera kort för alla matcher, bokför i testbokföringen och rätta."""
    from .clv_signal import final_rules, taken_players
    from .ledger import Ledger
    from .results import settle_open
    from .sources.http import JsonClient
    store = CardsStore(pm.c, root / "espn_kort")
    if ups is None and any(any(q.market == "cards" for q in qs) for _, qs, _ in data):
        try:
            from . import referees
            ref_stats, ups = referees.load_stats(root, diag), referees.upcoming(time.time(), diag=diag)
        except Exception as e:
            diag.log(f"Kort – domare: FEL {type(e).__name__}: {str(e)[:150]}")
            ref_stats, ups = {}, []
    rows, n_q = [], 0
    for evd, quotes, names in data:
        n_q += sum(q.market == "cards" for q in quotes)
        mult, note = 1.0, ""
        if ups:
            from . import referees
            ref = referees.referee_for(evd, ups)
            if ref:
                mult, note = referees.factor(ref_stats or {}, ref)
        try:
            rows += evaluate_cards(evd, quotes, names, pm, store, settings, cfg, time.time(), mult, note)
        except Exception as e:     # testmarknad – får aldrig stoppa skanningen
            diag.lines.append(f"  kort {evd.get('home_team')}: FEL {type(e).__name__}: {e}")
    lg = Ledger(root / "bokforing_kort_test.json")
    final_rules(rows, settings, None, "", taken_players(lg))
    new = lg.record(rows, {evd["id"]: evd for evd, _, _ in data})
    lg.update_closing(rows, time.time())
    try:
        settle_open(lg, JsonClient(root / ".cache_odds", ttl_s=900))
    except Exception as e:
        diag.log(f"Kort-rättning: {type(e).__name__}: {e}")
    lg.save()
    es = sorted((r.row.decision.cand.edge for r in rows), reverse=True)[:3]
    diag.log(f"Kort (test): {n_q} Kambi-odds, {len(rows)} ben med modell, "
             f"{sum(r.row.decision.playable for r in rows)} klarar kraven, {len(new)} nya bokförda, "
             f"bästa edge {', '.join(f'{e:+.1%}' for e in es) or '–'}, {store.fetched} nya ESPN-matcher")
