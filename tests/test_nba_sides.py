import time

from propsbot import nba_sides as ns
from propsbot.ledger import Ledger
from propsbot.sides import History


def o(typ, odds, line=None, part=None):
    x = {"type": typ, "odds": int(odds * 1000), "status": "OPEN"}
    if line is not None:
        x["line"] = int(line * 1000)
    if part:
        x["participant"] = part
    return x


RAW = {"betOffers": [
    {"criterion": {"englishLabel": "Including Overtime"}, "betOfferType": {"englishName": "Match"},
     "outcomes": [o("OT_ONE", 1.60, part="Boston Celtics"), o("OT_TWO", 2.45, part="Los Angeles Lakers")]},
    {"criterion": {"englishLabel": "Handicap - Including Overtime"}, "betOfferType": {"englishName": "Handicap"},
     "outcomes": [o("OT_ONE", 1.95, -4.5, "Boston Celtics"), o("OT_TWO", 1.90, 4.5, "Los Angeles Lakers")]},
    {"criterion": {"englishLabel": "Total Points - Including Overtime"}, "betOfferType": {"englishName": "Over/Under"},
     "outcomes": [o("OT_OVER", 2.05, 228.5), o("OT_UNDER", 1.80, 228.5)]},
    {"criterion": {"englishLabel": "Total Points by Boston Celtics - Including Overtime"},
     "outcomes": [o("OT_OVER", 1.9, 116.5), o("OT_UNDER", 1.9, 116.5)]},
    {"criterion": {"englishLabel": "Points scored by the player - Including Overtime"},
     "outcomes": [o("OT_OVER", 1.9, 20.5)]},
]}


def test_kambi_parse_by_team_name():
    k = ns.kambi_main(RAW, "Boston Celtics", "Los Angeles Lakers")
    assert k[("ml", 0.0, "home")] == 1.60 and k[("ml", 0.0, "away")] == 2.45
    assert k[("spread", -4.5, "home")] == 1.95 and k[("spread", 4.5, "away")] == 1.90
    assert k[("game_total", 228.5, "over")] == 2.05
    assert len(k) == 6                          # lagtotal och spelarprops ignoreras
    # utfallen i omvänd ordning: lagnamnet avgör sidan, inte ordningen/typen
    raw = {"betOffers": [{"criterion": {"englishLabel": "Including Overtime"},
                          "outcomes": [o("OT_TWO", 2.45, part="Los Angeles Lakers"), o("OT_ONE", 1.60, part="Boston Celtics")]}]}
    assert ns.kambi_main(raw, "Boston Celtics", "Los Angeles Lakers")[("ml", 0.0, "away")] == 2.45


def test_pinnacle_parse():
    mk = [{"matchupId": 7, "period": 0, "type": "moneyline", "limits": [{"amount": 5000}],
           "prices": [{"designation": "home", "price": -170}, {"designation": "away", "price": 150}]},
          {"matchupId": 7, "period": 0, "type": "total", "limits": [{"amount": 3000}],
           "prices": [{"designation": "over", "points": 228.5, "price": -105}, {"designation": "under", "points": 228.5, "price": -105}]},
          {"matchupId": 7, "period": 1, "type": "total", "prices": [{"designation": "over", "points": 114.5, "price": -110},
                                                                  {"designation": "under", "points": 114.5, "price": -110}]}]
    p = ns.pinnacle_main(mk, 7)
    assert abs(p[("ml", 0.0, "home")][0] + p[("ml", 0.0, "away")][0] - 1) < 1e-9
    assert abs(p[("game_total", 228.5, "over")][0] - 0.5) < 1e-9 and len(p) == 4   # bara hela matchen


def _x(key, edge, playable=True):
    return {"key": key, "edge": edge, "playable": playable, "reasons": [] if playable else ["redan ett spel i matchen (störst edge vinner)"]}


def test_blowout_blocks_over_and_releases_next():
    xs = [_x(("game_total", 228.5, "over"), 0.06), _x(("spread", -12.5, "home"), 0.04, False)]
    assert ns.blowout_block(xs, -13.0, {}) == 1
    assert not xs[0]["playable"] and "utklassningsrisk" in xs[0]["reasons"][0]
    assert xs[1]["playable"]                    # näst bästa spelet i matchen tar platsen
    xs = [_x(("game_total", 228.5, "over"), 0.06)]
    assert ns.blowout_block(xs, -3.0, {}) == 0 and xs[0]["playable"]


def test_run_records_and_settles(tmp_path):
    now = time.time()
    evd = {"id": "nba1", "home_team": "Boston Celtics", "away_team": "Los Angeles Lakers",
           "commence_time": now + 3600, "league": "NBA"}
    ns.KAMBI.clear(); ns.PIN.clear()
    ns.KAMBI["nba1"] = {"unibet": ns.kambi_main(RAW, evd["home_team"], evd["away_team"])}
    ns.PIN["nba1"] = {("game_total", 228.5, "over"): (0.53, 5000, False), ("game_total", 228.5, "under"): (0.47, 5000, False),
                      ("ml", 0.0, "home"): (0.60, 5000, False), ("ml", 0.0, "away"): (0.40, 5000, False)}

    class D:
        lines = []
        def log(self, x): self.lines.append(x)
    s = {"playable_books": ["unibet"]}
    ns.run(tmp_path, [evd], s, D(), {"nba1": -4.0})
    spel = Ledger(tmp_path / "nba_sides_spel.json")
    assert len(spel.bets) == 1 and spel.bets[0]["marknad"] == "game_total" and spel.bets[0]["spelare_id"] == "match"
    assert "totala poäng över 228.5" == spel.bets[0]["spel_text"]
    b = spel.bets[0]
    assert ns.settle(spel, {"nba1": (120, 115)}) and b["status"] == "vunnen"
