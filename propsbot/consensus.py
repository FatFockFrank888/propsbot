"""Konsensus av oberoende bolag (röster) för spelarprops – bara referens, aldrig spelbolag.

Röst = en plattform/bolag. Bolag via Kambi (Unibet m.fl.) är en och samma röst och räknas aldrig som referens mot
Unibet. Per röst räknas rättvis sannolikhet: tvåsidigt via power-de-vig, annars ensidigt med antagen marginal
(`propline_one_sided_margin`, standard 7 %). Rösterna vägs i logit-rymd. Minst `min_voices` (2) röster krävs.
Antagandet om marginal är en gissning som kalibreras mot utfallen (Brier för p_cons i alt_elasticitet).
"""
from __future__ import annotations

import math


def _devig_pair(o_over: float, o_under: float) -> float:
    from .market import devig_power
    return devig_power((o_over, o_under))[0]


def voice_of(book: str) -> str | None:
    """Bolag -> röst. None = används inte som oberoende röst (Kambi-baserade)."""
    b = (book or "").lower()
    if b.startswith(("pl_",)):
        b = b[3:]
    if b in ("unibet", "paf", "atg", "expekt", "leovegas", "betmgm_se", "svenskaspel", "casumo", "betrivers"):
        return None
    return b


def consensus_p(quotes: list, player_id: str, market: str, line: float, margin: float = 0.07, min_voices: int = 2):
    """quotes: OddsQuote-lista för matchen. Returnerar dict(p, n, voices) eller None."""
    by_voice: dict[str, dict[str, float]] = {}
    for q in quotes:
        if q.player_id != player_id or q.market != market or abs(q.line - line) > 1e-9:
            continue
        v = voice_of(q.book)
        if v is None or q.provider == "kambi":
            continue
        d = by_voice.setdefault(v, {})
        d[q.side] = max(d.get(q.side, 0.0), q.odds)
    ps = {}
    parts = []   # per röst: "p<v>" = tvåsidigt avmarginaliserad, "q<v>" = ensidigt 1/odds (marginalen läggs på efteråt)
    for v, d in sorted(by_voice.items()):
        if "over" in d and "under" in d:
            ps[v] = _devig_pair(d["over"], d["under"])
            parts.append(f"p{ps[v]:.4f}")
        elif "over" in d:
            ps[v] = min(0.99, 1.0 / (d["over"] * (1 + margin)))
            parts.append(f"q{1.0 / d['over']:.4f}")
    if len(ps) < min_voices:
        return None
    x = sum(math.log(p / (1 - p)) for p in ps.values()) / len(ps)
    return {"p": round(1 / (1 + math.exp(-x)), 4), "n": len(ps), "voices": sorted(ps),
            "spread": round(max(ps.values()) - min(ps.values()), 3), "parts": ";".join(parts)}


def p_from_parts(parts: str, margin: float) -> float | None:
    """Räknar om konsensusen ur sparade delar med en annan antagen marginal för ensidiga priser."""
    ps = []
    for tok in (parts or "").split(";"):
        if len(tok) < 2:
            continue
        try:
            v = float(tok[1:])
        except ValueError:
            continue
        ps.append(v if tok[0] == "p" else min(0.99, v / (1 + margin)) if tok[0] == "q" else None)
    ps = [p for p in ps if p is not None and 0 < p < 1]
    if len(ps) < 2:
        return None
    x = sum(math.log(p / (1 - p)) for p in ps) / len(ps)
    return 1 / (1 + math.exp(-x))
