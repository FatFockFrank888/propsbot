"""Kalshi (reglerad prediktionsbörs i USA) som skarp referens för NBA-props.

Öppet API, ingen nyckel. Varje marknad är "Spelare: N+ poäng" = över N-0,5.
Priset (0–1 USD) är en sannolikhet utan bolagsmarginal. Här handlar spelare som
bolagen har begränsat, så rörelser i priset är en sharp money-signal.

Bara likvida linjer används: glapp köp/sälj högst kalshi_max_spread (4 öre) och
minst kalshi_min_volume kontrakt handlade. Mittpriset blir en tvåsidig "bolags"-
kvot utan marginal (book = "kalshi"), som går in i konsensus som egen källa.
Få anrop per skanning (en per serie, cache 2 min) så att Kalshi inte spärrar.
"""
from __future__ import annotations

import calendar
import re
import time

from ..models import OddsQuote
from .http import JsonClient, SourceError
from .props_text import name_key, same_person

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = {
    "KXNBAPTS": "points", "KXNBAREB": "rebounds", "KXNBAAST": "assists", "KXNBA3PT": "threes",
    "KXNBAPRA": "pra", "KXNBAPR": "pr", "KXNBARA": "ra", "KXNBASTL": "steals", "KXNBABLK": "blocks",
}
TITLE = re.compile(r"^\s*(.+?):\s*(\d+(?:\.\d+)?)\+")


def _num(m: dict, *keys) -> float:
    for k in keys:
        v = m.get(k)
        if v not in (None, ""):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def fetch(c: JsonClient, settings: dict, diag=None) -> list[dict]:
    """Likvida, öppna spelarmarknader: [{namn, pid, marknad, linje, p_over, stänger, volym, glapp}]."""
    max_spread = settings.get("kalshi_max_spread", 0.04)
    min_vol = settings.get("kalshi_min_volume", 500)
    out, n_all = [], 0
    for ser, market in SERIES.items():
        try:
            data = c.get(f"{BASE}/markets", {"series_ticker": ser, "status": "open", "limit": 1000})
        except SourceError as e:
            if diag:
                diag.log(f"Kalshi {ser}: FEL {str(e)[:80]}")
            continue
        for m in (data or {}).get("markets", []):
            n_all += 1
            t = TITLE.match(m.get("title", ""))
            if not t:
                continue
            bid = _num(m, "yes_bid_dollars", "yes_bid")
            ask = _num(m, "yes_ask_dollars", "yes_ask")
            if bid > 1.5:            # gamla fält i cent
                bid, ask = bid / 100, ask / 100
            vol = _num(m, "volume_fp", "volume")
            if not (0 < bid < ask < 1) or ask - bid > max_spread or vol < min_vol:
                continue
            ct = m.get("close_time") or ""
            try:
                close = calendar.timegm(time.strptime(ct[:19], "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                continue
            name = t.group(1).strip()
            out.append({"namn": name, "pid": name_key(name), "marknad": market,
                        "linje": float(t.group(2)) - 0.5, "p_over": (bid + ask) / 2,
                        "stanger": close, "volym": vol, "glapp": ask - bid})
    if diag:
        diag.log(f"Kalshi: {len(out)} likvida linjer av {n_all} öppna marknader")
    return out


def add_to_events(per: dict, lines: list[dict], now: float) -> int:
    """Lägger Kalshi-linjerna som tvåsidiga, marginalfria kvoter på rätt match.
    Matchning: samma spelare (namnjämförelse) i matchens Kambi-odds och att Kalshi-marknaden
    stänger inom 8 timmar efter avspark."""
    n = 0
    for evd, qs_all, names in per.values():
        players = {q.player_id for q in qs_all if q.provider == "kambi"}
        ko = float(evd["commence_time"])
        for x in lines:
            if not (ko - 3600 <= x["stanger"] <= ko + 8 * 3600):
                continue
            pid = x["pid"] if x["pid"] in players else next(
                (k for k in players if same_person(x["pid"], k)), None)
            if not pid:
                continue
            p = min(0.97, max(0.03, x["p_over"]))
            for side, pp in (("over", p), ("under", 1 - p)):
                qs_all.append(OddsQuote(book="kalshi", match_id=evd["id"], player_id=pid,
                                        market=x["marknad"], line=x["linje"], side=side, odds=1 / pp,
                                        ts=now, provider="kalshi", variant=f"kalshi {x['marknad']}"))
            names.setdefault(pid, x["namn"])
            n += 1
    return n
