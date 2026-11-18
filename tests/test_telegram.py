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
