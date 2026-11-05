"""Ett spel per spelare och match i varje bokföring (även Skugga/Modelltest)."""
from types import SimpleNamespace as NS

from propsbot.ledger import Ledger, mark_duplicates


def _row(pid, market, line, edge, book="unibet", side="over", playable=False):
    cand = NS(match_id="m1", player_id=pid, player_name=pid, market=market, line=line, edge=edge, p=0.55,
              best=NS(book=book, side=side, odds=2.0))
    dec = NS(cand=cand, playable=playable, show=True, stake=0.01, play_from=1.9, reasons=[])
    return NS(row=NS(decision=dec), match="A – B")


def test_mark_duplicates_keeps_first_booked():
    bets = [{"match_id": "m1", "spelare_id": "x", "bokford": 2, "id": 2},
            {"match_id": "m1", "spelare_id": "x", "bokford": 1, "id": 1},
            {"match_id": "m1", "spelare_id": "y", "bokford": 3, "id": 3},
            {"match_id": "m2", "spelare_id": "x", "bokford": 4, "id": 4}]
    assert mark_duplicates(bets) == 1
    assert [b.get("dubblett", False) for b in bets] == [True, False, False, False]
    assert mark_duplicates(bets) == 0  # idempotent


def test_shadow_records_one_leg_per_player(tmp_path):
    lg = Ledger(tmp_path / "skugga.json")
    rows = [_row("x", "points", 20.5, 0.04), _row("x", "points", 21.5, 0.06), _row("x", "rebounds", 5.5, 0.03),
            _row("y", "assists", 4.5, 0.05)]
    new = lg.record(rows, {}, predicate=lambda r: True)
    assert sorted((b["spelare_id"], b["linje"]) for b in new) == [("x", 21.5), ("y", 4.5)]
    # Nästa körning: spelaren finns redan -> inget nytt ben på samma spelare
    again = lg.record([_row("x", "threes", 2.5, 0.09)], {}, predicate=lambda r: True)
    assert again == []
    assert lg.summary()["antal"] == 2


def test_old_duplicates_not_counted(tmp_path):
    import json
    p = tmp_path / "l.json"
    base = {"match_id": "m1", "spelare_id": "x", "status": "vunnen", "insats_pct": 0.01, "resultat_enheter": 0.01,
            "odds": 2.0, "stangning": 1.9, "edge": 0.05, "bolag": "unibet", "avspark": 1}
    p.write_text(json.dumps([dict(base, key="a", id=1, bokford=1), dict(base, key="b", id=2, bokford=2)]), encoding="utf-8")
    lg = Ledger(p)
    s = lg.summary()
    assert s["antal"] == 1 and s["dubbletter"] == 1 and len(lg.bets) == 2
