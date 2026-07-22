#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from twin_core.sop_compiler import compile_sop, release_sop


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile or release an evidence-bound SOP")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("spec", type=Path)
    build.add_argument("evidence_root", type=Path)
    build.add_argument("output_dir", type=Path)
    release = sub.add_parser("release")
    release.add_argument("output_dir", type=Path)
    release.add_argument("approved_by")
    release.add_argument("receipt", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        packet = compile_sop(args.spec, args.evidence_root, args.output_dir)
        print(f"compiled {len(packet['steps'])} draft SOP steps")
    else:
        receipt = release_sop(args.output_dir, args.approved_by, args.receipt)
        print(f"released {receipt['workflow_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
