"""Sammanslagna boten: spelarspärr, kort, NHL-testmarknader, webbsidans NHL-format."""
import math
from datetime import date

from propsbot.notify import PlayerGuard
from propsbot.sources.props_text import market_from_label


def test_player_guard_one_bet_per_player_and_match(tmp_path):
    g = PlayerGuard(tmp_path / "g.json")
    assert g.allows("nba", "m1", "LeBron James", "points|25.5")
    g.mark("nba", "m1", "LeBron James", "points|25.5")
    g.save()
    g = PlayerGuard(tmp_path / "g.json")
    assert g.allows("nba", "m1", "Lebron James", "points|25.5")          # samma spel: ok (omskick)
    assert not g.allows("nba", "m1", "LeBron James", "rebounds|7.5")     # annan marknad: nej
    assert not g.allows("nba", "m1", "LeBron James", "points|25.5|under")
    assert g.allows("nba", "m2", "LeBron James", "points|25.5")          # annan match: ok


def test_card_labels():
    assert market_from_label("To Get a Card") == ("cards", 0.5)
    assert market_from_label("To Get a Red Card") is None
    assert market_from_label("To Score or Get a Card") is None


def test_nhl_test_market_parse_and_poisson():
    from nhl.test_markets import market_of, parse_kambi, poisson_at_least
    assert market_of("Player to score at least 2 points - Including Overtime") == ("nhl_points", 1.5)
    assert market_of("Player to record at least 1 assists - Including Overtime") == ("nhl_assists", 0.5)
    assert market_of("To score - Including Overtime") == ("nhl_goals", 0.5)
    assert market_of("Player To score at least 1 Power Play Points -  Including Overtime") == ("nhl_pp_points", 0.5)
    assert market_of("Player To score at least 2 Power Play Points -  Including Overtime") == ("nhl_pp_points", 1.5)
    assert market_of("Total Power Play Goals by Utah Mammoth - Including Overtime") is None
    assert market_of("Total Power Play Goals - Including Overtime") is None
    assert market_of("Player's shots on goal - Including Overtime") is None
    raw = {"betOffers": [{"criterion": {"englishLabel": "Player to score at least 1 points - Including Overtime"},
                          "outcomes": [{"participant": "A B", "englishLabel": "Yes", "line": 1000, "odds": 2950},
                                       {"participant": "A B", "englishLabel": "No", "line": 1000, "odds": 1360}]}]}
    qs = parse_kambi(raw, "unibet")
    assert {(q.side, q.line, q.odds) for q in qs} == {("over", 0.5, 2.95), ("under", 0.5, 1.36)}
    assert abs(poisson_at_least(1, 0.5) - (1 - math.exp(-0.5))) < 1e-12


def test_nhl_pp_points_settle_from_game_log(tmp_path):
    from nhl.bot_settings import BotSettings
    from nhl.test_markets import TestMarkets
    tm = TestMarkets(tmp_path, BotSettings())
    tm.bets = [{"game_id": 5, "spelare_id": 9, "status": "öppen", "avspark": 1000, "marknad": "nhl_pp_points",
                "linje": 0.5, "sida": "over", "odds": 3.0, "insats_pct": 0.002}]
    box = {"gameState": "OFF", "playerByGameStats": {"homeTeam": {"forwards": [{"playerId": 9, "goals": 1, "assists": 0}]}}}
    assert tm.settle(lambda gid: box, now=1e10, fetch_pp=lambda pid, gid: None) == 0   # game log not updated yet
    assert tm.bets[0]["status"] == "öppen"
    assert tm.settle(lambda gid: box, now=1e10, fetch_pp=lambda pid, gid: {"pp_points": 1, "pp_goals": 1}) == 1
    assert tm.bets[0]["status"] == "vunnen" and tm.bets[0]["utfall"] == 1


