"""Provar om externa datakällor svarar från den här servern (för beslut om nya källor).

Just nu: börser och prediktionsmarknader (där begränsade, skarpa spelare spelar).
Letar efter NBA-/fotbollsprops och skriver ut antal + exempel i körningens logg.
"""
import json
import re
import urllib.request

from .sources.http import UA

PROP_WORDS = re.compile(r"points|rebounds|assists|threes|3-pointers|pts|shots on target|"
                        r"player|o/u|over|anytime", re.I)


def _get(url: str, n: int = 60_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read(n).decode("utf-8", "replace")


def kalshi() -> str:
    """Få anrop (Kalshi begränsar): poäng- och assistmarknader, alla fält med pris/volym."""
    import time
    base = "https://api.elections.kalshi.com/trade-api/v2"
    out = []
    for ser in ("KXNBAPTS", "KXNBAAST", "KXNBAREB"):
        time.sleep(1.5)
        _, b = _get(f"{base}/markets?series_ticker={ser}&status=open&limit=1000")
        ms = json.loads(b).get("markets", [])
        num = lambda m, *ks: next((float(m[k]) for k in ks if m.get(k) not in (None, "")), 0.0)
        vol = sum(num(m, "volume_fp", "volume") for m in ms)
        oi = sum(num(m, "open_interest_fp", "open_interest") for m in ms)
        quoted = [m for m in ms if num(m, "yes_bid_dollars", "yes_bid") > 0 and num(m, "yes_ask_dollars", "yes_ask") > 0]
        sp = sorted(num(m, "yes_ask_dollars", "yes_ask") - num(m, "yes_bid_dollars", "yes_bid") for m in quoted)
        top = sorted(ms, key=lambda m: -num(m, "volume_fp", "volume"))[:3]
        out.append(f"{ser}: {len(ms)} öppna, med bud {len(quoted)}, volym {vol:,.0f}, OI {oi:,.0f}, "
                   f"median spread {sp[len(sp)//2] if sp else None}")
        out += ["   " + m.get("title", "")[:45] + " | " + ", ".join(
            f"{k}={v}" for k, v in m.items() if any(w in k for w in ("bid", "ask", "volume", "interest", "close_time")))[:260]
            for m in top]
    return " || ".join(out)


def polymarket() -> str:
    _, body = _get("https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=nba")
    evs = json.loads(body)
    mk = [m for e in evs for m in e.get("markets", [])]
    # Bara matchprops ("X: Points O/U 24.5" o.d.), inte säsongsmarknader.
    props = [m for m in mk if re.search(r"points|rebounds|assists|threes", m.get("question", ""), re.I)
             and not re.search(r"season|career|lead the nba|mvp|20\d\d-\d\d", m.get("question", ""), re.I)]
    ou = [m for m in props if re.search(r"O/U", m.get("question", ""))]
    f = lambda m, k: float(m.get(k) or 0)
    liq = sum(f(m, "liquidity") for m in ou)
    vol = sum(f(m, "volume") for m in ou)
    top = sorted(ou, key=lambda m: -f(m, "volume"))[:8]
    ex = " || ".join(f"{m.get('question','')[:50]}: pris {m.get('outcomePrices')} bid {m.get('bestBid')} ask {m.get('bestAsk')} "
                     f"vol {f(m,'volume'):,.0f} likv {f(m,'liquidity'):,.0f}" for m in top)
    spreads = sorted(f(m, "bestAsk") - f(m, "bestBid") for m in ou if m.get("bestAsk") and m.get("bestBid"))
    med = spreads[len(spreads) // 2] if spreads else None
    return (f"spelar-O/U {len(ou)} (volym {vol:,.0f} USD, likviditet {liq:,.0f} USD, median spread {med}) || {ex}")


def plain(url: str) -> str:
    st, body = _get(url, 300)
    return f"{st} {body[:100]!r}"


def jsonish(url: str, keys=()) -> str:
    st, body = _get(url, 3_000_000)
    try:
        d = json.loads(body)
        info = ", ".join(f"{k}={len(d.get(k, []))}" for k in keys) if isinstance(d, dict) else f"lista {len(d)}"
        return f"{st} JSON ok {info}"
    except ValueError:
        return f"{st} inte JSON: {body[:80]!r}"


CHECKS = {
    # Fotbollsstatistik (fouls per spelare): vilka svarar från GitHub?
    "sofascore_events": lambda: jsonish("https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-11-01", ("events",)),
    "sofascore_lineups": lambda: jsonish("https://api.sofascore.com/api/v1/event/12436870/lineups", ("home",)),
    "fotmob_matches": lambda: jsonish("https://www.fotmob.com/api/matches?date=20261101", ("leagues",)),
    "fbref_pl": lambda: plain("https://fbref.com/en/comps/9/misc/Premier-League-Stats"),
    "understat": lambda: plain("https://understat.com/league/EPL"),
    "espn_summary": lambda: jsonish("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event=401878764", ("rosters",)),
}


def espn_fouls_fields() -> str:
    _, body = _get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event=401878764")
    d = json.loads(body)
    r = d["rosters"][0]["roster"][0]
    return ", ".join(sorted({s.get("name") or s.get("abbreviation") for s in r.get("stats", [])}))


def main() -> None:
    CHECKS["espn_stat_names"] = espn_fouls_fields
    out = []
    for name, fn in CHECKS.items():
        try:
            out.append(f"{name}: {fn()}")
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {getattr(e, 'code', '')} {str(e)[:80]}")
    print("::notice title=probe::" + "%0A".join(x.replace("%", "%25").replace("\n", " ") for x in out))


if __name__ == "__main__":
    main()
