"""Startelvor: spärr för fotbollsspel tills elvorna är kända."""
from propsbot.lineups import Lineup, gate

S = {"lineup_required": True, "lineup_fallback_minutes": 55}


def test_gate():
    pub = Lineup(True, ["Bukayo Saka"], ["Gabriel Jesus"])
    unpub = Lineup(False, [], ["Bukayo Saka", "Gabriel Jesus"])
    assert gate(pub, 70, S) is None                       # elvorna ute -> ok
    assert "startelvor" in gate(unpub, 70, S)             # inte ute än
    assert gate(None, 120, S) is None                     # ESPN saknar matchen (mindre liga) -> bortse från elvan
    assert gate(None, 50, S) is None and gate(unpub, 40, S) is None   # tidsregeln
    assert gate(unpub, 300, {"lineup_required": False}) is None


def test_starts():
    lu = Lineup(True, ["Bukayo Saka", "Martin Ødegaard"], ["Gabriel Jesus"])
    assert lu.starts("B. Saka") is True or lu.starts("Bukayo Saka") is True
    assert lu.starts("Gabriel Jesus") is False
    assert lu.starts("Someone Else") is None


def test_fotmob_fallback():
    from datetime import datetime, timezone
    from propsbot.lineups import Lineups
    start = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc).timestamp()
    def team(n, typ="standard"):
        return {"starters": [{"name": f"{n} {i}"} for i in range(11)], "subs": [{"name": f"{n} bänk"}],
                "unavailable": [{"name": f"{n} skadad"}]}
    class C:
        def __init__(self, typ): self.typ = typ
        def get(self, url, params=None, ttl=None):
            if url.endswith("/matches"):
                return {"leagues": [{"matches": [{"id": 1, "home": {"name": "Barnet"}, "away": {"name": "Tranmere Rovers"},
                                                  "status": {"utcTime": "2026-11-07T15:00:00.000Z"}}]}]}
            return {"content": {"lineup": {"lineupType": self.typ, "homeTeam": team("H"), "awayTeam": team("A")}}}
    lu = Lineups.__new__(Lineups); lu.c = C("standard")
    x = lu.fotmob("Barnet", "Tranmere Rovers", start)
    assert x.published and x.starts("H 3") is True and x.starts("H bänk") is False and "A skadad" in x.unavailable
    lu = Lineups.__new__(Lineups); lu.c = C("lastStarting11")
    x = lu.fotmob("Barnet", "Tranmere Rovers", start)
    assert not x.published and x.starters == []          # förra matchens elva räknas inte