def test_nhl_test_market_settles_from_boxscore(tmp_path):
    from nhl.bot_settings import BotSettings
    from nhl.test_markets import TestMarkets
    tm = TestMarkets(tmp_path, BotSettings())
    tm.bets = [{"game_id": 5, "spelare_id": 9, "status": "öppen", "avspark": 1000, "marknad": "nhl_points",
                "linje": 0.5, "sida": "under", "odds": 1.4, "insats_pct": 0.004}]
    box = {"gameState": "OFF", "playerByGameStats": {"homeTeam": {"forwards": [{"playerId": 9, "goals": 0, "assists": 0}]}}}
    assert tm.settle(lambda gid: box, now=1e10) == 1
    assert tm.bets[0]["status"] == "vunnen" and abs(tm.bets[0]["resultat_enheter"] - 0.0016) < 1e-9


def test_nhl_ledger_to_site_format():
    from nhl.site_export import ledger_sv
    b = {"id": "x", "created": "2026-11-04T16:00:00+00:00", "game_id": 1, "game": "OTT@BUF",
         "start": "2026-11-05T00:30:00+00:00", "player": "Tim Stützle", "player_id": 7, "line": 2.5, "side": "under",
         "book": "unibet", "odds": 1.9, "units": 3, "p_fair": 0.56, "edge": 0.064, "model_edge": 0.05,
         "close_odds": 1.85, "status": "won", "result_sog": 1, "profit_units": 2.7, "reasons": []}
    x = ledger_sv(b, 0.002)
    assert x["status"] == "vunnen" and x["marknad"] == "sog" and x["sida"] == "under"
    assert x["match"] == "OTT – BUF" and abs(x["insats_pct"] - 0.006) < 1e-12 and abs(x["resultat_enheter"] - 0.0054) < 1e-12


def test_dailyfaceoff_pp_units_parse():
    import json
    from nhl.pp_model import parse_dfo
    data = {"props": {"pageProps": {"combinations": {"sourceName": "Projected", "updatedAt": "x", "players": [
        {"name": "Lane Hutson", "categoryIdentifier": "ev", "groupIdentifier": "d1"},
        {"name": "Lane Hutson", "categoryIdentifier": "pp", "groupIdentifier": "pp1"},
        {"name": "Noah Dobson", "categoryIdentifier": "pp", "groupIdentifier": "pp2"},
        {"name": "Noah Dobson", "categoryIdentifier": "pk", "groupIdentifier": "pk2"},
        {"name": "Ivan Demidov", "categoryIdentifier": "oi", "groupIdentifier": "ir", "injuryStatus": "ir"}]}}}}
    html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(data) + "</script>"
    d = parse_dfo(html)
    p = d["players"]
    assert p["lane hutson"]["pp"] == 1 and p["lane hutson"]["lineup"]
    assert p["noah dobson"]["pp"] == 2 and p["noah dobson"]["pk"] == 2
    assert p["ivan demidov"]["out"]
    assert d["source"] == "Projected"


def test_news_blocks_and_rechecks(tmp_path):
    import time
    from types import SimpleNamespace as NS
    from propsbot.news import block_nba, nba_status_fn, recheck
    inj = {"lebron james": "out", "anthony davis": "questionable"}
    def row(name):
        d = NS(playable=True, stake=0.01, reasons=[], cand=NS(player_name=name))
        return NS(row=NS(decision=d))
    rows = [row("LeBron James"), row("Anthony Davis"), row("Austin Reaves")]
    assert block_nba(rows, inj) == (1, 1)
    assert not rows[0].row.decision.playable and rows[1].row.decision.playable and rows[2].row.decision.playable
    lg = NS(bets=[{"status": "öppen", "avspark": time.time() + 3600, "spelare": "Anthony Davis", "odds": 1.8,
                   "bolag": "unibet", "match": "LAL – BOS", "marknad": "points", "linje": 20.5}])
    logs = []
    assert recheck(lg, nba_status_fn(inj), {}, "NBA", False, logs.append) == 1
    assert lg.bets[0]["nyhet_status"] == "questionable"
    assert recheck(lg, nba_status_fn(inj), {}, "NBA", False, logs.append) == 0          # bara en gång
    assert recheck(lg, nba_status_fn({}), {}, "NBA", False, logs.append) == 1           # borta från listan
    assert lg.bets[0]["nyhet_status"] == "ok"


