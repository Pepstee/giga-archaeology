#!/usr/bin/env python3
"""Compile a local transcript into evidence-bound review candidates."""

from __future__ import annotations

import argparse
from pathlib import Path

from twin_core.transcript_actions import approve, compile_transcript


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("source", type=Path)
    compile_cmd.add_argument("output_dir", type=Path)
    approve_cmd = sub.add_parser("approve")
    approve_cmd.add_argument("packet", type=Path)
    approve_cmd.add_argument("output", type=Path)
    approve_cmd.add_argument("--approved-by", required=True)
    approve_cmd.add_argument("--candidate", action="append", default=[])
    args = parser.parse_args()
    if args.command == "compile":
        packet = compile_transcript(args.source, args.output_dir)
        print(f"compiled {packet['candidate_count']} candidate(s)")
    else:
        receipt = approve(args.packet, args.candidate, args.approved_by, args.output)
        print(f"approved {len(receipt['approved'])} candidate(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
