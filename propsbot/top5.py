"""Dagens topp 5: samma ranking som fliken Topp 5 på webbsidan (web/index.html, renderTopp).

Rankas bland de LIVE-spel som faktiskt är bokförda för speldagen (svensk tid, dagen byts kl. 08 så att
NBA-natten hör till kvällen innan). Styrkan räknas på värdena när spelet lades och ändras alltså inte
när oddset rör sig – ett spel du redan lagt försvinner inte ur listan för att oddset fallit, matchen
startat eller spelet avgjorts. Bara ett starkare nytt LIVE-spel kan trycka ner det.

Ingen egen notis sedan 14/11 (top5_notify, av): topp 5 är LIVE-spel som redan fått en LIVE-notis.

Styrka = edge (högst 15, över 15 dras ner) + halva modellens edge (±15) + sharp money (+1 / −2) + 1 för LIVE.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

U = 0.002
SPORTS = {"fotboll": "data.json", "nba": "nba/data.json"}
NAME = {"fotboll": "Fotboll", "nba": "NBA"}
MK = {"shots": "skott", "shots_on_target": "skott på mål", "sog": "skott på mål", "points": "poäng",
      "rebounds": "returer", "assists": "assist", "threes": "trepoängare", "pra": "PRA", "1x2": "1X2",
      "total": "mål totalt", "ah": "handikapp", "corners": "hörnor", "cah": "hörnhandikapp", "corners_home": "hörnor", "corners_away": "hörnor"}
SIDES = ("1x2", "total", "ah", "corners", "cah", "corners_home", "corners_away")


def _ts(s: str | None) -> float | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def score(r: dict) -> dict:
    e = (r.get("edge") or 0) * 100
    ec = min(e, 15) - max(0.0, e - 15) * 0.5
    m = (r["p_modell"] * r["odds"] - 1) * 100 if r.get("p_modell") is not None and r.get("odds") else None
    mp = 0.0 if m is None else 0.5 * max(-15.0, min(15.0, m))
    k = (r.get("kommentar") or "").lower()
    s = 1 if re.search(r"sharp money (with|med) (us|oss)", k) else -2 if re.search(r"sharp (money mot oss|moved .* against)", k) else 0
    live = 1 if r.get("live") else 0
    return {"score": ec + mp + s + live, "edge": e, "model": m, "sharp": s}


DAY_SHIFT_H = 8   # speldagen byts kl. 08 svensk tid


def _offset(ts: float) -> int:
    dt = datetime.fromtimestamp(ts, timezone.utc)
    y = dt.year
    last_sun = lambda m: max(d for d in (datetime(y, m, day, 1, tzinfo=timezone.utc) for day in range(25, 32))
                             if d.weekday() == 6)
    return 2 if last_sun(3) <= dt < last_sun(10) else 1


def play_day(ts: float) -> str:
    """Speldag (svensk tid) för en avsparkstid; matcher före kl. 08 hör till dagen innan."""
    return datetime.fromtimestamp(ts + _offset(ts) * 3600 - DAY_SHIFT_H * 3600, timezone.utc).strftime("%Y-%m-%d")


def _live_bets(d: dict) -> list[dict]:
    out = [b for b in d.get("bokforing", []) if d.get("live")]
    out += [b for b in d.get("sides_spel", []) if b.get("notis")]
    return [b for b in out if not b.get("dubblett") and b.get("status") not in ("struken",)]


def bet_score(b: dict) -> dict:
    """Styrka på värdena när spelet lades (ändras inte med oddset). Samma tal som insatsen (strength.py)."""
    from .strength import score as _score, sharp_signal
    m = b["modell_edge"] * 100 if b.get("modell_edge") is not None else None
    s = sharp_signal(b.get("stopp"))
    return {"score": _score(b.get("edge"), b.get("modell_edge"), s), "edge": (b.get("edge") or 0) * 100, "model": m, "sharp": s}


def ranking(site: Path, now: float | None = None, day: str | None = None) -> list[dict]:
    """Speldagens bokförda LIVE-spel, starkast först, högst ett per spelare/lag och match."""
    now = now or time.time()
    day = day or play_day(now)
    rows = []
    for sport, f in SPORTS.items():
        try:
            d = json.loads((site / f).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        for b in _live_bets(d):
            ts = b.get("avspark")
            if not ts or play_day(ts) != day:
                continue
            spel = b.get("spel_text") or f"{MK.get(b.get('marknad'), b.get('marknad'))} {'under' if b.get('sida') == 'under' else 'över'} {b.get('linje')}"
            rows.append(dict(b, sport=sport, ts=ts, spel=spel, t=bet_score(b), units=round((b.get("insats_pct") or 0) / U),
                             live=True, live_bet=True))
    rows.sort(key=lambda x: (-x["t"]["score"], x.get("bokford") or 0))
    seen, out = set(), []
    for x in rows:
        k = (x["sport"], x.get("match"), x.get("spelare"))
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _local(ts: float) -> str:
    # Svensk tid (CET/CEST) utan extra beroenden: sista söndagen i mars/oktober.
    dt = datetime.fromtimestamp(ts, timezone.utc)
    y = dt.year
    last_sun = lambda m: max(d for d in (datetime(y, m, day, 1, tzinfo=timezone.utc) for day in range(25, 32))
                             if d.weekday() == 6)
    off = 2 if last_sun(3) <= dt < last_sun(10) else 1
    return (dt + timedelta(hours=off)).strftime("%H:%M")


def message(x: dict, rank: int) -> tuple[str, str]:
    t = x["t"]
    title = f"TOPP 5 #{rank}: {x.get('spelare')} {x.get('spel')}"
    cushion = (x["odds"] / x["spela_fran"] - 1) if x.get("spela_fran") else None
    lines = [
        f"{NAME[x['sport']]} · {x.get('match')} · start {_local(x['ts'])}",
        f"{x.get('bolag')}: {x['odds']:.2f}" + (f"  (spela från {x['spela_fran']:.2f}" + (f", kudde {cushion:.1%})" if cushion is not None else ")") if x.get("spela_fran") else ""),
        f"Edge {t['edge']:.1f} %" + (f" · modell {t['model']:+.1f} %" if t["model"] is not None else "")
        + (" · sharp money ⬆" if t["sharp"] > 0 else "") + f" · styrka {t['score']:.1f}",
        f"Insats: {x['units']}u" + (" (som LIVE-spelet)" if x["live_bet"] else "")
        + " · LIVE",
    ]
    return title, "\n".join(lines)


def notify(root: Path, settings: dict, log=print, top_n: int = 5, now: float | None = None) -> int:
    """Skicka nya topp 5-spel. Returnerar antal skickade."""
    topic = settings.get("ntfy_topic")
    if not topic or not settings.get("top5_notify", False):
        return 0
    from .notify import send
    now = now or time.time()
    top = ranking(root / "site", now)[:top_n]
    path = root / "topp5_notis.json"
    try:
        sent = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        sent = {}
    n = 0
    for i, x in enumerate(top, 1):
        k = f"{x['sport']}|{x.get('match')}|{x.get('spelare')}"
        if k in sent or x["ts"] - now < 10 * 60 or x.get("status") != "öppen":
            continue
        title, msg = message(x, i)
        if send(topic, title, msg, priority=4, tags="trophy"):
            sent[k] = now
            n += 1
    sent = {k: v for k, v in sent.items() if now - v < 3 * 86400}
    path.write_text(json.dumps(sent, ensure_ascii=False), encoding="utf-8")
    log(f"Topp 5: {len(top)} spel, {n} nya notiser")
    return n
