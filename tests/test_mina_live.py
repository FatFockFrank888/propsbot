import json
import time

from propsbot import livewatch, mina


def nba_summ(reb, state="in", done=False, detail="Q3 5:12", h=78, a=70):
    return {"header": {"competitions": [{"status": {"type": {"state": state, "completed": done, "shortDetail": detail}},
                                         "competitors": [{"homeAway": "home", "score": str(h), "team": {"abbreviation": "TOR"}},
                                                         {"homeAway": "away", "score": str(a), "team": {"abbreviation": "WAS"}}]}]},
            "boxscore": {"players": [{"statistics": [{"labels": ["MIN", "PTS", "3PT", "REB", "AST"],
                                                      "athletes": [{"athlete": {"displayName": "Immanuel Quickley"},
                                                                    "stats": ["20", "12", "2-5", str(reb), "4"]}]}]}]}}


def soc_summ(events, state="in", done=False, sot=0):
    return {"header": {"competitions": [{"status": {"type": {"state": state, "completed": done, "shortDetail": "60'"}},
                                         "competitors": [{"homeAway": "home", "score": "1", "team": {"abbreviation": "ARS"}},
                                                         {"homeAway": "away", "score": "0", "team": {"abbreviation": "CHE"}}]}]},
            "keyEvents": events,
            "rosters": [{"roster": [{"athlete": {"displayName": "Bukayo Saka"}, "stats": [{"name": "shotsOnTarget", "value": sot}]}]}]}


NOW = time.time()
BET = {"ident": "nba|m1|iq", "sport": "nba", "spelare": "Immanuel Quickley", "spelare_id": "iq", "marknad": "rebounds",
       "linje": 3.5, "sida": "over", "match": "Toronto Raptors – Washington Wizards", "avspark": NOW - 3600,
       "status": "öppen", "units": 2, "odds": 2.06, "espn": ["basketball/nba", "1"]}


def run_steps(bets, summaries):
    sent, it = [], iter(summaries)
    w = livewatch.Watcher({"ntfy_topic": "t"}, send=lambda t, m, p, g: sent.append((t, m, p)), get=lambda *a, **k: next(it), log=lambda *_: None)
    for _ in summaries:
        w.step(bets, NOW)
    return sent


def test_nba_increments_then_won_then_silent():
    sent = run_steps([dict(BET)], [nba_summ(1), nba_summ(2), nba_summ(3), nba_summ(4), nba_summ(5)])
    titles = [t for t, _m, _p in sent]
    assert titles[0].startswith("👀 Bevakar")
    assert "+1 returer → 2 av 3,5" in titles[1] and "+1 returer → 3 av 3,5" in titles[2]
    assert titles[3].startswith("🏀") and titles[4].startswith("✅ VUNNET")
    assert len(sent) == 5                                   # inget efter att spelet är vunnet


def test_under_loses_and_final():
    b = dict(BET, sida="under")
    sent = run_steps([b], [nba_summ(3), nba_summ(4)])
    assert sent[-1][0].startswith("❌ FÖRLORAT")
    b2 = dict(BET, sida="under", ident="x")
    sent = run_steps([b2], [nba_summ(2), nba_summ(2, state="post", done=True, detail="Final")])
    assert sent[-1][0].startswith("🏁 Slut")


