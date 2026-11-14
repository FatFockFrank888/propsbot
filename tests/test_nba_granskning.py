"""Regressionstester från granskningen av NBA-kedjan (2026-11-11). Se GRANSKNING_NBA.md."""
import math
import random

import pytest

from propsbot.decision import play_from_odds
from propsbot.nba import coherent_blend


@pytest.mark.parametrize("pmo,pko,off,w0,dq", [(0.60, 0.50, 0.30, 0.3, 1.0), (0.60, 0.50, -0.7, 0.3, 0.5),
                                               (0.10, 0.85, 0.2, 0.3, 1.0), (0.97, 0.03, 0.0, 0.3, 1.0)])
def test_blend_is_coherent(pmo, pko, off, w0, dq):
    """En blandad över-sannolikhet; under = komplementet. Tidigare: 0,508 + 0,447 = 0,955."""
    _, p_over, _ = coherent_blend(pmo, pko, off, w0, dq)
    _, p_over_from_under_view, _ = coherent_blend(pmo, pko, off, w0, dq)
    assert 0 < p_over < 1 and p_over == p_over_from_under_view
    # samma tal oavsett vilken sida vi bokför: P(under) = 1 − P(över) exakt
    assert abs((1 - p_over) + p_over - 1) < 1e-12


def test_blend_monotone_in_line():
    """Högre linje -> lägre P(över) när modell och marknad båda sjunker (inga motsägande alternativa linjer)."""
    from propsbot.player_model import nb_over
    rnd = random.Random(7)
    for _ in range(200):
        mu = rnd.uniform(3, 30)
        lines = sorted(rnd.sample([x + 0.5 for x in range(0, 40)], 4))
        mk = sorted((rnd.uniform(0.05, 0.95) for _ in lines), reverse=True)
        ps = [coherent_blend(nb_over(mu, ln, 15), m, 0.2, 0.3, 1.0)[1] for ln, m in zip(lines, mk)]
        assert all(a >= b - 1e-12 for a, b in zip(ps, ps[1:]))


def test_play_from_rounds_up():
    # 1,05 / 0,6237 = 1,6835… -> 1,69 (inte 1,68, som ligger under tröskeln)
    pf = play_from_odds(0.6237, 0.05, 1.40)
    assert pf == 1.69 and pf * 0.6237 - 1 >= 0.05


def test_kambi_integer_line_is_skipped():
    from propsbot.nba import kambi_nba_props, SAMPLE
    from propsbot.sources.kambi_public import KambiEvent

    class C:
        def get(self, url, params=None):
            return {"betOffers": [{"criterion": {"englishLabel": "Points scored by the player - Including Overtime"},
                                   "outcomes": [
                                       {"participant": "Doe, John", "type": "OT_OVER", "line": 20000, "odds": 1900},
                                       {"participant": "Doe, John", "type": "OT_UNDER", "line": 20000, "odds": 1900},
                                       {"participant": "Doe, John", "type": "OT_OVER", "line": 20500, "odds": 2000}]}]}
    SAMPLE.pop("heltalslinjer_hoppade", None)
    qs, _ = kambi_nba_props(C(), "ubse", "unibet", "SE", KambiEvent(1, "A", "B", 0, "NBA"), "m1")
    assert [q.line for q in qs] == [20.5] and SAMPLE["heltalslinjer_hoppade"] == 2


def test_missing_player_is_not_auto_void(tmp_path):
    from propsbot.ledger import Ledger
    from propsbot.nba import settle_nba
    lg = Ledger(tmp_path / "l.json")
    start = 1_000_000.0
    lg.bets = [{"key": "k", "status": "öppen", "avspark": start, "match_id": "m", "hemma": "Phoenix Suns",
                "borta": "LA Clippers", "match": "Phoenix Suns – LA Clippers", "spelare": "Okänd Spelare", "marknad": "points", "linje": 20.5,
                "sida": "over", "odds": 2.0, "insats_pct": 0.01}]

    class C:
        def get(self, url, params=None, ttl=None):
            if url.endswith("/scoreboard"):
                return {"events": [{"id": "e1", "date": "1970-01-12T13:46:40Z", "status": {"type": {"completed": True}},
                                    "competitions": [{"competitors": [
                                        {"homeAway": "home", "team": {"displayName": "Phoenix Suns"}},
                                        {"homeAway": "away", "team": {"displayName": "LA Clippers"}}]}]}]}
            return {"boxscore": {"players": [{"statistics": [{"labels": ["PTS"], "athletes": [
                {"athlete": {"displayName": "Någon Annan"}, "stats": ["12"]}]}]}]}}
    settle_nba(lg, C(), now=start + 5 * 3600)
    assert lg.bets[0]["status"] == "öppen"                       # väntar i stället för att stryka
    settle_nba(lg, C(), now=start + 49 * 3600)
    assert lg.bets[0]["status"] == "struken" and "hittades inte" in lg.bets[0]["struken_orsak"]