def test_graduation_up_and_down(tmp_path):
    from propsbot.graduation import check
    s = {"graduation_min_bets": 50, "graduation_min_t": 1.0}
    assert not check(tmp_path, "sides", [1.0, 2.0, -0.5] * 10, s, "Sides", False, lambda *_: None)   # för få spel
    good = [2.0, 1.0, -0.5, 1.5, 0.5] * 10                                                            # 50 spel, snitt +0,9
    assert check(tmp_path, "sides", good, s, "Sides", False, lambda *_: None)
    assert check(tmp_path, "sides", good + [-0.2], s, "Sides", False, lambda *_: None)               # stannar uppe
    assert not check(tmp_path, "sides", [-1.0, -0.5, 0.2] * 12, s, "Sides", False, lambda *_: None)  # vänt -> ner


def test_news_teammate_out_role_shift():
    import time
    from types import SimpleNamespace as NS
    from propsbot.news import nba_teammate_fn, recheck
    now = time.time()
    team = NS(name="Phoenix Suns", players={"khaman maluach": NS(minutes=22.0), "mark williams": NS(minutes=28.0),
                                            "bench guy": NS(minutes=6.0)})
    last = {"models": {"m1": {"khaman maluach": {"rebounds": 7.4, "_min": 30.0}}}, "teams": {"m1": (team, None)}}
    bet = {"status": "öppen", "avspark": now + 7200, "bokford": now - 3600, "match_id": "m1", "spelare": "Khaman Maluach",
           "spelare_id": "khaman maluach", "marknad": "rebounds", "linje": 5.5, "sida": "under", "odds": 2.08,
           "bolag": "unibet", "match": "PHX – ORL", "modell_edge": 0.21}
    old = {"key": "mark williams", "name": "Mark Williams", "team": "Phoenix Suns", "status": "out", "ts": now - 86400}
    new = dict(old, ts=now - 60)
    bench = {"key": "bench guy", "name": "Bench Guy", "team": "Phoenix Suns", "status": "out", "ts": now - 60}
    lg = NS(bets=[bet])
    assert recheck(lg, nba_teammate_fn(last, [old, bench], {"rebounds": 10}), {}, "NBA", False, print, field="nyhet_lag") == 0
    assert recheck(lg, nba_teammate_fn(last, [new], {"rebounds": 10}), {}, "NBA", False, print, field="nyhet_lag") == 1
    assert "Mark Williams" in bet["nyhet"] and "edge vid 2.08" in bet["nyhet"] and bet["nyhet_status"].startswith("lag:")
    assert recheck(lg, nba_teammate_fn(last, [new], {"rebounds": 10}), {}, "NBA", False, print, field="nyhet_lag") == 0


def test_top5_notify_once(tmp_path, monkeypatch):
    import json, time
    from datetime import datetime, timezone
    import propsbot.notify as nt
    from propsbot import top5
    site = tmp_path / "site"; (site / "nba").mkdir(parents=True); (site / "nhl").mkdir()
    start = datetime.fromtimestamp(time.time() + 3 * 3600, timezone.utc).strftime("%Y-%m-%d %H:%M")
    rows = [{"spelare": f"P{i}", "match": f"M{i}", "spel": "poäng över 20.5", "marknad": "points", "odds": 2.0,
             "spela_fran": 1.9, "edge": 0.05 + i / 100, "spelbar": True, "live": True, "avspark": start, "bolag": "unibet",
             "insats_forslag": 0.01, "kommentar": ""} for i in range(7)]
    (site / "nba" / "data.json").write_text(json.dumps({"radar": rows}), encoding="utf-8")
    sent = []
    monkeypatch.setattr(nt, "send", lambda *a, **k: sent.append(a[1]) or True)
    assert top5.notify(tmp_path, {"ntfy_topic": "x"}, log=lambda *_: None) == 5
    assert sent[0].startswith("TOPP 5 #1: P6")
    assert top5.notify(tmp_path, {"ntfy_topic": "x"}, log=lambda *_: None) == 0     # inga dubbletter
