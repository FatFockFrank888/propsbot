"""OddsPapi (https://oddspapi.io) – bet365:s spelarprops för fotboll som referens (Pinnacle saknar dem).

Budget: 250 anrop/månad. Därför bara BULK: `odds-by-tournaments` ger alla matcher i upp till 5 ligor i ETT anrop
(med bookmakers=bet365). Aldrig match för match. Nyckeln läses ur ODDS_PAPI_KEY (query-param `apiKey`, ingen
header) och skrivs aldrig i loggen. Saknas nyckeln hoppas allt över.
Anropsbudget: månadsstopp `oddspapi_month_stop` (230); per ligagrupp högst ett anrop per `oddspapi_ttl_min`
(480 min) och bara när någon av våra matcher startar inom `oddspapi_window_h` (30 h) – bet365 öppnar
spelarprops sent, tidigare matcher har bara stängda marknader. Marknadskatalogen (/markets) och lagnamn
(/participants) cachas.
Tolkning (verifieras mot PropLine under datainsamlingen): marknadstyperna playertotals-shotsongoal och
playertotals-shots, `handicap` N,5 = "över N,5" (N+1 eller fler), ensidigt (bara över). OddsPapis period-etikett
(p1/fulltime) är opålitlig för fotbollens spelarprops, därför sparas den bara, den filtrerar inget.
Datainsamling: priserna skrivs till oddspapi_bet365.json. De går bara in som röst i konsensusen om
`oddspapi_voice` är true (standard false).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..models import OddsQuote
from .props_text import name_key, person_name, same_match

BASE = "https://api.oddspapi.io/v4"
STATE = "oddspapi_lage.json"
OUT = "oddspapi_bet365.json"
TOURNAMENTS = [17, 8, 23, 35, 34, 7, 34480]   # PL, La Liga, Serie A, Bundesliga, Ligue 1, CL (ej verifierad), Conference
MARKET_TYPES = {"playertotals-shotsongoal": "shots_on_target", "playertotals-shots": "shots"}
MONTH_STOP = 230
TTL_MIN = 480
WINDOW_H = 30
CATALOG_TTL_S = 30 * 86400
MAX_FIXTURES_KEPT = 200
COOLDOWN_S = 1.1
CHUNK = 5   # API:t tillåter högst 5 turnerings-id per anrop


def _ts(iso) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _get(path: str, key: str, **params):
    params["apiKey"] = key
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "propsbot", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def build_catalog(markets: list) -> dict[str, list]:
    """/markets -> {marketId: [vår marknad, linje, period]} för skott och skott på mål med halvlinjer (N,5)."""
    cat = {}
    for m in markets or []:
        ours = MARKET_TYPES.get(str(m.get("marketType")))
        try:
            hc = float(m.get("handicap"))
        except (TypeError, ValueError):
            continue
        if not ours or abs(hc * 2 - round(hc * 2)) > 1e-9 or abs(hc - int(hc) - 0.5) > 1e-9:
            continue   # bara halvlinjer (0,5 / 1,5 ...)
        cat[str(m.get("marketId"))] = [ours, hc, str(m.get("period"))]
    return cat


def parse_fixture(fx: dict, catalog: dict) -> tuple[list[dict], int]:
    """Matchens bet365-spelarpriser -> rader. Bara aktiva marknader/spelare. Returnerar (rader, marknader med >1 utfall)."""
    b = (fx.get("bookmakerOdds") or {}).get("bet365") or {}
    rows, multi = [], 0
    for mid, m in (b.get("markets") or {}).items():
        c = catalog.get(str(mid))
        if not c or not m.get("marketActive", True):
            continue
        outs = m.get("outcomes") or {}
        if len(outs) > 1:
            multi += 1
        for out in outs.values():
            for p in (out.get("players") or {}).values():
                price, name = p.get("price"), p.get("playerName")
                if not p.get("active") or not name or not isinstance(price, (int, float)) or price <= 1.0:
                    continue
                rows.append({"mid": str(mid), "market": c[0], "line": c[1], "period": c[2], "player": person_name(name),
                             "odds": round(float(price), 3), "changed": p.get("changedAt")})
    return rows, multi


def _chunks(ids: list, n: int = CHUNK) -> list[list]:
    return [ids[i:i + n] for i in range(0, len(ids), n)]


def add_oddspapi(root: Path, data: list, settings: dict, diag) -> int:
    key = (os.environ.get("ODDS_PAPI_KEY") or "").strip()
    if not key or not settings.get("oddspapi_enabled", True):
        diag.log("OddsPapi: av (ingen ODDS_PAPI_KEY)") if not key else None
        return 0
    path = root / STATE
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        st = {}
    now = time.time()
    month = time.strftime("%Y-%m", time.gmtime(now))
    if st.get("month") != month:
        st = {"month": month, "used": 0, "chunks": {}, "catalog": st.get("catalog", {}), "catalog_ts": st.get("catalog_ts", 0),
              "teams": st.get("teams", {}), "teams_try": st.get("teams_try", 0)}
    cap = settings.get("oddspapi_month_stop", MONTH_STOP)
    ttl = settings.get("oddspapi_ttl_min", TTL_MIN) * 60
    window = settings.get("oddspapi_window_h", WINDOW_H) * 3600
    calls = 0
    n_rows = 0
    last_call = [0.0]

    def call(p, **params):
        nonlocal calls
        if st["used"] >= cap:
            raise RuntimeError("månadsgräns")
        wait = COOLDOWN_S - (time.time() - last_call[0])
        if wait > 0:
            time.sleep(wait)
        st["used"] += 1
        calls += 1
        last_call[0] = time.time()
        return _get(p, key, **params)

    out = {}
    try:
        out = json.loads((root / OUT).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        out = {}
    out.setdefault("fixtures", {})
    try:
        soon = [(evd, qs, nm) for evd, qs, nm in data if evd.get("commence_time") and 0 < evd["commence_time"] - now <= window]
        if not soon:
            return 0
        if not st.get("catalog") or now - st.get("catalog_ts", 0) > CATALOG_TTL_S:
            st["catalog"] = build_catalog(call("markets"))
            st["catalog_ts"] = now
        catalog = st["catalog"]
        fixtures = []
        for grp in _chunks(list(settings.get("oddspapi_tournaments", TOURNAMENTS))):
            gk = ",".join(map(str, grp))
            if now - st["chunks"].get(gk, 0) <= ttl:
                continue
            try:
                res = call("odds-by-tournaments", tournamentIds=gk, bookmakers="bet365")
            except RuntimeError:
                raise
            except urllib.error.HTTPError as ex:
                diag.log(f"OddsPapi {gk}: HTTP {ex.code}")
                st["chunks"][gk] = now   # fel ska inte förbruka budgeten i en loop
                continue
            except Exception as ex:  # noqa: BLE001
                diag.log(f"OddsPapi {gk}: {type(ex).__name__}: {str(ex)[:100]}")
                continue
            st["chunks"][gk] = now
            if isinstance(res, list):
                fixtures += [f for f in res if f.get("hasOdds", True)]
        # lagnamn för matcher där vi har bet365-data
        need = {str(f[k]) for f in fixtures for k in ("participant1Id", "participant2Id")
                if (f.get("bookmakerOdds") or {}).get("bet365")} - set(st.get("teams", {}))
        if need and now - st.get("teams_try", 0) > 86400:
            st["teams_try"] = now
            try:
                allt = call("participants", sportId=10)
                st.setdefault("teams", {}).update({i: allt[i] for i in need if isinstance(allt, dict) and i in allt})
            except RuntimeError:
                raise
            except Exception as ex:  # noqa: BLE001
                diag.log(f"OddsPapi participants: {type(ex).__name__}: {str(ex)[:100]}")
        teams = st.get("teams", {})
        matched = multi_total = 0
        for f in fixtures:
            h, a = teams.get(str(f.get("participant1Id"))), teams.get(str(f.get("participant2Id")))
            start = _ts(f.get("startTime"))
            if not h or not a or not start:
                continue
            hit = next(((evd, qs, nm) for evd, qs, nm in soon if same_match(
                evd["home_team"], evd["away_team"], evd["commence_time"], h, a, start)), None)
            if not hit:
                continue
            rows, multi = parse_fixture(f, catalog)
            multi_total += multi
            if not rows:
                continue
            evd, qs, nm = hit
            matched += 1
            out["fixtures"][f["fixtureId"]] = {"match_id": evd["id"], "home": h, "away": a, "start": start, "ts": now,
                                               "rows": [[r["market"], r["line"], r["player"], r["odds"], r["mid"], r["period"],
                                                         r["changed"]] for r in rows]}
            if settings.get("oddspapi_voice", False):   # standard av: bara datainsamling
                for r in rows:
                    pid = name_key(r["player"])
                    nm.setdefault(pid, r["player"])
                    qs.append(OddsQuote(book="op_bet365", match_id=evd["id"], player_id=pid, market=r["market"],
                                        line=r["line"], side="over", odds=r["odds"], ts=now, provider="oddspapi",
                                        variant=f"op_{r['market']}"))
            n_rows += len(rows)
        if multi_total:
            diag.log(f"OddsPapi: {multi_total} marknader med fler än ett utfall (kontrollera över/under)")
        diag.log(f"OddsPapi: {len(fixtures)} matcher hämtade, {matched} matchade mot våra")
    except RuntimeError as ex:
        diag.log(f"OddsPapi: {ex} ({st['used']} anrop i {month})")
    except Exception as ex:  # noqa: BLE001 – får aldrig stoppa skanningen
        diag.log(f"OddsPapi: FEL {type(ex).__name__}: {str(ex)[:150]}")
    finally:
        keep = sorted(out["fixtures"].items(), key=lambda kv: -kv[1].get("start", 0))[:MAX_FIXTURES_KEPT]
        out["fixtures"] = {k: v for k, v in keep if v.get("start", 0) > now - 3 * 86400}
        try:
            path.write_text(json.dumps(st), encoding="utf-8")
            (root / OUT).write_text(json.dumps(out), encoding="utf-8")
        except OSError:
            pass
    diag.log(f"OddsPapi: {calls} anrop denna körning ({st['used']}/{cap} i {month}), {n_rows} bet365-priser sparade")
    return n_rows
