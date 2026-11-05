"""Startelvor: spärr för fotbollsspel tills elvorna är kända."""
from propsbot.lineups import Lineup, gate

S = {"lineup_required": True, "lineup_fallback_minutes": 55}


def test_gate():
    pub = Lineup(True, ["Bukayo Saka"], ["Gabriel Jesus"])
    unpub = Lineup(False, [], ["Bukayo Saka", "Gabriel Jesus"])
    assert gate(pub, 70, S) is None                       # elvorna ute -> ok
    assert "startelvor" in gate(unpub, 70, S)             # inte ute än
    assert "startelvor" in gate(None, 120, S)             # ESPN saknar matchen, långt kvar
    assert gate(None, 50, S) is None and gate(unpub, 40, S) is None   # tidsregeln
    assert gate(unpub, 300, {"lineup_required": False}) is None


def test_starts():
    lu = Lineup(True, ["Bukayo Saka", "Martin Ødegaard"], ["Gabriel Jesus"])
    assert lu.starts("B. Saka") is True or lu.starts("Bukayo Saka") is True
    assert lu.starts("Gabriel Jesus") is False
    assert lu.starts("Someone Else") is None
