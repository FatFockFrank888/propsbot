"""Skapar examples/match.json: en PÅHITTAD match med påhittade spelare och odds.

Bara för att kunna köra hela kedjan utan API-nycklar. Oddsen byggs från en
"sann" sannolikhet med brus och bolagsmarginal, så några ben får edge.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from propsbot.config import Config  # noqa: E402
from propsbot.simulator import MatchSimulator  # noqa: E402
from propsbot.sources.json_source import load_match  # noqa: E402

random.seed(3)


def squad(prefix, team_name, stars):
    pos = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "W", "W", "ST", "ST", "CM", "W"]
    players = []
    for i, p in enumerate(pos):
        d = {"id": f"{prefix}{i+1}", "name": f"{team_name} {p}{i+1}", "position": p,
             "minutes": {"p_start": 1.0 if i < 11 else 0.0}}
        players.append(d)
    for idx, extra in stars.items():
        players[idx].update(extra)
    return players


base = {
    "match_id": "EX-2026-11-01-HEM-BOR",
    "competition": "Exempelligan",
    "kickoff_utc": "2026-11-01T15:00:00Z",
    "lineup_confirmed": True,
    "referee": {"name": "Domare A", "added_time": 9.5, "pen_mult": 1.1, "freekick_mult": 1.05},
    "weather": {"wind_ms": 4.0, "heavy_rain": False, "artificial_turf": False},
    "pinnacle_match_odds": {"1x2": [1.62, 4.10, 5.60], "total": {"line": 2.5, "odds": [1.83, 2.06]}},
    "home": {
        "name": "Hemmalaget",
        "base_mix": {"distance": 0.33},
        # Bortalaget sitter lågt: hemmalaget får fler distansskott/inlägg.
        "opponent_profile": {"block_height": -1.3, "allowed_mult": {"distance": 1.12, "header": 1.08,
                                                                     "counter": 0.85}},
        "players": squad("H", "Hemma", {
            7: {"share": {"distance": 0.30, "freekick": 0.45}, "pen_order": 1,
                "on_target": {"distance": 0.31}, "xa_share": 0.20},
            10: {"share": {"box": 0.34, "header": 0.28}, "pen_order": 2},
            11: {"minutes": {"p_start": 0.0, "p_sub_on_if_bench": 0.0}},
        }),
    },
    "away": {
        "name": "Bortalaget",
        "opponent_profile": {"block_height": 0.6, "allowed_mult": {"counter": 1.10}},
        "players": squad("A", "Borta", {
            10: {"share": {"box": 0.30, "counter": 0.38}, "pen_order": 1},
        }),
    },
}

path = ROOT / "match.json"
path.write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
match, _ = load_match(path)
cfg = Config()
cfg.sim.n_sims = 6000
sim = MatchSimulator(match, cfg).run()

quotes = []
TS = 1793545200.0  # 2026-11-01 14:00 UTC
lines = {"shots": [0.5, 1.5, 2.5], "shots_on_target": [0.5, 1.5], "goal": [0.5], "assist": [0.5]}
margins = {"shots": 0.08, "shots_on_target": 0.09, "goal": 0.11, "assist": 0.13}
for p in match.home.players + match.away.players:
    if p.position == "GK" or sim.n_played(p.player_id) < 500:
        continue
    for mk, ls in lines.items():
        for line in ls:
            pt = sim.prob_over(p.player_id, mk, line)
            if not 0.08 < pt < 0.9:
                continue
            truth = min(0.95, max(0.03, pt * random.uniform(0.9, 1.12)))
            kambi = 1 / (truth * (1 + margins[mk]))
            kambi = round(kambi, 2)
            for book, adj, lag in (("unibet", 0, 0), ("paf", 0, 20), ("svenskaspel", 0.12, 60)):
                o = round(kambi * (1 + adj * (random.random() < 0.15)), 2)
                quotes.append({"book": book, "player_id": p.player_id, "market": mk, "line": line,
                               "side": "over", "odds": o, "ts": TS - lag})
            # Pinnacle tvåsidigt där marknaden finns (skott/skott på mål).
            if mk in ("shots", "shots_on_target") and random.random() < 0.7:
                pp = min(0.95, max(0.05, truth * random.uniform(0.97, 1.03)))
                quotes.append({"book": "pinnacle", "player_id": p.player_id, "market": mk,
                               "line": line, "side": "over", "odds": round(1 / (pp * 1.025), 3),
                               "ts": TS})
                quotes.append({"book": "pinnacle", "player_id": p.player_id, "market": mk,
                               "line": line, "side": "under",
                               "odds": round(1 / ((1 - pp) * 1.025), 3), "ts": TS})
            if random.random() < 0.6:
                o = round(1 / (truth * (1 + margins[mk] * random.uniform(0.6, 1.4))), 2)
                quotes.append({"book": "bet365", "player_id": p.player_id, "market": mk,
                               "line": line, "side": "over", "odds": o, "ts": TS - 30})

base["quotes"] = quotes
path.write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Skrev {path} med {len(quotes)} odds")
