"""Tester för de öppna källorna (Kambi, Pinnacle), notiser och hela gratis-skanningen.

OBS: svaren är byggda efter källornas kända JSON-struktur, inte inspelade.
Självdiagnosen på riktiga datorn sparar riktiga råsvar i diagnos/.
"""
import io
import json
import time
import urllib.parse
from datetime import datetime, timezone

import pytest

from propsbot.free_scan import scan_once
from propsbot.notify import SeenStore
from propsbot.sources import http as httpmod
from propsbot.sources.kambi_public import parse_betoffers
from propsbot.sources.pinnacle_public import american_to_decimal, parse_specials
from propsbot.sources.props_text import person_name, same_match, same_person

START = datetime.fromtimestamp(time.time() + 6 * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kambi_betoffers(sot_over=1850, sot_under=1900, goal=3400, extra=None):
    return {"betOffers": [
        {"criterion": {"englishLabel": "Player's shots on target"},
         "outcomes": [
             {"englishLabel": "Over", "type": "OT_OVER", "odds": sot_over, "line": 500,
              "participant": "Saka, Bukayo", "status": "OPEN"},
             {"englishLabel": "Under", "type": "OT_UNDER", "odds": sot_under, "line": 500,
              "participant": "Saka, Bukayo", "status": "OPEN"}]},
        {"criterion": {"englishLabel": "To score"},
         "outcomes": [{"englishLabel": "Saka, Bukayo", "odds": goal, "participant": "Saka, Bukayo",
                       "status": "OPEN"}]},
        {"criterion": {"englishLabel": "First goalscorer"},
         "outcomes": [{"englishLabel": "Saka, Bukayo", "odds": 7000, "status": "OPEN"}]},
        {"criterion": {"englishLabel": "Player to have 2+ shots"},
         "outcomes": [{"englishLabel": "Yes", "odds": 2100, "participant": "Saka, Bukayo",
                       "status": "OPEN"},
                      {"englishLabel": "Yes", "odds": 2500, "participant": "Rice, Declan",
                       "status": "SUSPENDED"}]},
    ] + (extra or [])}


def test_parse_kambi_betoffers():
    qs, names = parse_betoffers(kambi_betoffers(), "unibet", "k1")
    assert names == {"bukayo saka": "Bukayo Saka"}
    got = {(q.market, q.line, q.side): q.odds for q in qs}
    assert got[("shots_on_target", 0.5, "over")] == 1.85
    assert got[("shots_on_target", 0.5, "under")] == 1.90
    assert got[("goal", 0.5, "over")] == 3.4
    assert got[("shots", 1.5, "over")] == 2.1
    assert len(qs) == 4  # first goalscorer + avstängt utfall ignoreras
    assert all(q.provider == "kambi" for q in qs)


def pinnacle_related(home="Arsenal", away="Chelsea"):
    return [
        {"id": 100, "type": "matchup", "participants": [{"alignment": "home", "name": home},
                                                        {"alignment": "away", "name": away}]},
        {"id": 201, "type": "special",
         "special": {"description": "Bukayo Saka (Shots On Target)", "category": "Player Props"},
         "participants": [{"id": 1, "name": "Over"}, {"id": 2, "name": "Under"}]},
        {"id": 202, "type": "special",
         "special": {"description": "Bukayo Saka (Goals)", "category": "Player Props"},
         "participants": [{"id": 3, "name": "Yes"}, {"id": 4, "name": "No"}]},
        {"id": 203, "type": "special",
         "special": {"description": "Arsenal Total Corners", "category": "Team Props"},
         "participants": [{"id": 5, "name": "Over"}, {"id": 6, "name": "Under"}]},
    ]


def pinnacle_markets():
    return [
        {"matchupId": 201, "type": "total", "prices": [
            {"participantId": 1, "price": -125, "points": 0.5},
            {"participantId": 2, "price": 105, "points": 0.5}]},
        {"matchupId": 202, "type": "moneyline", "prices": [
            {"participantId": 3, "price": 240}, {"participantId": 4, "price": -320}]},
        {"matchupId": 203, "type": "total", "prices": [{"participantId": 5, "price": -110,
                                                       "points": 5.5}]},
    ]


def test_parse_pinnacle_specials():
    qs, names = parse_specials(pinnacle_related(), pinnacle_markets(), "k1")
    got = {(q.market, q.line, q.side): q.odds for q in qs}
    assert got[("shots_on_target", 0.5, "over")] == 1.8
    assert got[("shots_on_target", 0.5, "under")] == 2.05
    assert got[("goal", 0.5, "over")] == 3.4
    assert "bukayo saka" in names
    assert len(qs) == 4  # hörnor ignoreras


def test_american_to_decimal():
    assert american_to_decimal(150) == 2.5
    assert american_to_decimal(-200) == 1.5


def test_names_and_match_pairing():
    assert person_name("Saka, Bukayo") == "Bukayo Saka"
    assert same_person("Bukayo Saka", "B. Saka")
    assert same_person("Martin Ødegaard", "Martin Odegaard")
    assert not same_person("Bukayo Saka", "Declan Rice")
    t = time.time()
    assert same_match("Bayer Leverkusen", "VfB Stuttgart", t, "Bayer 04 Leverkusen", "Stuttgart", t + 600)
    assert not same_match("Arsenal", "Chelsea", t, "Arsenal", "Chelsea", t + 5 * 86400)
    assert not same_match("Arsenal", "Chelsea", t, "Brentford", "Fulham", t)


def test_seen_store(tmp_path):
    s = SeenStore(tmp_path / "s.json")
    assert s.is_new("a", 2.0)
    s.mark("a", 2.0)
    s.save()
    s2 = SeenStore(tmp_path / "s.json")
    assert not s2.is_new("a", 2.05)
    assert s2.is_new("a", 2.2)


# ------------------------------------------------------------ hela flödet
class _Resp(io.BytesIO):
    def __init__(self, data):
        super().__init__(json.dumps(data).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_urlopen(prices: dict, sent: list):
    def fake(req, timeout=20, **kw):
        url = req.full_url if hasattr(req, "full_url") else req
        if url.startswith("https://ntfy.sh"):
            sent.append(json.loads(req.data))
            return _Resp({"id": "x"})
        path = urllib.parse.urlparse(url).path
        if "listView" in path:
            return _Resp({"events": [{"event": {
                "id": 1001, "homeName": "Arsenal", "awayName": "Chelsea", "start": START,
                "state": "NOT_STARTED",
                "path": [{"englishName": "Football"}, {"englishName": "England"},
                         {"englishName": "Premier League"}]}}]})
        if "betoffer/event" in path:
            code = path.split("/")[3]
            if code not in prices:
                raise httpmod.urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b""))
            return _Resp(kambi_betoffers(sot_over=prices[code]))
        if path.endswith("/leagues"):
            return _Resp([{"id": 1980, "name": "England - Premier League"}])
        if path.endswith("/matchups") and "/leagues/" in path:
            return _Resp([{"id": 100, "type": "matchup", "startTime": START,
                           "participants": [{"alignment": "home", "name": "Arsenal"},
                                            {"alignment": "away", "name": "Chelsea"}]}])
        if path.endswith("/related"):
            return _Resp(pinnacle_related())
        if path.endswith("/markets/related/straight"):
            return _Resp(pinnacle_markets())
        raise httpmod.urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b""))
    return fake


