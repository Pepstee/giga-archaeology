"""Command-line entry point for the GIGA trust kernel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .external_proof import compile_proof
from .health import snapshot
from .integrity import sha256_file, verify_hash_baseline
from .lineage import reconcile_lineage
from .maturity import scorecard
from .memory_validation import render_report, validate_memory
from .store import DEFAULT_DATABASE, TwinStore


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="giga-twin")
    result.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    result.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialise the secure local trust-kernel store")
    validate = sub.add_parser("validate-memory", help="validate Markdown memory and index")
    validate.add_argument("--json", action="store_true", dest="as_json")
    sub.add_parser("health", help="emit a machine-derived GIGA health snapshot")
    sub.add_parser("maturity", help="emit the evidence-derived roadmap scorecard")
    integrity = sub.add_parser("verify-exports", help="verify immutable export hashes read-only")
    integrity.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="sha256 baseline; defaults to architecture/EXPORT_IMMUTABILITY_BASELINE.sha256",
    )
    artifact = sub.add_parser("register-artifact", help="register a derived file and its sources")
    artifact.add_argument("artifact", type=Path)
    artifact.add_argument("--source", action="append", type=Path, required=True)
    artifact.add_argument("--build-command", required=True)
    sub.add_parser("verify-artifacts", help="verify derived artefacts against registered sources")
    event = sub.add_parser("record-event", help="append an event from a JSON file or stdin")
    event.add_argument("--idempotency-key", required=True)
    event.add_argument("--kind", required=True)
    event.add_argument("--observed-at", required=True)
    event.add_argument("--source", required=True)
    event.add_argument("--actor", default="operator")
    event.add_argument("--trust-class", default="operator_confirmed")
    event.add_argument("--sensitivity", default="internal")
    event.add_argument("--payload-file", type=Path, help="JSON object file; defaults to stdin")
    proof = sub.add_parser(
        "compile-proof", help="compile evidence-linked local drafts with no publishing authority"
    )
    proof.add_argument("manifest", type=Path)
    proof.add_argument("--output", type=Path, required=True)
    lineage = sub.add_parser(
        "reconcile-lineage",
        help="adopt verified current artefact state while preserving superseded history",
    )
    lineage.add_argument("manifest", type=Path)
    lineage.add_argument(
        "--report-json", type=Path,
        default=Path("architecture/08_LINEAGE_RECONCILIATION.json"),
    )
    lineage.add_argument(
        "--report-markdown", type=Path,
        default=Path("architecture/08_LINEAGE_RECONCILIATION.md"),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "init":
        store = TwinStore(args.database)
        print(json.dumps({"database": str(store.database), "counts": store.counts()}, indent=2))
        return 0
    if args.command == "validate-memory":
        result = validate_memory(args.root / "memory")
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else render_report(result))
        return 0 if result["ok"] else 1
    if args.command == "health":
        print(json.dumps(snapshot(args.root, args.database), ensure_ascii=False, indent=2))
        return 0
    if args.command == "maturity":
        print(json.dumps(scorecard(args.root, args.database), ensure_ascii=False, indent=2))
        return 0
    if args.command == "verify-exports":
        baseline = args.baseline or args.root / "architecture" / "EXPORT_IMMUTABILITY_BASELINE.sha256"
        result = verify_hash_baseline(args.root, baseline)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.command == "register-artifact":
        root = args.root.resolve()
        artifact_path = args.artifact.resolve()
        source_paths = [source.resolve() for source in args.source]
        try:
            relative_artifact = artifact_path.relative_to(root)
            relative_sources = [source.relative_to(root) for source in source_paths]
        except ValueError as exc:
            raise SystemExit("artifact and sources must be inside the GIGA root") from exc
        if not artifact_path.is_file() or any(not source.is_file() for source in source_paths):
            raise SystemExit("artifact and sources must be regular files")
        store = TwinStore(args.database)
        store.register_artifact(
            path=str(relative_artifact),
            artifact_sha256=sha256_file(artifact_path),
            source_refs=[
                {"path": str(relative), "sha256": sha256_file(source)}
                for relative, source in zip(relative_sources, source_paths, strict=True)
            ],
            build_command=args.build_command,
        )
        print(json.dumps({"registered": str(relative_artifact)}))
        return 0
    if args.command == "verify-artifacts":
        result = TwinStore(args.database).audit_artifacts(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.command == "record-event":
        raw = args.payload_file.read_text(encoding="utf-8") if args.payload_file else sys.stdin.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise SystemExit("event payload must be a JSON object")
        store = TwinStore(args.database)
        event_id, created = store.record_event(
            idempotency_key=args.idempotency_key,
            kind=args.kind,
            observed_at=args.observed_at,
            source=args.source,
            actor=args.actor,
            trust_class=args.trust_class,
            sensitivity=args.sensitivity,
            payload=payload,
        )
        print(json.dumps({"event_id": event_id, "created": created}))
        return 0
    if args.command == "compile-proof":
        result = compile_proof(
            root=args.root,
            manifest=args.manifest if args.manifest.is_absolute() else args.root / args.manifest,
            output=args.output if args.output.is_absolute() else args.root / args.output,
            store=TwinStore(args.database),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "reconcile-lineage":
        root = args.root.resolve()
        report = reconcile_lineage(
            root=root,
            manifest=args.manifest if args.manifest.is_absolute() else root / args.manifest,
            store=TwinStore(args.database),
            report_json=args.report_json if args.report_json.is_absolute() else root / args.report_json,
            report_markdown=(
                args.report_markdown
                if args.report_markdown.is_absolute()
                else root / args.report_markdown
            ),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
