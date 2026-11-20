import json
import math
import random

from propsbot.nba_kalibrering import KalibLog, fit, load, predict

sig = lambda z: 1 / (1 + math.exp(-z))
L = lambda p: math.log(p / (1 - p))


def _write(tmp_path, n, model_signal, seed=1):
    """n avgjorda rader: marknaden är rätt i snitt; modellen är brus (0) eller bär verklig information (1)."""
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        truth = L(rnd.uniform(0.35, 0.65))
        info = rnd.gauss(0, 0.5)                      # det marknaden inte vet
        pk = sig(truth)
        p_true = sig(truth + info * model_signal)
        pm = sig(truth + 1.5 * info + rnd.gauss(0, 0.5))   # modellen: informationen, överdriven, + brus
        y = 1 if rnd.random() < p_true else 0
        rows.append({"k": f"m{i}|p|points|20.5", "match_id": f"m{i}", "spelare": "X", "hemma": "A", "borta": "B",
                     "avspark": 1e9 + i, "marknad": "points", "linje": 20.5, "t0": i, "t": i,
                     "pm": pm, "pk": pk, "pf": None, "pb": None, "status": "vunnen" if y else "förlorad", "y": y})
    lg = KalibLog(tmp_path)
    lg.rows = rows
    lg.save()


def test_noise_model_gets_no_weight(tmp_path):
    _write(tmp_path, 1500, model_signal=0.0)
    q = fit(tmp_path)["points"]
    assert q["modell"] in ("M0", "M1") and q["n"] == 1500
    p, aktiv = predict(load(tmp_path), "points", 0.5, pm_over=0.8)
    assert not aktiv and abs(p - 0.5) < 0.05          # modellens 80 % ignoreras: marknaden gäller


def test_informative_model_earns_weight(tmp_path):
    _write(tmp_path, 3000, model_signal=1.0)
    q = fit(tmp_path)["points"]
    assert q["modell"] == "M2" and 0.1 < q["c"] < 1.0 and q["vinst_mot_marknad"] > 0
    p, aktiv = predict(load(tmp_path), "points", 0.5, pm_over=0.8)
    assert aktiv and 0.5 < p < 0.8                     # modellen drar, men krympt (den är överkonfident)


def test_log_upsert_settle_prune(tmp_path):
    lg = KalibLog(tmp_path)
    e = {"mid": "m1", "pid": "p1", "spelare": "X", "hemma": "A", "borta": "B", "avspark": 1000.0, "mk": "points",
         "ln": 20.5, "pm": 0.6, "pk": 0.5, "pf": None, "pb": None, "dq": 1.0}
    lg.upsert(e, 100)
    lg.upsert(dict(e, pk=0.52), 200)                   # samma ben: uppdateras, ingen ny rad
    lg.upsert(dict(e, ln=21.5), 2000)                  # efter start: loggas inte
    assert len(lg.rows) == 1 and lg.rows[0]["pk"] == 0.52 and lg.rows[0]["t0"] == 100
    lg.settle(lg.rows[0], 25, True)
    assert lg.rows[0]["y"] == 1 and lg.rows[0]["status"] == "vunnen"
    lg.save()
    lg2 = KalibLog(tmp_path)
    lg2.prune(1000.0 + 41 * 86400)
    assert lg2.rows == []
