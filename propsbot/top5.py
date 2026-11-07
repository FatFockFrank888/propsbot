"""Topp 5 som notis: samma ranking som fliken Topp 5 på webbsidan (web/index.html, renderTopp).

Körs sist i varje körning, när alla sporters data är skrivna (site/data.json, site/nba/data.json,
site/nhl/data.json). Ett spel som för första gången hamnar bland de fem starkaste skickas som EN notis
(en per spelare/lag och match – flyttar spelet bara upp eller ner i listan skickas inget nytt).

Styrka = edge (högst 15, över 15 dras ner) + halva modellens edge (±15) + sharp money (+1 / −2) + 1 för LIVE.
Insats  = det bokförda LIVE-spelets insats, annars förslaget med samma tak som LIVE (5u, sides i data 3u).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

U = 0.002
SPORTS = {"fotboll": "data.json", "nba": "nba/data.json", "nhl": "nhl/data.json"}
NAME = {"fotboll": "Fotboll", "nba": "NBA", "nhl": "NHL"}
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


def _open_live(d: dict, sport: str) -> list[dict]:
    out = []
    if d.get("live"):
        out += [b for b in d.get("bokforing", []) if b.get("status") == "öppen" and not b.get("dubblett")]
    out += [b for b in d.get("sides_spel", []) if b.get("notis") and b.get("status") == "öppen"]
    return out


def ranking(site: Path, now: float | None = None) -> list[dict]:
    """Alla spelbara kandidater, starkast först, högst en per spelare/lag och match."""
    now = now or time.time()
    rows = []
    for sport, f in SPORTS.items():
        try:
            d = json.loads((site / f).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        live = _open_live(d, sport)
        for r in d.get("radar", []) or []:
            ts = _ts(r.get("avspark"))
            if not r.get("spelbar") or not ts or ts <= now + 60:
                continue
            x = dict(r, sport=sport, ts=ts, t=score(r))
            lb = next((b for b in live if b.get("spelare") == r.get("spelare")), None)
            cap = 3 if sport == "fotboll" and r.get("marknad") in SIDES and not r.get("live") else 5
            x["units"] = round(lb["insats_pct"] / U) if lb else min(cap, max(0, round((r.get("insats_pct") or r.get("insats_forslag") or 0) / U)))
            x["live_bet"] = bool(lb)
            rows.append(x)
    rows.sort(key=lambda x: -x["t"]["score"])
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
        + (" · LIVE" if x.get("live") else " · data, ingen LIVE-notis"),
    ]
    return title, "\n".join(lines)


def notify(root: Path, settings: dict, log=print, top_n: int = 5) -> int:
    """Skicka nya topp 5-spel. Returnerar antal skickade."""
    topic = settings.get("ntfy_topic")
    if not topic or not settings.get("top5_notify", True):
        return 0
    from .notify import send
    now = time.time()
    top = ranking(root / "site", now)[:top_n]
    path = root / "topp5_notis.json"
    try:
        sent = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        sent = {}
    n = 0
    for i, x in enumerate(top, 1):
        k = f"{x['sport']}|{x.get('match')}|{x.get('spelare')}"
        if k in sent or x["ts"] - now < 10 * 60:
            continue
        title, msg = message(x, i)
        if send(topic, title, msg, priority=4, tags="trophy"):
            sent[k] = now
            n += 1
    sent = {k: v for k, v in sent.items() if now - v < 3 * 86400}
    path.write_text(json.dumps(sent, ensure_ascii=False), encoding="utf-8")
    log(f"Topp 5: {len(top)} spel, {n} nya notiser")
    return n
