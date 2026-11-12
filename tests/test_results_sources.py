"""Rättning av sides: ESPN (amerikanskt datum, namnvarianter) och FotMob som reserv."""
from datetime import datetime, timezone

from propsbot.results import EspnResults, espn_match, team_similarity
from propsbot.sources.fotmob import FotmobResults


def ts(s: str) -> float:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


class FakeClient:
    def __init__(self, pages: dict):
        self.pages, self.calls = pages, []

    def get(self, url, params=None, ttl=None):
        self.calls.append((url, dict(params or {})))
        return self.pages.get((url.rsplit("/", 2)[-2] if "scoreboard" in url else "fotmob", (params or {}).get("dates") or (params or {}).get("date")), {})


def espn_ev(home, away, hs, as_, date, name="STATUS_FULL_TIME", done=True):
    return {"id": "1", "date": date, "status": {"type": {"name": name, "completed": done}},
            "competitions": [{"competitors": [{"homeAway": "home", "score": str(hs), "team": {"displayName": home}},
                                              {"homeAway": "away", "score": str(as_), "team": {"displayName": away}}]}]}


def test_team_names_that_contain_each_other_match():
    assert team_similarity("Ajax", "Ajax Amsterdam") >= 0.75
    assert team_similarity("Rennes", "Stade Rennais") >= 0.75
    assert team_similarity("Real Madrid", "Real Sociedad") < 0.75
    t = ts("2026-11-08T13:30:00")
    assert espn_match("FC Twente", "Ajax", t, "FC Twente", "Ajax Amsterdam", t)
    assert not espn_match("FC Twente", "Ajax", t, "FC Twente", "Ajax Amsterdam", t + 3600)   # fel avspark


def test_espn_late_utc_kickoff_is_on_previous_us_day():
    start = ts("2026-11-08T00:00:00")   # MLS-kväll: ESPN lägger den på 20261107
    c = FakeClient({("all", "20261107"): {"events": [espn_ev("San Diego FC", "Sporting Kansas City", 2, 1, "2026-11-08T00:00Z")]}})
    assert EspnResults(c).final_score("San Diego FC", "Sporting Kansas City", start) == (2, 1)


def test_espn_penalties_not_settled():
    start = ts("2026-11-10T19:00:00")
    c = FakeClient({("all", "20261110"): {"events": [espn_ev("Stockport County", "Tranmere Rovers", 1, 1, "2026-11-10T19:00Z", "STATUS_FINAL_PEN")]}})
    assert EspnResults(c).final_score("Stockport County", "Tranmere Rovers", start) is None


def fm(home, away, hs, as_, utc, reason="FT", finished=True):
    return {"home": {"name": home, "score": hs}, "away": {"name": away, "score": as_},
            "status": {"utcTime": utc, "finished": finished, "cancelled": False, "reason": {"short": reason}}}


def test_fotmob_final_score_and_skips():
    start = ts("2026-11-07T14:00:00")
    page = {"leagues": [{"matches": [fm("Helsingborg", "Falkenberg", 3, 0, "2026-11-07T14:00:00.000Z"),
                                     fm("Lyn", "Strømmen", 2, 2, "2026-11-07T12:00:00.000Z", "Pen")]}]}
    f = FotmobResults(FakeClient({("fotmob", "20261107"): page}))
    assert f.final_score("Helsingborgs IF", "Falkenbergs FF", start) == (3, 0)
    assert f.final_score("Lyn", "Strømmen", ts("2026-11-07T12:00:00")) is None   # straffar
    assert f.final_score("Helsingborgs IF", "Falkenbergs FF", start + 2 * 86400) is None


def ls_ev(home, away, esd, eps="FT", **sc):
    return {"T1": [{"Nm": home}], "T2": [{"Nm": away}], "Esd": esd, "Eps": eps, **sc}


def test_livescore_ordinary_time_score_and_skips():
    from propsbot.sources.livescore import LivescoreResults

    class C:
        def get(self, url, params=None, ttl=None):
            if "20261110" not in url:
                return {}
            return {"Stages": [{"Events": [
                ls_ev("Stockport County", "Tranmere Rovers", 20261110190000, "AP", Tr1="0", Tr2="0", Tr1OR="0", Tr2OR="0", Trp1="4", Trp2="3"),
                ls_ev("Barnet", "Wycombe", 20261110194500, "AET", Tr1="1", Tr2="2", Tr1OR="1", Tr2OR="1"),
                ls_ev("Japan FC", "Tokyo SC", 20261110100000, "FT", Tr1="3", Tr2="1"),
                ls_ev("Lyn", "Skeid", 20261110120000, "Postp.")]}]}
    ls = LivescoreResults(C())
    assert ls.final_score("Stockport County", "Tranmere Rovers", ts("2026-11-10T19:00:00")) == (0, 0)   # straffar: 90 min = 0–0
    assert ls.final_score("Barnet", "Wycombe", ts("2026-11-10T19:45:00")) == (1, 1)                    # förlängning räknas inte
    assert ls.final_score("Japan FC", "Tokyo SC", ts("2026-11-10T10:00:00")) == (3, 1)
    assert ls.final_score("Lyn", "Skeid", ts("2026-11-10T12:00:00")) is None


def test_unsettled_live_sides_alert_once(monkeypatch):
    import propsbot.notify as nt
    from propsbot.sides import unsettled_alert
    now = ts("2026-11-12T12:00:00")
    lg = type("L", (), {"bets": [
        {"notis": True, "status": "öppen", "avspark": now - 4 * 86400, "match": "A – B", "spel_text": "1X2: 1", "liga": "Football / Panama / Liga LPF"},
        {"notis": True, "status": "öppen", "avspark": now - 86400, "match": "C – D", "spel_text": "1X2: X", "liga": "x"},
        {"notis": False, "status": "öppen", "avspark": now - 5 * 86400, "match": "E – F", "spel_text": "", "liga": "x"}]})()
    sent = []
    monkeypatch.setattr(nt, "send", lambda *a, **k: sent.append(a[1]) or True)
    assert unsettled_alert(lg, "t", now, log=lambda *_: None) == 1 and len(sent) == 1
    assert unsettled_alert(lg, "t", now, log=lambda *_: None) == 0 and len(sent) == 1   # bara en gång