def test_market_status_rules():
    from propsbot.nba_eval import status
    assert status({"brier": None}) == "insufficient_data"
    assert status({"brier": {"n": 10, "diff_ci95": (-0.1, -0.01)}}) == "insufficient_data"
    assert status({"brier": {"n": 40, "diff_ci95": (0.001, 0.02)}, "clv_ci95": (0.5, 1.0)}) == "degraded"
    assert status({"brier": {"n": 40, "diff_ci95": (-0.02, -0.001)}, "clv_ci95": (0.2, 1.0)}) == "validated"
    assert status({"brier": {"n": 40, "diff_ci95": (-0.02, 0.01)}, "clv_ci95": (0.2, 1.0)}) == "shadow"
    assert status({"brier": {"n": 40, "diff_ci95": (-0.02, 0.01)}, "clv_ci95": (-1.0, -0.1)}) == "degraded"


def test_eval_dedups_prestations_and_is_deterministic(tmp_path):
    import json
    from propsbot.nba_eval import evaluate
    base = {"match_id": "m", "spelare_id": "p", "marknad": "points", "odds": 2.0, "stangning": 1.9, "avspark": 1.0e9,
            "bokford": 1.0e9 - 3600, "insats_pct": 0.01, "p_modell": 0.55, "p_marknad": 0.5}
    rows = [dict(base, linje=20.5, status="vunnen", resultat_enheter=0.01),
            dict(base, linje=21.5, status="vunnen", resultat_enheter=0.01, bokford=1.0e9 - 1800)]   # alt-linje, samma prestation
    (tmp_path / "nba_modelltest.json").write_text(json.dumps(rows))
    a, b = evaluate(tmp_path), evaluate(tmp_path)
    s = a["per_bokforing"]["modelltest"]
    assert s["rader"] == 2 and s["prestationer"] == 1 and s["brier"]["n"] == 1
    assert a["per_bokforing"] == b["per_bokforing"]


def test_sgo_quotes_two_sided_half_lines_fresh():
    import time
    from propsbot.sources.sgo import quotes_for
    now = time.time()
    iso = lambda ts: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ts))
    def bk(odds, ln, age=60, avail=True):
        return {"available": avail, "odds": odds, "overUnder": ln, "lastUpdatedAt": iso(now - age)}
    ev = {"teams": {"home": {"names": {"long": "Indiana Pacers"}}, "away": {"names": {"long": "Washington Wizards"}}},
          "status": {"startsAt": iso(now + 7200)}, "players": {"P1": {"name": "Aaron Nesmith"}},
          "odds": {
              "a": {"playerID": "P1", "betTypeID": "ou", "sideID": "over", "statID": "points",
                    "byBookmaker": {"fanduel": bk("-114", "13.5"), "draftkings": bk("+105", "14"), "caesars": bk("-118", "13.5"),
                                    "bovada": bk("-110", "13.5", age=7200)}},
              "b": {"playerID": "P1", "betTypeID": "ou", "sideID": "under", "statID": "points",
                    "byBookmaker": {"fanduel": bk("-114", "13.5"), "draftkings": bk("-125", "14"),
                                    "bovada": bk("-110", "13.5", age=7200)}}}}
    evd = {"id": "m", "home_team": "Indiana Pacers", "away_team": "Washington Wizards", "commence_time": now + 7200}
    qs, _ = quotes_for([ev], evd, now)
    # FanDuel tvåsidigt ok; DraftKings heltal (push) bort; Caesars bara en sida bort; Bovada för gammalt bort
    assert {(q.book, q.side) for q in qs} == {("us_fanduel", "over"), ("us_fanduel", "under")}


def test_benjamini_hochberg():
    from propsbot.nba_eval import benjamini_hochberg
    # 11 marknader: en tydlig, resten brus. Bara den tydliga klarar FDR 0,10.
    p = {"a": 0.001, **{f"m{i}": 0.04 + 0.08 * i for i in range(10)}}
    assert benjamini_hochberg(p, 0.10) == {"a"}
    assert benjamini_hochberg({"x": 0.04, "y": 0.045}, 0.05) == {"x", "y"}   # stegvis: båda under q·i/m
    assert benjamini_hochberg({"x": 0.3}, 0.10) == set()
