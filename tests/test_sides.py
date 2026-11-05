"""Fotboll sides & totals mot Pinnacle."""
from propsbot import sides
from propsbot.ledger import Ledger

S = {"sides_markets": ["1x2", "total", "ah"], "sides_min_edge": 0.03, "sides_max_edge": 0.10,
     "sides_alt_extra_edge": 0.01, "sides_odds_window": [1.60, 4.00], "sides_min_pin_limit": 1000,
     "max_odds_drop": 0.03, "sharp_against_pp": 2.0, "sharp_with_pp": 1.5, "sharp_min_age_s": 1800,
     "sides_max_units": 3}
EVD = {"id": "k1", "home_team": "A", "away_team": "B", "commence_time": 10_000, "league": "L"}


def _eval(kambi, pin, tmp_path, now=0):
    h = sides.History(tmp_path / "h.json")
    return {x["key"]: x for x in sides.evaluate(EVD, {"unibet": kambi}, pin, S, h, now, {"unibet"})}, h


def test_edge_rules_and_one_per_match(tmp_path):
    kambi = {("1x2", 0.0, "home"): 2.20, ("total", 2.5, "over"): 2.10, ("ah", -0.5, "home"): 2.18,
             ("1x2", 0.0, "away"): 5.0, ("total", 3.5, "over"): 3.30}
    pin = {("1x2", 0.0, "home"): (0.48, 20000, False),        # edge +5,6 %
           ("total", 2.5, "over"): (0.50, 20000, False),      # edge +5,0 %
           ("ah", -0.5, "home"): (0.48, 20000, True),         # +4,6 %, alternativ
           ("1x2", 0.0, "away"): (0.24, 20000, False),        # +20 % -> orimlig + utanför oddsram
           ("total", 3.5, "over"): (0.32, 500, False)}        # +5,6 % men svag referens
    r, _ = _eval(kambi, pin, tmp_path)
    assert r[("1x2", 0.0, "home")]["playable"]
    assert not r[("total", 2.5, "over")]["playable"]          # ett spel per match
    assert "redan ett spel" in r[("total", 2.5, "over")]["reasons"][-1]
    assert any("orimlig" in x for x in r[("1x2", 0.0, "away")]["reasons"])
    assert any("gräns" in x for x in r[("total", 3.5, "over")]["reasons"])


def test_odds_drop_and_sharp_against(tmp_path):
    k = ("total", 2.5, "under")
    _, h = _eval({k: 2.20}, {k: (0.50, 20000, False)}, tmp_path, now=0)
    h.save(0)
    r, _ = _eval({k: 2.10}, {k: (0.47, 20000, False)}, tmp_path, now=3600)
    reasons = " ".join(r[k]["reasons"])
    assert "fallit" in reasons and "sharp money mot oss" in reasons


def test_settle(tmp_path):
    lg = Ledger(tmp_path / "s.json")
    def bet(mk, ln, side, mid):
        return {"key": f"{mid}|{mk}|{ln}|{side}", "match_id": mid, "spelare_id": "match", "marknad": mk,
                "linje": ln, "sida": side, "odds": 2.0, "insats_pct": 0.004, "status": "öppen",
                "match": "A – B", "spel_text": "x", "bokford": 1}
    lg.bets = [bet("1x2", 0.0, "draw", "m1"), bet("total", 2.5, "over", "m2"), bet("ah", -0.5, "home", "m3"),
               bet("ah", 1.5, "away", "m4")]
    sides.settle(lg, {"m1": (1, 1), "m2": (2, 0), "m3": (1, 0), "m4": (2, 0)})
    assert [b["status"] for b in lg.bets] == ["vunnen", "förlorad", "vunnen", "förlorad"]
    assert lg.bets[0]["resultat_enheter"] == 0.004


def test_parsers():
    raw = {"betOffers": [
        {"criterion": {"englishLabel": "Full Time"}, "outcomes": [
            {"type": "OT_ONE", "odds": 1700}, {"type": "OT_CROSS", "odds": 3950}, {"type": "OT_TWO", "odds": 5500}]},
        {"criterion": {"englishLabel": "Total Goals"}, "outcomes": [
            {"type": "OT_OVER", "line": 2500, "odds": 1810}, {"type": "OT_UNDER", "line": 2500, "odds": 2000}]},
        {"criterion": {"englishLabel": "Asian Handicap"}, "outcomes": [
            {"label": "A", "line": -750, "odds": 1800}, {"label": "B", "line": 750, "odds": 1960}]},
        {"criterion": {"englishLabel": "Asian Handicap"}, "outcomes": [
            {"label": "A", "line": -500, "odds": 1630}, {"label": "B", "line": 500, "odds": 2200}]}]}
    km = sides.kambi_main(raw, "A", "B")
    assert km[("1x2", 0.0, "draw")] == 3.95 and km[("total", 2.5, "under")] == 2.0
    assert km[("ah", -0.5, "home")] == 1.63 and ("ah", -0.75, "home") not in km
    pin = sides.pinnacle_main([
        {"matchupId": 7, "period": 0, "type": "total", "isAlternate": False, "limits": [{"amount": 20000}],
         "prices": [{"designation": "over", "points": 2.5, "price": -110}, {"designation": "under", "points": 2.5, "price": -100}]},
        {"matchupId": 8, "period": 0, "type": "total", "prices": [{"designation": "over", "points": 9.5, "price": 100},
                                                                  {"designation": "under", "points": 9.5, "price": -120}]}], 7)
    assert set(pin) == {("total", 2.5, "over"), ("total", 2.5, "under")}
    assert abs(sum(v[0] for v in pin.values()) - 1) < 1e-9
