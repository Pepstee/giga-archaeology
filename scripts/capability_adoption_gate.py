#!/usr/bin/env python3
"""Compile or enforce the repository capability adoption/liveness registry."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twin_core.capability_adoption import (  # noqa: E402
    CapabilityAdoptionError,
    canonical_json,
    compile_adoption_registry,
    observe_liveness,
    require_active,
    verify_declared_active,
)


# Candidate feeds are supplied explicitly for the selected repository.


def _candidate_feeds(extras: list[str]) -> tuple[str, ...]:
    feeds = tuple(extras)
    if len(set(feeds)) != len(feeds):
        raise CapabilityAdoptionError("candidate feeds must be unique")
    return feeds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("status", "report", "require-active", "enforce-claims")
    )
    parser.add_argument("capability_id", nargs="?")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--observed-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--candidate-feed", action="append", default=[])
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument(
        "--allow-uncommitted-authority",
        action="store_true",
        help="test/development only; production checks require exact current-HEAD bytes",
    )
    args = parser.parse_args(argv)
    if args.command == "require-active" and not args.capability_id:
        parser.error("require-active needs a capability id")
    if args.command in {"require-active", "enforce-claims"} and (
        args.allow_uncommitted_authority
    ):
        parser.error(f"{args.command} never accepts uncommitted authority")
    if args.command in {"status", "report", "enforce-claims"} and args.capability_id:
        parser.error(f"{args.command} does not accept a capability id")
    if args.command != "report" and args.format != "json":
        parser.error("--format is available only for report")
    try:
        result_status = 0
        root = args.root.absolute()
        candidate_feeds = _candidate_feeds(args.candidate_feed)
        payload = compile_adoption_registry(
            root,
            args.observed_at,
            candidate_feeds=candidate_feeds,
            require_git_head=not args.allow_uncommitted_authority,
        )
        if args.command == "report":
            report = observe_liveness(root, payload)
            current = compile_adoption_registry(
                root,
                args.observed_at,
                candidate_feeds=candidate_feeds,
                require_git_head=not args.allow_uncommitted_authority,
            )
            if current["registry_sha256"] != payload["registry_sha256"]:
                raise CapabilityAdoptionError(
                    "capability authority changed during liveness observation"
                )
            serialized = (
                _markdown_report(report)
                if args.format == "markdown"
                else canonical_json(report)
            )
            if any(
                capability["claim"] == "ACTIVE" and capability["state"] != "ACTIVE"
                for capability in report["capabilities"]
            ):
                result_status = 2
        elif args.command == "require-active":
            capability = require_active(payload, args.capability_id)
            result = {
                "status": "PASS",
                "capability": capability,
                "registry_sha256": payload["registry_sha256"],
                "execution_authority_granted": False,
            }
            serialized = (
                json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            )
        elif args.command == "enforce-claims":
            capabilities = verify_declared_active(root, payload)
            current = compile_adoption_registry(
                root,
                args.observed_at,
                candidate_feeds=candidate_feeds,
                require_git_head=True,
            )
            if current["registry_sha256"] != payload["registry_sha256"]:
                raise CapabilityAdoptionError(
                    "capability authority changed during owner verification"
                )
            result = {
                "status": "PASS",
                "declared_active": [item["id"] for item in capabilities],
                "declared_active_count": len(capabilities),
                "registry_sha256": payload["registry_sha256"],
                "execution_authority_granted": False,
            }
            serialized = (
                json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            )
        else:
            serialized = canonical_json(payload)
        sys.stdout.write(serialized)
        return result_status
    except (CapabilityAdoptionError, OSError) as exc:
        print(
            json.dumps({"status": "REFUSED", "error": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


def _markdown_cell(value: object) -> str:
    if value is None:
        return "—"
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("\n", " ")


def _markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    states = summary["states"]
    lines = [
        "# GIGA capability liveness",
        "",
        f"Observed: `{_markdown_cell(report['observed_at'])}`  ",
        f"Registry: `{_markdown_cell(report['registry_sha256'])}`  ",
        f"Report: `{_markdown_cell(report['report_sha256'])}`  ",
        f"Source authority: `{_markdown_cell(report['source_authority'])}`  ",
        "Execution authority granted: `false`",
        "",
        "## State totals",
        "",
        "| State | Count |",
        "|---|---:|",
    ]
    for state in ("ACTIVE", "ADOPTED_UNPROVEN", "DEGRADED", "STALE", "BROKEN"):
        lines.append(f"| `{state}` | {states[state]} |")
    lines.extend(
        (
            "",
            "## Capabilities",
            "",
            "| Capability | Consumer | Deployment | Claim | Live state | Last successful use | Next check | Reason |",
            "|---|---|---|---|---|---|---|---|",
        )
    )
    for capability in report["capabilities"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_cell(capability["id"]),
                    _markdown_cell(capability["consumer_id"]),
                    _markdown_cell(capability["deployment_id"]),
                    f"`{_markdown_cell(capability['claim'])}`",
                    f"`{_markdown_cell(capability['state'])}`",
                    _markdown_cell(capability["last_successful_use_at"]),
                    _markdown_cell(capability["next_check_at"]),
                    _markdown_cell(capability["reason"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "## Implemented but disconnected",
            "",
            "| Candidate | Capability | Entrypoint hint present | Evidence sources |",
            "|---|---|---|---:|",
        )
    )
    for candidate in report["implemented_but_disconnected"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_cell(candidate["candidate_id"]),
                    _markdown_cell(candidate["capability_id"]),
                    _markdown_cell(candidate["has_entrypoint_hint"]),
                    _markdown_cell(candidate["evidence_source_count"]),
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "> Status and liveness evidence only. This report grants no execution authority.",
            "",
        )
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
