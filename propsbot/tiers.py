"""A/B/C Tier: ersätter "Official Bets" (18/11).

Varje spel som boten bokför (LIVE, regelspel, skuggspel – props och sides, fotboll och NBA) prövas mot tre
nästlade nivåer. Ett spel hamnar i den HÖGSTA nivå det klarar, och varje spelare och match (sides: match och
grupp) får högst ett spel. Nivåerna rättas var för sig, så att vi ser om t.ex. B presterar bättre än A
(för strikta krav = för lite omsättning och större varians).

  C Tier  edge och statistik talar för spelet: edge ≥ tier_c_min_edge (4 %) mot konsensus utan marginal,
          odds tier_c_odds (1,40–6,50), inga hårda spärrar (skadelista, startelva, orimlig edge …) och inget
          sharp money mot oss. Bara bokföring – för att se om kraven är för skarpa och vad som ska kalibreras.
  B Tier  C + fokus på CLV: odds tier_b_odds (1,60–6,00), edge ≥ tier_b_min_edge (5 %) och ≤ tier_b_max_edge,
          Pinnacle (eller DraftKings där Pinnacle saknar marknaden) som referens, oddset faller inte, ingen
          annan skarp källa säger emot, förväntad CLV ≥ 0 där den finns. Spelas.
  A Tier  B + klarar ALLA våra parametrar (NBA: LIVE-kraven i live.py; fotboll: alla regler = regelspel),
          odds tier_a_odds (1,60–3,50). Spelas. Notis för nya spel i A och B (tier_notify, 18/11).

Insats: flat 1–3u, 1u = tier_unit (1 %) av kassan. 1u standard, 2u high (edge ≥ tier_2u_edge), 3u maxbet
(edge ≥ tier_3u_edge och ≤ tier_3u_max_edge, Pinnacle som referens och sharp money med oss). Riktigt höga
edgar (> 20 %) är oftast fel i linjen och blir aldrig maxbet. Inga tak (18/11): inga dags- eller matchbudgetar –
varje A- och B-spel räknas som spelat (användaren väljer själv vad som tas).

Ett spel klassas när det först syns och låses (värden som ändras fram till start, t.ex. Pinnacles pris,
ändrar inte nivån i efterhand). En senare rad på samma spelare och match får uppgradera nivån före start.
Resultat och CLV hämtas från källbokföringen vid varje körning.

Spela från (23/11): källornas "spela från" räknades med för lågt edgekrav (props 2–4 %, sides 3 %), så notisen
visade ett odds under det som verkligen krävdes. Varje nivåspel får nu krav_edge = den edge spelet faktiskt
måste klara för sin nivå (se krav_edge()), spela_fran = min_odds(sannolikhet, krav_edge) och rum =
odds / spela_fran − 1 (hur långt oddset kan falla innan spelet inte längre håller). Källans värde sparas som
spela_fran_kalla. Nivån och bokföringen påverkas inte – bara det visade lägsta oddset.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

TIERS = ("A", "B", "C")
RANK = {"A": 3, "B": 2, "C": 1}

# (sport, fil, källa). Källan styr A: "live" = NBA LIVE-kraven, "spel" = alla regler (fotboll).
SOURCES = [
    ("nba", "nba_live.json", "live"),
    ("nba", "nba_bokforing_v2.json", "spel"),
    ("nba", "nba_skugga_v2.json", "skugga"),
    ("nba", "nba_sides_spel.json", "spel"),
    ("nba", "nba_sides_skugga.json", "skugga"),
    ("fotboll", "bokforing_v3.json", "spel"),
    ("fotboll", "bokforing_skugga_v4.json", "skugga"),
    ("fotboll", "sides_spel.json", "spel"),
    ("fotboll", "sides_skugga.json", "skugga"),
]
SRC_RANK = {"live": 3, "spel": 2, "skugga": 1}

DEFAULTS = {
    "tiers_on": True,
    "tier_unit": 0.01,
    "tier_c_min_edge": 0.04, "tier_c_odds": [1.40, 6.50], "tier_max_edge": 0.25,
    "tier_b_min_edge": 0.05, "tier_b_max_edge": 0.20, "tier_b_odds": [1.60, 6.00],
    "tier_a_odds": [1.60, 3.50],
    "tier_2u_edge": 0.09, "tier_3u_edge": 0.12, "tier_3u_max_edge": 0.20,
    "tier_notify_max_age_s": 3600,
    "tier_notify": ["A", "B"],      # 18/11: notis för nya A- och B-spel (var bara A)
}

# Spärrar som gör spelet ospelbart i alla nivåer (fel i underlaget eller spelaren spelar inte).
HARD = ("inte i startelvan", "matchen har startat", "kunde inte mätas", "orimlig", "avviker",
        "kontrollera manuellt", "lagkamrat nyss ute", "startelvan okänd", "kombo med bara",
        "oddset är", "väntar på startelvor")
# Spärrar som säger att CLV-läget är dåligt: stoppar B och A, inte C.
CLV_BAD = ("oddset har fallit", "för svag referens", "håller inte med", "Pinnacles linje flyttad")
DK_MARKETS_OK = ("steals", "blocks", "pr", "pra", "ra", "pa")


LIVE_KEYS = {"live_min_edge": {"points": 0.05, "threes": 0.05, "assists": 0.05, "rebounds": 0.05}, "live_max_edge": 0.15,
             "live_odds_window": [1.60, 3.50], "nba_pinnacle_markets": ["points", "rebounds", "assists", "threes"]}


# Källornas edgekrav (för krav_edge). Standardvärdena är källmodulernas egna (clv_signal.final_rules, sides.evaluate).
KRAV_KEYS = {"min_edge_all": 0.05, "extra_edge_without_sharp": 0.03,
             "sides_min_edge": 0.03, "nba_sides_min_edge": 0.03, "sides_alt_extra_edge": 0.01,
             "sides_single_ref_extra_edge": 0.01, "sides_low_limit": 2000, "sides_low_limit_extra_edge": 0.01}


def cfg(settings: dict) -> dict:
    c = {k: settings.get(k, v) for k, v in DEFAULTS.items()}
    c["_live"] = {k: settings.get(k, v) for k, v in LIVE_KEYS.items()}   # för "varför inte A" (NBA LIVE-kraven)
    c["_krav"] = {k: settings.get(k, v) for k, v in KRAV_KEYS.items()}   # för krav_edge / spela från
    return c


def min_odds(p: float, krav_edge: float) -> float:
    """Lägsta odds som klarar krav_edge vid sannolikheten p: (1 + krav_edge) / p, avrundat UPPÅT till två
    decimaler (aldrig under den verkliga tröskeln)."""
    return math.ceil((1.0 + krav_edge) / p * 100 - 1e-9) / 100


def _source_krav(b: dict, sport: str, c: dict) -> float:
    """Edgekravet i källan för att spelet ska klara ALLA regler (det som A bygger på).

    props (fotboll och NBA): gemensamma kravet min_edge_all (clv_signal.final_rules) och beslutsreglernas krav per
      marknad (DecisionConfig: mål/assist 4 %, övriga 2 %; + extra_edge_without_sharp när Pinnacle/tvåsidig källa
      saknas – syns i stoppet "högre edgekrav", och påslaget gäller bara marknaderna i min_edge_by_market).
      NBA: dessutom LIVE-kravet per marknad (live_min_edge), som A kräver även för regelspel.
    sides (fotboll och NBA): sides_min_edge (NBA: nba_sides_min_edge) + alternativ linje + en enda referens
      (hörnor, Smarkets) + låg Pinnacle-gräns (pin_grans < sides_low_limit), som i sides.evaluate."""
    from .config import DecisionConfig
    from .sides import SINGLE_REF
    k = c.get("_krav") or KRAV_KEYS
    mk = b.get("marknad")
    if b.get("spelare_id") in ("match", "hörnor"):
        need = k["nba_sides_min_edge"] if sport == "nba" else k["sides_min_edge"]
        single = sport != "nba" and mk in SINGLE_REF
        if b.get("alternativ_linje"):
            need += k["sides_alt_extra_edge"]
        if single:
            need += k["sides_single_ref_extra_edge"]
        elif b.get("pin_grans") is not None and b["pin_grans"] < k["sides_low_limit"]:
            need += k["sides_low_limit_extra_edge"]
        return need
    dc = DecisionConfig()
    dec = dc.min_edge_by_market.get(mk, dc.min_edge)
    if mk in dc.min_edge_by_market and "högre edgekrav" in _stopp(b):
        dec += k["extra_edge_without_sharp"]
    need = max(k["min_edge_all"], dec)
    if sport == "nba":
        live = ((c.get("_live") or LIVE_KEYS).get("live_min_edge") or {}).get(mk)
        if live is not None:
            need = max(need, live)
    return need


def krav_edge(b: dict, tier: str, src: str, sport: str, c: dict) -> float:
    """Den edge spelet faktiskt måste klara för sin nivå.
    C: tier_c_min_edge. B: tier_b_min_edge (B kräver inte källans regler – ett skuggspel kan vara B).
    A: max(tier_b_min_edge, källans krav för att klara alla regler, se _source_krav)."""
    if tier == "C":
        return c["tier_c_min_edge"]
    need = c["tier_b_min_edge"]
    if tier == "A":
        need = max(need, _source_krav(b, sport, c))
    return round(need, 6)


def annotate(tb: dict, src_b: dict | None, c: dict) -> None:
    """Sätter krav_edge, spela_fran (rättat), spela_fran_kalla och rum på ett nivåspel.
    Äldre spel utan krav_edge räknas om här (källans fält läses från källbokföringen när den finns)."""
    if tb.get("krav_edge") is None:
        b = dict(tb, **{k: v for k, v in (src_b or {}).items()
                        if k in ("marknad", "stopp", "spelare_id", "alternativ_linje", "pin_grans")})
        if "spela_fran_kalla" not in tb:
            tb["spela_fran_kalla"] = tb.get("spela_fran")
        tb["krav_edge"] = krav_edge(b, tb["tier"], tb.get("kalla", ""), tb.get("sport", ""), c)
    p, o = tb.get("sannolikhet"), tb.get("odds")
    if p and p > 0:
        tb["spela_fran"] = min_odds(p, tb["krav_edge"])
        tb["rum"] = o / tb["spela_fran"] - 1 if o else None


def live_reasons(b: dict, c: dict) -> list[str]:
    """Konkret vilket NBA LIVE-krav (live.py) spelet inte klarade – visas som "Inte A: …" på sidan."""
    L = c.get("_live") or LIVE_KEYS
    mk, e, o = b.get("marknad"), b.get("edge") or 0.0, b.get("odds") or 0.0
    need = (L["live_min_edge"] or {}).get(mk)
    out = []
    if need is None:
        out.append(f"marknaden {MK.get(mk, mk)} spelas inte i A (för lite data)")
    else:
        if e < need:
            out.append(f"edge {e:.1%} < A-krav {need:.0%}")
        if e > L["live_max_edge"]:
            out.append(f"edge {e:.1%} > A-tak {L['live_max_edge']:.0%}")
    lo, hi = L["live_odds_window"]
    if not (lo <= o <= hi):
        out.append(f"odds {o:.2f} utanför A {lo:.2f}–{hi:.2f}")
    if mk in L["nba_pinnacle_markets"] and b.get("pin_stang_p") is None and b.get("pin_p") is None:
        out.append("Pinnacle saknar linjen")
    stop = [p for p in _stopp(b).split("; ") if p and not p.startswith(("sharp money med", "linjejusterat", "modell "))]
    if stop and not out:
        out.append(stop[0])
    return out or ["för få oberoende jämförelsekällor (minst 2) vid bokningen"]


def _stopp(b: dict) -> str:
    return b.get("stopp") or ""


def hard_block(b: dict) -> str | None:
    s = _stopp(b)
    for part in s.split("; "):
        if part.startswith("skadelista") and "kolla före start" not in part:
            return part
        if any(h in part for h in HARD):
            return part
    return None


def sharp_ref(b: dict, sport: str = "") -> bool:
    """Skarp referens för linjen: Pinnacle, eller DraftKings för NBA-marknader som Pinnacle saknar.
    NBA-spel före 15/11 har bara den samlade skarpa referensen (Pinnacle/DK, skarp_stang_p) – den räknas."""
    if b.get("pin_stang_p") is not None or b.get("pin_p") is not None:
        return True
    if b.get("marknad") in DK_MARKETS_OK and b.get("dk_stang_p") is not None:
        return True
    return sport == "nba" and b.get("skarp_stang_p") is not None


def classify(b: dict, src: str, sport: str, c: dict) -> tuple[str | None, list[str]]:
    """Nivå för ett bokfört spel + varför det inte nådde högre."""
    why: list[str] = []
    e, o = b.get("edge") or 0.0, b.get("odds") or 0.0
    hb = hard_block(b)
    if hb:
        return None, [hb]
    s = _stopp(b)
    lo, hi = c["tier_c_odds"]
    if e < c["tier_c_min_edge"] or e > c["tier_max_edge"] or not (lo <= o <= hi) or "sharp money mot oss" in s:
        return None, ["klarar inte C"]
    tier = "C"
    lo, hi = c["tier_b_odds"]
    if not (lo <= o <= hi):
        why.append(f"odds {o:.2f} utanför B {lo:.2f}–{hi:.2f}")
    if e < c["tier_b_min_edge"]:
        why.append(f"edge {e:.1%} < B {c['tier_b_min_edge']:.0%}")
    if e > c["tier_b_max_edge"]:
        why.append(f"edge {e:.1%} > B {c['tier_b_max_edge']:.0%}")
    if not sharp_ref(b, sport):
        why.append("ingen skarp referens (Pinnacle/DK)")
    bad = next((p for p in s.split("; ") if any(x in p for x in CLV_BAD)), None)
    if bad:
        why.append(bad)
    if b.get("forv_clv_pp") is not None and b["forv_clv_pp"] < 0:
        why.append(f"förväntad CLV {b['forv_clv_pp']:+.1f} pe")
    if why:
        return tier, why
    tier = "B"
    lo, hi = c["tier_a_odds"]
    if sport == "nba" and b.get("spelare_id") not in ("match",) and src != "live":
        why += live_reasons(b, c)
    elif src not in ("live", "spel"):
        why.append("stoppad av en regel")
    if not (lo <= o <= hi):
        why.append(f"odds {o:.2f} utanför A {lo:.2f}–{hi:.2f}")
    if why:
        return tier, why
    return "A", []


def units_for(b: dict, c: dict, sport: str = "") -> int:
    e = b.get("edge") or 0.0
    s = _stopp(b)
    if e >= c["tier_3u_edge"] and e <= c["tier_3u_max_edge"] and sharp_ref(b, sport) and "sharp money med oss" in s:
        return 3
    if e >= c["tier_2u_edge"]:
        return 2
    return 1


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime((ts or 0) - 6 * 3600))


def _ident(sport: str, b: dict) -> str:
    who = b.get("spelare_id") or b.get("spelare")
    if who in ("match", "hörnor"):
        who = f"{who}|{'hörnor' if b.get('spelare_id') == 'hörnor' else 'mål'}"
    return f"{sport}|{b.get('match_id')}|{who}"


SYNC = ("status", "utfall", "stangning", "stangning_ts", "skarp_stang_p", "skarp_stang_ts", "skarp_verifierad",
        "skarp_status", "pin_stang_p", "dk_stang_p", "smk_stang_p", "clv_skarp_pp", "clv_pin_pp", "clv_dk_pp",
        "nyhet", "nyhet_status", "nyhet_ts", "dubblett", "struken_orsak")
COPY = ("match_id", "match", "hemma", "borta", "liga", "avspark", "spelare", "spelare_id", "marknad", "linje", "sida",
        "spel_text", "bolag", "odds", "sannolikhet", "ratt_odds", "edge", "spela_fran", "stopp", "forv_clv_pp",
        "p_modell", "p_marknad", "pin_p", "smk_p", "modell_edge", "analys", "prognos", "bolag_bokning", "bolag_stangning",
        "pin_grans", "alternativ_linje")


class TierBook:
    def __init__(self, path: Path):
        self.path = path
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            d = {}
        self.bets: list[dict] = d.get("bets", [])
        self.seen: set = set(d.get("sedda", []))

    def save(self) -> None:
        from .ledger import rensa_nan
        self.path.write_text(json.dumps(rensa_nan({"bets": self.bets, "sedda": sorted(self.seen)}),
                                        ensure_ascii=False, allow_nan=False), encoding="utf-8")


def _load(root: Path, sports: set) -> list[tuple[str, str, str, dict]]:
    out = []
    for sport, fname, src in SOURCES:
        if sport not in sports:
            continue
        f = root / fname
        if not f.exists():
            continue
        try:
            bets = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for b in bets if isinstance(bets, list) else []:
            if b.get("key"):
                out.append((sport, fname, src, b))
    return out


def _result_u(tb: dict, src_b: dict) -> float | None:
    st, u = tb.get("status"), tb["units"]
    if st not in ("vunnen", "förlorad", "push", "struken"):
        return None
    ins, res = src_b.get("insats_pct"), src_b.get("resultat_enheter")
    if ins and res is not None:          # exakt kvot från källan (asiatiska linjer: halv vinst/förlust)
        return res / ins * u
    if st == "vunnen":
        return (tb["odds"] - 1.0) * u
    if st == "förlorad":
        return -float(u)
    return 0.0


def update(root: Path, settings: dict, now: float | None = None, sports: tuple = ("nba", "fotboll"),
           log=print) -> dict:
    """Klassa nya spel, uppgradera, synka resultat. Returnerar {"book", "new_a": [...]}."""
    now = now or time.time()
    c = cfg(settings)
    book = TierBook(root / "tiers.json")
    by_ident = {b["ident"]: b for b in book.bets}
    allb = _load(root, set(sports))
    src_by = {(f, b["key"]): b for _s, f, _src, b in allb}
    # Samma spel kan stå i flera filer (LIVE-spelet finns också bland regelspelen): bästa källan vinner.
    best: dict = {}
    for sport, f, src, b in allb:
        k = (sport, b["key"])
        if k not in best or SRC_RANK[src] > SRC_RANK[best[k][2]]:
            best[k] = (sport, f, src, b)
    todo = sorted((x for x in best.values() if f"{x[1]}|{x[3]['key']}" not in book.seen),
                  key=lambda x: (x[3].get("bokford") or 0, -SRC_RANK[x[2]]))
    for tb in book.bets:   # tak finns inte längre (18/11): äldre spel över taket räknas som spelade
        if tb.pop("tak", None):
            tb["spelad"] = tb["tier"] in ("A", "B")
    n_new, n_up = 0, 0
    for sport, f, src, b in todo:
        book.seen.add(f"{f}|{b['key']}")
        if b.get("dubblett"):
            continue
        tier, why = classify(b, src, sport, c)
        if tier is None:
            continue
        ident = _ident(sport, b)
        old = by_ident.get(ident)
        t_seen = b.get("bokford") or now
        if old is not None:
            if RANK[tier] <= RANK[old["tier"]] or (old.get("avspark") or 0) <= t_seen:
                continue
        u = units_for(b, c, sport)
        tb = {k: b.get(k) for k in COPY}
        tb.update(ident=ident, sport=sport, tier=tier, units=u, kalla=src, kalla_fil=f, kalla_key=b["key"],
                  bokford=t_seen, inte_hogre=why, unit_pct=c["tier_unit"])
        if old is not None:
            tb["uppgraderad_fran"] = old["tier"]
            tb["id"] = old["id"]
            if old.get("notis"):
                tb["notis"] = True
        else:
            tb["id"] = len(book.bets) + 1
        if b.get("notis"):        # källan har redan skickat notis (gamla LIVE-notisen) – ingen dubblett
            tb["notis"] = True
        tb["spelad"] = tier in ("A", "B")
        annotate(tb, b, c)
        if old is not None:
            book.bets[book.bets.index(old)] = tb
            n_up += 1
        else:
            book.bets.append(tb)
            n_new += 1
        by_ident[ident] = tb
    # A-spel utan notis före start (nya, uppgraderade eller misslyckade förra körningen – skickas igen)
    nt = set(c["tier_notify"])
    new_a = [tb for tb in book.bets if tb["tier"] in nt and tb.get("spelad") and not tb.get("notis")
             and (tb.get("avspark") or 0) > now and now - (tb.get("bokford") or 0) <= c["tier_notify_max_age_s"]]
    for tb in book.bets:   # resultat och CLV från källan
        sb = src_by.get((tb["kalla_fil"], tb["kalla_key"]))
        annotate(tb, sb, c)   # spela från / rum (äldre spel utan krav_edge räknas om)
        if sb is None:
            continue
        if tb.get("status") == "öppen" and tb["tier"] != "A":   # "varför inte högre" räknas om (bara visning, nivån är låst)
            try:
                tb["inte_hogre"] = classify(sb, tb["kalla"], tb["sport"], c)[1] or tb.get("inte_hogre")
            except Exception:  # noqa: BLE001
                pass
        for k in SYNC:
            if k in sb:
                tb[k] = sb[k]
        tb["resultat_u"] = _result_u(tb, sb)
        # sides: CLV mot Pinnacles stängning (utan marginal) när källan inte räknat clv_skarp_pp
        if (tb.get("clv_skarp_pp") is None and tb.get("pin_stang_p") and tb.get("odds")
                and (tb.get("avspark") or now) < now):
            tb["clv_skarp_pp"] = (tb["pin_stang_p"] - 1 / tb["odds"]) * 100
    book.save()
    cnt = {t: sum(1 for b in book.bets if b["tier"] == t) for t in TIERS}
    log(f"Tiers: {n_new} nya, {n_up} uppgraderade, {len(new_a)} nya för notis ({'/'.join(sorted(nt))}); totalt "
        + ", ".join(f"{t} {n}" for t, n in cnt.items()))
    return {"book": book, "new_a": new_a}


def units_text(u: int) -> str:
    return {1: "1u – standard", 2: "2u – high", 3: "3u – MAXBET 💪"}.get(u, f"{u}u")


MK = {"points": "poäng", "rebounds": "returer", "assists": "assist", "threes": "trepoängare", "steals": "steals",
      "blocks": "blocks", "pra": "PRA", "pr": "poäng+returer", "ra": "returer+assist", "pa": "poäng+assist",
      "shots_on_target": "skott på mål", "shots": "skott", "goal": "mål", "assist": "assist"}


def spela_fran_text(b: dict) -> str:
    """"(spela från 1.98, rum +3,5 %)" – med ⚠️ snävt när rummet är under 1 % (skynda att spela)."""
    sf, rum = b.get("spela_fran"), b.get("rum")
    if sf is None:
        return ""
    if rum is None:
        return f"(spela från {sf:.2f})"
    rum_txt = f"{rum * 100:+.1f}".replace(".", ",")
    return f"(spela från {sf:.2f}, rum {rum_txt} %)" + (" ⚠️ snävt" if rum < 0.01 else "")


def notify_a(root: Path, bets: list[dict], settings: dict, log=print) -> int:
    """En notis per nytt spel i de nivåer som ger notis (tier_notify, standard A och B).
    Egen kanal tier_ntfy_topic (18/11: propsbot-tier-ab-…); saknas den används den vanliga ntfy_topic."""
    topic = settings.get("tier_ntfy_topic") or settings.get("ntfy_topic")
    if not topic or not bets:
        return 0
    from datetime import datetime, timezone
    from .notify import send
    sent = 0
    for b in bets:
        txt = b.get("spel_text") or (f"{MK.get(b['marknad'], b['marknad'])} "
                                     f"{'under' if b.get('sida') == 'under' else 'över'} {b['linje']:g}")
        who = b["spelare"] if b.get("spelare_id") not in ("match", "hörnor") else b["match"]
        up = f" (uppgraderad från {b['uppgraderad_fran']})" if b.get("uppgraderad_fran") else ""
        title = f"{b['tier']} TIER {'NBA' if b['sport'] == 'nba' else 'FOTBOLL'}: {who} {txt}"
        ko = datetime.fromtimestamp(b["avspark"], timezone.utc).strftime("%Y-%m-%d %H:%M")
        msg = (f"{b['match']} · {b.get('liga') or ''} ({ko} UTC){up}\n"
               f"{b['bolag']}: {b['odds']:.2f}  {spela_fran_text(b)}\n"
               f"Edge {b['edge']:.1%}\nInsats: {units_text(b['units'])} ({b['units'] * b['unit_pct']:.0%} av kassan)")
        from urllib.parse import quote
        click = settings.get("site_url", "https://fatfockfrank888.github.io/propsbot/") + "#ta=" + quote(b["ident"], safe="")
        if send(topic, title, msg, priority=5 if b["units"] >= 3 else 4 if b["tier"] == "A" else 3, click=click,
                tags="basketball" if b["sport"] == "nba" else "soccer"):
            b["notis"] = True
            sent += 1
    log(f"Tiers: {sent} notiser skickade")
    return sent


def run(root: Path, settings: dict, notify: bool = True, log=print) -> dict:
    res = update(root, settings, log=log)
    if notify:
        notify_a(root, res["new_a"], settings, log)
        res["book"].save()
    site = root / "site"
    site.mkdir(parents=True, exist_ok=True)
    from .ledger import rensa_nan
    pub = [{k: v for k, v in b.items() if k != "analys"} | ({"analys": b["analys"]} if b.get("status") == "öppen" else {})
           for b in res["book"].bets]
    (site / "tiers.json").write_text(json.dumps(rensa_nan({"uppdaterad_ts": time.time(), "regler": cfg(settings),
                                                           "bets": pub}), ensure_ascii=False, allow_nan=False),
                                     encoding="utf-8")
    return res
