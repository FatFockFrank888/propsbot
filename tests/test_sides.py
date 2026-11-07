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
    assert km[("ah", -0.5, "home")] == 1.63 and km[("ah", -0.75, "home")] == 1.80
    pin = sides.pinnacle_main([
        {"matchupId": 7, "period": 0, "type": "total", "isAlternate": False, "limits": [{"amount": 20000}],
         "prices": [{"designation": "over", "points": 2.5, "price": -110}, {"designation": "under", "points": 2.5, "price": -100}]},
        {"matchupId": 8, "period": 0, "type": "total", "prices": [{"designation": "over", "points": 9.5, "price": 100},
                                                                  {"designation": "under", "points": 9.5, "price": -120}]}], 7)
    assert set(pin) == {("total", 2.5, "over"), ("total", 2.5, "under")}
    assert abs(sum(v[0] for v in pin.values()) - 1) < 1e-9


def test_espn_import():
    from propsbot.sources.http import JsonClient  # noqa: F401 – samma import som sides.run använder
    import inspect
    assert "from .sources.http import JsonClient" in inspect.getsource(sides.run)


def test_asian_settlement():
    r = sides.result_units
    st = 0.01
    assert r("ah", 0.0, "home", 1, 1, 2.0, st) == 0.0                          # hel linje: push
    assert abs(r("ah", -0.25, "home", 1, 1, 2.0, st) + 0.005) < 1e-12          # halv förlust
    assert abs(r("ah", -0.75, "home", 2, 1, 2.0, st) - 0.005) < 1e-12          # halv vinst
    assert abs(r("ah", -0.75, "home", 3, 1, 2.0, st) - 0.01) < 1e-12           # full vinst
    assert abs(r("ah", 0.25, "away", 1, 1, 2.0, st) - 0.005) < 1e-12           # borta +0.25 oavgjort: halv vinst
    assert abs(r("total", 2.25, "over", 1, 1, 2.0, st) + 0.005) < 1e-12        # 2 mål: halv förlust
    assert abs(r("total", 2.75, "under", 2, 1, 2.0, st) + 0.005) < 1e-12       # 3 mål: halv förlust
    assert r("total", 3.0, "under", 2, 1, 2.0, st) == 0.0                       # 3 mål: push
    assert sides.parts(2.25) == [2.0, 2.5] and sides.parts(-0.75) == [-1.0, -0.5] and sides.parts(1.0) == [1.0]


def test_asian_total_parsed_and_status_push(tmp_path):
    raw = {"betOffers": [{"criterion": {"englishLabel": "Asian Total"}, "outcomes": [
        {"type": "OT_OVER", "line": 2250, "odds": 1580}, {"type": "OT_UNDER", "line": 2250, "odds": 2300}]}]}
    assert sides.kambi_main(raw, "A", "B")[("total", 2.25, "under")] == 2.30
    lg = Ledger(tmp_path / "s.json")
    lg.bets = [{"key": "k", "match_id": "m", "spelare_id": "match", "marknad": "ah", "linje": 0.0, "sida": "home",
                "odds": 1.9, "insats_pct": 0.004, "status": "öppen", "match": "A – B", "spel_text": "x", "bokford": 1}]
    sides.settle(lg, {"m": (0, 0)})
    assert lg.bets[0]["status"] == "push" and lg.bets[0]["resultat_enheter"] == 0.0


def test_pinnacle_limit_tiers(tmp_path):
    s = dict(S, sides_min_pin_limit=500, sides_low_limit=2000, sides_low_limit_extra_edge=0.01)
    k = ("total", 2.5, "over")
    h = sides.History(tmp_path / "h.json")
    def ev(lim):
        return sides.evaluate(EVD, {"unibet": {k: 2.07}}, {k: (0.50, lim, False)}, s, h, 0, {"unibet"})[0]
    assert ev(5000)["playable"]                       # edge 3,5 % >= 3 %
    low = ev(1000)                                    # svag referens: kräver 4 %
    assert not low["playable"] and "gräns 1000" in low["reasons"][0]
    assert any("för svag referens" in r for r in ev(400)["reasons"])


def test_smarkets_second_reference(tmp_path):
    import time
    from propsbot.sides import History, evaluate
    s = {"sides_min_edge": 0.03, "sides_max_edge": 0.10, "sides_odds_window": [1.4, 6.0], "sides_min_pin_limit": 500,
         "sides_low_limit": 2000, "playable_books": ["unibet"]}
    evd = {"id": "e1", "home_team": "A", "away_team": "B", "commence_time": time.time() + 7200}
    kambi = {"unibet": {("total", 2.5, "over"): 2.10}}
    pin = {("total", 2.5, "over"): (0.52, 5000, False)}
    h = History(tmp_path / "h.json")
    x = evaluate(evd, kambi, pin, s, h, time.time(), {"unibet"})[0]                    # bara Pinnacle
    assert x["playable"] and abs(x["edge"] - (0.52 * 2.10 - 1)) < 1e-9
    x = evaluate(evd, kambi, pin, s, h, time.time(), {"unibet"}, smk={("total", 2.5, "over"): (0.50, 100)})[0]
    assert abs(x["p"] - 0.51) < 1e-9 and x["p_pin"] == 0.52 and x["p_smk"] == 0.50 and x["playable"]
    x = evaluate(evd, kambi, pin, s, h, time.time(), {"unibet"}, smk={("total", 2.5, "over"): (0.46, 100)})[0]
    assert not x["playable"] and any("Smarkets håller inte med" in r for r in x["reasons"])


def test_corners_vs_smarkets(tmp_path):
    import time
    from propsbot.sides import History, evaluate, result_units
    s = {"sides_min_edge": 0.03, "sides_max_edge": 0.10, "sides_odds_window": [1.4, 6.0], "playable_books": ["unibet"],
         "sides_markets": ["corners"]}
    evd = {"id": "e1", "home_team": "A", "away_team": "B", "commence_time": time.time() + 7200}
    kambi = {"unibet": {("corners", 9.5, "over"): 2.10}}
    h = History(tmp_path / "h.json")
    assert evaluate(evd, kambi, {}, s, h, time.time(), {"unibet"}) == []                     # ingen referens
    x = evaluate(evd, kambi, {}, s, h, time.time(), {"unibet"}, smk={("corners", 9.5, "over"): (0.52, 150)})[0]
    assert abs(x["edge"] - (0.52 * 2.10 - 1)) < 1e-9 and x["playable"]                        # 9,2 % >= 3 + 1 %
    x = evaluate(evd, kambi, {}, s, h, time.time(), {"unibet"}, smk={("corners", 9.5, "over"): (0.49, 150)})[0]
    assert not x["playable"]                                                                   # 2,9 % < 4 %
    assert result_units("corners", 9.5, "over", 6, 4, 2.0, 0.01) > 0 and result_units("corners", 9.5, "over", 5, 4, 2.0, 0.01) < 0
