"""Odds Alert (oddsvakt.py): matchning mot Kambi, lägen, spärrar, egna bevakningar och sparat läge. Inget nätverk."""
import json
import time

import propsbot.notify as nt
from propsbot import oddsvakt as ov

NOW = time.time()
KO = NOW + 6 * 3600
S = {"kambi_offerings": {"ubse": "unibet", "svenskaspel": "svenskaspel"}, "tier_b_min_edge": 0.05,
     "oddsvakt_bekrafta": 2, "oddsvakt_cooldown_s": 600, "site_url": "https://x/"}

NBA_BET = {"ident": "nba|nba111|gui santos", "sport": "nba", "tier": "B", "notis": True, "status": "öppen",
           "match_id": "nba111", "match": "Golden State Warriors – Boston Celtics", "hemma": "Golden State Warriors",
           "borta": "Boston Celtics", "avspark": KO, "spelare": "Gui Santos", "spelare_id": "gui santos",
           "marknad": "pa", "linje": 10.5, "sida": "under", "spel_text": None, "bolag": "unibet", "odds": 1.97,
           "spela_fran": 1.88, "bokford": NOW - 60, "kalla_fil": "nba_bokforing_v2.json", "kalla_key": "k1"}
SIDE_BET = {"ident": "fotboll|k222|match|mål", "sport": "fotboll", "tier": "A", "notis": True, "status": "öppen",
            "match_id": "k222", "match": "Örgryte IS – Kalmar FF", "hemma": "Örgryte IS", "borta": "Kalmar FF",
            "avspark": KO, "spelare": "Kalmar FF", "spelare_id": "match", "marknad": "1x2", "linje": 0.0, "sida": "away",
            "spel_text": "1X2: 2", "bolag": "unibet", "odds": 2.2, "spela_fran": 2.15, "pin_stang_p": 0.4885,
            "bokford": NOW - 60, "kalla_fil": "sides_spel.json", "kalla_key": "k222|1x2|0|away|unibet"}


def nba_raw(odds=1.97, status="OPEN"):
    return {"betOffers": [
        {"criterion": {"englishLabel": "Points & Assists by the player - Including Overtime"},
         "outcomes": [{"participant": "Gui Santos", "participantId": 9, "type": "OT_OVER", "line": 10500, "odds": 1770, "status": status},
                      {"participant": "Gui Santos", "participantId": 9, "type": "OT_UNDER", "line": 10500, "odds": int(odds * 1000), "status": status},
                      {"participant": "Gui Santos", "participantId": 9, "type": "OT_UNDER", "line": 11500, "odds": 2300}]},
        {"criterion": {"englishLabel": "Points scored by the player - Including Overtime"},
         "outcomes": [{"participant": "Gui Santos", "participantId": 9, "type": "OT_UNDER", "line": 10500, "odds": 3000}]}]}


def side_raw(away=2.2):
    return {"betOffers": [{"criterion": {"englishLabel": "Full Time"},
                           "outcomes": [{"type": "OT_ONE", "odds": 3100}, {"type": "OT_CROSS", "odds": 3400},
                                        {"type": "OT_TWO", "odds": int(away * 1000)}]}]}


def setup(tmp_path, bets, mina=None):
    (tmp_path / "tiers.json").write_text(json.dumps({"bets": bets}), encoding="utf-8")
    if mina is not None:
        (tmp_path / "mina_spel.json").write_text(json.dumps({"spel": {i: {"ident": i} for i in mina}}), encoding="utf-8")


def vakt(tmp_path, seq, settings=S):
    """Vakt med en följd av Kambi-svar (ett per läsning; samma svar för alla spel i läsningen)."""
    sent, calls = [], []
    state = {"raw": None}

    def fetch(code, eid):
        calls.append((code, eid))
        r = state["raw"]
        if isinstance(r, Exception):
            raise r
        return r
    v = ov.Vakt(tmp_path, settings, send=lambda t, m, p, c: sent.append((t, m, p, c)) or True, fetch=fetch, log=lambda *_: None)

    def run(now=NOW):
        for i, r in enumerate(seq):
            state["raw"] = r
            v.step(now + i * 30)
        v.save(now + len(seq) * 30)
    return v, sent, calls, run


