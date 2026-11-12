"""Lagnyheter vid varje skanning: skador, avstängningar och laguppställningar.

* NBA: ESPN:s skadelista (out / doubtful / questionable / day-to-day), uppdateras löpande under dagen.
* Fotboll: startelvorna (ESPN, ca 1 h före avspark) – lineups.py.

Två saker görs:
1. block_*(): inga nya spel på en spelare som är ute / tveksam (out, doubtful) eller inte i startelvan.
2. recheck(): varje öppet LIVE-spel före start kontrolleras igen. Ändras spelarens status skickas EN notis
   (och statusen sparas på spelet: "nyhet", "nyhet_status", "nyhet_ts", syns på webbsidan).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

ESPN_NBA = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
BAD = ("out", "doubtful", "suspension", "suspended")
WARN = ("questionable", "day-to-day", "game time decision", "gtd")


def nba_injuries(client) -> dict[str, str]:
    """name_key -> status (gemener). Tom vid fel."""
    from .nba_model import name_key
    try:
        raw = client.get(f"{ESPN_NBA}/injuries", ttl=600) or {}
    except Exception:  # noqa: BLE001 - nyheter får aldrig stoppa skanningen
        return {}
    out = {}
    for team in raw.get("injuries", []) or []:
        for inj in team.get("injuries", []) or []:
            name = (inj.get("athlete") or {}).get("displayName", "")
            status = (inj.get("status") or (inj.get("type") or {}).get("description") or "").lower()
            if name:
                out[name_key(name)] = status
    return out


def nba_status(injuries: dict[str, str], player: str) -> str | None:
    from .nba_model import name_key, same_person
    k = name_key(player or "")
    st = injuries.get(k)
    if st is None:
        st = next((v for kk, v in injuries.items() if same_person(kk, k)), None)
    return st


def block_nba(rows, injuries: dict[str, str]) -> tuple[int, int]:
    """Stoppa spelbara ben på spelare som är out/doubtful; markera questionable. Returnerar (stoppade, varnade)."""
    from .clv_signal import _block
    n_block = n_warn = 0
    for r in rows:
        d = r.row.decision
        if not d.playable:
            continue
        st = nba_status(injuries, d.cand.player_name)
        if not st:
            continue
        if any(x in st for x in BAD):
            _block(d, f"skadelista: {st} (ESPN)")
            n_block += 1
        elif any(x in st for x in WARN):
            d.reasons.append(f"skadelista: {st} (ESPN) – kolla före start")
            n_warn += 1
    return n_block, n_warn


def recheck(ledger, status_fn, settings: dict, sport: str, notify: bool, log, field: str = "nyhet") -> int:
    """status_fn(bet) -> (nyckel, text) eller None (okänt). nyckel "ok" = spelar som vanligt.
    Skickar en notis när statusen ändras för ett öppet spel före start. Returnerar antal ändringar."""
    from .notify import send
    now = time.time()
    n = 0
    for b in ledger.bets:
        if b.get("status") != "öppen" or not b.get("avspark") or b["avspark"] <= now or b.get("dubblett"):
            continue
        try:
            res = status_fn(b)
        except Exception:  # noqa: BLE001
            continue
        if res is None:
            continue
        key, text = res
        prev = b.get(f"{field}_status")
        if key == prev or (key == "ok" and prev is None):
            continue
        b[f"{field}_status"] = key
        b[field] = text
        b[f"{field}_ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if field != "nyhet":            # webbsidan visar "nyhet": senaste nyheten oavsett slag
            b["nyhet"], b["nyhet_status"] = text, ("ok" if key == "ok" else key)
        n += 1
        log(f"LAGNYHET {sport}: {text} (förut: {prev or 'okänd'})")
        if notify and settings.get("ntfy_topic"):
            bad = key != "ok"
            spel = b.get("spel_text") or f"{b.get('marknad')} {'under' if b.get('sida') == 'under' else 'över'} {b.get('linje')}"
            send(settings["ntfy_topic"], f"NYHET {sport}: {b.get('spelare')}" + (" – kolla spelet" if bad else " – klar"),
                 f"{text}.\nDitt spel: {spel} @ {b.get('odds', 0):.2f} ({b.get('bolag')}), {b.get('match')}."
                 + ("\nSpelar han inte blir spelet normalt struket (void)." if bad else ""),
                 priority=5 if bad else 3, tags="rotating_light" if bad else "white_check_mark")
    return n


def nba_status_fn(injuries: dict[str, str]):
    def fn(b):
        st = nba_status(injuries, b.get("spelare"))
        if not st:
            return ("ok", f"{b.get('spelare')} inte längre på skadelistan (ESPN)")
        if any(x in st for x in BAD + WARN):
            return (st, f"{b.get('spelare')}: {st} enligt ESPN:s skadelista")
        return None
    return fn


def football_status_fn(lineups, settings: dict):
    """Startelvan (ESPN): inte i startelvan -> larm; i startelvan -> ok (bara om vi larmat förut)."""
    def fn(b):
        mtk = (b["avspark"] - time.time()) / 60
        if mtk > settings.get("lineup_lookup_minutes", 150):
            return None
        lu = lineups.get(b["match_id"], b.get("hemma"), b.get("borta"), b["avspark"])
        if lu is None or not lu.published:
            return None
        starts = lu.starts(b.get("spelare") or "")
        if starts is False:
            return ("bänk", f"{b.get('spelare')} är inte i startelvan")
        if starts:
            return ("ok", f"{b.get('spelare')} startar")
        return None
    return fn


# ------------------------------------------------------------------ lagkamrater (NBA)
def nba_injury_list(client) -> list[dict]:
    """[{key, name, team, status, ts}] från ESPN:s skadelista (ts = när statusen senast ändrades)."""
    from .nba_model import name_key
    try:
        raw = client.get(f"{ESPN_NBA}/injuries", ttl=600) or {}
    except Exception:  # noqa: BLE001
        return []
    out = []
    for team in raw.get("injuries", []) or []:
        for inj in team.get("injuries", []) or []:
            name = (inj.get("athlete") or {}).get("displayName", "")
            try:
                ts = datetime.fromisoformat((inj.get("date") or "").replace("Z", "+00:00")).timestamp()
            except ValueError:
                ts = 0.0
            if name:
                out.append({"key": name_key(name), "name": name, "team": team.get("displayName", ""),
                            "status": (inj.get("status") or "").lower(), "ts": ts})
    return out


def nba_teammate_fn(last: dict, injuries: list[dict], nb_r: dict, min_minutes: float = 15.0):
    """En lagkamrat med minst 15 min/match blir out/doubtful EFTER att spelet lades -> rollförändring.
    Notisen visar modellens nya förväntan för vår spelare (speltid och väntat värde) och edge vid vårt odds."""
    from .nba_model import match_model_player
    from .player_model import nb_over

    def fn(b):
        models, teams = last.get("models") or {}, last.get("teams") or {}
        m, pair = models.get(b.get("match_id")), teams.get(b.get("match_id"))
        if not m or not pair:
            return None
        k = match_model_player(m, b.get("spelare_id") or "")
        if not k:
            return None
        team = next((t for t in pair if t and k in t.players), None)
        if team is None:
            return None
        booked = (b.get("bokford") or 0) + 600
        new_out = [i for i in injuries if i["team"] == team.name and i["key"] != k and i["ts"] > booked
                   and any(x in i["status"] for x in BAD)
                   and (team.players.get(i["key"]) is not None and team.players[i["key"]].minutes >= min_minutes)]
        if not new_out:
            return None
        mk, line = b.get("marknad"), b.get("linje")
        mu = (m.get(k) or {}).get(mk)
        mins = (m.get(k) or {}).get("_min")
        who = ", ".join(f"{i['name']} ({i['status']})" for i in new_out)
        text = f"Lagkamrat ute: {who}."
        if mu is not None and line is not None:
            p = nb_over(mu, line, nb_r.get(mk, 15))
            if b.get("sida") == "under":
                p = 1 - p
            edge = p * b.get("odds", 0) - 1
            text += (f" Modellen nu: {b.get('spelare')} väntat {mu:.1f} ({mins:.0f} min), "
                     f"{'under' if b.get('sida') == 'under' else 'över'} {line:g} {p:.0%}, edge vid {b.get('odds', 0):.2f}: {edge:+.0%}"
                     + (f" (vid bokning modell {b['modell_edge']:+.0%})" if b.get("modell_edge") is not None else ""))
        return ("lag:" + ",".join(sorted(i["key"] for i in new_out)), text)
    return fn