def test_soccer_goal_red_var_and_player():
    b = {"ident": "f|m|saka", "sport": "fotboll", "spelare": "Bukayo Saka", "spelare_id": "saka", "marknad": "shots_on_target",
         "linje": 1.5, "sida": "over", "match": "Arsenal – Chelsea", "avspark": NOW - 1800, "status": "öppen", "units": 1,
         "odds": 2.1, "espn": ["soccer/all", "9"]}
    g = {"id": "1", "type": {"text": "Goal"}, "clock": {"displayValue": "55'"}, "team": {"displayName": "Arsenal"},
         "participants": [{"athlete": {"displayName": "Bukayo Saka"}}], "scoringPlay": True}
    r = {"id": "2", "type": {"text": "Red Card"}, "clock": {"displayValue": "58'"}, "team": {"displayName": "Chelsea"}}
    y = {"id": "3", "type": {"text": "Yellow Card"}}
    sent = run_steps([b], [soc_summ([], sot=0), soc_summ([g, y], sot=1), soc_summ([g, r, y], sot=1), soc_summ([r, y], sot=2)])
    t = [x[0] for x in sent]
    assert any(x.startswith("⚽ MÅL 55'") for x in t) and any(x.startswith("🟥 RÖTT KORT") for x in t)
    assert not any("Yellow" in x for x in t)               # gula kort ger ingen pling
    assert any(x.startswith("↩️ MÅL BORTDÖMT") for x in t)
    assert any("+1 skott på mål → 1 av 1,5" in x for x in t) and t[-1].startswith("✅ VUNNET")


def test_messages_and_user_result(tmp_path):
    tiers = {"nba|m1|iq": {"ident": "nba|m1|iq", "sport": "nba", "tier": "A", "kalla_fil": "nba_live.json", "kalla_key": "k",
                           "odds": 2.0, "bolag": "unibet", "avspark": NOW - 7200, "marknad": "rebounds", "linje": 3.5}}
    book = mina.Book(tmp_path / "mina_spel.json")
    msgs = [{"id": "a", "time": 1, "event": "message", "message": json.dumps({"v": 1, "typ": "tog", "ident": "nba|m1|iq", "odds": 2.2, "units": 2})},
            {"id": "b", "time": 2, "event": "message", "message": json.dumps({"v": 1, "typ": "tog", "ident": "nba|m1|iq", "odds": 2.3, "units": 3})},
            {"id": "c", "time": 3, "event": "message", "message": "skräp"}]
    assert mina.apply_messages(book, msgs, tiers, NOW) == 2
    b = book.bets["nba|m1|iq"]
    assert b["odds"] == 2.3 and b["units"] == 3 and b["bot_odds"] == 2.0 and b["tier"] == "A"
    assert mina.apply_messages(book, msgs, tiers, NOW) == 0          # samma meddelanden igen: inget
    (tmp_path / "nba_live.json").write_text(json.dumps([{"key": "k", "status": "vunnen", "odds": 2.0, "insats_pct": 0.002,
                                                         "resultat_enheter": 0.002, "skarp_stang_p": 0.5, "utfall": 5}]))
    mina.settle(book, tmp_path, NOW)
    assert b["status"] == "vunnen" and abs(b["resultat_u"] - 3 * 1.3) < 1e-9 and abs(b["clv_pp"] - (0.5 - 1 / 2.3) * 100) < 1e-9
    mina.apply_messages(book, [{"id": "d", "time": 4, "event": "message", "message": json.dumps({"v": 1, "typ": "angra", "ident": "nba|m1|iq"})}], tiers, NOW)
    assert not book.bets


def test_half_win_on_quarter_line():
    b = {"status": "vunnen", "units": 2, "odds": 2.0}
    src = {"insats_pct": 0.01, "resultat_enheter": 0.0045, "odds": 1.9}       # halv vinst på 1,90
    assert abs(mina._user_result(b, src) - 0.0045 / 0.01 / 0.9 * 1.0 * 2) < 1e-9


def test_pairing_link_once(tmp_path, monkeypatch):
    import propsbot.notify as nt
    sent = []
    monkeypatch.setattr(nt, "send", lambda topic, title, msg, **k: sent.append((topic, k.get("click"))) or True)
    s = {"ntfy_topic": "propsbot-abc"}
    assert mina.send_pairing_link(tmp_path, s, log=lambda *_: None)
    assert not mina.send_pairing_link(tmp_path, s, log=lambda *_: None)          # bara en gång per kanal
    assert sent == [("propsbot-abc", "https://fatfockfrank888.github.io/propsbot/#koppla=propsbot-abc")]
    assert "propsbot-abc" not in (tmp_path / "koppling_skickad.txt").read_text()   # bara en hash sparas
