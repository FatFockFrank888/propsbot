from types import SimpleNamespace as NS

from propsbot.decision import Candidate, Decision
from propsbot.live import select_live
from propsbot.models import OddsQuote


def row(match, player, market, odds, p, groups=3, line=4.5, stake=0.02):
    q = OddsQuote(book="unibet", match_id=match, player_id=player, market=market, line=line,
                  side="over", odds=odds, ts=0.0)
    c = Candidate(match, player, player, market, line, p, q, None, 1000.0, True, 120.0)
    return NS(row=NS(decision=Decision(c, True, True, 1.6, stake, [])), n_groups=groups, match="A – B")


class L:
    bets = []


S = {}


def test_live_thresholds_model_agreement_and_caps():
    pts_lo = row("m1", "a", "points", 2.0, 0.54)        # 8 % < 10 % poängkrav
    pts_hi = row("m1", "b", "points", 2.0, 0.56)        # 12 %
    thr = row("m1", "c", "threes", 2.0, 0.54)           # 8 %
    thr2 = row("m1", "d", "threes", 2.0, 0.55)          # 10 % men tredje spelet i matchen
    one_src = row("m2", "e", "assists", 2.0, 0.56, groups=1)
    no_model = row("m2", "f", "rebounds", 2.0, 0.56)
    steals = row("m2", "g", "steals", 2.0, 0.60)        # inte en live-marknad
    model = [row(r.row.decision.cand.match_id, r.row.decision.cand.player_id, r.row.decision.cand.market,
                 2.0, 0.55) for r in (pts_lo, pts_hi, thr, thr2, one_src, steals)]
    out = select_live([pts_lo, pts_hi, thr, thr2, one_src, no_model, steals], model, S, L())
    picked = {r.row.decision.cand.player_id for r in out}
    m1 = picked - {"f"}
    assert m1 in ({"b", "d"}, {"b", "c"})
    assert "f" in picked          # returer utan modellrad: tillåtet sedan 12/11
    assert len([r for r in out if r.row.decision.cand.match_id == "m1"]) == 2
    assert all(round(r.live_stake / 0.002) <= 5 for r in out)


def test_live_model_required_for_points_and_disagreement_blocks():
    pts_nomodel = row("m1", "a", "points", 2.0, 0.56)     # poäng utan modellrad: nej
    ast_nomodel = row("m2", "b", "assists", 2.0, 0.55)    # assist utan modellrad: ja
    reb_against = row("m3", "c", "rebounds", 2.0, 0.56)   # modellen säger emot: nej
    thr_backed = row("m4", "d", "threes", 2.0, 0.53)      # lägre edge men modellens stöd: först
    model = [row("m3", "c", "rebounds", 2.0, 0.51), row("m4", "d", "threes", 2.0, 0.56)]
    out = select_live([pts_nomodel, ast_nomodel, reb_against, thr_backed], model, S, L())
    assert [r.row.decision.cand.player_id for r in out] == ["d", "b"]
    assert out[1].live_model_edge is None
