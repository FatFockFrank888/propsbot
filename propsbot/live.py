"""LIVE: de hårt sållade spelen som faktiskt spelas (notis + egen bokföring nba_live.json).

Allt annat bokförs som förut (Spel/Skugga/Modelltest) för att samla data – men bara
LIVE-spelen skickas som notis. Kraven bygger på 509 unika avgjorda NBA-spel (3/11):

  * edge 5–15 % på poäng, returer, assist och trepoängare (live_min_edge / live_max_edge).
    Marknader som saknas i listan (steals, blocks, PRA …) spelas inte live – för lite data.
    Ändrat 4/11 efter ~400 avgjorda spel: edge över 15 % slog inte stängningen, och poängkravet
    10 % gav inte bättre CLV än 5 % när modellen höll med.
  * modellen måste hålla med: modelltestets edge på samma linje ≥ live_model_min_edge (5 %)
  * minst två oberoende jämförelsekällor (Pinnacle, Kalshi, DK/FD …)
  * odds live_odds_window (1,40–3,00)
  * alla vanliga spärrar (oddsfall, sharp money mot oss, ett spel per spelare) gäller redan
  * riskkontroll: högst live_max_units per spel, live_max_per_match spel per match,
    live_max_per_day spel och live_max_units_day units per matchdag (amerikansk tid).
    Bästa edge först; resten bokförs inte live.
"""
from __future__ import annotations

import time

from .clv_signal import units

UNIT = 0.002


def _us_day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts - 6 * 3600))


def _key(c) -> tuple:
    return (c.match_id, c.player_id, c.market, c.line, c.best.side)


def select_live(rows, model_rows, settings: dict, live_ledger) -> list:
    th = settings.get("live_min_edge", {"points": 0.10, "threes": 0.06, "assists": 0.06, "rebounds": 0.06})
    lo, hi = settings.get("live_odds_window", [1.40, 3.00])
    m_min = settings.get("live_model_min_edge", 0.05)
    max_edge = settings.get("live_max_edge", 0.15)
    min_groups = settings.get("live_min_groups", 2)
    max_u = settings.get("live_max_units", 5)
    per_match = settings.get("live_max_per_match", 2)
    per_day = settings.get("live_max_per_day", 8)
    u_day = settings.get("live_max_units_day", 25)

    model_edge = {}
    for r in model_rows or []:
        c = r.row.decision.cand
        model_edge[_key(c)] = max(model_edge.get(_key(c), -1.0), c.edge)

    blocked = set(settings.get("live_blocked_markets") or [])
    cands = []
    for r in rows:
        d = r.row.decision
        c = d.cand
        if not (d.playable and d.show) or c.market in blocked:
            continue
        need = th.get(c.market)
        if need is None or c.edge < need or c.edge > max_edge or not (lo <= c.best.odds <= hi):
            continue
        if (r.n_groups or 0) < min_groups:
            continue
        me = model_edge.get(_key(c))
        if me is None or me < m_min:
            continue
        r.live_model_edge = me
        cands.append(r)
    cands.sort(key=lambda r: -r.row.decision.cand.edge)

    # det som redan är bokfört live räknas in i taken
    from collections import Counter
    n_day, u_used, n_match = Counter(), Counter(), Counter()
    have = set()
    for b in live_ledger.bets:
        day = _us_day(b.get("avspark") or b["bokford"])
        n_day[day] += 1
        u_used[day] += units(b.get("insats_pct") or 0)
        n_match[b["match_id"]] += 1
        have.add(b["key"])
    from .ledger import bet_key
    out = []
    for r in cands:
        d, c = r.row.decision, r.row.decision.cand
        if bet_key(r) in have:
            out.append(r)                    # redan live – behåll (för stängningsodds)
            continue
        day = _us_day(c.now + c.minutes_to_kickoff * 60)
        u = min(max_u, max(1, units(d.stake)))
        if n_match[c.match_id] >= per_match or n_day[day] >= per_day or u_used[day] + u > u_day:
            continue
        r.live_stake = u * UNIT
        n_match[c.match_id] += 1
        n_day[day] += 1
        u_used[day] += u
        out.append(r)
    return out


def record_live(live_ledger, live_rows, all_rows, evd_by_id: dict) -> list[dict]:
    """Bokför LIVE-spelen med den kappade insatsen. Returnerar de nya."""
    new = []
    for r in live_rows:
        if getattr(r, "live_stake", None) is None:
            continue
        d = r.row.decision
        orig = d.stake
        d.stake = r.live_stake
        new += live_ledger.record([r], evd_by_id, predicate=lambda _r: True)
        d.stake = orig
    for b in new:
        b["modell_edge"] = getattr(next((r for r in live_rows if r.row.decision.cand.player_id == b["spelare_id"]
                                         and r.row.decision.cand.market == b["marknad"]), None), "live_model_edge", None)
    live_ledger.update_closing(all_rows, time.time())
    return new
