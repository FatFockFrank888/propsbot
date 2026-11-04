"""Command-line entry point: `python -m nhl <command>`."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

from . import __version__
from .backtest import collect_records, print_summary, summarize
from .bot_settings import BotSettings
from .config import Settings, season_for
from .edges import evaluate
from .http import HttpError, JsonClient
from .names import normalize_name
from .nhl_api import NhlApi
from .odds import OddsApi, PropQuote, load_odds_csv, match_events, odds_csv_path, write_odds_template
from .report import evaluation_rows, print_evaluations, print_projections, projection_rows, write_csv, write_picks_json
from .slate import build_slate

log = logging.getLogger("nhl")


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD") from exc


def _lines(value: str) -> list[float]:
    try:
        return [float(x) for x in value.split(",") if x.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid line list {value!r}") from exc


def _csv_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nhl", description="NHL shots-on-goal player props bot")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="-v info, -vv debug")
    parser.add_argument("--env-file", type=Path, help="path to .env (default: project root)")
    sub = parser.add_subparsers(dest="command", required=True)

    sl = sub.add_parser("slate", help="project every skater on a date and find +EV bets")
    sl.add_argument("--date", type=_date, default=date.today(), help="game date YYYY-MM-DD (default: today)")
    sl.add_argument("--teams", type=_csv_list, help="only games involving these teams, e.g. BUF,TOR")
    sl.add_argument("--player", help="only show players whose name contains this text")
    sl.add_argument("--lines", type=_lines, default=[1.5, 2.5, 3.5], help="lines for projection table (default 1.5,2.5,3.5)")
    sl.add_argument("--top", type=int, default=40, help="rows in projection table (0 = all)")
    sl.add_argument("--odds-file", type=Path, help="manual odds CSV (default: odds/<date>.csv)")
    sl.add_argument("--no-api", action="store_true", help="do not call The Odds API even if a key is set")
    sl.add_argument("--include-started", action="store_true", help="include live/finished games")
    sl.add_argument("--show-all", action="store_true", help="also list evaluated bets that did not qualify")
    sl.add_argument("--min-edge", type=float, help="override MIN_EDGE (e.g. 0.03)")
    sl.add_argument("--min-ev", type=float, help="override MIN_EV (e.g. 0.03)")
    sl.add_argument("--bankroll", type=float, help="override BANKROLL")
    sl.add_argument("--no-save", action="store_true", help="do not write files to output/ or odds/")

    bt = sub.add_parser("backtest", help="walk-forward test of the projection model on a past season")
    bt.add_argument("--season", default=None, help="season id, e.g. 20252026 (default: last completed)")
    bt.add_argument("--teams", type=_csv_list, help="restrict to these teams (faster)")
    bt.add_argument("--lines", type=_lines, default=[1.5, 2.5, 3.5])

    sc = sub.add_parser("scan", help="one edge scan: Kambi books vs references + model, update ledgers")
    sc.add_argument("--no-notify", action="store_true", help="do not send ntfy notifications")
    sc.add_argument("--diagnose", action="store_true", help="save raw Kambi responses that fail to parse")

    wa = sub.add_parser("watch", help="scan continuously (every scan_interval_min)")
    wa.add_argument("--no-notify", action="store_true")
    wa.add_argument("--diagnose", action="store_true")

    sub.add_parser("report", help="results per ledger: ROI, CLV, record")
    sub.add_parser("validate", help="is the bot finding +EV? CLV/ROI with confidence intervals, calibration")
    sub.add_parser("notify-test", help="send a test notification to your ntfy topic")
    db = sub.add_parser("dashboard", help="build output/dashboard.html and open it in the browser")
    db.add_argument("--no-open", action="store_true", help="only write the file")

    ex = sub.add_parser("export", help="write all ledgers to CSV (opens in Excel)")
    ex.add_argument("--out", type=Path, help="output folder (default: output/ledgers)")
    ex.add_argument("--sheet", action="store_true",
                    help="write Google-Sheet CSVs (nhl_live.csv, nhl.csv, nhl_sammanfattning.csv) like the other bots")

    kp = sub.add_parser("kambi-probe", help="list NHL events and shot criteria per Kambi book")
    kp.add_argument("--save", action="store_true", help="save raw event JSON to data/diagnos")

    sub.add_parser("clear-cache", help="delete cached API responses")
    return parser


def _configure_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity == 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def cmd_slate(args: argparse.Namespace, s: Settings) -> int:
    overrides = {k: v for k, v in {"min_edge": args.min_edge, "min_ev": args.min_ev, "bankroll": args.bankroll}.items() if v is not None}
    s = replace(s, **overrides)
    client = JsonClient(s.cache_dir)
    nhl = NhlApi(client)

    print(f"NHL shots-on-goal props | {args.date.isoformat()} | bet books: {', '.join(s.bet_books)}")
    projections = build_slate(nhl, s, args.date, teams=args.teams, include_started=args.include_started)
    if not projections:
        print("No upcoming games found for this date.")
        return 0
    games = {p.game.game_id: p.game for p in projections}
    print(f"{len(games)} game(s), {len(projections)} skaters projected\n")

    shown = projections
    if args.player:
        needle = normalize_name(args.player)
        shown = [p for p in projections if needle in normalize_name(p.skater.name)]
    print_projections(shown, args.lines, s.dispersion, args.top or None)

    # ---- odds
    quotes: list[PropQuote] = []
    csv_path = args.odds_file or odds_csv_path(s, args.date)
    if csv_path.is_file():
        csv_quotes = load_odds_csv(csv_path)
        quotes += csv_quotes
        print(f"\nLoaded {len(csv_quotes)} manual quote(s) from {csv_path}")

    if s.odds_api_key and not args.no_api:
        try:
            api = OddsApi(client, s)
            mapping = match_events(games.values(), api.events(), nhl.abbrev_by_full_name())
            api_quotes: list[PropQuote] = []
            for game_id, event_id in mapping.items():
                api_quotes += api.props(event_id, game_id)
            quotes += api_quotes
            books = sorted({q.book for q in api_quotes})
            print(f"Odds API: {len(api_quotes)} quote(s) from {', '.join(books) or 'no books'} "
                  f"for {len(mapping)}/{len(games)} game(s); requests remaining: {api.requests_remaining or '?'}")
            missing = [b for b in s.bet_books if b not in books]
            if missing:
                print(f"  No API props from {', '.join(missing)} - enter their lines in {csv_path}")
        except HttpError as exc:
            print(f"Odds API error: {exc}", file=sys.stderr)
    elif not s.odds_api_key:
        log.info("ODDS_API_KEY not set; using manual odds only")

    if not args.no_save and write_odds_template(csv_path, projections, s.dispersion):
        print(f"\nWrote odds template: {csv_path}\n  Fill in book/over/under (decimal odds) for "
              f"{'/'.join(s.bet_books)} and re-run.")

    if not quotes:
        print("\nNo odds loaded - showing projections only.")
        if not args.no_save:
            _save_projections(s, args.date, projections, args.lines)
        return 0

    evals, unmatched = evaluate(projections, quotes, s)
    if args.player:
        needle = normalize_name(args.player)
        evals = [e for e in evals if needle in normalize_name(e.projection.skater.name)]
    picks = [e for e in evals if e.is_pick]
    print_evaluations(picks, s, f"PICKS ({len(picks)})  min edge {s.min_edge:.1%}, min EV {s.min_ev:.1%}, "
                                f"{s.kelly_fraction:g}x Kelly, bankroll {s.bankroll:,.0f} {s.currency}")
    if args.show_all:
        print_evaluations([e for e in evals if not e.is_pick], s, "Evaluated, not qualifying")
    if unmatched:
        names = sorted({q.player for q in unmatched})
        print(f"\nUnmatched player names ({len(names)}): {', '.join(names[:15])}{' ...' if len(names) > 15 else ''}")

    if not args.no_save:
        _save_projections(s, args.date, projections, args.lines)
        headers, rows = evaluation_rows(evals, s)
        write_csv(s.output_dir / f"evaluations_{args.date.isoformat()}.csv", headers, rows)
        write_picks_json(s.output_dir / f"picks_{args.date.isoformat()}.json", picks, s, args.date)
        print(f"\nSaved results to {s.output_dir}")
    return 0


def _save_projections(s: Settings, day: date, projections, lines) -> None:
    headers, rows = projection_rows(sorted(projections, key=lambda p: -p.mu), lines, s.dispersion)
    write_csv(s.output_dir / f"projections_{day.isoformat()}.csv", headers, rows)


def cmd_backtest(args: argparse.Namespace, s: Settings) -> int:
    season = args.season
    if season is None:
        today = date.today()
        current = season_for(today)
        start = int(current[:4]) - 1
        season = f"{start}{start + 1}"
    if len(season) != 8 or not season.isdigit():
        print(f"Invalid season {season!r}; expected e.g. 20252026", file=sys.stderr)
        return 2
    client = JsonClient(s.cache_dir)
    nhl = NhlApi(client)
    print(f"Collecting game logs for {season} (first run downloads ~1 request per player; cached afterwards)...")
    records = collect_records(nhl, s, season, teams=args.teams)
    print_summary(summarize(records, args.lines, s.dispersion), season, s.dispersion)
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)
    try:
        settings = Settings.from_env(args.env_file)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        if args.command == "slate":
            return cmd_slate(args, settings)
        if args.command == "backtest":
            return cmd_backtest(args, settings)
        if args.command in ("scan", "watch", "report", "export", "kambi-probe", "validate", "notify-test", "dashboard"):
            from . import bot_cli

            bot = BotSettings.load()
            return bot_cli.run(args, bot, settings)
        if args.command == "clear-cache":
            removed = JsonClient(settings.cache_dir).clear_cache()
            print(f"Removed {removed} cached response(s).")
            return 0
    except HttpError as exc:
        print(f"Network/API error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    return 0