def test_free_scan_end_to_end(tmp_path, monkeypatch):
    sent: list = []
    # Paf ligger efter med 2,10 på skott på mål (Pinnacle marginalfritt ≈ 53 %).
    prices = {"ubse": 1850, "paf": 2100}
    fake = _fake_urlopen(prices, sent)
    monkeypatch.setattr(httpmod.urllib.request, "urlopen", fake)
    import propsbot.notify as nmod
    monkeypatch.setattr(nmod.urllib.request, "urlopen", fake)
    monkeypatch.setattr(httpmod.time, "sleep", lambda s: None)

    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"kambi_offerings": {"ubse": "unibet", "paf": "paf",
                                                        "nope": "finnsinte"},
                                    "ntfy_topic": "propsbot-test"}), encoding="utf-8")
    rows = scan_once(tmp_path, settings)
    playable = [r for r in rows if r.row.decision.playable and r.row.decision.show]
    assert len(playable) == 1
    c = playable[0].row.decision.cand
    assert (c.best.book, c.market, c.best.odds) == ("paf", "shots_on_target", 2.1)
    assert 0.5 < c.p < 0.56
    assert len(sent) == 1 and "Bukayo Saka" in sent[0]["title"]
    diag = (tmp_path / "diagnos" / "diagnos.txt").read_text(encoding="utf-8")
    assert "Pinnacle: OK" in diag and "1 spelbara ben" in diag
    # Andra skanningen: samma ben -> ingen ny notis.
    scan_once(tmp_path, settings)
    assert len(sent) == 1


