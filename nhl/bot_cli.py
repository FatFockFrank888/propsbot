"""Edge-bot commands: scan, watch, report, export, kambi-probe."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from .bot_settings import BotSettings
from .config import Settings
from .http import HttpError, JsonClient
from .ledger import LEDGERS, open_ledgers
from .report import format_table
from .scanner import ScanReport, Scanner, next_interval_minutes
from .sources.kambi import KambiClient, is_sog_label, parse_sog_betoffers

log = logging.getLogger(__name__)

REVIEW_AT = 150  # settled live bets before parameters are reviewed

LEDGER_COLUMNS = [
    "created", "ledger", "status", "us_date", "game", "player", "team", "side", "line", "book", "odds",
    "units", "stake", "edge", "model_edge", "p_fair", "p_market", "p_model", "proj_sog", "groups", "sharp",
    "two_sided", "tags", "reasons", "close_odds", "close_p", "clv", "result_sog", "profit_units", "settled_at",
]


def run(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    if args.command == "scan":
        return cmd_scan(args, s, cfg)
    if args.command == "watch":
        return cmd_watch(args, s, cfg)
    if args.command == "report":
        return cmd_report(s)
    if args.command == "export":
        return cmd_export(args, s, cfg)
    if args.command == "kambi-probe":
        return cmd_kambi_probe(args, s, cfg)
    if args.command == "validate":
        return cmd_validate(s)
    if args.command == "notify-test":
        return cmd_notify_test(s)
    if args.command == "dashboard":
        return cmd_dashboard(args, s, cfg)
    raise ValueError(f"unknown command {args.command}")


def _ci(x: dict) -> str:
    if x["mean"] is None:
        return "n/a"
    if x["lo"] is None:
        return f"{x['mean']:+.1%} (n={x['n']})"
    return f"{x['mean']:+.1%}  [{x['lo']:+.1%}, {x['hi']:+.1%}]  t={x['t']:.1f}  n={x['n']}"


def cmd_validate(s: BotSettings) -> int:
    from .history import LineHistory
    from .validate import bet_validation, edge_buckets, leg_validation, verdict

    ledgers = open_ledgers(s)
    history = LineHistory(s.data_path / "line_history.sqlite")
    try:
        legs = leg_validation(history.settled_legs(), s.min_edge_all)
        counts = history.leg_counts()
    finally:
        history.close()

    for name, ledger in ledgers.items():
        v = bet_validation(ledger.bets)
        print(f"\n=== {name.upper()}  ({v['bets']} bets, {v['settled']} settled, {v['profit_units']:+.1f}u)")
        print(f"  CLV vs references  {_ci(v['clv'])}")
        print(f"  CLV vs Kambi close {_ci(v['kambi_clv'])}")
        print(f"  Price beat close   {_ci(v['price_clv'])}")
        print(f"  ROI per bet        {_ci(v['roi'])}")
        print(f"  Expected ROI       {_ci(v['expected_roi'])}")
        if name in ("live", "bokforing"):
            rows = [[b["bucket"], b["n"], _pct(b["avg_edge"]), _pct(b["avg_clv"]), b["settled"], _pct(b["roi"])]
                    for b in edge_buckets(ledger.bets)]
            print(format_table(["Edge", "Bets", "Avg edge", "Avg CLV", "Settled", "ROI"], rows, {1, 2, 3, 4, 5}))
        if name == "live":
            for line in verdict(v, legs):
                print(line)

    print(f"\n=== ALL EVALUATED LINES  (open {counts.get('open', 0)}, graded {legs['graded_lines']}, "
          f"push/void {counts.get('push', 0) + counts.get('void', 0)})")
    if legs["scores"]:
        rows = [[k.replace("close_p_", ""), f"{v['log_loss']:.4f}", f"{v['brier']:.4f}"] for k, v in legs["scores"].items()]
        print(format_table(["Source (at close)", "Log loss", "Brier"], rows, {1, 2}))
    print(f"  Would-have-bet lines (edge >= {s.min_edge_all:.0%}, passed rules): CLV {_ci(legs['flagged_clv'])}")
    print(f"                                                         ROI {_ci(legs['flagged_roi'])}")
    if legs["calibration"]:
        rows = [[c["bucket"], c["n"], _pct(c["predicted"]), _pct(c["actual"])] for c in legs["calibration"]]
        print("\n  Calibration of the fair probability (close)")
        print(format_table(["Fair p", "N", "Predicted", "Actual"], rows, {1, 2, 3}))
    return 0


def cmd_notify_test(s: BotSettings) -> int:
    from .notify import send

    if not s.ntfy_topic:
        print("ntfy_topic is empty in settings.json - set it first.")
        return 2
    ok = send(s.ntfy_topic, "NHL bot test", "If you can read this, live bets will reach this phone.")
    print("Sent." if ok else "Failed to send (see warning above).")
    return 0 if ok else 1


def _pct(x: float | None) -> str:
    return "" if x is None else f"{x * 100:.1f}%"


def print_scan(rep: ScanReport, s: BotSettings, cfg: Settings) -> None:
    local = rep.started.astimezone().strftime("%Y-%m-%d %H:%M")
    print(f"[{local}] Kambi NHL events {rep.kambi_events} | matched {rep.games} | with SOG props "
          f"{rep.games_with_props} | playable quotes {rep.playable_quotes} | reference quotes {rep.reference_quotes} "
          f"| legs {rep.legs} | Bovada games {rep.bovada_games} | Pinnacle games {rep.pinnacle_games}")
    if rep.us_fetched:
        print(f"  Odds API fetched: {', '.join(rep.us_fetched)}")
    if rep.settled or rep.legs_settled:
        print(f"  Settled {rep.settled} bet(s) and {rep.legs_settled} logged line(s)")
    if rep.games and not rep.games_with_props:
        print("  No shots-on-goal props posted at the Kambi books yet (they usually appear closer to puck drop).")
    for err in rep.errors:
        print(f"  ! {err}")
    if rep.unmatched:
        names = sorted(rep.unmatched)
        print(f"  Unmatched names ({len(names)}): {', '.join(names[:10])}{' ...' if len(names) > 10 else ''}")

    if rep.live_new:
        print(f"\n  NEW LIVE BETS ({len(rep.live_new)})" + ("" if s.ntfy_topic else "  [ntfy_topic not set: no notification]"))
        rows = [[b["player"], b["game"], f"{b['side'].capitalize()} {b['line']:g}", b["book"], f"{b['odds']:.2f}",
                 f"{b['units']}u", f"{b['stake']:.0f}", _pct(b["edge"]), _pct(b["model_edge"]), ",".join(b["groups"]),
                 " ".join(b["tags"])] for b in rep.live_new]
        print(format_table(["Player", "Game", "Bet", "Book", "Odds", "Units", s.currency, "Edge", "Model", "Refs", "Tags"],
                           rows, {4, 5, 6, 7, 8}))
    if rep.data_new or rep.shadow_new or rep.model_new or rep.test_new:
        print(f"  Data ledger +{rep.data_new} | shadow +{rep.shadow_new} | model test +{rep.model_new}"
              f" | test markets +{rep.test_new}")
    if rep.pushed:
        print(f"  Pushed {rep.pushed} LIVE notification(s)")
    if rep.top_legs:
        print("\n  Best edges this scan")
        rows = []
        for l in rep.top_legs:
            status = "LIVE-OK" if not l.blocks and not l.live_blocks else ("DATA" if not l.blocks else l.blocks[0])
            if not l.blocks and l.live_blocks:
                status = f"DATA ({l.live_blocks[0]})"
            rows.append([l.projection.skater.name, f"{l.game.away}@{l.game.home}", f"{l.side.capitalize()} {l.line:g}",
                         l.book, f"{l.odds:.2f}", _pct(l.p_fair), _pct(l.p_market), _pct(l.p_model), _pct(l.edge),
                         _pct(l.model_edge), len(l.refs), status])
        print(format_table(["Player", "Game", "Bet", "Book", "Odds", "Fair", "Market", "Model", "Edge", "ModelEdge",
                            "Refs", "Status"], rows, {4, 5, 6, 7, 8, 9, 10}))


def dashboard_path(cfg: Settings) -> Path:
    return cfg.output_dir / "dashboard.html"


def _refresh_dashboard(scanner: Scanner, s: BotSettings, cfg: Settings) -> None:
    from .dashboard import write_dashboard

    try:
        write_dashboard(s, dashboard_path(cfg), scanner.ledgers, scanner.history)
    except Exception:  # noqa: BLE001 - the dashboard must never stop scanning
        log.exception("Could not write dashboard")


def _after_scan(scanner: Scanner, rep: ScanReport, s: BotSettings, cfg: Settings) -> None:
    kambi_down = bool(rep.errors) and rep.kambi_events == 0 and all(e.startswith("kambi") for e in rep.errors)
    scanner.record_health(not kambi_down, "; ".join(rep.errors))
    scanner.maybe_daily_recap()
    _refresh_dashboard(scanner, s, cfg)
    _write_radar(scanner, rep, s)


def _write_radar(scanner: Scanner, rep: ScanReport, s: BotSettings) -> None:
    """Current edges for the merged site (same format as football/NBA)."""
    from .site_export import radar_rows

    try:
        from .engine import leg_key
        live_keys = {leg_key(b["game_id"], b["player_id"], b["line"], b["side"]) for b in scanner.ledgers["live"].bets}
        rows = radar_rows(rep.all_legs, s, live_keys)
        out = {"uppdaterad_ts": rep.started.timestamp(), "radar": rows,
               "matcher": rep.games, "matcher_med_props": rep.games_with_props, "fel": rep.errors[:5]}
        s.data_path.mkdir(parents=True, exist_ok=True)
        (s.data_path / "radar.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001 - the site must never stop scanning
        log.exception("Could not write radar.json")


def cmd_scan(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    """One scan. This is what GitHub Actions (or any scheduler) runs every few minutes."""
    scanner = Scanner(s, cfg, diagnose=args.diagnose, notify=not args.no_notify)
    try:
        try:
            rep = scanner.run_once()
        except HttpError as exc:
            print(f"Scan failed (network): {exc}")
            scanner.record_health(False, str(exc))
            return 1
        print_scan(rep, s, cfg)
        _after_scan(scanner, rep, s, cfg)
    finally:
        scanner.close()
    return 0


def cmd_dashboard(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    import webbrowser

    from .dashboard import write_dashboard

    path = write_dashboard(s, dashboard_path(cfg))
    print(f"Dashboard: {path}")
    if not args.no_open:
        webbrowser.open(path.resolve().as_uri())
    return 0


def cmd_watch(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    print(f"Watching NHL shots-on-goal props. Notifications: "
          f"{'ntfy topic ' + s.ntfy_topic if s.ntfy_topic and not args.no_notify else 'off'}. Ctrl+C to stop.")
    scanner = Scanner(s, cfg, diagnose=args.diagnose, notify=not args.no_notify)
    try:
        while True:
            try:
                rep = scanner.run_once()
                print_scan(rep, s, cfg)
                _after_scan(scanner, rep, s, cfg)
            except HttpError as exc:
                print(f"Scan failed (network): {exc}")
                scanner.record_health(False, str(exc))
            except Exception as exc:  # noqa: BLE001 - keep the watcher alive, but show the bug
                log.exception("Scan failed")
                scanner.record_health(False, repr(exc))
            wait = next_interval_minutes(s)
            print(f"  next scan in {wait:g} min\n")
            time.sleep(wait * 60)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        scanner.close()
    return 0


def cmd_report(s: BotSettings) -> int:
    rows = []
    for name, ledger in open_ledgers(s).items():
        st = ledger.stats()
        rows.append([name, st["bets"], st["open"], st["settled"], f"{st['won']}-{st['lost']}-{st['push']}", st["void"],
                     st["units_staked"], f"{st['profit_units']:+.2f}", _pct(st["roi"]), _pct(st["avg_clv"]),
                     _pct(st["beat_close"])])
    print(format_table(["Ledger", "Bets", "Open", "Settled", "W-L-P", "Void", "Units", "Profit u", "ROI", "Avg CLV",
                        "Beat close"], rows, set(range(1, 11))))
    print(f"\n1u = {s.unit_value():.0f} {s.currency} ({s.unit_pct:.1%} of {s.bankroll:,.0f}). "
          f"CLV = odds taken x closing fair probability - 1.")
    settled_live = rows[0][3] if rows else 0
    print(f"Live bets settled: {settled_live}/{REVIEW_AT} until the parameter review.")
    return 0


def cmd_export(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    if args.sheet:
        from .sheet_export import write_sheet_csvs

        for path in write_sheet_csvs(s, args.out or cfg.output_dir / "csv"):
            print(f"Wrote {path}")
        return 0
    out = args.out or cfg.output_dir / "ledgers"
    out.mkdir(parents=True, exist_ok=True)
    for name, ledger in open_ledgers(s).items():
        path = out / f"{Path(LEDGERS[name]).stem}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(LEDGER_COLUMNS)
            for b in ledger.bets:
                row = []
                for col in LEDGER_COLUMNS:
                    v = b.get(col)
                    if isinstance(v, list):
                        v = ", ".join(map(str, v))
                    elif isinstance(v, float):
                        v = f"{v:.4f}".replace(".", ",")
                    row.append("" if v is None else v)
                writer.writerow(row)
        print(f"Wrote {path} ({len(ledger.bets)} rows)")
    return 0


def cmd_kambi_probe(args: argparse.Namespace, s: BotSettings, cfg: Settings) -> int:
    client = JsonClient(cfg.cache_dir)
    kambi = KambiClient(client, s.kambi_market)
    diag = s.data_path / "diagnos"
    for off, book in s.kambi_offerings.items():
        try:
            events = [e for e in kambi.events(off) if e.state == "NOT_STARTED"]
        except HttpError as exc:
            print(f"{off}: error {exc}")
            continue
        print(f"{off} ({book}): {len(events)} upcoming NHL event(s)")
        for e in events[: s.max_events]:
            raw = kambi.raw_event(off, e.event_id) or {}
            quotes, labels = parse_sog_betoffers(raw, book, playable=True)
            sog = sorted({l for l in labels if is_sog_label(l)})
            print(f"  {e.start:%m-%d %H:%M}Z {e.away} @ {e.home}: {len(raw.get('betOffers', []))} offers, "
                  f"SOG criteria {sog or 'none'}, parsed {len(quotes)} quote(s)")
            if args.save:
                diag.mkdir(parents=True, exist_ok=True)
                (diag / f"kambi_{off}_{e.event_id}.json").write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0
