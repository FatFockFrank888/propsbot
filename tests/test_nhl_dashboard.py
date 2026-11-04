import json
import re
from dataclasses import replace

from nhl.bot_settings import BotSettings
from nhl.dashboard import write_dashboard
from nhl.ledger import Ledger, LEDGERS


def _extract(html: str) -> dict:
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "embedded data missing"
    return json.loads(m.group(1))


def test_dashboard_empty_and_with_bets(tmp_path):
    s = replace(BotSettings(), data_dir=str(tmp_path / "data"))
    out = write_dashboard(s, tmp_path / "dash.html")
    data = _extract(out.read_text(encoding="utf-8"))
    assert data["status"]["level"] == "warning"
    assert data["ledgers"]["live"]["bets"] == 0 and data["cum"]["live"] == []

    led = Ledger("live", s.data_path / LEDGERS["live"])
    for i, (status, profit) in enumerate([("won", 3.0), ("lost", -2.0), ("open", None)]):
        led.add({"id": str(i), "created": f"2026-11-0{i + 1}T10:00:00+00:00", "game_id": i, "game": "OTT@BUF",
                 "start": f"2026-11-0{i + 1}T23:00:00+00:00", "us_date": f"2026-11-0{i + 1}",
                 "player": "Name </script><b>x", "player_id": i, "line": 2.5, "side": "over", "book": "unibet",
                 "odds": 2.5, "units": 2, "stake": 40, "edge": 0.08, "model_edge": 0.05, "clv": 0.03,
                 "status": status, "profit_units": profit, "settled_at": None if status == "open" else f"2026-11-0{i + 2}"})
    led.save()
    html = write_dashboard(s, tmp_path / "dash.html").read_text(encoding="utf-8")
    assert "</script><b>" not in html  # embedded names cannot break out of the data block
    data = _extract(html)
    assert [p["cum"] for p in data["cum"]["live"]] == [3.0, 1.0]
    assert len(data["open_live"]) == 1 and len(data["clv_series"]) == 3
    assert data["ledgers"]["live"]["settled"] == 2
