from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .goal_parser import parse_goal_text, parse_goal_with_openai
from .models import Goal
from .pipeline import load_goal, make_digest, run_pipeline, save_goal
from .sources import collect_json_ld
from .telegram import run_control_loop, send_digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="land-monitor")
    sub = parser.add_subparsers(dest="command", required=True)

    goal = sub.add_parser("goal", help="Create or correct a goal in natural Russian.")
    goal.add_argument("text")
    goal.add_argument("--base")
    goal.add_argument("--out", required=True)
    goal.add_argument("--use-openai", action="store_true")

    run = sub.add_parser("run", help="Run analysis and write the report payload.")
    run.add_argument("--input", required=True)
    run.add_argument("--goal", required=True)
    run.add_argument("--features")
    run.add_argument("--cadastre")
    run.add_argument("--out", required=True)
    run.add_argument("--use-openai", action="store_true")
    run.add_argument("--live-routing", action="store_true")
    run.add_argument("--telegram", action="store_true")

    digest = sub.add_parser("digest", help="Print or send a digest from a report payload.")
    digest.add_argument("--report", required=True)
    digest.add_argument("--send", action="store_true")

    collect = sub.add_parser("collect", help="Authorized JSON-LD collection using Scrapling.")
    collect.add_argument("--source", required=True)
    collect.add_argument("--search-url", action="append", required=True)
    collect.add_argument("--stealth", action="store_true")
    collect.add_argument("--out", required=True)

    bot = sub.add_parser("bot", help="Accept natural-language goal corrections in Telegram.")
    bot.add_argument("--input", required=True)
    bot.add_argument("--goal", required=True)
    bot.add_argument("--features")
    bot.add_argument("--cadastre")
    bot.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "goal":
        base = load_goal(args.base) if args.base else Goal()
        parsed = (
            parse_goal_with_openai(args.text, base)
            if args.use_openai
            else parse_goal_text(args.text, base)
        )
        save_goal(parsed, args.out)
        print(args.out)
        return 0

    if args.command == "run":
        report = run_pipeline(
            args.input,
            args.goal,
            args.out,
            feature_points_path=args.features,
            cadastral_values_path=args.cadastre,
            use_openai=args.use_openai,
            use_live_routing=args.live_routing,
        )
        print(make_digest(report))
        if args.telegram:
            send_digest(report)
        return 0

    if args.command == "digest":
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        if args.send:
            send_digest(report)
        else:
            print(make_digest(report))
        return 0

    if args.command == "collect":
        listings = collect_json_ld(args.search_url, args.source, stealth=args.stealth)
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps([asdict(listing) for listing in listings], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"{len(listings)} listings -> {destination}")
        return 0

    if args.command == "bot":
        run_control_loop(
            input_path=args.input,
            goal_path=args.goal,
            output_path=args.out,
            feature_points_path=args.features,
            cadastral_values_path=args.cadastre,
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
