import time

from propsbot import corners as c

HEAD = "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC,AvgH,AvgD,AvgA,Avg>2.5,Avg<2.5\n"


def _csv(n=80, now=None):
    import random
    random.seed(1)
    teams = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    rows = []
    t0 = (now or time.time()) - n * 86400
    for i in range(n):
        h, a = random.sample(teams, 2)
        strong = h == "Alpha"
        hc = random.randint(6, 10) if strong else random.randint(2, 7)
        ac = random.randint(1, 4) if strong else random.randint(2, 6)
        d = time.strftime("%d/%m/%Y", time.gmtime(t0 + i * 86400))
        oh, od, oa = (1.3, 5.5, 9.0) if strong else (2.5, 3.3, 2.8)
        rows.append(f"E0,{d},15:00,{h},{a},1,1,{hc},{ac},{oh},{od},{oa},1.9,1.9")
    return HEAD + "\n".join(rows)


def test_model_and_probabilities():
    now = time.time()
    rows = c.parse_csv(_csv(now=now), "E0")
    assert len(rows) == 80 and rows[0]["sup"] is not None
    m = c.Models(rows, now)
    code, d = m.dist("Alpha FC", "Beta")
    assert code == "E0" and d["lh"] > d["la"]            # hörnstarkt lag hemma
    code, d2 = m.dist("Alpha", "Beta", sup=0.6, o25=0.6)
    assert d2["metod"] == "odds+lag"
    p_over = c.p_side(d, ("corners", 9.5, "over"))
    p_under = c.p_side(d, ("corners", 9.5, "under"))
    assert abs(p_over + p_under - 1) < 1e-6                # halvlinje: över + under = 1
    ph = c.p_side(d, ("cah", -1.5, "home"))
    pa = c.p_side(d, ("cah", 1.5, "away"))
    assert abs(ph + pa - 1) < 1e-6                         # hemma −1,5 och borta +1,5 är komplement
    assert m.dist("Okänt lag", "Beta") == (None, None)
    assert m.result("Alpha", "Beta", rows[[i for i, x in enumerate(rows) if x["hemma"] == "Alpha" and x["borta"] == "Beta"][0]]["ts"])


def test_market_strength_and_season():
    pin = {("1x2", 0.0, "home"): (0.6, 0, 0), ("1x2", 0.0, "away"): (0.2, 0, 0), ("total", 2.5, "over"): (0.55, 0, 0)}
    assert c._market_strength(pin) == (0.6 - 0.2, 0.55)
    assert c._market_strength({}) == (None, None)
    jan = time.mktime((2027, 1, 10, 12, 0, 0, 0, 0, 0))
    assert c.season_codes(jan) == ["2627", "2526"]
