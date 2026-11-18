import json
import time

from propsbot.tiers import classify, cfg, run, units_for

C = cfg({})


def bet(**kw):
    b = {"key": "k1", "match_id": "m1", "spelare_id": "p1", "spelare": "X", "marknad": "points", "linje": 20.5,
         "sida": "over", "odds": 2.0, "edge": 0.07, "stopp": "", "bokford": time.time(), "avspark": time.time() + 7200,
         "match": "A – B", "bolag": "unibet", "spela_fran": 1.9, "status": "öppen", "pin_stang_p": 0.53,
         "insats_pct": 0.002}
    b.update(kw)
    return b


def test_levels():
    assert classify(bet(), "live", "nba", C)[0] == "A"
    assert classify(bet(), "spel", "nba", C)[0] == "B"                 # NBA: A kräver LIVE-kraven
    assert classify(bet(pin_stang_p=None), "live", "nba", C)[0] == "C"  # ingen skarp referens
    assert classify(bet(odds=1.50), "live", "nba", C)[0] == "C"         # under B:s golv 1,60
    assert classify(bet(odds=4.5), "spel", "fotboll", C)[0] == "B"      # över A:s tak 3,50
    assert classify(bet(edge=0.03), "live", "nba", C)[0] is None
    assert classify(bet(stopp="skadelista: out (ESPN)"), "skugga", "nba", C)[0] is None
    assert classify(bet(stopp="skadelista: questionable (ESPN) – kolla före start"), "live", "nba", C)[0] == "A"
    assert classify(bet(stopp="sharp money mot oss: referensen har rört sig -2.5 enheter"), "skugga", "nba", C)[0] is None
    assert classify(bet(stopp="oddset har fallit 4.0% från 2.08 – för sent"), "skugga", "nba", C)[0] == "C"


def test_units():
    assert units_for(bet(edge=0.06), C) == 1
    assert units_for(bet(edge=0.10), C) == 2
    assert units_for(bet(edge=0.13, stopp="sharp money med oss: referensen +2.0 enheter"), C) == 3
    assert units_for(bet(edge=0.13), C) == 2                           # maxbet kräver sharp money med oss
    assert units_for(bet(edge=0.22, stopp="sharp money med oss"), C) == 2   # orimligt hög edge: aldrig maxbet


def test_run_upgrade_settle_no_caps(tmp_path):
    now = time.time()
    skugga = [bet(key="s1", odds=1.5, bokford=now - 600)]                 # C först
    live = [bet(key="l1", linje=21.5, bokford=now - 60, edge=0.10)]       # sedan A på samma spelare
    spel = [bet(key="b%d" % i, match_id="m%d" % (i + 2), spelare_id="q%d" % i, bokford=now - 30, edge=0.10)
            for i in range(6)]                                            # B: 2u styck, inga tak -> alla 6 spelas
    (tmp_path / "nba_skugga_v2.json").write_text(json.dumps(skugga))
    (tmp_path / "nba_live.json").write_text(json.dumps(live))
    (tmp_path / "nba_bokforing_v2.json").write_text(json.dumps(live + spel))
    sent = []
    import propsbot.notify as nt
    orig = nt.send
    nt.send = lambda *a, **k: sent.append(a) or True
    try:
        res = run(tmp_path, {"ntfy_topic": "t"}, notify=True, log=lambda *_: None)
    finally:
        nt.send = orig
    bets = {b["kalla_key"]: b for b in res["book"].bets}
    assert "s1" not in bets and bets["l1"]["tier"] == "A" and bets["l1"]["uppgraderad_fran"] == "C"
    assert len(sent) == 7 and bets["l1"]["notis"]                     # A + 6 B (notis för A och B sedan 18/11)
    assert sum("A TIER" in x[1] for x in sent) == 1 and sum("B TIER" in x[1] for x in sent) == 6
    b_played = [b for b in res["book"].bets if b["tier"] == "B" and b["spelad"]]
    assert len(b_played) == 6 and not any(b.get("tak") for b in res["book"].bets)
    # rättning från källan
    live[0].update(status="vunnen", resultat_enheter=0.002, avspark=now - 10)
    (tmp_path / "nba_live.json").write_text(json.dumps(live))
    res = run(tmp_path, {}, notify=False, log=lambda *_: None)
    a = next(b for b in res["book"].bets if b["kalla_key"] == "l1")
    assert a["status"] == "vunnen" and a["resultat_u"] == 2.0        # 2u, odds 2,0
    assert len(res["book"].bets) == 7                                   # ingenting bokas om
    assert (tmp_path / "site" / "tiers.json").exists()
