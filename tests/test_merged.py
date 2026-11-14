"""Sammanslagna boten: spelarspärr, kort, lagnyheter, graduering, topp 5."""
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
    weak = [2.0, 1.0, -0.5, 1.5, 0.5, -1.0, -1.5, 3.0, -2.0, 1.0] * 5                                 # snitt +0,4, t ≈ 1,9
    assert not check(tmp_path, "sides", weak, s, "Sides", False, lambda *_: None)                     # slumpnivå räcker inte
    good = [2.0, 1.0, -0.5, 1.5, 0.5] * 10                                                            # 50 spel, snitt +0,9, t ≈ 6
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


def test_top5_no_push_by_default_and_stable(tmp_path, monkeypatch):
    """Dagens topp 5 rankas på bokförda LIVE-spel och ligger kvar när oddset faller eller matchen startat.
    Ingen egen notis som standard (14/11): topp 5-spelen har redan fått en LIVE-notis."""
    import json
    from datetime import datetime, timezone
    import propsbot.notify as nt
    from propsbot import top5
    site = tmp_path / "site"; (site / "nba").mkdir(parents=True)
    now = datetime(2026, 11, 12, 11, 0, tzinfo=timezone.utc).timestamp()   # kl. 12 svensk tid
    bets = [{"spelare": f"P{i}", "match": f"M{i}", "marknad": "points", "linje": 20.5, "sida": "over", "odds": 2.0,
             "spela_fran": 1.9, "edge": 0.05 + i / 100, "avspark": now + 3 * 3600, "bolag": "unibet",
             "insats_pct": 0.01, "status": "öppen", "stopp": "", "bokford": now - 600} for i in range(7)]
    (site / "nba" / "data.json").write_text(json.dumps({"live": True, "bokforing": bets}), encoding="utf-8")
    sent = []
    monkeypatch.setattr(nt, "send", lambda *a, **k: sent.append(a[1]) or True)
    assert top5.notify(tmp_path, {"ntfy_topic": "x"}, log=lambda *_: None, now=now) == 0     # av som standard
    assert not sent
    on = {"ntfy_topic": "x", "top5_notify": True}
    assert top5.notify(tmp_path, on, log=lambda *_: None, now=now) == 5
    assert sent[0].startswith("TOPP 5 #1: P6")
    assert top5.notify(tmp_path, on, log=lambda *_: None, now=now) == 0     # inga dubbletter
    # oddset rasar och P6 startar: rankingen är densamma (styrkan räknas på bokningen)
    bets[6].update(stangning=1.5, status="vunnen")
    (site / "nba" / "data.json").write_text(json.dumps({"live": True, "bokforing": bets}), encoding="utf-8")
    assert [x["spelare"] for x in top5.ranking(site, now + 4 * 3600)][:2] == ["P6", "P5"]
    # NBA-natten (kl. 02 svensk tid) hör till kvällen innan
    assert top5.play_day(datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc).timestamp()) == "2026-11-12"


def test_cleanup_removes_nhl_state(tmp_path):
    from propsbot.__main__ import _cleanup
    (tmp_path / "nhl").mkdir(); (tmp_path / "nhl" / "nhl_live.json").write_text("[]")
    (tmp_path / "site" / "nhl").mkdir(parents=True); (tmp_path / "site" / "csv").mkdir()
    (tmp_path / "site" / "csv" / "nhl.csv").write_text("x"); (tmp_path / "site" / "csv" / "nba.csv").write_text("x")
    (tmp_path / "nba_live.json").write_text("[]")
    _cleanup(tmp_path)
    assert not (tmp_path / "nhl").exists() and not (tmp_path / "site" / "nhl").exists()
    assert not (tmp_path / "site" / "csv" / "nhl.csv").exists()
    assert (tmp_path / "site" / "csv" / "nba.csv").exists() and (tmp_path / "nba_live.json").exists()


def test_strength_units_scale():
    """Insats 1–10u efter styrkan: svaga spel 1u, de starkaste 10u (max)."""
    from propsbot.strength import score, units_for, units_from, stake_text
    assert [units_for(s) for s in (3, 7, 9.5, 11, 14, 17, 20, 30)] == [1, 1, 3, 4, 6, 8, 10, 10]
    assert units_from(0.05) == 1                          # 5 % edge utan modell: styrka 6
    assert units_from(0.10, 0.10) == 7                    # 10 + 5 + 1 = 16
    assert units_from(0.13, 0.14, sharp=1) == 10          # 13 + 7 + 1 + 1 = 22
    assert units_from(0.13, 0.14, sharp=1, cap=5) == 5
    assert score(0.20) == 15 - 2.5 + 1                     # edge över 15 dras ner
    assert "MAX" in stake_text(10) and "MAX" not in stake_text(9)


def test_live_stake_follows_strength():
    """NBA LIVE: insatsen följer styrkan, inte Kelly-taket – starkare spel får fler units."""
    from types import SimpleNamespace as NS
    from propsbot.live import select_live

    def row(pid, edge, me):
        cand = NS(match_id=f"m{pid}", player_id=pid, market="assists", line=5.5, best=NS(side="over", odds=2.0, book="unibet"),
                  edge=edge, now=0.0, minutes_to_kickoff=600)
        d = NS(cand=cand, playable=True, show=True, stake=0.02, reasons=[])
        return NS(row=NS(decision=d), n_groups=3), NS(row=NS(decision=NS(cand=NS(**{**cand.__dict__, "edge": me}))))
    a, ma = row("a", 0.06, 0.06)
    b, mb = row("b", 0.14, 0.15)
    out = select_live([a, b], [ma, mb], {"live_min_edge": {"assists": 0.05}, "live_odds_window": [1.6, 3.0]},
                      NS(bets=[]))
    assert {r.row.decision.cand.player_id: round(r.live_stake / 0.002) for r in out} == {"a": 3, "b": 10}
