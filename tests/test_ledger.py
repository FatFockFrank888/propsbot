"""Bokföring, rättning mot ESPN-format och webbdata. ESPN-svaren är byggda efter
API:ets kända struktur, inte inspelade."""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone

from propsbot.ledger import Ledger
from propsbot.results import settle_open
from propsbot.sources import http as httpmod
from propsbot.sources.http import JsonClient

KICK = time.time() - 5 * 3600


def bet(**kw):
    b = {"key": "k", "id": 1, "bokford": KICK - 3600, "match_id": "k1", "match": "Arsenal – Chelsea",
         "hemma": "Arsenal", "borta": "Chelsea", "liga": "", "avspark": KICK, "spelare": "Bukayo Saka",
         "spelare_id": "bukayo saka", "marknad": "shots_on_target", "linje": 0.5, "bolag": "paf",
         "odds": 2.10, "sannolikhet": 0.53, "ratt_odds": 1.89, "edge": 0.113, "spela_fran": 1.92,
         "insats_pct": 0.02, "stangning": 1.95, "status": "öppen", "utfall": None,
         "resultat_enheter": None}
    b.update(kw)
    return b


def test_settle_and_summary(tmp_path):
    lg = Ledger(tmp_path / "b.json")
    lg.bets = [bet(), bet(key="k2", id=2, spelare="Declan Rice", bolag="unibet", odds=1.8)]
    lg.settle(lg.bets[0], 2, True)
    lg.settle(lg.bets[1], 0, True)
    s = lg.summary()
    assert lg.bets[0]["status"] == "vunnen" and abs(lg.bets[0]["resultat_enheter"] - 0.022) < 1e-9
    assert lg.bets[1]["status"] == "förlorad" and lg.bets[1]["resultat_enheter"] == -0.02
    assert s["rattade"] == 2 and abs(s["resultat_pct"] - 0.002) < 1e-9
    assert set(s["per_bolag"]) == {"paf", "unibet"}
    assert s["clv_snitt"] is not None
    lg.save()
    assert Ledger(tmp_path / "b.json").bets[0]["status"] == "vunnen"


class _R(io.BytesIO):
    def __init__(self, d):
        super().__init__(json.dumps(d).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_settle_open_with_espn(tmp_path, monkeypatch):
    day = datetime.fromtimestamp(KICK, timezone.utc)

    def fake(req, timeout=20, **kw):
        url = req.full_url
        path = urllib.parse.urlparse(url).path
        if path.endswith("/scoreboard"):
            if "/eng.1/" not in path:
                return _R({"events": []})
            return _R({"events": [{"id": "7001", "date": day.strftime("%Y-%m-%dT%H:%MZ"),
                                   "status": {"type": {"completed": True}},
                                   "competitions": [{"competitors": [
                                       {"homeAway": "home", "team": {"displayName": "Arsenal"}},
                                       {"homeAway": "away", "team": {"displayName": "Chelsea"}}]}]}]})
        if path.endswith("/summary"):
            return _R({"rosters": [{"roster": [
                {"athlete": {"displayName": "Bukayo Saka"}, "starter": True,
                 "stats": [{"name": "shotsOnTarget", "value": 2}, {"name": "totalShots", "value": 4}]},
                {"athlete": {"displayName": "Declan Rice"}, "starter": False, "subbedIn": False,
                 "stats": []}]}]})
        raise AssertionError(url)

    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)
    lg = Ledger(tmp_path / "b.json")
    lg.bets = [bet(), bet(key="k2", id=2, spelare="Declan Rice"), bet(key="k3", id=3, spelare="Okänd Spelare"),
               bet(key="k4", id=4, avspark=time.time() + 3600)]
    log = settle_open(lg, JsonClient(tmp_path / "c", min_interval_s=0))
    st = [b["status"] for b in lg.bets]
    assert st == ["vunnen", "struken", "struken", "öppen"], (st, log)
    assert lg.bets[0]["utfall"] == 2
