"""Kommandon:
  python -m propsbot skanna            – en skanning med öppna källor (Kambi + Pinnacle)
  python -m propsbot bevaka            – skanna om och om igen, mobilnotis vid nya spel
  python -m propsbot skanna-oddsapi    – skanning enbart via The Odds API (kostar krediter)
  python -m propsbot bolag             – visa vilka bolag/marknader nyckeln ger
  python -m propsbot demo examples/match.json   – kör simulatorn på exempelmatchen
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _state_root() -> Path:
    import os
    d = os.environ.get("PROPSBOT_STATE_DIR")
    if not d:
        return ROOT
    p = Path(d).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_demo(args) -> None:
    from .config import Config
    from .pipeline import BookSetup, evaluate_match, format_table
    from .simulator import MatchSimulator
    from .sources.json_source import load_match
    from .store import Store

    cfg = Config()
    if args.sims:
        cfg.sim.n_sims = args.sims
    match, quotes = load_match(args.match_json)
    books = BookSetup(pinnacle="pinnacle", kambi_group=frozenset(args.kambi.split(",")),
                      playable=frozenset(args.spelbara.split(",")))
    t0 = time.time()
    sim = MatchSimulator(match, cfg).run()
    print(f"{match.home.name} – {match.away.name}  |  väntade mål (Pinnacle) "
          f"{match.home.exp_goals:.2f}–{match.away.exp_goals:.2f}  |  simulerat "
          f"{sim.goals_home.mean():.2f}–{sim.goals_away.mean():.2f}  "
          f"({cfg.sim.n_sims} sim, {time.time() - t0:.1f} s)")
    now = args.now if args.now is not None else max((q.ts for q in quotes), default=time.time())
    rows = evaluate_match(match, quotes, books, cfg, now=now,
                          store=Store(args.db) if args.db else None, sim=sim)
    print(format_table(rows, only_shown=not args.alla))


def cmd_scan(args) -> None:
    from .scan import format_scan, run_scan
    from .sources.the_odds_api import OddsApiError
    try:
        rows = run_scan(Path(args.settings), Path(args.ut), Path(args.db),
                        only_playable=args.bara_spel)
    except OddsApiError as e:
        sys.exit(f"Fel: {e}")
    print()
    print(format_scan(rows))
    n = sum(r.row.decision.playable and r.row.decision.show for r in rows)
    print(f"\n{n} spelbara ben (odds 1,40–6,00).")


def _ensure_topic(settings_path: Path) -> str:
    import json
    from .notify import new_topic
    from .scan import load_settings
    s = load_settings(settings_path)
    if not s.get("ntfy_topic"):
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
        raw["ntfy_topic"] = new_topic()
        settings_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        s["ntfy_topic"] = raw["ntfy_topic"]
    return s["ntfy_topic"]


def _print_topic(topic: str) -> None:
    print("=" * 64)
    print("MOBILNOTISER: installera appen 'ntfy' (App Store / Google Play),")
    print(f"tryck + och prenumerera på kanalen:   {topic}")
    print("=" * 64)


OBSOLETE = ("nba_usodds.json", "bokforing_v2.json", "bokforing_skugga_v3.json", "bokforing_modell_v3.json", "parlays_v2.json", "bokforing.json", "bokforing_skugga.json", "bokforing_skugga_v2.json", "parlays.json",
            "bokforing_modell.json", "bokforing_modell_v2.json", "nba_bokforing.json",
            "nba_skugga.json", "nba_parlays.json", "resultat",
            # NHL borttagen 12/11 (historiken finns kvar i data-grenens git-historik)
            "nhl", "site/nhl", ".cache_odds/nhl", "site/csv/nhl.csv", "site/csv/nhl_live.csv", "site/csv/nhl_sammanfattning.csv")


def _cleanup(root: Path) -> None:
    """Ta bort bokföringar från tidigare, felaktiga versioner (och gamla CSV-filer)."""
    import shutil
    for name in OBSOLETE:
        f = root / name
        if f.is_dir():
            shutil.rmtree(f, ignore_errors=True)
        elif f.exists():
            f.unlink()


def cmd_free(args) -> None:
    from .free_scan import scan_once
    from .scan import format_scan
    _cleanup(_state_root())
    topic = _ensure_topic(Path(args.settings))
    _print_topic(topic)
    import traceback
    try:
        _announce_merge(_state_root(), Path(args.settings))
    except Exception as e:
        print(f"Testnotis: fel {type(e).__name__}: {e}")
    # En bot, två sporter: varje sport körs för sig så att ett fel i en aldrig stoppar de andra.
    try:
        rows = scan_once(_state_root(), Path(args.settings))
        print()
        print(format_scan(rows))
    except Exception as e:
        print(f"Fotboll: fel {type(e).__name__}: {e}")
        traceback.print_exc()
    try:
        run_nba(_state_root(), Path(args.settings))
    except Exception as e:
        print(f"NBA: fel {type(e).__name__}: {e}")
        traceback.print_exc()
    try:
        from .site import build_site
        build_site(_state_root(), Path(args.settings))
    except Exception as e:
        print(f"Webbsidan: fel {type(e).__name__}: {e}")
        traceback.print_exc()
    # Topp 5 skickas inte som notis (14/11): topp 5 är alltid LIVE-spel som redan fått en egen notis.
    try:
        from .workbook import build
        n = build(_state_root(), _state_root() / "site" / "propsbot_bokforing.xlsx")
        print(f"Excel-bokföring: {n} spel")
        from .workbook import write_csv_exports
        write_csv_exports(_state_root(), _state_root() / "site" / "csv")
    except Exception as e:
        print(f"Excel-bokföring: fel {type(e).__name__}: {e}")


def run_nba(root: Path, settings_path: Path) -> None:
    import os
    from .export import write_site
    from .free_scan import notify_new
    from .nba import nba_scan
    from .parlays import ParlayLedger, suggest
    from .results import settle_open  # noqa: F401  (fotbollens rättning används inte för NBA)
    from .scan import load_settings
    settings = load_settings(settings_path)
    if not settings.get("nba_enabled", True):
        return
    res = nba_scan(root, settings_path)
    sugg = suggest(res["rows"], res["evd"], settings)
    pl = ParlayLedger(root / "nba_parlays_v2.json")
    new_p = pl.record(sugg)
    from .nba import settle_nba
    from .sources.http import JsonClient
    try:
        settle_nba(pl.legs_ledger(), JsonClient(root / ".cache_odds", ttl_s=900))
    except Exception as e:
        res["diag"].log(f"NBA parlay-rättning: {e}")
    pl.update_status()
    pl.save()
    write_site(root / "site" / "nba", res["rows"], res["ledger"], settings, res.get("test"),
               {"parlay_forslag": sugg, "parlay_bokforing": sorted(pl.items, key=lambda x: -x["bokford"]),
                "parlay_sammanfattning": pl.summary()}, res["shadow"], sport="NBA",
               live_ledger=res.get("live") if settings.get("live_on", True) else None,
               live_keys={__import__("propsbot.ledger", fromlist=["bet_key"]).bet_key(r) for r in res.get("live_rows", [])})
    if settings.get("ntfy_topic"):
        nba_settings = dict(settings, ntfy_topic=settings["ntfy_topic"])
        # Bara LIVE-spelen skickas som notis; övrigt bokförs som data.
        n = notify_new(res.get("live_rows", []) if settings.get("live_on", True) else res["playable"],
                       nba_settings, root, live=True)
        from .clv_signal import units
        from .notify import send
        for x in (new_p if settings.get("live_enabled", True) and settings.get("parlays_notify", False) else []):
            legs = "\n".join(f"• {l['spelare']} {l['marknad']} {'under' if l.get('sida') == 'under' else 'över'} {l['linje']:g} ({l['odds']:.2f})"
                             for l in x["ben"])
            send(settings["ntfy_topic"], f"NBA PARLAY {x['antal_ben']} ben @ {x['odds']:.2f} hos {x['bolag']}",
                 f"{legs}\nEV {x['ev']:.1%}, insats {units(x['insats_pct'])}/10 units")
        res["diag"].log(f"NBA notiser: {n}")
    if os.environ.get("GITHUB_ACTIONS"):
        keep = [l for l in res["diag"].lines if l.startswith(("Kambi NBA", "Pinnacle NBA", "NBA"))][:30]
        print("::notice title=nba::" + "%0A".join(x.replace("%", "%25") for x in keep))


def push_overview(settings: dict) -> str:
    """Vilka spel som ger notis, per sport."""
    th = settings.get("live_min_edge", {})
    lines = [
        "NBA: LIVE-spel (" + ", ".join(f"{k} ≥{v:.0%}" for k, v in th.items()) + ")"
        if settings.get("live_on", True) and settings.get("nba_enabled", True) else "NBA: av",
        f"Fotboll: LIVE-spel {', '.join({'shots_on_target': 'skott på mål', 'shots': 'skott'}.get(m, m) for m in settings.get('football_markets', ['shots_on_target']))} (≥{settings.get('min_edge_all', 0.05):.0%})" if settings.get("football_live") else "Fotboll: bara data (ingen notis)",
        ("Fotboll sides/totals: LIVE-spel 1X2, mål över/under, handikapp mot Pinnacle "
         f"(≥{settings.get('sides_min_edge', 0.03):.0%})") if settings.get("sides_live")
        else "Fotboll sides/totals (1X2, mål, handikapp mot Pinnacle): bara data tills vidare",
        "Test (fouls, kort), skuggspel, modelltest, parlays: bara data",
        "Ett spel per spelare och match – aldrig två notiser på samma spelare.",
    ]
    return "\n".join(lines)


def _announce_merge(root: Path, settings_path: Path) -> None:
    """Första körningen av den sammanslagna boten: en notis som visar att kanalen fungerar."""
    import hashlib
    from .notify import send
    from .scan import load_settings
    s = load_settings(settings_path)
    topic = s.get("ntfy_topic")
    if not topic:
        return
    f = root / "notis_sammanslagen.txt"
    overview = push_overview(s)
    th = hashlib.sha1((topic + overview).encode()).hexdigest()[:12]   # ny notis när reglerna ändras
    if f.exists() and f.read_text(encoding="utf-8").strip() == th:
        return
    if send(topic, "Propsbot: så här skickas notiser",
            "Fotboll och NBA i en bot.\n" + overview, priority=3, tags="white_check_mark"):
        f.write_text(th, encoding="utf-8")
        print("Testnotis (sammanslagen bot) skickad.")


def cmd_watch(args) -> None:
    from .free_scan import watch
    topic = _ensure_topic(Path(args.settings))
    _print_topic(topic)
    try:
        watch(_state_root(), Path(args.settings))
    except KeyboardInterrupt:
        print("Avslutad.")


def cmd_params(args) -> None:
    from .params import as_markdown
    md = as_markdown(Path(args.settings))
    (ROOT / "PARAMETRAR.md").write_text(md + chr(10), encoding="utf-8")
    print(md)


def cmd_books(args) -> None:
    from .scan import discover_books
    from .sources.the_odds_api import OddsApiError
    try:
        discover_books(Path(args.settings))
    except OddsApiError as e:
        sys.exit(f"Fel: {e}")


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0].endswith(".json"):
        argv = ["demo"] + argv  # bakåtkompatibelt: python -m propsbot examples/match.json
    ap = argparse.ArgumentParser(prog="propsbot", description="Player props för fotboll")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("skanna", help="en skanning med Kambi + Pinnacle (gratis)")
    f.add_argument("--settings", default=str(ROOT / "settings.json"))
    f.set_defaults(func=cmd_free)

    w = sub.add_parser("bevaka", help="skanna löpande och skicka mobilnotiser")
    w.add_argument("--settings", default=str(ROOT / "settings.json"))
    w.set_defaults(func=cmd_watch)

    s = sub.add_parser("skanna-oddsapi", help="skanning via The Odds API (krediter)")
    s.add_argument("--settings", default=str(ROOT / "settings.json"))
    s.add_argument("--ut", default=str(ROOT / "resultat"))
    s.add_argument("--db", default=str(ROOT / "propsbot.sqlite"))
    s.add_argument("--bara-spel", action="store_true")
    s.set_defaults(func=cmd_scan)

    pa = sub.add_parser("parametrar", help="skriv alla parametrar per sport till PARAMETRAR.md")
    pa.add_argument("--settings", default=str(ROOT / "settings.json"))
    pa.set_defaults(func=cmd_params)

    b = sub.add_parser("bolag", help="visa bolag och marknader för nyckeln")
    b.add_argument("--settings", default=str(ROOT / "settings.json"))
    b.set_defaults(func=cmd_books)

    d = sub.add_parser("demo", help="kör simulatorn på en JSON-match")
    d.add_argument("match_json")
    d.add_argument("--alla", action="store_true")
    d.add_argument("--db", default=None)
    d.add_argument("--sims", type=int, default=None)
    d.add_argument("--now", type=float, default=None)
    d.add_argument("--kambi", default="unibet,paf,svenskaspel")
    d.add_argument("--spelbara", default="unibet,paf,svenskaspel,bet365")
    d.set_defaults(func=cmd_demo)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
