"""Fas 8: Kelly-förslaget (kelly_pct) driver nu den riktiga insatsen (stake_kr, 28/11) i stället för att
bara bokföras i skugga. Notiser/CLV opåverkade."""
import json
import time

import propsbot.notify as nt
from propsbot.quant import kelly
from propsbot.tiers import cfg, kr_to_units, run, stake_kr

C = cfg({})


def bet(**kw):
    b = {"key": "k1", "match_id": "m1", "spelare_id": "p1", "spelare": "X", "marknad": "points", "linje": 20.5,
         "sida": "over", "odds": 2.0, "edge": 0.07, "stopp": "", "bokford": time.time(), "avspark": time.time() + 7200,
         "match": "A – B", "bolag": "unibet", "spela_fran": 1.9, "status": "öppen", "pin_stang_p": 0.53,
         "insats_pct": 0.002, "sannolikhet": 0.535}
    b.update(kw)
    return b


def _run(tmp_path, bets, monkeypatch):
    (tmp_path / "nba_bokforing_v2.json").write_text(json.dumps(bets))
    sent = []
    monkeypatch.setattr(nt, "send", lambda *a, **k: sent.append(a) or True)
    res = run(tmp_path, {"ntfy_topic": "t"}, notify=True, log=lambda *_: None)
    return res["book"].bets, sent


def test_kelly_shadow_fields_and_units_unchanged(tmp_path, monkeypatch):
    src = [bet(), bet(key="k2", match_id="m2", spelare_id="p2", odds=4.5, edge=0.10, sannolikhet=0.2444),
           bet(key="k3", match_id="m3", spelare_id="p3", sannolikhet=None)]
    bets, sent = _run(tmp_path, src, monkeypatch)
    by = {b["kalla_key"]: b for b in bets}
    for s in src:
        tb = by.get(s["key"])
        if tb is None:
            continue
        k_pct = round(kelly.stake(s["sannolikhet"], s["odds"]), 4)
        assert tb["kelly_pct"] == k_pct
        assert 0 <= tb["kelly_u"] <= 2
        assert tb["units"] == kr_to_units(stake_kr(s, C, k_pct, "nba"), C)       # kelly styr nu insatsen
    assert by["k3"]["kelly_pct"] == 0.0 and by["k3"]["kelly_u"] == 0          # saknad p -> 0, ingen krasch
    assert by["k3"]["stake_kr"] == C["tier_stake_min_kr"]                        # golvet, inte 0
    assert by["k2"]["kelly_pct"] < 0.01                                          # långt odds: liten kelly
    assert all("kelly" not in x[2] for x in sent)                                # notistexten orörd


def test_no_writes_outside_tmp(tmp_path, monkeypatch):
    import builtins
    real_open = builtins.open
    bad = []

    def guard(file, mode="r", *a, **k):
        if any(m in mode for m in "wax") and not str(file).startswith(str(tmp_path)):
            bad.append(str(file))
        return real_open(file, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", guard)
    _run(tmp_path, [bet()], monkeypatch)
    assert not bad