# ------------------------------------------------------------------ matchning
def test_find_odds_nba_prop_and_side():
    assert ov.find_odds(NBA_BET, nba_raw(2.05)) == 2.05            # rätt marknad (PA), linje, sida, spelare
    assert ov.find_odds(NBA_BET, nba_raw(status="SUSPENDED")) is None
    assert ov.find_odds(dict(NBA_BET, spelare="Someone Else", spelare_id="someone else"), nba_raw()) is None
    assert ov.find_odds(SIDE_BET, side_raw(2.3)) == 2.3
    assert ov.find_odds(dict(SIDE_BET, sida="home"), side_raw()) == 3.1
    assert ov.find_odds(SIDE_BET, None) is None
    assert ov.event_id("k222") == 222 and ov.event_id("nba111") == 111 and ov.event_id("x5") is None


def test_find_odds_football_prop():
    raw = {"betOffers": [{"criterion": {"englishLabel": "Player's shots on target"},
                          "outcomes": [{"participant": "Saka, Bukayo", "participantId": 5, "type": "OT_OVER", "label": "Over",
                                        "line": 1500, "odds": 2400}]}]}
    b = {"sport": "fotboll", "spelare": "Bukayo Saka", "spelare_id": "bukayo saka", "marknad": "shots_on_target",
         "linje": 1.5, "sida": "over", "match_id": "k9"}
    assert ov.find_odds(b, raw) == 2.4
    assert ov.find_odds(dict(b, linje=2.5), raw) is None


def test_required_odds_uses_fresh_sharp_p():
    # sides: Pinnacle nu 0,4885, krav 5 % -> 1,05/0,4885 = 2,15 (= spela från)
    assert ov.required_odds(SIDE_BET, S) == 2.15
    # Pinnacle har fallit: kravet höjs
    assert ov.required_odds(dict(SIDE_BET, pin_stang_p=0.45), S) == 2.34
    # Pinnacle har stigit: aldrig under spela från
    assert ov.required_odds(dict(SIDE_BET, pin_stang_p=0.55), S) == 2.15
    # krav_edge från spelet (agent A) används före tier_b_min_edge
    assert ov.required_odds(dict(SIDE_BET, krav_edge=0.03, spela_fran=None), S) == 2.11
    # props: skarp_stang_p bara om nyare än bokningen, och bara som förändring sedan bevakningen började (p0)
    nb = dict(NBA_BET, skarp_stang_p=0.5, skarp_stang_ts=NOW, sannolikhet=0.56)
    assert ov.required_odds(nb, S) == 1.88                    # ingen p0: bara spela från
    assert ov.required_odds(nb, S, p0=0.5) == 1.88            # oförändrad skarp: spela från
    assert ov.required_odds(nb, S, p0=0.55) == 2.06           # skarp föll 5 pe: 1,05/0,51 -> kravet höjs
    assert ov.required_odds(dict(nb, skarp_stang_ts=NOW - 3600), S, p0=0.55) == 1.88   # gammal skarp: ignoreras


# ------------------------------------------------------------------ lägen
def test_over_under_over_gives_gone_then_back_up(tmp_path):
    setup(tmp_path, [SIDE_BET])
    v, sent, calls, run = vakt(tmp_path, [side_raw(2.2), side_raw(2.0), side_raw(2.0), side_raw(2.0)])
    run()
    assert len(sent) == 1 and sent[0][0] == "ODDS ALERT ❌ Kalmar FF 1X2: 2" and "2.00 < 2.15 – spela inte" in sent[0][1]
    assert sent[0][2] == 3 and sent[0][3] == "https://x/#ta=fotboll%7Ck222%7Cmatch%7Cm%C3%A5l"
    # tillbaka upp efter spärren (10 min)
    v._fetch = lambda c, e: side_raw(2.25)
    v.step(NOW + 700)
    v.step(NOW + 730)
    assert len(sent) == 2 and sent[1][0].startswith("ODDS ALERT ✅ Kalmar FF 1X2: 2")
    assert "unibet 2.25 ≥ spela från 2.15 – ta det nu" in sent[1][1] and sent[1][2] == 5
    assert calls[0] == ("ubse", 222)


