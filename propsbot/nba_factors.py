"""NBA faktormodell (skuggläge): fler förklaringsfaktorer ovanpå minuter × takt per minut.

Grundmodellen (nba_model.expected) styr LIVE i dag. Den här modellen räknar fram ett eget väntat värde per
spelare och marknad, bokförs som p_faktorer (skugga) och jämförs i nba_eval mot marknaden och mot
grundmodellen på samma avgjorda spel. Ingenting här påverkar LIVE förrän det visat sig bättre.

Faktorer (alla är multiplikatorer kring 1, krympta mot 1 efter underlagets storlek och begränsade):

  Speltid
    * Skadade/avstängda lagkamrater: deras minuter (× hur ofta de faktiskt spelat i urvalet; har de redan
      missat de tre senaste matcherna är frånvaron redan med i lagkamraternas siffror) går i första hand till
      samma position (vikt 1,6) och till rotationsspelare, 85 % fördelas.
    * Lagets minuter: varje spelares minuter gäller om han spelar. Vägt med sannolikheten att han spelar
      (spelade senaste matchen = 1, annars andelen matcher han spelat) ska laget landa på 241 min. Skillnaden
      läggs mest på bänken (vikt minuter × utrymme till 48), högst −25 %/+10 % per spelare.
    * Användning (usage): produktionen som försvinner med en stjärna täcks bara delvis av extra minuter.
      Hälften av det som saknas fördelas på de friska i proportion till deras egen produktion
      (samma position väger 1,4). Taket är +25 %.
    * Minutbegränsning (ESPN:s skadekommentar: "minutes restriction" m.m.) -> 72 % av minuterna, större
      spridning. Tillbaka efter minst två missade matcher utan sådan text -> 88 %.
    * Schema: back-to-back -3 % för startspelare (≥ 28 min), -1 % för övriga; tredje matchen på fyra kvällar -1,5 %.
    * Questionable / day-to-day -10 %.
  Matchmiljö
    * Poäng-, trepoängs- och assistnivån sätts av marknaden: lagets väntade poäng ur Pinnacles total och spread
      (hemmalagets poäng = (total − spread)/2) mot vad modellens spelare summerar till. Utan Pinnacle: snittet
      av lagets gjorda och motståndarens insläppta poäng, ±1,2 för hemma/borta. 80 % av avvikelsen används.
    * Tempo (bollinnehav ur boxscore: FGA + 0,44·FTA − OREB + TO) för returer, steals och blocks:
      motståndarens tempo mot ligans.
    * Försvar per position (G/F/C): vad motståndaren släpper till spelare på samma position per bollinnehav,
      mot ligan. För poäng/trepoängare/assist räknas det RELATIVT motståndarens försvar i stort (det
      är redan med i lagets väntade poäng), annars absolut. Krympt med insamlade minuter, ±12 %.
    * Mot just den här motståndaren (i år + förra säsongen): spelarens takt per minut mot laget jämfört med
      hans vanliga. Vikt n/(n+8) – två matcher ger 20 % vikt – och ±8 %. Inte för steals/blocks (brus).
  Träffbild (bara information, påverkar inte prognosen): andel matcher över linjen senaste 5, 10, säsongen,
  mot motståndaren och hemma/borta.
"""
from __future__ import annotations

from .nba_model import COMBO, OUT_STATUS, STATS, NbaModel, NbaTeam, name_key

ENV_ELASTICITY = {"points": 1.0, "threes": 0.8, "assists": 0.7}
PACE_ELASTICITY = {"rebounds": 0.8, "steals": 1.0, "blocks": 0.8}
POS_K = {"points": 600, "rebounds": 600, "assists": 600, "threes": 900, "steals": 1500, "blocks": 1500}
VS_K = 8.0
RESTRICT = ("minutes restriction", "minute restriction", "minutes limit", "limited minutes", "minutes cap",
            "minute limit", "restricted minutes")
POS = ("G", "F", "C")


def _poss(rows: list[dict]) -> float:
    return sum(r.get("fga", 0) + 0.44 * r.get("fta", 0) - r.get("oreb", 0) + r.get("to", 0) for r in rows)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _shrink(raw: float, n: float, k: float) -> float:
    return 1.0 + (raw - 1.0) * (n / (n + k) if n > 0 else 0.0)


