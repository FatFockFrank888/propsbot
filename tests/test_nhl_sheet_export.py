import csv
from dataclasses import replace

from nhl.bot_settings import BotSettings
from nhl.ledger import LEDGERS, Ledger
from nhl.sheet_export import write_sheet_csvs

# Exact headers of the NBA/football bots' published CSVs (the Google Sheet relies on them).
LIVE_HEADER = "Bokförd,Sport,Typ,Avspark,Match,Spelare,Marknad,Sida,Linje,Bolag,Odds,Stängning,CLV (%),Sannolikhet,Edge,Insats (u),Status,Utfall,Resultat (u)"
SUMMARY_HEADER = "Sport,Typ,Spel,Avgjorda,Vunna,Träff %,Insats (u),Resultat (u),ROI %,Snitt-CLV %,Öppna,Uppdaterad (UTC)"


def test_sheet_csvs_match_other_bots(tmp_path):
    s = replace(BotSettings(), data_dir=str(tmp_path / "data"))
    led = Ledger("live", s.data_path / LEDGERS["live"])
    base = {"game_id": 1, "game": "OTT@BUF", "start": "2026-11-05T00:30:00+00:00", "us_date": "2026-11-04",
            "player_id": 1, "line": 2.5, "side": "over", "book": "unibet", "odds": 2.1, "units": 3,
            "p_fair": 0.52, "edge": 0.092, "close_odds": 1.95, "clv": 0.04, "ledger": "live"}
    led.add({**base, "id": "a", "created": "2026-11-04T18:00:00+00:00", "player": "Tage Thompson",
             "status": "won", "profit_units": 3.3, "result_sog": 4})
    led.add({**base, "id": "b", "created": "2026-11-04T19:00:00+00:00", "player": "Tim Stützle", "side": "under",
             "status": "open", "profit_units": None, "clv": None})
    led.save()

    live, alla, summary = write_sheet_csvs(s, tmp_path / "csv")
    # Must never collide with the sheet script's tab detection ('/live.csv', '/alla_spel.csv', ...).
    for p in (live, alla, summary):
        assert ("/" + p.name) not in ("/live.csv", "/alla_spel.csv", "/sammanfattning.csv", "/nba.csv",
                                      "/fotboll.csv", "/parlays.csv")
    lines = live.read_text(encoding="utf-8").splitlines()
    assert lines[0] == LIVE_HEADER
    rows = list(csv.reader(lines[1:]))
    # Same value formats as the other bots, e.g.
    # 2026-11-03 03:13,NBA,Modelltest,2026-11-03 03:16,Golden State Warriors – Phoenix Suns,Jordan Goodwin,
    # Poäng,Över,6.5,unibet,1.81,1.81,0.0,0.5939,0.0749,10.0,förlorad,4.0,-10.0
    assert rows[0][5] == "Tim Stützle" and rows[0][7] == "Under" and rows[0][16] == "öppen"  # newest first
    assert rows[0][17] == "" and rows[0][18] == ""
    assert rows[1] == ["2026-11-04 18:00", "NHL", "Live", "2026-11-05 00:30", "Buffalo Sabres – Ottawa Senators",
                       "Tage Thompson", "Skott på mål", "Över", "2.5", "unibet", "2.1", "1.95", "4.0", "0.5200",
                       "0.0920", "3.0", "vunnen", "4.0", "3.3"]
    s_lines = summary.read_text(encoding="utf-8").splitlines()
    assert s_lines[0] == SUMMARY_HEADER
    live_summary = next(r for r in csv.reader(s_lines[1:]) if r[1] == "Live")
    assert live_summary[2:5] == ["2", "1", "1"] and live_summary[8] == "110.0"
    assert alla.read_text(encoding="utf-8").splitlines()[0] == LIVE_HEADER
