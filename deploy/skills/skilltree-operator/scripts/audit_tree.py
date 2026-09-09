#!/usr/bin/env python3
"""Build an evidence-backed implementation registry from the immutable SkillTree export."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path


STATUSES = {"implemented", "partial", "available", "external", "blocked", "documented"}
PRECEDENCE = {
    name: rank
    for rank, name in enumerate(
        ("documented", "available", "blocked", "partial", "external", "implemented")
    )
}
REPORT_STATUSES = (
    "implemented",
    "external",
    "partial",
    "available",
    "blocked",
    "documented",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_evidence(evidence_root: Path, relative: str) -> tuple[bool, str]:
    if not relative or relative == "." or Path(relative).is_absolute():
        raise ValueError(
            f"evidence must be an exact repository-relative path: {relative}"
        )
    if any(char in relative for char in "*?["):
        raise ValueError(f"evidence paths must be exact, not globs: {relative}")
    candidate = (evidence_root / relative).resolve()
    try:
        candidate.relative_to(evidence_root)
    except ValueError as exc:
        raise ValueError(f"evidence escapes evidence root: {relative}") from exc
    if not candidate.exists():
        return False, relative
    if candidate.is_dir() and not any(
        item.name[0] != "." for item in candidate.iterdir()
    ):
        return False, relative
    return True, relative


def external_evidence(path_text: str) -> tuple[bool, str]:
    path = Path(path_text)
    if not path.is_absolute() or any(char in path_text for char in "*?["):
        raise ValueError(
            f"external evidence must be an exact absolute path: {path_text}"
        )
    return path.exists(), path_text


def skill_names(roots: list[Path]) -> set[str]:
    names: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*/SKILL.md"):
            head = path.read_text(encoding="utf-8", errors="replace")[:2000]
            match = re.search(r"(?m)^name:\s*['\"]?([^'\"\n]+)", head)
            if match:
                names.add(match.group(1).strip().casefold())
    return names


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def build_registry(
    root: Path,
    export: Path,
    evidence_map_path: Path,
    evidence_root: Path,
    skill_roots: list[Path],
) -> tuple[dict, list[str]]:
    tree = load_json(export / "data" / "tree.json")
    playbook = load_json(export / "data" / "playbook.json")
    evidence_map = load_json(evidence_map_path)
    declarations = evidence_map["jobs"]
    hub_declaration = evidence_map.get("hub", {})
    installed = skill_names([*skill_roots, root / "deploy" / "skills"])

    locations: dict[str, dict] = {}
    for department in tree:
        for function in department.get("functions", []):
            for job in function.get("jobs", []):
                locations[job["name"]] = {
                    "department": department["name"],
                    "function": function["name"],
                    "description": job.get("desc", ""),
                    "target_level": job.get("level", "autonomous"),
                    "capabilities": job.get("skills", []),
                    "tools": job.get("tools", []),
                }

    unknown = sorted(set(declarations) - set(playbook))
    if unknown:
        raise ValueError(f"evidence map contains unknown jobs: {unknown}")

    rows = []
    for name, entry in playbook.items():
        declaration = declarations.get(name, {})
        declared = declaration.get("status", "documented")
        if declared not in STATUSES:
            raise ValueError(f"invalid status for {name}: {declared}")
        checks = [
            safe_evidence(evidence_root, item)
            for item in declaration.get("evidence", [])
        ]
        external_checks = [
            external_evidence(item) for item in declaration.get("external_evidence", [])
        ]
        found = [item for ok, item in checks if ok]
        missing = [item for ok, item in checks if not ok]
        external_found = [item for ok, item in external_checks if ok]
        external_missing = [item for ok, item in external_checks if not ok]
        if declared == "implemented":
            status = (
                "implemented"
                if checks and not missing
                else ("partial" if found else "documented")
            )
        elif declared == "external":
            complete = (
                checks and not missing and external_checks and not external_missing
            )
            status = (
                "external"
                if complete
                else ("partial" if found or external_found else "documented")
            )
        elif declared == "partial":
            status = "partial" if found else "documented"
        else:
            status = declared

        files = entry.get("files", [])
        advertised = {normalized(Path(item.get("path", "")).stem) for item in files}
        matches = sorted(advertised & {normalized(item) for item in installed})
        if status == "documented" and matches:
            status = "available"
        location = locations.get(name, {})
        row = {
            "job": name,
            **location,
            "status": status,
            "prerequisites": entry.get("req", []),
            "human_control": entry.get("human"),
            "replacement_claim": entry.get("replaces"),
            "evidence_found": found,
            "evidence_missing": missing,
            "external_evidence_found": external_found,
            "external_evidence_missing": external_missing,
            "matching_skills": matches,
            "note": declaration.get("note", ""),
            "blocker": declaration.get("blocker"),
        }
        rows.append(row)

    hub_checks = [
        safe_evidence(evidence_root, item)
        for item in hub_declaration.get("evidence", [])
    ]
    hub_found = [item for ok, item in hub_checks if ok]
    hub_missing = [item for ok, item in hub_checks if not ok]
    hub_status = (
        "implemented"
        if hub_checks and not hub_missing
        else ("partial" if hub_found else "documented")
    )
    by_name = {row["job"]: row for row in rows}
    for row in rows:
        prereq_states = []
        for prerequisite in row["prerequisites"]:
            target = by_name.get(prerequisite)
            status = (
                hub_status
                if prerequisite == "Company Knowledge Base"
                else (target["status"] if target else "missing")
            )
            prereq_states.append({"job": prerequisite, "status": status})
        row["prerequisite_states"] = prereq_states
        row["eligible_to_advance"] = all(
            item["status"] in {"implemented", "external"} for item in prereq_states
        )

    counts = Counter(row["status"] for row in rows)
    registry = {
        "schema_version": "1.0",
        "source_export": str(export.relative_to(root)),
        "hub": {
            "job": "Company Knowledge Base",
            "status": hub_status,
            "evidence_found": hub_found,
            "evidence_missing": hub_missing,
            "note": hub_declaration.get("note", ""),
        },
        "jobs_total": len(rows),
        "counts": dict(sorted(counts.items())),
        "jobs": sorted(rows, key=lambda row: (-PRECEDENCE[row["status"]], row["job"])),
    }
    lines = [
        "# GIGA SkillTree implementation audit",
        "",
        f"Jobs audited: **{len(rows)}**",
        "",
    ]
    lines.append("| Status | Count |")
    lines.append("|---|---:|")
    for status in REPORT_STATUSES:
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.extend(["", "## Evidence-backed capabilities", ""])
    for row in registry["jobs"]:
        if row["status"] == "documented":
            continue
        evidence = ", ".join(f"`{item}`" for item in row["evidence_found"]) or "none"
        lines.append(
            f"- **{row['job']}** — `{row['status']}` — {row['note'] or 'No note.'} Evidence: {evidence}"
        )
    lines.extend(["", "## Eligible undocumented nodes", ""])
    eligible = [
        row
        for row in rows
        if row["status"] == "documented" and row["eligible_to_advance"]
    ]
    for row in sorted(eligible, key=lambda item: item["job"]):
        lines.append(
            f"- {row['job']} ({row.get('department', 'unknown')} / {row.get('function', 'unknown')})"
        )
    return registry, lines


def registry_payload(registry: dict) -> bytes:
    return (json.dumps(registry, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def report_payload(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def _os_replace(source: Path, target: Path) -> None:
    os.replace(source, target)


def _fsync_write(path: Path, payload: bytes) -> None:
    with open(path, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


class AtomicPairWriteError(RuntimeError):
    """The generated pair could not be committed or fully restored."""


def _temporary_path(target: Path, suffix: str) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=suffix, dir=target.parent
    )
    os.close(descriptor)
    return Path(name)


def write_atomic_pair(targets: list[tuple[Path, bytes]]) -> None:
    """Write every payload or none: same-directory temps, originals saved, rollback on failure."""
    staged: list[tuple[Path, Path]] = []
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    try:
        for target, payload in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = _temporary_path(target, ".new")
            staged.append((target, temp))
            _fsync_write(temp, payload)
            os.chmod(temp, target.stat().st_mode & 0o777 if target.exists() else 0o644)
            if target.exists():
                backup = _temporary_path(target, ".backup")
                backups[target] = backup
                _fsync_write(backup, target.read_bytes())
                os.chmod(backup, target.stat().st_mode & 0o777)
            else:
                backups[target] = None
        for target, temp in staged:
            _os_replace(temp, target)
            replaced.append(target)
    except BaseException as exc:
        rollback_failures: list[str] = []
        for target in reversed(replaced):
            backup = backups.get(target)
            try:
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    _os_replace(backup, target)
            except OSError as rollback_exc:
                rollback_failures.append(f"{target}: {rollback_exc}")
        for _, temp in staged:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        for backup in backups.values():
            if backup is not None:
                try:
                    backup.unlink(missing_ok=True)
                except OSError:
                    pass
        detail = f"atomic pair write failed: {exc}"
        if rollback_failures:
            detail += "; rollback incomplete: " + "; ".join(rollback_failures)
        raise AtomicPairWriteError(detail) from exc
    else:
        for backup in backups.values():
            if backup is not None:
                backup.unlink(missing_ok=True)


def check_mode(
    output: Path,
    report: Path,
    compat_report: Path,
    payloads: list[tuple[Path, bytes]],
) -> list[str]:
    failures: list[str] = []
    for (path, payload), label in zip(payloads, ("registry", "report")):
        if not path.exists():
            failures.append(f"{label} missing: {path}")
        elif path.read_bytes() != payload:
            failures.append(
                f"tracked {label} differs from canonical generation: {path}"
            )
    if not compat_report.is_symlink():
        failures.append(
            f"compatibility surface must be a symlink to {report.name}: {compat_report}"
        )
    elif compat_report.resolve() != report.resolve():
        failures.append(
            f"compatibility surface symlink diverged: {compat_report} -> {compat_report.resolve()}"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--evidence-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--compat-report", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skill-root", action="append", type=Path, default=[])
    args = parser.parse_args()

    if args.check and args.compat_report is None:
        parser.error("--check requires --compat-report")
    if not args.check and args.compat_report is not None:
        parser.error("--compat-report is only valid together with --check")

    root = args.root.resolve()
    export = args.export.resolve()
    if not export.is_relative_to(root):
        raise SystemExit("export must be inside giga-user")
    if not export.is_dir():
        raise SystemExit(f"export is not a directory: {export}")
    evidence_map_path = args.evidence_map.resolve()
    if not evidence_map_path.is_relative_to(root) or not evidence_map_path.is_file():
        raise SystemExit(
            f"evidence map must be a regular file inside the source root: {args.evidence_map}"
        )
    for label, source_input in (
        ("tree", (export / "data" / "tree.json").resolve()),
        ("playbook", (export / "data" / "playbook.json").resolve()),
    ):
        if not source_input.is_relative_to(root) or not source_input.is_file():
            raise SystemExit(
                f"{label} must be a regular file inside the source root: {source_input}"
            )
    evidence_root = (args.evidence_root or args.root).resolve()
    if not evidence_root.is_dir():
        raise SystemExit(f"evidence root is not a directory: {evidence_root}")

    governed_paths = [("--output", args.output), ("--report", args.report)]
    if args.compat_report is not None:
        governed_paths.append(("--compat-report", args.compat_report))
    resolved_governed: dict[str, Path] = {}
    for flag, governed in governed_paths:
        resolved = governed.resolve()
        resolved_governed[flag] = resolved
        if evidence_root != root and resolved.is_relative_to(evidence_root):
            raise SystemExit(
                f"refusing to use a path inside the read-only evidence root: {governed}"
            )
        if not resolved.is_relative_to(root):
            raise SystemExit(
                f"{flag} must stay inside the giga-user source root: {governed}"
            )
    if resolved_governed["--output"] == resolved_governed["--report"]:
        raise SystemExit("--output and --report must resolve to distinct paths")

    try:
        registry, lines = build_registry(
            root, export, evidence_map_path, evidence_root, [*args.skill_root]
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payloads = [
        (args.output, registry_payload(registry)),
        (args.report, report_payload(lines)),
    ]

    if args.check:
        failures = check_mode(args.output, args.report, args.compat_report, payloads)
        if failures:
            for failure in failures:
                print(f"DRIFT: {failure}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "check": "ok",
                    "output": str(args.output),
                    "report": str(args.report),
                    "compat_report": str(args.compat_report),
                    "counts": registry["counts"],
                }
            )
        )
        return 0

    try:
        write_atomic_pair(payloads)
    except AtomicPairWriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(args.output),
                "report": str(args.report),
                "counts": registry["counts"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
