"""CLV mot den skarpa stängningen (Pinnacle/DraftKings), inte mot Unibets eget stängningsodds.

Unibet (Kambi) följer Pinnacle med fördröjning, så Unibets eget stängningsodds säger lite om
huruvida vi slog marknaden. Rätt mått: den skarpa marknadens rättvisa sannolikhet (utan marginal)
för vår sida vid avspark, jämförd med den implicita sannolikheten i oddset vi tog hos Unibet.

    CLV (procentenheter) = (p_skarp_stängning − 1 / vårt_odds) × 100        (positivt = bra)

p_skarp_stängning är den senaste noteringen före avspark av referensens sannolikhet för linjen
(samma "rätta" sannolikhet som boten räknar edge mot: Pinnacle väger tyngst, DraftKings och övriga
oberoende källor; Kambi-gruppen är aldrig med). Den finns i historikfilerna (pinnacle_historik.json,
nba_historik.json). Därtill sparas Pinnacles och DraftKings egna sannolikheter var för sig när
råoddsen finns (från 2026-11-15; äldre spel har bara referensen).

Fält på spelet:
  skarp_stang_p / skarp_stang_ts   referensens sannolikhet för vår sida vid senaste notering före start
  pin_stang_p, dk_stang_p          Pinnacles resp. DraftKings rättvisa sannolikhet (om de fanns)
  clv_skarp_pp, clv_pin_pp, clv_dk_pp
  skarp_kalla                      "skanning" (löpande) eller "bakåt" (rekonstruerad ur datahistoriken)
"""
from __future__ import annotations

from collections import defaultdict

from .market import devig_power

DK_BOOKS = ("us_draftkings", "oa_us_draftkings")


def line_key_bet(b: dict) -> str:
    """Samma nyckel som clv_signal.line_key, men från ett bokfört spel."""
    side = "|under" if b.get("sida") == "under" else ""
    return f"{b.get('match_id')}|{b.get('spelare_id')}|{b.get('marknad')}|{b.get('linje')}{side}"


def _pp(p: float | None, odds: float | None) -> float | None:
    if p is None or not odds or odds <= 1.0 or p != p:
        return None
    return (p - 1.0 / odds) * 100


VERIFIED_MIN = 60   # skarp stängning noterad högst så här många minuter före start = verifierad


def recompute(b: dict) -> None:
    ts, ko = b.get("skarp_stang_ts"), b.get("avspark")
    b["skarp_verifierad"] = bool(ts and ko and ko - ts <= VERIFIED_MIN * 60)
    b["clv_skarp_pp"] = _pp(b.get("skarp_stang_p"), b.get("odds"))
    b["clv_pin_pp"] = _pp(b.get("pin_stang_p"), b.get("odds"))
    b["clv_dk_pp"] = _pp(b.get("dk_stang_p"), b.get("odds"))


def book_probs(quotes) -> dict[tuple, dict[str, float]]:
    """(match_id, spelare, marknad, linje) -> {"pinnacle": p_över, "draftkings": p_över}, tvåsidigt utan marginal.
    Pinnacle ensidigt (bara över) får 3 % marginal, som i scan.group_fair_prob."""
    by: dict[tuple, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for q in quotes:
        name = "pinnacle" if q.book == "pinnacle" else "draftkings" if q.book in DK_BOOKS else None
        if name and q.odds and q.odds > 1.0:
            by[(q.match_id, q.player_id, q.market, q.line)][name][q.side] = q.odds
    out: dict[tuple, dict[str, float]] = {}
    for k, books in by.items():
        d = {}
        for name, s in books.items():
            if "over" in s and "under" in s:
                d[name] = devig_power((s["over"], s["under"]))[0]
            elif name == "pinnacle" and "over" in s:
                d[name] = 1.0 / (s["over"] * 1.03)
        if d:
            out[k] = d
    return out


def update(ledger, hist_d: dict, now: float, books: dict | None = None, source: str = "skanning") -> int:
    """Uppdatera skarp stängning för spel före avspark. hist_d: History.d (nyckel -> [p0, t0, p, t, ...]).
    Bara noteringar före avspark räknas, och en äldre notering skriver aldrig över en nyare.
    Returnerar antal uppdaterade spel."""
    n = 0
    for b in ledger.bets:
        ko = b.get("avspark")
        if not ko:
            continue
        h = hist_d.get(line_key_bet(b))
        changed = False
        if h and len(h) >= 4 and h[2] is not None and h[3] < ko and h[3] > (b.get("skarp_stang_ts") or 0):
            b["skarp_stang_p"], b["skarp_stang_ts"], b["skarp_kalla"] = h[2], h[3], source
            changed = True
        if books is not None and now < ko:
            bp = books.get((b.get("match_id"), b.get("spelare_id"), b.get("marknad"), b.get("linje")))
            if bp:
                under = b.get("sida") == "under"
                if "pinnacle" in bp:
                    b["pin_stang_p"] = 1.0 - bp["pinnacle"] if under else bp["pinnacle"]
                if "draftkings" in bp:
                    b["dk_stang_p"] = 1.0 - bp["draftkings"] if under else bp["draftkings"]
                b["bolag_stang_ts"] = now
                changed = True
        if changed:
            recompute(b)
            n += 1
    return n


def clv_pp(b: dict) -> float | None:
    """CLV för ett spel: mot skarp stängning om den finns, annars mot bolagets eget stängningsodds."""
    v = b.get("clv_skarp_pp")
    if v is None and b.get("skarp_stang_p") is not None:
        v = _pp(b["skarp_stang_p"], b.get("odds"))
    if v is not None:
        return v
    if b.get("stangning") and b.get("odds"):
        return (1 / b["stangning"] - 1 / b["odds"]) * 100
    return None


def clv_bolag_pp(b: dict) -> float | None:
    """Gamla måttet: mot bolagets (Unibets) eget stängningsodds."""
    if b.get("stangning") and b.get("odds"):
        return (1 / b["stangning"] - 1 / b["odds"]) * 100
    return None


def refresh(ledgers, hist_d: dict | None, now: float, quotes=None) -> int:
    """Körs varje skanning: bakåträkningen (engångsdata i repot) + löpande uppdatering."""
    from .skarp_bakat import apply_backfill
    books = book_probs(quotes) if quotes is not None else None
    n = 0
    for lg in ledgers:
        apply_backfill(lg)
        if hist_d is not None or books is not None:
            n += update(lg, hist_d or {}, now, books)
    return n


def stats(bets: list[dict], now: float) -> dict:
    """Snitt-CLV mot skarp stängning för startade spel (alla och verifierade), plus Pinnacle/DK var för sig."""
    st = [b for b in bets if b.get("avspark") and b["avspark"] < now]
    def m(key, only_ver=False):
        xs = [b[key] for b in st if b.get(key) is not None and (not only_ver or b.get("skarp_verifierad"))]
        return (sum(xs) / len(xs) if xs else None), len(xs), (sum(x > 0 for x in xs) / len(xs) if xs else None)
    a, na, ba = m("clv_skarp_pp")
    v, nv, bv = m("clv_skarp_pp", True)
    pn, npn, _ = m("clv_pin_pp")
    dk, ndk, _ = m("clv_dk_pp")
    return {"clv_skarp_pp": a, "clv_skarp_antal": na, "clv_skarp_slog": ba,
            "clv_skarp_ver_pp": v, "clv_skarp_ver_antal": nv, "clv_skarp_ver_slog": bv,
            "clv_pin_pp": pn, "clv_pin_antal": npn, "clv_dk_pp": dk, "clv_dk_antal": ndk,
            "clv_skarp_tackning": (na / len(st)) if st else None}