def test_hysteresis_single_blip_no_alert(tmp_path):
    setup(tmp_path, [SIDE_BET])
    _v, sent, _c, run = vakt(tmp_path, [side_raw(2.2), side_raw(2.0), side_raw(2.2), side_raw(2.0), side_raw(2.2)])
    run()
    assert sent == []


def test_cooldown_defers_back_up(tmp_path):
    setup(tmp_path, [SIDE_BET])
    v, sent, _c, run = vakt(tmp_path, [side_raw(2.0), side_raw(2.0), side_raw(2.3), side_raw(2.3), side_raw(2.3)])
    run()
    assert [t[:12] for t, *_ in sent] == ["ODDS ALERT ❌"]          # BACK UP inom 10 min väntar
    assert v.st[SIDE_BET["ident"]]["state"] == "under"
    v.step(NOW + 650)                                               # spärren ute, läget står kvar -> skickas
    assert len(sent) == 2 and "✅" in sent[1][0]


def test_borta_after_over_gives_gone(tmp_path):
    setup(tmp_path, [NBA_BET])
    v, sent, _c, run = vakt(tmp_path, [nba_raw(), None, None])     # 404 = matchen borta hos Kambi
    run()
    assert len(sent) == 1 and "spelet är borta" in sent[0][1]
    assert sent[0][0].startswith("ODDS ALERT ❌ Gui Santos poäng+assist under 10.5")
    assert v.st[NBA_BET["ident"]]["state"] == "borta"


def test_fetch_error_is_not_a_reading(tmp_path):
    setup(tmp_path, [SIDE_BET])
    _v, sent, _c, run = vakt(tmp_path, [RuntimeError("nät"), RuntimeError("nät"), RuntimeError("nät")])
    run()
    assert sent == []


def test_one_fetch_per_event_and_bolag(tmp_path):
    b2 = dict(SIDE_BET, ident="fotboll|k222|hörnor|hörnor", spelare_id="hörnor")
    setup(tmp_path, [SIDE_BET, b2])
    _v, _s, calls, run = vakt(tmp_path, [side_raw()])
    run()
    assert calls == [("ubse", 222)]


def test_taken_bet_not_watched(tmp_path):
    setup(tmp_path, [SIDE_BET], mina=[SIDE_BET["ident"]])
    v, sent, calls, run = vakt(tmp_path, [side_raw(2.0)] * 3)
    run()
    assert sent == [] and calls == []
    # "tog"-klick under körningen stoppar också bevakningen; "angra" startar den igen
    setup(tmp_path, [SIDE_BET], mina=[])
    v.reload()
    msg = lambda i, typ, t: {"id": i, "time": t, "event": "message", "message": json.dumps({"v": 1, "typ": typ, "ident": SIDE_BET["ident"], "ts": t})}
    v.read_messages([msg("a", "tog", NOW)], NOW)
    assert v.targets(NOW) == {}
    v.read_messages([msg("b", "angra", NOW + 1)], NOW)
    assert SIDE_BET["ident"] in v.targets(NOW)


def test_kickoff_stops_watching(tmp_path):
    setup(tmp_path, [SIDE_BET])
    v, sent, calls, _run = vakt(tmp_path, [])
    assert v.step(KO + 1) == 0 and calls == []


