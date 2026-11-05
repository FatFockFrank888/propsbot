"""Power-play model for the NHL power-play points test market.

Expected PP points tonight = (player's PP points per PP minute)
                           x (team's expected PP minutes tonight)
                           x (player's share of the team's PP time, from his PP unit)
                           x (opponent penalty kill factor) x (opponent PK reshuffle factor)

Sources (all free, no key):
  * DailyFaceoff line combinations (dailyfaceoff.com/teams/<slug>/line-combinations): projected PP1/PP2,
    PK1/PK2 and injured/out players per team. DailyFaceoff aggregates beat reporters' X posts and the
    morning skate, so a player moved up to PP1 shows here hours before the game.
  * NHL stats API: per-game PP time on ice per player (skater/timeonice), PP points and PP time per
    season (skater/powerplay), team PP time / PK time / PP goals against (team/powerplay, team/penaltykill).

The edge we are after:
  * "moved up": DailyFaceoff has him on PP1 but his recent PP share is PP2-ish -> the market still prices
    his old role. The reverse ("moved down") lowers the expectation.
  * "PK reshuffled": the opponent's regular penalty killers (by recent short-handed TOI) are out or no
    longer on its projected PK units -> the PK is weaker than its season numbers.
Everything degrades gracefully: if a source fails the model falls back to the old per-game rate.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .names import normalize_name

log = logging.getLogger(__name__)

STATS = "https://api.nhle.com/stats/rest/en"
DFO = "https://www.dailyfaceoff.com/teams/{slug}/line-combinations"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# Share of the team's PP time by projected unit (league-typical: PP1 ~60 %, PP2 ~35 %).
UNIT_SHARE = {1: 0.60, 2: 0.33, None: 0.03}
PP1_SHARE_MIN = 0.45            # recent share above this = he has been a PP1 player
PRIOR_PTS_PER_60 = {"F": 4.5, "D": 3.5}
PRIOR_MIN = 60.0                # prior worth 60 PP minutes
PREV_SEASON_WEIGHT = 0.5
TEAM_PRIOR_GAMES = 10.0
RECENT_GAMES = 5
PK_RESHUFFLE_MAX = 0.12         # at most +12 % PP conversion when the opponent's PK is reshuffled


@dataclass
class PPInfo:
    mu: float
    unit: int | None = None
    recent_share: float | None = None
    share: float = 0.0
    exp_pp_min: float = 0.0
    pts_per_60: float = 0.0
    opp_pk_factor: float = 1.0
    pk_missing: list[str] = field(default_factory=list)
    pk_factor: float = 1.0
    moved: str = ""              # "upp till PP1" / "ner från PP1" / ""
    out: bool = False
    source: str = ""

    def text(self) -> str:
        unit = f"PP{self.unit}" if self.unit else "ingen PP-enhet"
        parts = [f"{unit} ({self.source or 'DFO'})", f"{self.exp_pp_min * self.share:.1f} PP-min väntat",
                 f"{self.pts_per_60:.1f} PP-poäng/60", f"motst. PK x{self.opp_pk_factor:.2f}"]
        if self.moved:
            parts.insert(1, f"flyttad {self.moved}")
        if self.pk_missing:
            parts.append(f"motst. PK omgjord (saknar {', '.join(self.pk_missing)}) x{self.pk_factor:.2f}")
        return "; ".join(parts)


def _get_text(url: str, cache: Path, ttl: float) -> str:
    p = cache / ("dfo_" + hashlib.sha1(url.encode()).hexdigest()[:20] + ".html")
    if p.exists() and time.time() - p.stat().st_mtime < ttl:
        return p.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8", "replace")
    p.write_text(body, encoding="utf-8")
    return body


def parse_dfo(html: str) -> dict[str, Any] | None:
    """{"players": {norm name: {"pp": 1|2|None, "pk": 1|2|None, "out": bool}}, "updated", "source"}."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    c = (json.loads(m.group(1)).get("props", {}).get("pageProps", {}) or {}).get("combinations") or {}
    players: dict[str, dict[str, Any]] = {}
    for p in c.get("players", []) or []:
        name = normalize_name(p.get("name") or "")
        if not name:
            continue
        d = players.setdefault(name, {"pp": None, "pk": None, "out": False, "lineup": False})
        cat, grp = p.get("categoryIdentifier"), p.get("groupIdentifier") or ""
        if cat == "pp" and grp in ("pp1", "pp2"):
            d["pp"] = int(grp[-1])
        elif cat == "pk" and grp in ("pk1", "pk2"):
            d["pk"] = int(grp[-1])
        elif cat == "oi" or p.get("injuryStatus") in ("ir", "out", "ltir", "dtd-out"):
            d["out"] = True
        elif cat == "ev":
            d["lineup"] = True
    return {"players": players, "updated": c.get("updatedAt"), "source": (c.get("sourceName") or "").strip()}


