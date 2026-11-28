import json
import time

from propsbot.parlays import build_parlays, notify_parlays, run, settle_parlays


def leg(**kw):
    b = {"ident": "nba|m1|p1", "match_id": "m1", "match": "A – B", "spelare": "X", "marknad": "points",
         "linje": 20.5, "sida": "over", "odds": 1.90, "sannolikhet": 0.60, "bolag": "paf", "sport": "nba",
         "tier": "A", "status": "öppen", "avspark": time.time() + 3600}
    b.update(kw)
    return b


def test_build_parlays_cross_match_and_edge():
    a = leg()
    b = leg(ident="nba|m2|p2", match_id="m2", spelare="Y", odds=1.90, sannolikhet=0.60)
    out = build_parlays([a, b], {}, set())
    assert len(out) == 1
    p = out[0]
    assert p["combo_p"] == round(0.6 * 0.6, 4) and p["combo_odds"] == round(1.9 * 1.9, 3)
    assert p["combo_edge"] == round(0.6 * 0.6 * (1.9 * 1.9) - 1, 4)
    assert 15.0 <= p["stake_kr"] <= 30.0


def test_same_match_never_combined():
    a = leg()
    b = leg(ident="nba|m1|p2", spelare="Y")   # samma match_id
    assert build_parlays([a, b], {}, set()) == []


def test_min_edge_filters_weak_combo():
    a = leg(odds=1.50, sannolikhet=0.55)   # edge ensam ~ -17 %, kombinerat ändå under kravet
    b = leg(ident="nba|m2|p2", match_id="m2", odds=1.50, sannolikhet=0.55)
    assert build_parlays([a, b], {"parlay_min_edge": 0.08}, set()) == []


def test_existing_ident_skips_rebuild():
    a = leg()
    b = leg(ident="nba|m2|p2", match_id="m2", spelare="Y")
    ident = "parlay|" + "+".join(sorted((a["ident"], b["ident"])))
    assert build_parlays([a, b], {}, {ident}) == []


def test_settle_parlays_win_loss_struken():
    a = leg()
    b = leg(ident="nba|m2|p2", match_id="m2", spelare="Y")
    [p] = build_parlays([a, b], {}, set())
    bets_win = [dict(a, status="vunnen"), dict(b, status="vunnen")]
    settle_parlays([p], bets_win)
    assert p["status"] == "vunnen" and p["resultat_kr"] == round(p["stake_kr"] * (p["combo_odds"] - 1), 1)

    p2 = dict(p, status="öppen")
    bets_loss = [dict(a, status="förlorad"), dict(b, status="vunnen")]
    settle_parlays([p2], bets_loss)
    assert p2["status"] == "förlorad" and p2["resultat_kr"] == -p2["stake_kr"]

    p3 = dict(p, status="öppen")
    bets_struken = [dict(a, status="struken"), dict(b, status="öppen")]
    settle_parlays([p3], bets_struken)
    assert p3["status"] == "struken" and p3["resultat_kr"] == 0.0


def test_notify_parlays_dedup(monkeypatch):
    import propsbot.notify as nt
    sent = []
    monkeypatch.setattr(nt, "send", lambda *a, **k: sent.append(a) or True)
    a = leg()
    b = leg(ident="nba|m2|p2", match_id="m2", spelare="Y")
    [p] = build_parlays([a, b], {}, set())
    n = notify_parlays([p], {"ntfy_topic": "t"})
    assert n == 1 and p["notis"] and "PARLAY" in sent[0][1]
    n2 = notify_parlays([p], {"ntfy_topic": "t"})
    assert n2 == 0                                   # redan notiserad, skickas inte igen


def test_run_roundtrip_persists_and_settles(tmp_path):
    a = leg()
    b = leg(ident="nba|m2|p2", match_id="m2", spelare="Y")
    out1 = run(tmp_path, [a, b], {"ntfy_topic": "t"}, notify=False, log=lambda *_: None)
    assert len(out1) == 1 and out1[0]["status"] == "öppen"
    saved = json.loads((tmp_path / "site" / "parlays.json").read_text())
    assert len(saved["parlayer"]) == 1
    a_done, b_done = dict(a, status="vunnen"), dict(b, status="vunnen")
    out2 = run(tmp_path, [a_done, b_done], {"ntfy_topic": "t"}, notify=False, log=lambda *_: None)
    assert len(out2) == 1 and out2[0]["status"] == "vunnen"   # samma parlay rättad, ingen ny skapad