def test_custom_watch_from_messages(tmp_path):
    src = dict(SIDE_BET, ident=None, key="k222|1x2|0|away|unibet")
    src.pop("ident")
    setup(tmp_path, [])
    (tmp_path / "sides_spel.json").write_text(json.dumps([src]), encoding="utf-8")
    v, sent, calls, _run = vakt(tmp_path, [])
    m = {"v": 1, "typ": "bevaka", "ident": "fotboll|k222|match|mål", "sport": "fotboll", "kalla_fil": "sides_spel.json",
         "kalla_key": "k222|1x2|0|away|unibet", "bolag": "svenskaspel", "min_odds": 2.4, "ts": NOW}
    v.read_messages([{"id": "m1", "time": NOW, "event": "message", "message": json.dumps(m)}], NOW)
    tg = v.targets(NOW)
    assert tg["fotboll|k222|match|mål"]["min"] == 2.4 and tg["fotboll|k222|match|mål"]["typ"] == "egen"
    for i, o in enumerate([2.2, 2.2, 2.45, 2.45]):      # startläge under (ingen notis), sedan över -> BACK UP
        v._fetch = lambda c, e, o=o: calls.append((c, e)) or side_raw(o)
        v.step(NOW + i * 30)
    assert len(sent) == 1 and "✅" in sent[0][0] and "svenskaspel 2.45 ≥ spela från 2.40" in sent[0][1]
    assert calls[0] == ("svenskaspel", 222)
    v.save(NOW + 200)
    pub = json.loads((tmp_path / "site" / "oddsvakt.json").read_text(encoding="utf-8"))["bevakningar"]["fotboll|k222|match|mål"]
    assert pub["status"] == "over" and pub["odds_nu"] == 2.45 and pub["min_odds"] == 2.4 and pub["typ"] == "egen"
    # sluta_bevaka (nyare) tar bort; ett äldre bevaka-meddelande läggs inte tillbaka
    stop = {"v": 1, "typ": "sluta_bevaka", "ident": "fotboll|k222|match|mål", "ts": NOW + 10}
    old = dict(m, ts=NOW + 5)
    v.read_messages([{"id": "m2", "time": NOW + 10, "event": "message", "message": json.dumps(stop)},
                     {"id": "m3", "time": NOW + 11, "event": "message", "message": json.dumps(old)}], NOW)
    assert v.targets(NOW) == {}


def test_restart_does_not_realert(tmp_path):
    setup(tmp_path, [SIDE_BET])
    _v, sent, _c, run = vakt(tmp_path, [side_raw(2.0)] * 3)
    run()
    assert len(sent) == 1
    v2, sent2, _c2, run2 = vakt(tmp_path, [side_raw(2.0)] * 3)     # ny körning läser oddsvakt_lage.json
    run2(NOW + 100)
    assert sent2 == [] and v2.st[SIDE_BET["ident"]]["state"] == "under"
    log = [json.loads(x) for x in (tmp_path / "oddsvakt_logg.jsonl").read_text(encoding="utf-8").splitlines()]
    assert log[0]["o"] == 2.0 and log[0]["s"] == "under" and len(log) == 2   # bara första läsningen per körning (oförändrat)


def test_log_prune(tmp_path):
    setup(tmp_path, [])
    f = tmp_path / "oddsvakt_logg.jsonl"
    f.write_text(json.dumps({"t": NOW - 8 * 86400}) + "\n" + json.dumps({"t": NOW}) + "\n", encoding="utf-8")
    v, *_ = vakt(tmp_path, [])
    assert v.prune_log(NOW) == 1 and len(f.read_text().splitlines()) == 1


def test_start_flag(tmp_path):
    setup(tmp_path, [SIDE_BET])
    assert ov.write_start_flag(tmp_path, S, NOW, log=lambda *_: None) == 1
    assert (tmp_path / "oddsvakt_start.txt").read_text() == "1"
    setup(tmp_path, [dict(SIDE_BET, avspark=NOW - 10)])
    assert ov.write_start_flag(tmp_path, S, NOW, log=lambda *_: None) == 0 and not (tmp_path / "oddsvakt_start.txt").exists()
    assert not (tmp_path / "oddsvakt_lage.json").exists()          # skanningen skriver aldrig oddsvaktens filer


def test_main_loop_exits_when_idle(tmp_path):
    setup(tmp_path, [])
    t = [NOW]
    logs = []
    ov.main(tmp_path, dict(S, oddsvakt_tomgang_s=60), log=logs.append, clock=lambda: t[0],
            sleep=lambda s: t.__setitem__(0, t[0] + s), fetch=lambda *a: None, send=lambda *a: True,
            poll=lambda *a: [], git=False)
    assert any("inget att bevaka" in x for x in logs) and (tmp_path / "oddsvakt_lage.json").exists()


