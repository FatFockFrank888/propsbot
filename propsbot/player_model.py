"""Egen spelarmodell från ESPN:s öppna matchstatistik.

För varje kommande match:
1. Hitta matchen och lagens ESPN-id (scoreboard för avsparksdagen).
2. Hämta lagens senaste avslutade matcher (lagets schema) och spelarstatistik
   per match (summary). Avslutade matcher ändras aldrig och cachas permanent.
3. Spelarens takt per framträdande (start = 1, inhopp = 0,35) som viktat snitt
   med halveringstid i matcher, krympt mot lagets snitt per startspelare.
4. Skala med lagets väntade mål (Pinnacle) mot lagets snitt i urvalet.
5. P(över linje): Poisson för mål/assist, negativ binomial för skott.

Resultatet vägs ihop med marknaden i line_adjust (modellvikt i settings).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .quant.fb_minutes import minutes_from_espn
from .results import BASE, LEAGUES, STAT_NAMES
from .sources.http import JsonClient, SourceError
from .sources.props_text import name_key, same_match, same_person

MARKETS = ("shots", "shots_on_target", "goal", "assist")
ELASTICITY = {"goal": 1.0, "assist": 1.0, "shots_on_target": 0.6, "shots": 0.5}
# 25/11: experiment, bara loggning. Värden ur brorsens modellkarta (anpassade mot ~58 000 spelarmatcher mot matchodds):
# lagets nivå slår på mål/assist 0,5, skott på mål 0,35, skott 0,2. Styr ingen spelbeslut – se alt_elasticitet.py.
ELASTICITY_ALT = {"goal": 0.5, "assist": 0.5, "shots_on_target": 0.35, "shots": 0.2}
# Hybrid (25/11): mitt emellan vår och brorsens. Primär modell i Spelarprops-testet (egen bokföring, inga notiser).
ELASTICITY_HYB = {m: (ELASTICITY[m] + ELASTICITY_ALT[m]) / 2 for m in ELASTICITY}
NB_SHAPE = {"shots": 6.0, "shots_on_target": 10.0}   # överspridning (lägre = mer spridning)
FB2_MARKETS = ("shots", "shots_on_target")             # F5-skuggan (backtest BACKTEST_PER90_2026-11-26.md)
FB2_PRIOR_MIN = 900.0                                   # minsta minuter för ett positionssnitt i ligan


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class PlayerRates:
    name: str
    team_id: str
    apps: float                     # viktade framträdanden
    starts: int
    n_matches: int
    rate: dict[str, float] = field(default_factory=dict)   # per framträdande
    mu_alt: dict[str, float] = field(default_factory=dict)  # väntat antal med ELASTICITY_ALT (loggas, styr inget)
    mu_cur: dict[str, float] = field(default_factory=dict)  # med nuvarande ELASTICITY
    mu_hyb: dict[str, float] = field(default_factory=dict)  # med ELASTICITY_HYB (Spelarprops-testets modell)
    # F5 (26/11, skugga): takt per 90 krympt mot ligans positionssnitt (quant/fb_rates) och E[min | start]
    fb2: dict[str, float] = field(default_factory=dict)     # per 90
    fb2_emin: float | None = None
    fb2_grp: str | None = None
    mu_fb2: dict[str, float] = field(default_factory=dict)  # väntat antal med ELASTICITY_HYB


@dataclass
class TeamModel:
    team_id: str
    name: str
    avg_goals: float
    players: dict[str, PlayerRates]  # name_key -> rates


class EspnStore:
    """Permanent cache av avslutade matchers spelarstatistik (små utdrag)."""

    def __init__(self, client: JsonClient, cache_dir: Path, refetch_budget: int = 0):
        self.c = client
        self.dir = cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.fetched = 0
        self.refetch_left = refetch_budget     # gamla utdrag utan minuter/position som får hämtas om (F5)
        self.refetched = 0

    def match_extract(self, league: str, event_id: str, need_v2: bool = False) -> dict | None:
        f = self.dir / f"{league}_{event_id}.json"
        if f.exists():
            old = json.loads(f.read_text(encoding="utf-8"))
            if not need_v2 or old.get("v", 1) >= 2 or self.refetch_left <= 0:
                return old
            self.refetch_left -= 1
            self.refetched += 1
        raw = self.c.get(f"{BASE}/{league}/summary", {"event": event_id}, ttl=86400)
        if not raw:
            return None
        out = {"v": 2, "teams": {}}
        for team in raw.get("rosters", []) or []:
            tid = str((team.get("team") or {}).get("id", ""))
            players = []
            for e in team.get("roster", []) or []:
                st = {}
                for s in e.get("stats", []) or []:
                    st[s.get("name") or s.get("abbreviation")] = _num(s.get("value", s.get("displayValue")))
                started = bool(e.get("starter"))
                sub = bool(e.get("subbedIn")) or (not started and st.get("appearances", 0) > 0)
                if not (started or sub):
                    continue
                players.append({
                    "n": (e.get("athlete") or {}).get("displayName", ""), "s": started,
                    # F1/F2 (26/11): minuter ur bytesminuten och position, för per-90-takten (bara nya matcher)
                    "min": minutes_from_espn(e), "pos": (e.get("position") or {}).get("abbreviation"),
                    **{m: next((st[k] for k in STAT_NAMES[m] if k in st), 0.0) for m in MARKETS}})
            out["teams"][tid] = players
        # lagets mål ur header/competitors
        for comp in ((raw.get("header") or {}).get("competitions") or [{}])[:1]:
            for c in comp.get("competitors", []):
                out.setdefault("goals", {})[str((c.get("team") or c).get("id", c.get("id", "")))] = \
                    _num(c.get("score"))
        if out["teams"]:
            existed = f.exists()
            f.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            self.fetched += 0 if existed else 1
        return out


class PlayerModel:
    def __init__(self, client: JsonClient, cache_dir: Path, n_matches: int = 8,
                 half_life: float = 5.0, prior_apps: float = 3.0, sub_weight: float = 0.35,
                 fb2_matches: int = 15, fb2_backfill: int = 0):
        self.c = client
        self.store = EspnStore(client, cache_dir, refetch_budget=fb2_backfill)
        self.n_fb2 = fb2_matches
        self._priors: dict[str, dict] = {}
        self.n = n_matches
        self.hl = half_life
        self.prior = prior_apps
        self.sub_w = sub_weight
        self._boards: dict[tuple[str, str], list] = {}
        self._teams: dict[str, TeamModel] = {}

    # --------------------------------------------------------- hitta match
    def find_upcoming(self, home: str, away: str, start: float
                      ) -> tuple[str, str, str, str, str] | None:
        """(liga, event_id, hemma_id, borta_id) för kommande match."""
        day = datetime.fromtimestamp(start, timezone.utc).strftime("%Y%m%d")
        for lg in LEAGUES:
            key = (lg, day)
            if key not in self._boards:
                try:
                    raw = self.c.get(f"{BASE}/{lg}/scoreboard", {"dates": day}, ttl=3600) or {}
                except SourceError:
                    raw = {}
                self._boards[key] = raw.get("events", [])
            for ev in self._boards[key]:
                comp = (ev.get("competitions") or [{}])[0]
                t = {c.get("homeAway"): c.get("team", {}) for c in comp.get("competitors", [])}
                if "home" not in t or "away" not in t:
                    continue
                try:
                    st = _ts(ev["date"])
                except (KeyError, ValueError):
                    continue
                if same_match(home, away, start, t["home"].get("displayName", ""),
                              t["away"].get("displayName", ""), st):
                    return lg, str(ev["id"]), str(t["home"].get("id")), str(t["away"].get("id")), day
        return None

    # --------------------------------------------------------- lagmodell
    def team(self, league: str, team_id: str, before: float) -> TeamModel | None:
        if team_id in self._teams:
            return self._teams[team_id]
        sched = self.c.get(f"{BASE}/{league}/teams/{team_id}/schedule", ttl=6 * 3600) or {}
        done = []
        name = (sched.get("team") or {}).get("displayName", team_id)
        for ev in sched.get("events", []) or []:
            comp = (ev.get("competitions") or [{}])[0]
            status = (comp.get("status") or ev.get("status") or {}).get("type", {})
            try:
                st = _ts(ev["date"])
            except (KeyError, ValueError):
                continue
            if status.get("completed") and st < before:
                done.append((st, str(ev["id"])))
        done.sort(reverse=True)
        done_fb2 = done[: max(self.n, self.n_fb2)]
        done = done[: self.n]
        if not done:
            return None
        acc: dict[str, dict] = {}
        goals = []
        for age, (_, eid) in enumerate(done):          # age 0 = senaste
            ex = self.store.match_extract(league, eid)
            if not ex or team_id not in ex.get("teams", {}):
                continue
            w_age = 0.5 ** (age / self.hl)
            goals.append(ex.get("goals", {}).get(team_id))
            for p in ex["teams"][team_id]:
                k = name_key(p["n"])
                a = acc.setdefault(k, {"name": p["n"], "apps": 0.0, "starts": 0, "n": 0,
                                       **{m: 0.0 for m in MARKETS}})
                w = w_age * (1.0 if p["s"] else self.sub_w)
                a["apps"] += w
                a["starts"] += int(p["s"])
                a["n"] += 1
                for m in MARKETS:
                    a[m] += w_age * p[m]
        if not acc:
            return None
        # lagets snitt per startspelare (prior för krympning)
        tot_w = sum(0.5 ** (i / self.hl) for i in range(len(done)))
        team_rate = {m: sum(a[m] for a in acc.values()) / tot_w / 11.0 for m in MARKETS}
        players = {}
        for k, a in acc.items():
            rate = {m: (a[m] + team_rate[m] * self.prior) / (a["apps"] + self.prior)
                    for m in MARKETS}
            players[k] = PlayerRates(a["name"], team_id, a["apps"], a["starts"], a["n"], rate)
        try:
            self._fb2(league, team_id, done_fb2, players)
        except Exception:  # noqa: BLE001 – skuggmodellen får aldrig stoppa den vanliga
            pass
        g = [x for x in goals if x is not None]
        tm = TeamModel(team_id, name, sum(g) / len(g) if g else 1.35, players)
        self._teams[team_id] = tm
        return tm


    # --------------------------------------------------------- F5: per 90 (skugga)
    def league_priors(self, league: str) -> dict:
        """(grupp eller '*') -> {marknad: per 90} ur alla v2-utdrag för ligan i cachen (bara avslutade matcher)."""
        if league in self._priors:
            return self._priors[league]
        from .quant.fb_rates import position_group
        acc: dict = {}
        for f in self.store.dir.glob(f"{league}_*.json"):
            try:
                ex = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if ex.get("v", 1) < 2:
                continue
            for ps in ex.get("teams", {}).values():
                for p in ps:
                    g = position_group(p.get("pos")) if p.get("s") else None
                    if not g or g == "GK" or not p.get("min"):
                        continue
                    for key in (g, "*"):
                        a = acc.setdefault(key, {"min": 0.0, **{m: 0.0 for m in FB2_MARKETS}})
                        a["min"] += p["min"]
                        for m in FB2_MARKETS:
                            a[m] += p.get(m) or 0.0
        out = {k: {m: a[m] * 90.0 / a["min"] for m in FB2_MARKETS} for k, a in acc.items() if a["min"] >= FB2_PRIOR_MIN}
        self._priors[league] = out
        return out

    def _fb2(self, league: str, team_id: str, done: list, players: dict) -> None:
        from .quant.fb_minutes import Status, expected_minutes
        from .quant.fb_rates import M_PRIOR, position_group, shrunk_rate
        hist: dict[str, list] = {}
        for _, eid in done:                                   # nyaste först
            ex = self.store.match_extract(league, eid, need_v2=True)
            if not ex or ex.get("v", 1) < 2 or team_id not in ex.get("teams", {}):
                continue
            for p in ex["teams"][team_id]:
                hist.setdefault(name_key(p["n"]), []).append(p)
        priors = self.league_priors(league)
        if not priors:
            return
        for k, pr in players.items():
            h = [p for p in hist.get(k, []) if p.get("min") is not None]
            if not h:
                continue
            groups = [position_group(p.get("pos")) for p in h if p.get("s")]
            groups = [g for g in groups if g]
            grp = max(set(groups), key=groups.count) if groups else None
            if grp == "GK":
                continue
            pri = priors.get(grp) or priors.get("*")
            if not pri:
                continue
            for m in FB2_MARKETS:
                rows = [{"min": p["min"], "n": p.get(m) or 0.0, "age": i} for i, p in enumerate(h)]
                pr.fb2[m], _ = shrunk_rate(rows, pri[m], M_PRIOR[m])
            pr.fb2_emin = expected_minutes([(bool(p.get("s")), p["min"]) for p in h], Status.CONFIRMED_XI)
            pr.fb2_grp = grp


# ------------------------------------------------------------ sannolikheter
def poisson_over(mu: float, line: float) -> float:
    k = int(math.floor(line))
    return max(0.0, 1.0 - sum(math.exp(-mu) * mu ** i / math.factorial(i) for i in range(k + 1)))


def nb_over(mu: float, line: float, shape: float) -> float:
    """Negativ binomial med medel mu och form r (Poisson-gamma)."""
    r = shape
    p = r / (r + mu)
    k = int(math.floor(line))
    cdf = 0.0
    for i in range(k + 1):
        cdf += math.exp(math.lgamma(i + r) - math.lgamma(r) - math.lgamma(i + 1)
                        + r * math.log(p) + i * math.log(1 - p))
    return max(0.0, 1.0 - cdf)


def model_probs(tm: TeamModel, exp_goals: float, min_apps: float = 2.0
                ) -> dict[tuple[str, str], tuple[float, PlayerRates]]:
    """(name_key, marknad) -> (väntat antal i matchen, spelarens takt)."""
    ratio = exp_goals / max(tm.avg_goals, 0.3)
    ratio = min(max(ratio, 0.6), 1.7)
    out = {}
    for k, pr in tm.players.items():
        if pr.apps < min_apps:
            continue
        for m in MARKETS:
            out[(k, m)] = (pr.rate[m] * ratio ** ELASTICITY[m], pr)
            pr.mu_alt[m] = pr.rate[m] * ratio ** ELASTICITY_ALT[m]
            pr.mu_cur[m] = out[(k, m)][0]
            pr.mu_hyb[m] = pr.rate[m] * ratio ** ELASTICITY_HYB[m]
            if m in pr.fb2 and pr.fb2_emin:
                pr.mu_fb2[m] = pr.fb2[m] * pr.fb2_emin / 90.0 * ratio ** ELASTICITY_HYB[m]
    return out


def prob_over(market: str, mu: float, line: float) -> float:
    if market in NB_SHAPE:
        return nb_over(mu, line, NB_SHAPE[market])
    return poisson_over(mu, line)


def match_player(models: dict, kambi_name_key: str) -> str | None:
    if any(k == kambi_name_key for k, _ in models):
        return kambi_name_key
    names = {k for k, _ in models}
    return next((k for k in names if same_person(k, kambi_name_key)), None)
