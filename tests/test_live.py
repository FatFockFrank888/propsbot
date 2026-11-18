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
    rows_ = [pts_lo, pts_hi, thr, thr2, one_src, no_model, steals]
    free = select_live(rows_, model, S, L())             # 18/11: inga tak som standard
    assert len([r for r in free if r.row.decision.cand.match_id == "m1"]) == 3
    out = select_live(rows_, model, {"live_max_per_match": 2}, L())   # tak kan slås på igen i settings
    picked = {r.row.decision.cand.player_id for r in out}
    m1 = picked - {"f"}
    assert m1 in ({"b", "d"}, {"b", "c"})
    assert "f" in picked          # returer utan modellrad: tillåtet sedan 12/11
    assert len([r for r in out if r.row.decision.cand.match_id == "m1"]) == 2
    assert all(1 <= round(r.live_stake / 0.002) <= 10 for r in out)   # 1–10u efter styrkan (14/11)


def test_live_model_required_for_points_and_disagreement_blocks():
    pts_nomodel = row("m1", "a", "points", 2.0, 0.56)     # poäng utan modellrad: nej
    ast_nomodel = row("m2", "b", "assists", 2.0, 0.55)    # assist utan modellrad: ja
    reb_against = row("m3", "c", "rebounds", 2.0, 0.56)   # modellen säger emot: nej
    thr_backed = row("m4", "d", "threes", 2.0, 0.53)      # lägre edge men modellens stöd: först
    model = [row("m3", "c", "rebounds", 2.0, 0.51), row("m4", "d", "threes", 2.0, 0.56)]
    out = select_live([pts_nomodel, ast_nomodel, reb_against, thr_backed], model, dict(S, live_use_model=True), L())
    assert [r.row.decision.cand.player_id for r in out] == ["d", "b"]
    assert out[1].live_model_edge is None


def test_live_ignores_model_by_default():
    """15/11: modellen slog inte skarp stängning – LIVE väljer och rankar bara på edge mot Pinnacle/DK."""
    pts_nomodel = row("m1", "a", "points", 2.0, 0.56)
    reb_against = row("m3", "c", "rebounds", 2.0, 0.57)
    thr_backed = row("m4", "d", "threes", 2.0, 0.53)
    model = [row("m3", "c", "rebounds", 2.0, 0.51), row("m4", "d", "threes", 2.0, 0.56)]
    out = select_live([pts_nomodel, reb_against, thr_backed], model, S, L())
    ids = [r.row.decision.cand.player_id for r in out]
    assert set(ids) <= {"a", "c", "d"} and ids == sorted(ids, key=lambda i: -next(
        r.row.decision.cand.edge for r in (pts_nomodel, reb_against, thr_backed) if r.row.decision.cand.player_id == i))


def test_live_requires_pinnacle_line():
    with_pin = row("m1", "a", "assists", 2.0, 0.56)
    without_pin = row("m2", "b", "assists", 2.0, 0.56)      # t.ex. bara DraftKings + Kalshi
    other_line = row("m3", "c", "assists", 2.0, 0.56, line=5.5)
    sharp = {("m1", "a", "assists", 4.5), ("m3", "c", "assists", 4.5)}
    out = select_live([with_pin, without_pin, other_line], [], S, L(), sharp)
    assert [r.row.decision.cand.player_id for r in out] == ["a"]
    assert len(select_live([with_pin, without_pin], [], S, L())) == 2   # None = inget krav


def test_live_dk_reference_for_markets_pinnacle_lacks():
    """Steals/blocks/kombos: DraftKings-linjen räcker som referens (Pinnacle saknar marknaden)."""
    s = {"live_min_edge": {"steals": 0.07, "pa": 0.07}, "live_odds_window": [1.5, 3.5]}
    st = row("m1", "a", "steals", 2.0, 0.56)
    pa = row("m2", "b", "pa", 2.0, 0.56)
    sharp = {("m1", "a", "steals", 4.5), ("m2", "b", "pa", 4.5)}   # byggs i nba.py av Pinnacle + DK
    assert [r.row.decision.cand.player_id for r in select_live([st, pa], [], s, L(), sharp)] == ["a", "b"]


def test_teammate_news_holds_unders_only():
    """Lagkamrat nyss out: under-spel på laget väntar (referensen kan släpa), över påverkas inte."""
    from propsbot.news import hold_after_teammate_news
    team = NS(name="Utah Jazz", players={"a": NS(minutes=30), "b": NS(minutes=28), "star": NS(minutes=34)})
    last = {"models": {"m1": {"a": {}, "b": {}, "star": {}}}, "teams": {"m1": (team, None)}}
    under = row("m1", "a", "points", 2.0, 0.56)
    under.row.decision.cand.best = OddsQuote(book="unibet", match_id="m1", player_id="a", market="points",
                                             line=4.5, side="under", odds=2.0, ts=0.0)
    over = row("m1", "b", "points", 2.0, 0.56)
    inj = [{"key": "star", "name": "Star", "team": "Utah Jazz", "status": "out", "ts": 1000.0}]
    assert hold_after_teammate_news([under, over], inj, last, 1000.0 + 600) == 1
    assert not under.row.decision.playable and over.row.decision.playable
    under.row.decision.playable = True
    assert hold_after_teammate_news([under], inj, last, 1000.0 + 3600) == 0     # efter 45 min: inget stopp
