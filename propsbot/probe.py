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
    base = "https://api.elections.kalshi.com/trade-api/v2"
    _, body = _get(f"{base}/series?category=Sports")
    series = json.loads(body).get("series", [])
    nba = [s for s in series if re.search(r"\bNBA\b|basketball", s.get("title", ""), re.I)]
    props = [s for s in nba if PROP_WORDS.search(s.get("title", ""))]
    soc = [s for s in series if re.search(r"premier|la liga|soccer|football club|EPL", s.get("title", ""), re.I)]
    pl = [s for s in nba if re.search(r"player", s.get("title", ""), re.I)]
    out = [f"{len(series)} sportserier, NBA {len(nba)}, spelarserier {len(pl)}: "
           + ", ".join(s.get("ticker", "") for s in pl[:40])]
    # Öppna marknader i spelarserierna: antal, volym, spread (är de levande och likvida?)
    tot_n = tot_vol = 0
    samples = []
    for s in pl[:25]:
        try:
            _, b = _get(f"{base}/markets?series_ticker={s['ticker']}&status=open&limit=200")
        except Exception:
            continue
        ms = json.loads(b).get("markets", [])
        vol = sum(int(m.get("volume") or 0) for m in ms)
        oi = sum(int(m.get("open_interest") or 0) for m in ms)
        tot_n += len(ms); tot_vol += vol
        if ms:
            m = max(ms, key=lambda m: int(m.get("volume") or 0))
            samples.append(f"{s['ticker']}: {len(ms)} öppna, volym {vol}, OI {oi}, ex '{m.get('title','')[:60]}' "
                           f"{m.get('subtitle') or m.get('yes_sub_title') or ''} bid {m.get('yes_bid')} ask {m.get('yes_ask')} "
                           f"stänger {m.get('close_time','')[:16]}")
    out.append(f"öppna spelarmarknader {tot_n}, total volym {tot_vol}")
    return " || ".join(out + samples[:12])


def polymarket() -> str:
    _, body = _get("https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=nba")
    evs = json.loads(body)
    mk = [m for e in evs for m in e.get("markets", [])]
    # Bara matchprops ("X: Points O/U 24.5" o.d.), inte säsongsmarknader.
    props = [m for m in mk if re.search(r"points|rebounds|assists|threes", m.get("question", ""), re.I)
             and not re.search(r"season|career|lead the nba|mvp|20\d\d-\d\d", m.get("question", ""), re.I)]
    liq = sum(float(m.get("liquidity") or 0) for m in props)
    ex = "; ".join(m.get("question", "")[:70] for m in props[:5])
    return f"NBA-event {len(evs)}, marknader {len(mk)}, spelarprops {len(props)} (likviditet ~{liq:,.0f} USD) | {ex}"


def plain(url: str) -> str:
    st, body = _get(url, 300)
    return f"{st} {body[:100]!r}"


CHECKS = {
    "kalshi": kalshi,
    "polymarket": polymarket,
    "novig_web": lambda: plain("https://novig.us/"),
    "novig_api": lambda: plain("https://api.novig.us/"),
    "prophetx_web": lambda: plain("https://www.prophetx.co/"),
    "prophetx_api": lambda: plain("https://api.prophetx.co/"),
    "rotowire_smart_money": lambda: plain("https://www.rotowire.com/betting/nba/smart-money.php"),
}


def main() -> None:
    out = []
    for name, fn in CHECKS.items():
        try:
            out.append(f"{name}: {fn()}")
        except Exception as e:
            out.append(f"{name}: FEL {type(e).__name__} {getattr(e, 'code', '')} {str(e)[:80]}")
    print("::notice title=probe::" + "%0A".join(x.replace("%", "%25").replace("\n", " ") for x in out))


if __name__ == "__main__":
    main()