class FactorModel:
    def __init__(self, nm: NbaModel):
        self.nm = nm
        self._prof: dict[str, dict | None] = {}
        self._prev: dict[str, list] = {}
        self.league: dict | None = None

    # ------------------------------------------------------------ lagprofil (tempo, försvar per position)
    def profile(self, team: NbaTeam) -> dict | None:
        if team.team_id in self._prof:
            return self._prof[team.team_id]
        tid = team.team_id
        pace_w = pace_sum = 0.0
        allowed = {p: {"pm": 0.0, "min": 0.0, **{s: 0.0 for s in STATS}} for p in POS}
        for age, g in enumerate(team.games):
            bx = self.nm.box(g[1])
            if not bx or bx.get("v", 1) < 2 or tid not in bx["teams"]:
                continue
            mine = bx["teams"][tid]
            theirs = [r for k, rows in bx["teams"].items() if k != tid for r in rows]
            if not mine or not theirs:
                continue
            pace_g = (_poss(mine) + _poss(theirs)) / 2
            if pace_g < 70:          # orimligt (saknade fält) – hoppa
                continue
            w = 0.5 ** (age / self.nm.hl)
            pace_sum += w * pace_g
            pace_w += w
            for r in theirs:
                a = allowed.get(r.get("p") or "", None)
                if a is None:
                    continue
                a["pm"] += w * r["min"] * pace_g / 48.0      # "bollinnehav på plan" (viktat)
                a["min"] += r["min"]
                for s in STATS:
                    a[s] += w * r[s]
        prof = None
        if pace_w:
            prof = {"pace": pace_sum / pace_w, "allowed": allowed}
        self._prof[tid] = prof
        return prof

    def set_league(self, teams: list[NbaTeam]) -> dict | None:
        """Ligabaslinje = summan över skanningens lags profiler (motståndarna täcker en stor del av ligan)."""
        profs = [p for p in (self.profile(t) for t in teams if t) if p]
        if not profs:
            self.league = None
            return None
        lg = {"pace": sum(p["pace"] for p in profs) / len(profs), "allowed": {}}
        for pos in POS:
            pm = sum(p["allowed"][pos]["pm"] for p in profs)
            lg["allowed"][pos] = {s: (sum(p["allowed"][pos][s] for p in profs) / pm if pm else None) for s in STATS}
        pm_all = sum(p["allowed"][pos]["pm"] for p in profs for pos in POS)
        lg["all"] = {s: (sum(p["allowed"][pos][s] for p in profs for pos in POS) / pm_all if pm_all else None)
                     for s in STATS}
        self.league = lg
        return lg

    def pos_factor(self, opp: NbaTeam | None, pos: str, stat: str, relative: bool) -> float:
        lg, prof = self.league, (self.profile(opp) if opp else None)
        if not lg or not prof or pos not in POS:
            return 1.0
        a = prof["allowed"][pos]
        base = lg["allowed"][pos].get(stat)
        if not a["pm"] or not base:
            return 1.0
        raw = (a[stat] / a["pm"]) / base
        if relative:
            pm_all = sum(prof["allowed"][p]["pm"] for p in POS)
            tot = sum(prof["allowed"][p][stat] for p in POS)
            if pm_all and tot and lg["all"].get(stat):
                raw /= (tot / pm_all) / lg["all"][stat]
        return _clamp(_shrink(raw, a["min"], POS_K[stat]), 0.88, 1.12)

    # ------------------------------------------------------------ för analyssidan
    def abbrevs(self) -> dict[str, str]:
        """ESPN lag-id -> förkortning (BOS). Tom vid fel."""
        if not hasattr(self, "_abbr"):
            from .nba_model import ESPN
            self._abbr = {}
            try:
                raw = self.nm.c.get(f"{ESPN}/teams", ttl=7 * 86400) or {}
                for lg in ((raw.get("sports") or [{}])[0].get("leagues") or [{}]):
                    for t in lg.get("teams", []) or []:
                        t = t.get("team") or {}
                        if t.get("id"):
                            self._abbr[str(t["id"])] = t.get("abbreviation") or ""
            except Exception:  # noqa: BLE001 – bara visning; får aldrig stoppa prognosen
                self._abbr = {}
        return self._abbr

    def recent(self, team: NbaTeam, key: str, market: str, n: int = 10) -> list[dict]:
        """Senaste n matcherna (nyast först): datum, motståndare, hemma, minuter, värde för marknaden."""
        parts = COMBO.get(market, (market,))
        ab = self.abbrevs()
        return [{"ts": r["ts"], "mot": ab.get(r["opp"] or "", ""), "hemma": r["home"], "min": round(r["min"], 1),
                 "v": sum(r.get(p, 0.0) for p in parts)} for r in self.log(team, key, team.season_games)[:n]]

    def absent(self, team: NbaTeam) -> list[dict]:
        """Lagets spelare på skadelistan (minst 8 min/match i urvalet), mest speltid först."""
        inj = self.nm.injuries()
        out = [{"namn": p.name, "status": inj[k], "min": round(p.minutes, 1),
                "redan_borta": p.last_age >= 3} for k, p in team.players.items() if inj.get(k) and p.minutes >= 8]
        return sorted(out, key=lambda x: -x["min"])

    # ------------------------------------------------------------ spelarlogg (träffbild, mot motståndaren)
    def prev_vs(self, team: NbaTeam, opp_id: str) -> list:
        """Förra säsongens matcher mot motståndaren: [(ts, event_id, opp, hemma?)]."""
        if not team.season_year or not opp_id:
            return []
        key = f"{team.team_id}:{team.season_year - 1}"
        if key not in self._prev:
            from .nba_model import ESPN, SourceError, _ts
            out = []
            try:
                sched = self.nm.c.get(f"{ESPN}/teams/{team.team_id}/schedule",
                                      {"season": team.season_year - 1}, ttl=7 * 86400) or {}
            except SourceError:
                sched = {}
            for ev in sched.get("events", []) or []:
                comp = (ev.get("competitions") or [{}])[0]
                if not ((comp.get("status") or {}).get("type") or {}).get("completed"):
                    continue
                o, h = None, None
                for x in comp.get("competitors", []) or []:
                    xid = str(x.get("id") or (x.get("team") or {}).get("id") or "")
                    if xid == team.team_id:
                        h = x.get("homeAway") == "home"
                    elif xid:
                        o = xid
                try:
                    out.append((_ts(ev["date"]), str(ev["id"]), o, h))
                except (KeyError, ValueError):
                    pass
            self._prev[key] = out
        return [g for g in self._prev[key] if g[2] == opp_id]

    def log(self, team: NbaTeam, key: str, games: list) -> list[dict]:
        """Spelarens rader i lagets matcher (nyast först): {ts, opp, home, min, stats...}."""
        out = []
        for ts, eid, opp, home in games:
            bx = self.nm.box(eid)
            if not bx:
                continue
            row = next((r for r in bx["teams"].get(team.team_id, []) if name_key(r["n"]) == key), None)
            if row:
                out.append({"ts": ts, "opp": opp, "home": home, **row})
        return sorted(out, key=lambda r: -r["ts"])

    def hit_rates(self, team: NbaTeam, key: str, market: str, line: float, opp_id: str | None,
                  is_home: bool | None) -> dict:
        parts = COMBO.get(market, (market,))
        season = self.log(team, key, team.season_games)
        vs = [r for r in season if r["opp"] == opp_id] + (self.log(team, key, self.prev_vs(team, opp_id))
                                                          if opp_id else [])

        def rate(rows):
            vals = [sum(r.get(p, 0.0) for p in parts) for r in rows]
            return (round(sum(v > line for v in vals) / len(vals), 3), len(vals)) if vals else (None, 0)

        out = {}
        for name, rows in (("l5", season[:5]), ("l10", season[:10]), ("sasong", season), ("mot", vs),
                           ("hemmaborta", [r for r in season if r["home"] == is_home] if is_home is not None else [])):
            out[f"traff_{name}"], out[f"traff_{name}_n"] = rate(rows)
        return out

    def vs_factor(self, team: NbaTeam, key: str, opp_id: str | None, per_min: dict) -> tuple[dict, int]:
        if not opp_id:
            return {}, 0
        rows = [r for r in self.log(team, key, team.season_games) if r["opp"] == opp_id] \
            + self.log(team, key, self.prev_vs(team, opp_id))
        mins = sum(r["min"] for r in rows)
        if not rows or mins < 10:
            return {}, len(rows)
        out = {}
        for s in ("points", "rebounds", "assists", "threes"):
            if per_min.get(s):
                raw = (sum(r[s] for r in rows) / mins) / per_min[s]
                out[s] = _clamp(_shrink(raw, len(rows), VS_K), 0.92, 1.08)
        return out, len(rows)

    # ------------------------------------------------------------ prognos
    def expected(self, team: NbaTeam, opp: NbaTeam | None, start: float, is_home: bool | None,
                 total: float | None = None, spread_home: float | None = None) -> dict[str, dict]:
        nm = self.nm
        inj = nm.injuries()
        st = {k: inj.get(k, "") for k in team.players}
        out_keys = {k for k in team.players if any(s in st[k] for s in OUT_STATUS)}
        healthy = {k: p for k, p in team.players.items() if k not in out_keys and p.minutes >= 8}
        if not healthy:
            return {}

        # 1. speltid: frånvarandes minuter till samma position och rotationen
        miss_min = {p: 0.0 for p in POS + ("",)}
        miss_prod = {s: 0.0 for s in STATS}
        for k in out_keys:
            p = team.players[k]
            if p.last_age >= 3:
                continue
            m = p.minutes * p.presence
            miss_min[p.pos if p.pos in POS else ""] += m
            for s in STATS:
                miss_prod[s] += m * p.per_min[s]
        mins = {k: p.minutes for k, p in healthy.items()}
        for pos, m in miss_min.items():
            if m <= 0:
                continue
            w = {k: p.minutes * (1.6 if pos and p.pos == pos else 1.0) * (1.0 if p.minutes >= 15 else 0.6)
                 for k, p in healthy.items()}
            ws = sum(w.values()) or 1.0
            for k in healthy:
                mins[k] += 0.85 * m * w[k] / ws
        regained = {s: sum((mins[k] - p.minutes) * p.per_min[s] for k, p in healthy.items()) for s in STATS}
        # Lagets minuter: minuterna ovan gäller OM spelaren spelar. Vägt med sannolikheten att han spelar
        # (spelade senaste matchen -> 1, annars hur ofta han spelat) ska laget landa på ~241 min (inkl. förlängning).
        # Skillnaden tas mest från/ges mest till bänken: vikt = minuter × utrymme kvar till 48 (en stjärna på 36 min
        # är stabil, rotationen absorberar), högst −25 % / +10 % per spelare.
        others = {k: p for k, p in team.players.items() if k not in out_keys and k not in healthy}
        for k, p in others.items():
            mins[k] = p.minutes
        allp = {**healthy, **others}
        q = {k: (1.0 if p.last_age == 0 else p.presence) for k, p in allp.items()}
        team_min = sum(q[k] * mins[k] for k in allp)
        wq = {k: mins[k] * max(0.0, 48.0 - mins[k]) / 48.0 for k in allp}
        den = sum(q[k] * wq[k] for k in allp)
        if team_min and den:
            c = (241.0 - team_min) / den
            for k in allp:
                mins[k] = _clamp(mins[k] + c * wq[k], 0.75 * mins[k], 1.10 * mins[k])
        scale = (sum(q[k] * mins[k] for k in allp) / team_min) if team_min else 1.0

        # 2. användning: halva den produktion som inte täcks av extra minuter
        out_pos = {team.players[k].pos for k in out_keys if team.players[k].last_age < 3}
        usage = {k: {s: 1.0 for s in STATS} for k in healthy}
        for s in STATS:
            gap = max(0.0, miss_prod[s] - regained[s])
            if gap <= 0:
                continue
            w = {k: mins[k] * p.per_min[s] * (1.4 if p.pos in out_pos else 1.0) for k, p in healthy.items()}
            ws = sum(w.values())
            if not ws:
                continue
            for k, p in healthy.items():
                base = mins[k] * p.per_min[s]
                if base > 0:
                    usage[k][s] = min(1.25, 1.0 + 0.5 * gap * w[k] / ws / base)

        # 3. schema, tillbakakomst, minutbegränsning, status
        b2b = team.last_game is not None and start - team.last_game < 30 * 3600
        three_in_four = sum(1 for g in team.season_games if start - 4 * 86400 < g[0] < start) >= 2
        flags = {}
        sd_mult = {}
        for k, p in healthy.items():
            f = 1.0
            if b2b:
                f *= 0.97 if p.minutes >= 28 else 0.99
            if three_in_four:
                f *= 0.985
            com = nm.injury_comment(k)
            restricted = any(x in com for x in RESTRICT)
            returning = p.last_age >= 2
            sd_mult[k] = 1.0
            if restricted:
                f *= 0.72
                sd_mult[k] = 1.3
            elif returning:
                f *= 0.88
                sd_mult[k] = 1.25
            if "questionable" in st[k] or "day-to-day" in st[k]:
                f *= 0.9
            mins[k] = min(42.0, mins[k] * f)
            flags[k] = {"minutbegransning": restricted, "tillbaka": returning and not restricted}

        # 4. matchmiljö: lagets väntade poäng (marknaden) mot modellens summa
        proj_pts = (sum(q[k] * mins[k] * p.per_min["points"] * usage[k]["points"] for k, p in healthy.items())
                    + sum(q[k] * mins[k] * p.per_min["points"] for k, p in others.items()))
        if total is not None and spread_home is not None and is_home is not None:
            implied = (total - spread_home) / 2 if is_home else (total + spread_home) / 2
            env_src = "pinnacle"
        else:
            implied = ((team.scored + (opp.allowed if opp else team.scored)) / 2
                       + (1.2 if is_home else -1.2 if is_home is False else 0.0))
            env_src = "snitt"
        env = _clamp(1.0 + 0.8 * (implied / proj_pts - 1.0), 0.85, 1.15) if proj_pts else 1.0

        prof_t, prof_o = self.profile(team), (self.profile(opp) if opp else None)
        lg = self.league
        pace_ratio = (prof_o["pace"] / lg["pace"]) if prof_o and lg and lg["pace"] else 1.0
        pace_ratio = _clamp(pace_ratio, 0.92, 1.08)
        opp_id = opp.team_id if opp else None

        res = {}
        for k, p in healthy.items():
            vs, n_vs = self.vs_factor(team, k, opp_id, p.per_min)
            e, fac = {}, {}
            for s in STATS:
                f_env = env ** ENV_ELASTICITY[s] if s in ENV_ELASTICITY else 1.0
                f_pace = pace_ratio ** PACE_ELASTICITY[s] if s in PACE_ELASTICITY else 1.0
                f_pos = self.pos_factor(opp, p.pos, s, relative=s in ENV_ELASTICITY)
                f_vs = vs.get(s, 1.0)
                e[s] = mins[k] * p.per_min[s] * usage[k][s] * f_env * f_pace * f_pos * f_vs
                fac[s] = {"anv": usage[k][s], "miljo": f_env, "tempo": f_pace, "pos": f_pos, "mot": f_vs}
            for c, parts in COMBO.items():
                e[c] = sum(e[x] for x in parts)
            e["_min"] = mins[k]
            e["_min_sd"] = p.min_sd * sd_mult[k]
            e["_g"] = p.games
            e["_f"] = {"stat": fac, "minuter_bas": round(p.minutes, 1), "pos": p.pos, "b2b": b2b,
                       "lagminuter_skala": round(scale, 3),
                       "tre_pa_fyra": three_in_four, "miljo_kalla": env_src, "lag_vantade_poang": round(implied, 1),
                       "mot_n": n_vs, **flags[k]}
            res[k] = e
        return res


def factor_summary(e: dict, market: str) -> dict:
    """Platta fält för bokföringen (ett tal per faktor; kombinationer = produktviktat snitt)."""
    f = e.get("_f") or {}
    parts = COMBO.get(market, (market,))
    out = {}
    for name in ("anv", "miljo", "tempo", "pos", "mot"):
        num = sum(e.get(p, 0.0) * f["stat"][p][name] for p in parts if p in f.get("stat", {}))
        den = sum(e.get(p, 0.0) for p in parts)
        out[f"f_{name}"] = round(num / den, 3) if den else None
    out.update(f_minuter_bas=f.get("minuter_bas"), f_b2b=f.get("b2b"), f_tre_pa_fyra=f.get("tre_pa_fyra"),
               f_minutbegransning=f.get("minutbegransning"), f_tillbaka=f.get("tillbaka"),
               f_miljo_kalla=f.get("miljo_kalla"), f_lag_poang=f.get("lag_vantade_poang"), f_mot_n=f.get("mot_n"))
    return out
