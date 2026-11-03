from propsbot.referees import factor, norm


def test_factor_uses_fouls_then_cards_and_caps():
    st = {"fd": {"michael oliver": [10, 300.0, 50.0]}, "tm": {"tobias stieler": [200, 1000.0]},
          "snitt": {"fd_fouls": 24.0, "tm_kort": 4.0}}
    m, note = factor(st, "Michael Oliver")          # 30 fouls/match mot 24 -> uppåt, tak 1,15
    assert 1.0 < m <= 1.15 and "fouls/match" in note
    m2, note2 = factor(st, "Tobias Stieler")        # 5 kort/match mot 4 -> lite uppåt
    assert 1.0 < m2 < 1.15 and "kort/match" in note2
    assert factor(st, "Okänd Domare")[0] == 1.0
    assert norm("Clément Turpin") == "clement turpin"
