"""F0 (docs/PLAN_FOOTBALL_PROPS.md): tolkning av ESPN-, FotMob- och Kambi-fält. Fixturer, inget nät."""
from propsbot.probe import clock_minute, espn_player_fields, fotmob_player_fields, kambi_player_markets


def _p(starter, plays=(), pos="CD-L", **kw):
    return {"starter": starter, "position": {"abbreviation": pos}, "subbedIn": kw.get("inn", False),
            "subbedOut": kw.get("out", False), "stats": [{"name": "totalShots", "value": 1.0}, {"name": "foulsCommitted", "value": 2.0}],
            "plays": [{"substitution": True, "clock": {"displayValue": c}} for c in plays]}


def test_clock_minute():
    assert clock_minute("67'") == 67 and clock_minute("90'+1'") == 90 and clock_minute(" 45' ") == 45
    assert clock_minute("HT") is None and clock_minute(None) is None


def test_espn_fields():
    summ = {"rosters": [{"roster": [_p(True), _p(True, ["67'"], out=True), _p(False, ["67'"], pos="SUB", inn=True)]}],
            "boxscore": {"teams": [{"statistics": [{"name": "totalTackles"}, {"name": "wonCorners"}]}]},
            "gameInfo": {}}
    f = espn_player_fields(summ)
    assert f["spelare"] == 3 and f["start_flagga"] and f["byten"] == 2 and f["minuter_harledbara"]
    assert "foulsCommitted" in f["statistik"] and not f["tacklingar_spelare"] and f["tacklingar_lag"]
    assert not f["domare"]
    bad = {"rosters": [{"roster": [_p(True, ["okänd"])]}]}
    assert not espn_player_fields(bad)["minuter_harledbara"]
    assert espn_player_fields({})["spelare"] == 0          # saknade nycklar -> ingen krasch


def test_fotmob_fields():
    st = lambda k: {"x": {"key": k, "stat": {"value": 1}}}
    d = {"content": {"playerStats": {"1": {"stats": [{"stats": {**st("minutes_played"), "y": {"key": "matchstats.headers.tackles"},
                                                                  "z": {"key": "fouls"}}}]}},
                     "lineup": {"homeTeam": {"starters": [{"id": 1, "positionId": 11}]}, "awayTeam": {"starters": []}},
                     "matchFacts": {"infoBox": {"Referee": {"text": "Domare X"}}}}}
    f = fotmob_player_fields(d)
    assert f["minuter"] and f["tacklingar"] and f["fouls"] and f["position"] and f["startspelare"] == 1
    assert f["domare"] == "Domare X"
    assert fotmob_player_fields({}) == {"spelare": 0, "nycklar": [], "minuter": False, "tacklingar": False,
                                        "fouls": False, "startspelare": 0, "position": False, "domare": None}


def test_kambi_markets():
    o = lambda line, t="OT_OVER": {"line": line, "type": t}
    bos = [{"criterion": {"englishLabel": "Player's shots on target (Settled using Opta data)"}, "outcomes": [o(500), o(1500)]},
           {"criterion": {"englishLabel": "Player's fouls conceded"}, "outcomes": [o(500), o(500, "OT_UNDER")]},
           {"criterion": {"englishLabel": "To Get a Card"}, "outcomes": [{"type": "OT_YES"}]},
           {"criterion": {"englishLabel": "Player's tackles"}, "outcomes": [o(1500)]},
           {"criterion": {"englishLabel": "Total Goals"}, "outcomes": [o(2500)]}]
    m = kambi_player_markets(bos)
    assert set(m) == {"skott_pa_mal", "fouls", "kort", "tacklingar"}
    assert m["skott_pa_mal"]["linjer"] == [0.5, 1.5] and m["skott_pa_mal"]["tvasidiga"] == 0
    assert m["fouls"]["tvasidiga"] == 1
    assert kambi_player_markets([]) == {}
