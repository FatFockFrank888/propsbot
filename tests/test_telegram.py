import json

import propsbot.notify as nt


def test_routing_and_fallback(monkeypatch):
    sent = []
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")
    monkeypatch.setattr(nt, "send_telegram", lambda cid, t, m, p=4, click=None: sent.append((cid, t, p, click)) or True)

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"id": "1", "time": 0}).encode()
    monkeypatch.setattr(nt.urllib.request, "urlopen", lambda *a, **k: R())
    nt.configure({"ntfy_topic": "main-t", "tier_ntfy_topic": "tier-t", "live_ntfy_topic": "live-t",
                  "telegram_chats": {"main": 1, "tier": 2, "live": 3}})
    assert nt.send("tier-t", "B TIER", "x") and nt.send("live-t", "MÅL", "y", priority=5, click="u") and nt.send("main-t", "Nyhet", "z")
    assert [s[0] for s in sent] == [2, 3, 1] and sent[1][3] == "u"
    nt.configure({"ntfy_topic": "main-t", "telegram_chats": {"main": 1}})      # bara huvudchatt: allt dit
    sent.clear()
    nt.send("main-t", "a", "b")
    assert sent[0][0] == 1
    nt.configure({"ntfy_topic": "main-t"})                                    # ingen Telegram: bara ntfy
    sent.clear()
    assert nt.send("main-t", "a", "b") and not sent


def test_format_bet_readable_swedish_time():
    from propsbot.msg import format_bet, kickoff_sv
    from datetime import datetime, timezone
    ts = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc).timestamp()
    assert kickoff_sv(ts) == "ons 25/11 01:00 (svensk tid)"
    b = {"match": "A – B", "bolag": "unibet", "odds": 2.02, "spela_fran": 1.95, "edge": 0.0642, "sannolikhet": 0.5268,
         "rum": 0.005, "forv_clv_pp": 1.2, "units": 1, "unit_pct": 0.01}
    title, msg = format_bet(b, tier="B", sport="nba", who="K. Huerter", spel="poäng över 11,5",
                            ko_text=kickoff_sv(ts), units_txt="1u – standard", unit_pct=0.01)
    assert title.startswith("B-TIER · NBA")
    assert "@ 2,02 (spela från 1,95, rum +0,5 %)" in msg and "rättvist odds 1,90" in msg
    assert "Insats: 1u – standard (1 % av kassan)" in msg and "snävt rum" in msg and "UTC" not in msg


def test_format_bet_shows_kr_when_stake_kr_present():
    from propsbot.msg import format_bet, kickoff_sv
    from datetime import datetime, timezone
    ts = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc).timestamp()
    b = {"match": "A – B", "bolag": "paf", "odds": 2.02, "spela_fran": 1.95, "edge": 0.0642, "sannolikhet": 0.5268,
         "rum": 0.005, "forv_clv_pp": 1.2, "units": 2.83, "unit_pct": 0.01, "stake_kr": 28.3}
    title, msg = format_bet(b, tier="B", sport="nba", who="K. Huerter", spel="poäng över 11,5",
                            ko_text=kickoff_sv(ts), units_txt="2.83u", unit_pct=0.01)
    assert "Insats: 28 kr" in msg and "2.83u" not in msg and "av kassan" not in msg


def test_telegram_retries(monkeypatch):
    import urllib.error
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")
    monkeypatch.setattr(nt.time, "sleep", lambda s: None)
    calls = []

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok": true}'

    def fake(*a, **k):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.URLError("x")
        return R()
    monkeypatch.setattr(nt.urllib.request, "urlopen", fake)
    assert nt.send_telegram(1, "t", "m") is True and len(calls) == 3


def test_motiv_text_and_csv_columns():
    from propsbot.msg import build_motiv, motiv_text
    from propsbot.workbook import CSV_HEAD
    b = {"sannolikhet": 0.55, "odds": 2.0, "edge": 0.10, "pin_p": 0.54, "prognos": 5.1, "linje": 4.5, "pin_grans": 400,
         "forv_clv_pp": 1.0}
    fair, why, risk = motiv_text(b)
    assert fair == "1,82" and "edge 10,0 %" in why and "Pinnacle 54,0 %" in why and "prognos 5,1 mot linje 4,5" in why
    assert "låg Pinnacle-gräns" in risk and build_motiv(b)["fair_odds"] == 1.818
    assert CSV_HEAD[-3:] == ["Fair odds", "Motivering", "Risk"]


def test_unibet_link_and_buttons(monkeypatch):
    from propsbot.msg import unibet_url
    assert unibet_url("k1029147328", "unibet") == "https://www.unibet.se/betting/sports/event/1029147328"
    assert unibet_url("nba1028754099", "unibet") == "https://www.unibet.se/betting/sports/event/1028754099"
    assert unibet_url("k1029147328", "svenskaspel") is None and unibet_url("401234", "unibet") is None
    import urllib.request
    sent = {}
    monkeypatch.setenv("TELEGRAM_TOKEN", "x")

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok": true}'

    def fake(req, timeout=0):
        sent["body"] = json.loads(req.data.decode())
        return R()
    monkeypatch.setattr(nt.urllib.request, "urlopen", fake)
    assert nt.send_telegram(1, "t", "m", click="https://x/y", link=("Hos Unibet", "https://u/1")) is True
    assert [b["text"] for b in sent["body"]["reply_markup"]["inline_keyboard"][0]] == ["Öppna", "Hos Unibet"]


def test_link_is_added_to_message_text(monkeypatch):
    seen = {}
    monkeypatch.setattr(nt, "send_telegram", lambda cid, t, m, p=4, click=None, link=None: seen.update(tg=m) or True)
    monkeypatch.setitem(nt.TG_ROUTE, "tt", 1)

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"id": "1", "time": 0}'
    monkeypatch.setattr(nt.urllib.request, "urlopen", lambda req, timeout=0: seen.update(ntfy=json.loads(req.data.decode())["message"]) or R())
    assert nt.send("tt", "t", "Match A", link=("Hos Unibet", "https://www.unibet.se/betting/sports/event/1")) is True
    for k in ("tg", "ntfy"):
        assert seen[k].endswith("Hos Unibet: https://www.unibet.se/betting/sports/event/1")