class PPContext:
    """Built once per scan; every source is cached and every failure is swallowed."""

    def __init__(self, client, nhl, cache_dir: Path) -> None:
        self.client = client
        self.nhl = nhl
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self._dfo: dict[str, Any] = {}
        self._toi: dict[tuple[str, str], list[dict]] = {}
        self._season: dict[str, dict[int, dict]] = {}
        self._team: dict[str, dict[str, dict]] = {}
        self._slugs: dict[str, str] | None = None
        self.errors: list[str] = []

    # ------------------------------------------------------------------ news
    def player_status(self, team: str, name: str) -> tuple[str | None, str]:
        """("ute" | "inte i laget" | "spelar" | None, källa) from DailyFaceoff. None = unknown (no data)."""
        d = self.dfo(team)
        if not d or not d.get("players"):
            return None, ""
        src = f"DailyFaceoff {d.get('source') or ''}".strip()
        n_lineup = sum(1 for v in d["players"].values() if v.get("lineup"))
        me = d["players"].get(normalize_name(name))
        if me is not None and me.get("out"):
            return "ute", src
        fresh = not (d.get("source") or "").lower().startswith("last game")   # a real projection, not last game
        if fresh and n_lineup >= 16 and (me is None or not me.get("lineup")):
            return "inte i laget", src
        return ("spelar" if me is not None else None), src

    # ------------------------------------------------------------------ sources
    def _stats(self, report: str, cay: str, ttl: float, game: bool = False) -> list[dict]:
        data, _ = self.client.get(f"{STATS}/{report}", {
            "isAggregate": "false", "isGame": "true" if game else "false", "start": 0, "limit": -1,
            "cayenneExp": cay}, ttl=ttl)
        return data.get("data", []) or []

    def slug(self, abbrev: str) -> str | None:
        if self._slugs is None:
            self._slugs = {}
            for _tid, (tri, full) in self.nhl.teams().items():
                self._slugs[tri] = re.sub(r"[^a-z0-9]+", "-", full.lower().replace("é", "e").replace(".", "")).strip("-")
        return self._slugs.get(abbrev)

    def dfo(self, abbrev: str) -> dict[str, Any] | None:
        if abbrev not in self._dfo:
            self._dfo[abbrev] = None
            slug = self.slug(abbrev)
            if slug:
                try:
                    self._dfo[abbrev] = parse_dfo(_get_text(DFO.format(slug=slug), self.cache, 20 * 60))
                except Exception as exc:  # noqa: BLE001
                    self.errors.append(f"DailyFaceoff {abbrev}: {exc}")
        return self._dfo[abbrev]

    def team_toi(self, abbrev: str, season: str) -> list[dict]:
        """Per-game PP/SH time on ice for every skater of a team this season."""
        k = (abbrev, season)
        if k not in self._toi:
            try:
                self._toi[k] = self._stats("skater/timeonice",
                                           f"seasonId={season} and gameTypeId=2 and teamAbbrev='{abbrev}'", 3 * 3600, game=True)
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"PP-tid {abbrev}: {exc}")
                self._toi[k] = []
        return self._toi[k]

    def season_pp(self, season: str) -> dict[int, dict]:
        if season not in self._season:
            try:
                rows = self._stats("skater/powerplay", f"seasonId={season} and gameTypeId=2", 6 * 3600)
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"PP-statistik {season}: {exc}")
                rows = []
            out: dict[int, dict] = {}
            for r in rows:   # a traded player has one row per team: sum them
                d = out.setdefault(int(r["playerId"]), {"pts": 0.0, "toi": 0.0})
                d["pts"] += float(r.get("ppPoints") or 0)
                d["toi"] += float(r.get("ppTimeOnIce") or 0)
            self._season[season] = out
        return self._season[season]

    def teams(self, season: str) -> dict[str, dict]:
        """tri-code -> {"pp_toi", "pk_toi", "ppga", "gp"} per game (seconds / goals)."""
        if season not in self._team:
            out: dict[str, dict] = {}
            try:
                name_to_tri = {full: tri for tri, full in self.nhl.teams().values()}
                cay = f"seasonId={season} and gameTypeId=2"
                for r in self._stats("team/powerplay", cay, 6 * 3600):
                    tri = name_to_tri.get(r.get("teamFullName"))
                    if tri:
                        out.setdefault(tri, {})["pp_toi"] = float(r.get("ppTimeOnIcePerGame") or 0)
                        out[tri]["gp"] = float(r.get("gamesPlayed") or 0)
                for r in self._stats("team/penaltykill", cay, 6 * 3600):
                    tri = name_to_tri.get(r.get("teamFullName"))
                    if tri:
                        d = out.setdefault(tri, {})
                        d["pk_toi"] = float(r.get("pkTimeOnIcePerGame") or 0)
                        d["ppga"] = float(r.get("ppGoalsAgainstPerGame") or 0)
                        d.setdefault("gp", float(r.get("gamesPlayed") or 0))
            except Exception as exc:  # noqa: BLE001
                self.errors.append(f"lagens PP/PK: {exc}")
            self._team[season] = out
        return self._team[season]

    # -------------------------------------------------------------------- model
    def expected(self, proj, game, prev_season: str) -> PPInfo | None:
        """Expected PP points for one skater in one game, or None (fall back to the old rate)."""
        sk = proj.skater
        team = sk.team
        opp = game.away if team == game.home else game.home
        teams = self.teams(game.season)
        if team not in teams or opp not in teams:
            return None
        lg = list(teams.values())
        avg = lambda k: sum(t.get(k, 0) for t in lg) / max(1, len(lg))
        lg_pp, lg_pk, lg_ga = avg("pp_toi"), avg("pk_toi"), avg("ppga")
        if lg_pp <= 0 or lg_pk <= 0:
            return None

        def shrunk(val: float, lg_val: float, gp: float) -> float:
            w = gp / (gp + TEAM_PRIOR_GAMES)
            return (w * val + (1 - w) * lg_val) / lg_val

        t, o = teams[team], teams[opp]
        # team PP minutes tonight: own ability to draw penalties x opponent's tendency to take them
        exp_pp_sec = lg_pp * math.sqrt(shrunk(t.get("pp_toi", lg_pp), lg_pp, t.get("gp", 0))
                                       * shrunk(o.get("pk_toi", lg_pk), lg_pk, o.get("gp", 0)))
        # opponent PK quality: PP goals against per PK minute vs league
        o_rate = o.get("ppga", lg_ga) / max(1.0, o.get("pk_toi", lg_pk))
        lg_rate = lg_ga / lg_pk
        w = o.get("gp", 0) / (o.get("gp", 0) + TEAM_PRIOR_GAMES)
        opp_pk = (w * o_rate + (1 - w) * lg_rate) / lg_rate if lg_rate > 0 else 1.0
        opp_pk = min(1.35, max(0.7, opp_pk))

        # player's recent share of the team's PP time
        rows = [r for r in self.team_toi(team, game.season) if int(r.get("playerId", 0)) == sk.player_id
                and str(r.get("gameDate", "")) < game.game_date.isoformat()]
        rows.sort(key=lambda r: r.get("gameDate", ""), reverse=True)
        recent = rows[:RECENT_GAMES]
        team_pp_recent = t.get("pp_toi", lg_pp)
        recent_share = (sum(float(r.get("ppTimeOnIce") or 0) for r in recent) / len(recent) / team_pp_recent
                        if recent and team_pp_recent > 0 else None)
        if recent_share is not None:
            recent_share = min(0.85, recent_share)

        info = PPInfo(mu=0.0, recent_share=recent_share, exp_pp_min=exp_pp_sec / 60, opp_pk_factor=opp_pk)
        d = self.dfo(team)
        me = (d or {}).get("players", {}).get(normalize_name(sk.name)) if d else None
        if d and d.get("players"):
            info.source = f"DailyFaceoff {d.get('source') or ''}".strip()
            if me is not None and me.get("out"):
                info.out = True
                return info
            info.unit = me.get("pp") if me else None
            base = UNIT_SHARE[info.unit]
            if recent_share is None:
                share = base
            else:
                was_pp1 = recent_share >= PP1_SHARE_MIN
                if info.unit == 1 and not was_pp1:
                    info.moved = "upp till PP1"
                elif info.unit != 1 and was_pp1:
                    info.moved = "ner från PP1"
                wt = 0.8 if info.moved else 0.5     # a role change: trust the new unit
                share = wt * base + (1 - wt) * recent_share
        else:
            info.source = "senaste matchernas PP-tid"
            if recent_share is None:
                return None
            share = recent_share
        info.share = share

        # PP points per PP minute: this season + half of last season, shrunk toward a position prior
        cur = self.season_pp(game.season).get(sk.player_id, {"pts": 0.0, "toi": 0.0})
        prev = self.season_pp(prev_season).get(sk.player_id, {"pts": 0.0, "toi": 0.0})
        prior = PRIOR_PTS_PER_60.get(sk.position, 4.0)
        pts = cur["pts"] + PREV_SEASON_WEIGHT * prev["pts"] + prior * PRIOR_MIN / 60
        mins = cur["toi"] / 60 + PREV_SEASON_WEIGHT * prev["toi"] / 60 + PRIOR_MIN
        info.pts_per_60 = 60 * pts / mins

        # opponent PK reshuffle: its regular penalty killers (recent SH time) out / off the PK units
        info.pk_factor = 1.0
        od = self.dfo(opp)
        if od and od.get("players"):
            orows = [r for r in self.team_toi(opp, game.season) if str(r.get("gameDate", "")) < game.game_date.isoformat()]
            dates = sorted({r.get("gameDate") for r in orows}, reverse=True)[:RECENT_GAMES]
            sh: dict[str, float] = {}
            names: dict[str, str] = {}
            for r in orows:
                if r.get("gameDate") in dates:
                    n = normalize_name(r.get("skaterFullName") or "")
                    sh[n] = sh.get(n, 0.0) + float(r.get("shTimeOnIce") or 0)
                    names[n] = r.get("skaterFullName") or n
            total = sum(sh.values())
            if total > 0:
                top = sorted(sh, key=sh.get, reverse=True)[:4]          # the regular PK1 + PK2 core
                # missing = out, not in tonight's lineup, or no longer on PK1/PK2
                missing = [n for n in top if n not in od["players"] or od["players"][n].get("out")
                           or od["players"][n].get("pk") is None]
                share_missing = sum(sh[n] for n in missing) / total
                if missing:
                    info.pk_missing = [names[n].split()[-1] for n in missing]
                    info.pk_factor = 1 + min(PK_RESHUFFLE_MAX, 0.25 * share_missing)
        info.mu = (info.pts_per_60 / 60) * info.exp_pp_min * share * opp_pk * info.pk_factor
        return info