def test_git_sync_commits_only_own_files(tmp_path):
    (tmp_path / "oddsvakt_lage.json").write_text("{}")
    calls = []

    class R:
        returncode, stderr = 0, ""
    ov.git_sync(tmp_path, log=lambda *_: None, run=lambda *a: calls.append(a) or R())
    assert calls[0] == ("add", "--", "oddsvakt_lage.json")
    assert calls[1][-2:] == ("--", "oddsvakt_lage.json")
    assert ("rebase", "-q", "-X", "theirs", "FETCH_HEAD") in calls and ("push", "-q", "origin", "HEAD:data") in calls


# ------------------------------------------------------------------ notiser
def test_notify_oddsvakt_chat_and_fallback(monkeypatch):
    sent = []
    monkeypatch.setattr(nt, "send_telegram", lambda cid, t, m, p=4, click=None: sent.append(cid) or True)
    base = {"ntfy_topic": "main-t", "tier_ntfy_topic": "tier-t", "telegram_only": True}
    nt.configure(dict(base, telegram_chats={"main": 1, "tier": 2, "oddsvakt": 9}))
    assert nt.oddsvakt_topic(dict(base, telegram_chats={"oddsvakt": 9})) == "tier-t-oddsvakt"
    nt.send(nt.oddsvakt_topic(dict(base, telegram_chats={"oddsvakt": 9})), "ODDS ALERT ✅ x", "y")
    nt.send("tier-t", "B TIER", "z")
    assert sent == [9, 2]
    sent.clear()
    s2 = dict(base, telegram_chats={"main": 1, "tier": 2, "oddsvakt": None})   # ingen oddsvakt-chatt: nivåchatten
    nt.configure(s2)
    assert nt.oddsvakt_topic(s2) == "tier-t"
    nt.send(nt.oddsvakt_topic(s2), "ODDS ALERT ❌ x", "y")
    assert sent == [2]
    nt.configure({})


def test_main_warns_without_oddsvakt_chat(tmp_path):
    setup(tmp_path, [])
    logs = []
    t = [NOW]
    ov.main(tmp_path, dict(S, oddsvakt_tomgang_s=0, telegram_chats={"tier": 2}), log=logs.append, clock=lambda: t[0],
            sleep=lambda s: t.__setitem__(0, t[0] + s), fetch=lambda *a: None, send=lambda *a: True, poll=lambda *a: [], git=False)
    assert any("telegram_chats.oddsvakt saknas" in x for x in logs)


def test_mina_ignores_watch_messages():
    from propsbot import mina
    book = mina.Book.__new__(mina.Book)
    book.bets, book.seen, book.last_id = {}, set(), None
    msgs = [{"id": "1", "time": 1, "message": json.dumps({"v": 1, "typ": "bevaka", "ident": "x", "min_odds": 2.0})},
            {"id": "2", "time": 2, "message": json.dumps({"v": 1, "typ": "sluta_bevaka", "ident": "x"})}]
    assert mina.apply_messages(book, msgs, {}, NOW) == 0 and book.bets == {}


def test_prop_with_sharp_below_model_p_no_false_gone(tmp_path):
    # props: modellens sannolikhet (0,56) över den skarpa (0,48). Oddset ligger kvar -> ingen GONE vid start.
    nb = dict(NBA_BET, sannolikhet=0.56, skarp_stang_p=0.48, skarp_stang_ts=NOW)
    setup(tmp_path, [nb])
    v, sent, calls, run = vakt(tmp_path, [nba_raw(1.97)] * 4)
    run()
    assert sent == [] and v.bas_p[nb["ident"]] == 0.48
    # den skarpa faller 6 pe efter starten -> kravet 1,05/0,50 = 2,10 > 1,97 -> GONE
    nb2 = dict(nb, skarp_stang_p=0.42)
    setup(tmp_path, [nb2])
    v.reload()
    v.step(NOW + 200)
    v.step(NOW + 230)
    assert len(sent) == 1 and sent[0][0].startswith("ODDS ALERT ❌")
