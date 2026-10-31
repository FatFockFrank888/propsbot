import time

from propsbot.config import Config
from propsbot.decision import Candidate, evaluate
from propsbot.models import OddsQuote
from propsbot.parlays import ParlayLedger, suggest
from propsbot.pipeline import Row
from propsbot.scan import DEFAULT_SETTINGS, ScanRow
TEST_SETTINGS = dict(DEFAULT_SETTINGS, playable_books=[])  # alla bolag spelbara i testerna


def row(match, player, p, odds, book="unibet"):
    now = time.time()
    q = OddsQuote(book, match, player, "shots", 0.5, "over", odds, now)
    c = Candidate(match, player, player.title(), "shots", 0.5, p, q, None, now, True, 120)
    return ScanRow("fotboll", f"{match} H – A", "2026-11-01 15:00", Row(evaluate(c, Config().decision),
                   float("nan"), p, 0), 1)


def test_suggest_rules():
    rows = [row("m1", "a", 0.55, 2.0), row("m1", "b", 0.60, 1.9), row("m2", "c", 0.52, 2.1),
            row("m3", "d", 0.50, 2.2), row("m4", "e", 0.40, 2.0), row("m5", "f", 0.55, 2.0, "paf")]
    evd = {f"m{i}": {"home_team": "H", "away_team": "A", "commence_time": time.time() + 7200}
           for i in range(1, 6)}
    sug = suggest(rows, evd, TEST_SETTINGS)
    assert sug
    for s in sug:
        assert 2 <= s["antal_ben"] <= 5
        assert len({l["match_id"] for l in s["ben"]}) == s["antal_ben"]   # olika matcher
        assert {l["bolag"] for l in s["ben"]} == {s["bolag"]}              # samma bolag
        assert "e" not in {l["spelare_id"] for l in s["ben"]}               # negativ edge ej med
        assert 0 < s["insats_pct"] <= TEST_SETTINGS["parlay_max_stake"]
        assert abs(s["odds"] - __import__("math").prod(l["odds"] for l in s["ben"])) < 1e-9


def test_parlay_ledger_settlement(tmp_path):
    pl = ParlayLedger(tmp_path / "p.json")
    leg = lambda k, o: {"key": k, "odds": o, "status": "öppen"}  # noqa: E731
    s = [{"key": "x", "bolag": "unibet", "ben": [leg("a", 2.0), leg("b", 2.0), leg("c", 1.5)],
          "antal_ben": 3, "odds": 6.0, "sannolikhet": 0.2, "ev": 0.2, "insats_pct": 0.005}]
    assert len(pl.record(s)) == 1 and pl.record(s) == []
    it = pl.items[0]
    it["ben"][0]["status"], it["ben"][1]["status"], it["ben"][2]["status"] = "vunnen", "struken", "vunnen"
    pl.update_status()
    assert it["status"] == "vunnen" and abs(it["slutodds"] - 3.0) < 1e-9
    assert abs(it["resultat_enheter"] - 0.01) < 1e-9
    pl.save()
    assert ParlayLedger(tmp_path / "p.json").summary()["vunna"] == 1
