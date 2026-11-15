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
  skarp_status                     verifierad | flyttad linje | borttagen | gammal notering (se classify)
  skarp_flyttad_fran, skarp_flytt_for_oss
                                   linjen som referensen flyttade till och om flytten gick vår väg

Försvinner vår linje hos referensen men en närliggande linje för samma spelare och marknad finns kvar
till start (NBA), räknas den linjens stängning om till vår linje med samma negativa binomial som
nba.interpolate_pinnacle. Flytten säger också åt vilket håll pengarna gick: över + linjen upp
(under + linjen ned) = pengar på vår sida. Analys 15/11 (NBA, 31/10–15/11): ~80 % av flyttarna gick
vår väg, och de spelen hade klart bättre CLV och ROI än flyttar mot oss.
"""
from __future__ import annotations

import time
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
    if b.get("skarp_flyttad_fran") is None:
        # status sätts först när matchen startat (före start är stängningen inte känd än)
        started = bool(ko and ko <= time.time())
        b["skarp_status"] = (("verifierad" if b["skarp_verifierad"] else "gammal notering" if ts else None)
                             if started else None)
    b["clv_skarp_pp"] = _pp(b.get("skarp_stang_p"), b.get("odds"))
    b["clv_pin_pp"] = _pp(b.get("pin_stang_p"), b.get("odds"))
    b["clv_dk_pp"] = _pp(b.get("dk_stang_p"), b.get("odds"))


def book_probs(quotes) -> dict[tuple, dict]:
    """(match_id, spelare, marknad, linje) -> {"pinnacle": p_över, "draftkings": p_över, "_raw": {...}}.
    p är tvåsidigt utan marginal; Pinnacle ensidigt (bara över) får 3 % marginal, som i scan.group_fair_prob.
    "_raw": bolagens faktiska odds {"pinnacle"/"draftkings"/"unibet": {"over": o, "under": o}} för analysen;
    "_pin_flyttad": Pinnacles pris är omräknat från en närliggande linje (nba.interpolate_pinnacle)."""
    by: dict[tuple, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    moved: set = set()
    for q in quotes:
        name = ("pinnacle" if q.book == "pinnacle" else "draftkings" if q.book in DK_BOOKS
                else "unibet" if q.book == "unibet" else None)
        if name and q.odds and q.odds > 1.0:
            k = (q.match_id, q.player_id, q.market, q.line)
            by[k][name][q.side] = q.odds
            if name == "pinnacle" and str(getattr(q, "variant", "")).startswith("flyttad"):
                moved.add(k)
    out: dict[tuple, dict] = {}
    for k, books in by.items():
        d: dict = {}
        for name, s in books.items():
            if name == "unibet":
                continue
            if "over" in s and "under" in s:
                d[name] = devig_power((s["over"], s["under"]))[0]
            elif name == "pinnacle" and "over" in s:
                d[name] = 1.0 / (s["over"] * 1.03)
        d["_raw"] = {name: {sd: round(o, 3) for sd, o in s.items()} for name, s in books.items()}
        if k in moved:
            d["_pin_flyttad"] = True
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
                snap = {"ts": now, "odds": bp.get("_raw", {}), "pin_flyttad": bool(bp.get("_pin_flyttad"))}
                if "pinnacle" in bp:
                    b["pin_stang_p"] = snap["pin_p"] = 1.0 - bp["pinnacle"] if under else bp["pinnacle"]
                if "draftkings" in bp:
                    b["dk_stang_p"] = snap["dk_p"] = 1.0 - bp["draftkings"] if under else bp["draftkings"]
                # Analysen: bolagens odds vid bokningen (första noteringen) och senast före start (= stängning)
                if "bolag_bokning" not in b and now - (b.get("bokford") or 0) < 1800:   # bara i bokningens körning
                    b["bolag_bokning"] = snap
                b["bolag_stangning"] = snap
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
        if hist_d:
            apply_moved(lg, hist_d)
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
            "clv_skarp_tackning": (na / len(st)) if st else None,
            "clv_skarp_per_status": {k: {"n": len(v), "clv_pp": sum(v) / len(v)} for k, v in _by_status(st).items()}}


def _by_status(st: list[dict]) -> dict[str, list[float]]:
    g: dict[str, list[float]] = defaultdict(list)
    for b in st:
        if b.get("clv_skarp_pp") is None:
            continue
        k = b.get("skarp_status") or "?"
        if k == "flyttad linje":
            k += " (för oss)" if b.get("skarp_flytt_for_oss") else " (mot oss)"
        g[k].append(b["clv_skarp_pp"])
    return g


def _lines_by_player(hist_d: dict) -> dict[str, dict[float, list]]:
    """match|spelare|marknad -> {linje: [(p_över, ts), ...]} ur historikens nycklar (båda sidor)."""
    out: dict[str, dict[float, list]] = defaultdict(lambda: defaultdict(list))
    for k, h in hist_d.items():
        parts = k.split("|")
        if len(parts) < 4 or len(h) < 4 or h[2] is None or h[3] is None:
            continue
        try:
            ln = float(parts[3])
        except ValueError:
            continue
        p_over = 1.0 - h[2] if len(parts) > 4 and parts[4] == "under" else h[2]
        out["|".join(parts[:3])][ln].append((p_over, h[3]))
    return out


def translate(p_over: float, from_line: float, to_line: float, market: str) -> float | None:
    """P(över to_line) givet referensens P(över from_line) – samma metod som nba.interpolate_pinnacle."""
    from .nba import NB_R
    from .player_model import nb_over
    if market not in NB_R:
        return None
    r = NB_R[market]
    lo, hi = 0.01, 120.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if nb_over(mid, from_line, r) < p_over:
            lo = mid
        else:
            hi = mid
    p = nb_over((lo + hi) / 2, to_line, r)
    return p if 0.03 < p < 0.97 else None


def apply_moved(ledger, hist_d: dict) -> int:
    """Spel vars linje försvann hos referensen > 60 min före start: finns en närliggande linje kvar
    (noterad efter vår sista notering, före start) räknas dess stängning om till vår linje."""
    from .nba import MAX_LINE_GAP
    by = _lines_by_player(hist_d)
    n = 0
    for b in ledger.bets:
        ko, ts = b.get("avspark"), b.get("skarp_stang_ts")
        if not ko or not ts or b.get("skarp_verifierad") or b.get("skarp_flyttad_fran") is not None:
            continue
        if ko > time.time():      # stängningen är inte känd före start
            continue
        lines = by.get(f"{b.get('match_id')}|{b.get('spelare_id')}|{b.get('marknad')}")
        if not lines:
            continue
        gap = MAX_LINE_GAP.get(b.get("marknad"), 1.5)
        best = None
        for ln, obs in lines.items():
            if ln == b.get("linje") or abs(ln - b["linje"]) > gap:
                continue
            pre = [o for o in obs if ts < o[1] < ko]
            if pre:
                o = max(pre, key=lambda x: x[1])
                if best is None or (o[1], -abs(ln - b["linje"])) > (best[2], -abs(best[0] - b["linje"])):
                    best = (ln, o[0], o[1])
        if not best:
            if ko - ts > VERIFIED_MIN * 60:
                b["skarp_status"] = "borttagen"
            continue
        ln, p_over, t = best
        p = translate(p_over, ln, b["linje"], b.get("marknad"))
        if p is None:
            continue
        under = b.get("sida") == "under"
        b["skarp_stang_p_egen_linje"], b["skarp_stang_ts_egen_linje"] = b.get("skarp_stang_p"), ts
        b["skarp_stang_p"] = 1.0 - p if under else p
        b["skarp_stang_ts"] = t
        b["skarp_flyttad_fran"] = ln
        b["skarp_flytt_for_oss"] = (ln > b["linje"]) != under   # över + linjen upp = pengar på vår sida
        recompute(b)
        b["skarp_status"] = "flyttad linje"
        n += 1
    return n