# ------------------------------------------------------- linjejustering
from propsbot.line_adjust import (Lines, adjust_prob, evaluate_line_adjusted,  # noqa: E402
                                  kambi_match_lines, pinnacle_match_lines)
from propsbot.config import Config  # noqa: E402
from propsbot.scan import DEFAULT_SETTINGS  # noqa: E402


def test_adjust_prob_direction_and_identity():
    assert abs(adjust_prob(0.40, 0.5, 1.0, "goal") - 0.40) < 1e-6
    assert adjust_prob(0.40, 0.5, 1.15, "goal") > 0.43
    assert adjust_prob(0.40, 0.5, 0.85, "goal") < 0.37
    # skott reagerar svagare än mål
    assert adjust_prob(0.40, 0.5, 1.15, "shots") < adjust_prob(0.40, 0.5, 1.15, "goal")
    assert 0 < adjust_prob(0.30, 1.5, 1.1, "shots") < 1


def test_parse_match_lines():
    raw = {"betOffers": [
        {"criterion": {"englishLabel": "Full Time"}, "outcomes": [
            {"type": "OT_ONE", "odds": 1900}, {"type": "OT_CROSS", "odds": 3600},
            {"type": "OT_TWO", "odds": 4200}]},
        {"criterion": {"englishLabel": "Total Goals"}, "outcomes": [
            {"type": "OT_OVER", "odds": 1950, "line": 2500}, {"type": "OT_UNDER", "odds": 1850, "line": 2500},
            {"type": "OT_OVER", "odds": 3100, "line": 3500}, {"type": "OT_UNDER", "odds": 1350, "line": 3500}]},
        {"criterion": {"englishLabel": "Half Time"}, "outcomes": [{"type": "OT_ONE", "odds": 2500}]}]}
    kl = kambi_match_lines(raw)
    assert kl.odds_1x2 == (1.9, 3.6, 4.2) and kl.total_line == 2.5
    mk = [{"matchupId": 100, "period": 0, "type": "moneyline", "prices": [
              {"designation": "home", "price": -105}, {"designation": "draw", "price": 270},
              {"designation": "away", "price": 330}]},
          {"matchupId": 100, "period": 0, "type": "total", "prices": [
              {"designation": "over", "price": -130, "points": 2.5},
              {"designation": "under", "price": 115, "points": 2.5}]},
          {"matchupId": 100, "period": 1, "type": "total", "prices": []}]
    pl = pinnacle_match_lines(mk, 100)
    assert pl.total_line == 2.5 and abs(pl.odds_total[0] - 1.769) < 0.01
    lh, la = pl.lambdas()
    assert 2.0 < lh + la < 3.6


def test_line_adjusted_finds_edge_when_pinnacle_expects_more_goals():
    from propsbot.models import OddsQuote
    now = time.time()
    evd = {"id": "k1", "home_team": "A", "away_team": "B", "commence_time": now + 7200}
    kambi = Lines((2.0, 3.5, 3.8), 2.5, (2.10, 1.75))      # Kambi: lågt målsnitt
    pin = Lines((1.95, 3.7, 4.0), 2.5, (1.55, 2.55))       # Pinnacle: klart fler mål
    q = [OddsQuote(b, "k1", "x y", "goal", 0.5, "over", o, now, provider="kambi")
         for b, o in (("unibet", 2.60), ("paf", 2.75), ("atg", 2.60))]
    rows, info = evaluate_line_adjusted(evd, q, {"x y": "X Y"}, DEFAULT_SETTINGS, Config(), now,
                                        pin, kambi)
    d = rows[0].row.decision
    assert d.cand.best.book == "paf"
    assert d.cand.p > rows[0].row.p_market      # uppjusterad
    assert "kvot" in info
    # Omvänt: Pinnacle väntar färre mål -> aldrig spelbart
    rows2, _ = evaluate_line_adjusted(evd, q, {"x y": "X Y"}, DEFAULT_SETTINGS, Config(), now,
                                      kambi, pin)
    assert not rows2[0].row.decision.playable
