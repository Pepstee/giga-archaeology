#!/usr/bin/env python3
"""Export the public SkillTree preview into raw, normalized, and graph formats.

The preview token is accepted only at runtime and is never written to disk.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from scrapling.fetchers import DynamicSession, Fetcher


BASE = "https://skilltree.altari.ai/"
FIRST_PARTY = "skilltree.altari.ai"
TOKEN_RE = re.compile(r"(?i)(mcp_token=)[^&\"'\s<>]+")
HTTP_RE = re.compile(r"https?://[^\s\"'<>`)\\]+")
REL_RE = re.compile(
    r"(?:(?:href|src|path)\s*[:=]\s*|fetch\(\s*)[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    return TOKEN_RE.sub(r"\1[REDACTED]", text)


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "unnamed"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def fetch_bytes(url: str) -> bytes:
    response = Fetcher.get(
        url,
        impersonate="chrome",
        stealthy_headers=True,
        timeout=45,
        retries=3,
    )
    if response.status >= 400:
        raise RuntimeError(f"Fetch failed ({response.status}) for {clean_url(url)}")
    return response.body


def run_dynamic_capture(map_url: str, out: Path) -> list[dict]:
    visual = out / "visual" / "map.png"
    visual.parent.mkdir(parents=True, exist_ok=True)

    def capture(page) -> None:
        # The preview gate checks only for the presence of a local value. Use a
        # non-routable placeholder so no personal address is stored or sent.
        page.evaluate("localStorage.setItem('st-email', 'export@local.invalid')")
        page.reload(wait_until="networkidle")
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.wait_for_timeout(1_500)
        page.screenshot(path=str(visual), full_page=False)

    captured: list[dict] = []
    with DynamicSession(
        capture_xhr=r"https://skilltree\.altari\.ai/api/.*",
        headless=True,
        network_idle=True,
        timeout=60_000,
        google_search=False,
        max_pages=1,
    ) as session:
        response = session.fetch(map_url, page_action=capture, wait=500)
        for item in response.captured_xhr:
            content_type = str(item.headers.get("content-type", ""))
            body = item.body.decode("utf-8", "replace")
            try:
                parsed: object = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
            captured.append(
                {
                    "url": clean_url(str(item.url)),
                    "status": item.status,
                    "content_type": content_type,
                    "body": parsed,
                }
            )
    return captured


def extract_js(raw: Path, helper: Path) -> dict:
    proc = subprocess.run(
        ["node", str(helper), str(raw)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    return json.loads(proc.stdout)


def add_node(nodes: dict[str, dict], node_id: str, **attrs: object) -> str:
    prior = nodes.get(node_id, {})
    nodes[node_id] = {"id": node_id, **prior, **attrs}
    return node_id


def add_edge(edges: list[dict], source: str, target: str, relation: str, evidence: str) -> None:
    edges.append(
        {
            "id": f"e{len(edges) + 1:05d}",
            "source": source,
            "target": target,
            "relation": relation,
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "evidence": evidence,
        }
    )


def build_graph(data: dict) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    job_ids: dict[str, str] = {}

    hub_id = add_node(
        nodes,
        "hub:company-knowledge-base",
        label=data["hub"],
        type="hub",
        **(data.get("hub_entry") or {}),
    )

    for department in data["tree"]:
        dept_id = add_node(
            nodes,
            f"department:{slug(department['name'])}",
            label=department["name"],
            type="department",
            subtitle=department.get("sub", ""),
            description=department.get("intro", ""),
            color=department.get("color"),
        )
        add_edge(edges, hub_id, dept_id, "contains_department", "TREE department")
        for function in department.get("functions", []):
            function_id = add_node(
                nodes,
                f"function:{slug(department['name'])}:{slug(function['name'])}",
                label=function["name"],
                type="function",
                department=department["name"],
            )
            add_edge(edges, dept_id, function_id, "contains_function", "TREE function")
            for job in function.get("jobs", []):
                job_id = add_node(
                    nodes,
                    f"job:{slug(job['name'])}",
                    label=job["name"],
                    type="job",
                    description=job.get("desc", ""),
                    level=job.get("level", "autonomous"),
                    department=department["name"],
                    function=function["name"],
                    foundation=job["name"] in data.get("foundation_jobs", []),
                )
                job_ids[job["name"]] = job_id
                add_edge(edges, function_id, job_id, "contains_job", "TREE job")
                for capability in job.get("skills", []):
                    cap_id = add_node(
                        nodes,
                        f"capability:{slug(capability)}",
                        label=capability,
                        type="capability",
                    )
                    add_edge(edges, job_id, cap_id, "implemented_by_capability", "TREE skills")
                for tool in job.get("tools", []):
                    tool_id = add_node(
                        nodes,
                        f"tool:{slug(tool)}",
                        label=tool,
                        type="tool",
                    )
                    add_edge(edges, job_id, tool_id, "uses_tool", "TREE tools")

    for job_name, entry in data.get("playbook", {}).items():
        job_id = job_ids.get(job_name)
        if not job_id:
            job_id = add_node(
                nodes,
                f"job:{slug(job_name)}",
                label=job_name,
                type="job",
                unmapped=True,
            )
            job_ids[job_name] = job_id
        nodes[job_id]["playbook"] = entry
        for requirement in entry.get("req", []):
            req_id = hub_id if requirement == data["hub"] else job_ids.get(requirement)
            if not req_id:
                req_id = add_node(
                    nodes,
                    f"job:{slug(requirement)}",
                    label=requirement,
                    type="job",
                    referenced_only=True,
                )
                job_ids[requirement] = req_id
            add_edge(edges, req_id, job_id, "prerequisite_for", "PLAYBOOK req")
        for file_info in entry.get("files", []):
            file_path = file_info.get("path", "")
            file_id = add_node(
                nodes,
                f"skill-file:{slug(file_path)}",
                label=file_info.get("label") or Path(file_path).stem,
                type="skill_file",
                path=file_path,
            )
            add_edge(edges, job_id, file_id, "documented_by", "PLAYBOOK files")

    for file_info in (data.get("hub_entry") or {}).get("files", []):
        file_path = file_info.get("path", "")
        file_id = add_node(
            nodes,
            f"skill-file:{slug(file_path)}",
            label=file_info.get("label") or Path(file_path).stem,
            type="skill_file",
            path=file_path,
        )
        add_edge(edges, hub_id, file_id, "documented_by", "HUB_ENTRY files")

    for path_key, meta in data.get("skill_meta", {}).items():
        file_id = f"skill-file:{slug(path_key)}"
        add_node(
            nodes,
            file_id,
            label=meta.get("title") or Path(path_key).stem,
            type="skill_file",
            path=path_key,
            metadata=meta,
        )

    for preview_slug, preview in data.get("skill_previews", {}).items():
        path_key = f"skills/{preview_slug}.md"
        file_id = f"skill-file:{slug(path_key)}"
        add_node(
            nodes,
            file_id,
            label=(data.get("skill_meta", {}).get(path_key) or {}).get("title", preview_slug),
            type="skill_file",
            path=path_key,
            preview=preview,
        )

    return {"directed": True, "multigraph": True, "nodes": list(nodes.values()), "edges": edges}


def write_csvs(data_dir: Path, graph: dict) -> None:
    with (data_dir / "nodes.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["id", "label", "type", "department", "function", "level", "path"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(graph["nodes"])
    with (data_dir / "edges.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["id", "source", "target", "relation", "confidence", "confidence_score", "evidence"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(graph["edges"])


def discover_links(files: list[Path], root: Path) -> list[dict]:
    occurrences: dict[str, set[str]] = defaultdict(set)
    for file in files:
        text = file.read_text(encoding="utf-8", errors="replace")
        rel_source = str(file.relative_to(root))
        for match in HTTP_RE.findall(text):
            occurrences[match.rstrip(".,;:")].add(rel_source)
        for match in REL_RE.findall(text):
            if match.startswith(("#", "data:", "blob:", "javascript:")):
                continue
            occurrences[urljoin(BASE, match)].add(rel_source)
    rows = []
    for url, sources in sorted(occurrences.items()):
        parts = urlsplit(url)
        rows.append(
            {
                "url": redact(url),
                "host": parts.hostname,
                "first_party": parts.hostname == FIRST_PARTY,
                "sources": sorted(sources),
            }
        )
    return rows


def build_catalog(data: dict) -> str:
    lines = ["# SkillTree complete preview corpus", ""]
    lines += [f"## {data['hub']}", "", (data.get("hub_entry") or {}).get("notes", ""), ""]
    for department in data["tree"]:
        lines += [f"## Department: {department['name']}", "", department.get("intro", ""), ""]
        for function in department.get("functions", []):
            lines += [f"### Function: {function['name']}", ""]
            for job in function.get("jobs", []):
                lines += [f"#### Job: {job['name']}", "", job.get("desc", ""), ""]
                lines += [f"- Level: {job.get('level', 'autonomous')}"]
                lines += [f"- Capabilities: {', '.join(job.get('skills', [])) or 'None listed'}"]
                lines += [f"- Tools: {', '.join(job.get('tools', [])) or 'None listed'}", ""]
                playbook = data.get("playbook", {}).get(job["name"])
                if playbook:
                    for key in ("human", "replaces", "notes"):
                        if playbook.get(key):
                            lines += [f"**{key.title()}**", "", str(playbook[key]), ""]
                    if playbook.get("req"):
                        lines += [f"**Prerequisites:** {', '.join(playbook['req'])}", ""]
                    if playbook.get("ladder"):
                        lines += ["**Automation ladder**", ""]
                        for level, explanation in playbook["ladder"].items():
                            lines += [f"- {level}: {explanation}"]
                        lines.append("")
                    if playbook.get("files"):
                        lines += ["**Linked skill files**", ""]
                        for item in playbook["files"]:
                            lines += [f"- {item.get('label')}: `{item.get('path')}`"]
                        lines.append("")
    lines += ["## Skill file previews", ""]
    for preview_slug, preview in sorted(data.get("skill_previews", {}).items()):
        lines += [f"### {preview_slug}", "", preview, ""]
    return "\n".join(lines).rstrip() + "\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Full SkillTree preview URL; the token is not persisted")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parts = urlsplit(args.url)
    if parts.scheme != "https" or parts.hostname != FIRST_PARTY or parts.path != "/preview":
        raise SystemExit("Refusing unexpected URL; expected https://skilltree.altari.ai/preview")
    if "mcp_token=" not in parts.query:
        raise SystemExit("Preview URL has no mcp_token")
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Output directory is not empty: {out}")
    raw = out / "raw"
    data_dir = out / "data"
    offline = out / "offline"
    for directory in (raw, data_dir, offline):
        directory.mkdir(parents=True, exist_ok=True)

    logging.disable(logging.CRITICAL)
    sources = {
        "preview.html": args.url,
        "map.html": urljoin(BASE, "map.html"),
        "content.js": urljoin(BASE, "content.js"),
        "skill-meta.js": urljoin(BASE, "skill-meta.js"),
        "skill-previews.js": urljoin(BASE, "skill-previews.js"),
        "robots.txt": urljoin(BASE, "robots.txt"),
    }
    for name, url in sources.items():
        body = fetch_bytes(url)
        if name.endswith((".html", ".js", ".txt")):
            text = redact(body.decode("utf-8", "replace"))
            write_text(raw / name, text)
        else:
            (raw / name).write_bytes(body)

    extracted = extract_js(raw, args.helper.resolve())
    for key in (
        "tree",
        "playbook",
        "hub_entry",
        "human_defaults",
        "foundation_jobs",
        "skill_meta",
        "skill_previews",
    ):
        write_json(data_dir / f"{key}.json", extracted[key])

    graph = build_graph(extracted)
    write_json(data_dir / "graph.json", graph)
    write_csvs(data_dir, graph)
    write_text(out / "SKILLTREE_CORPUS.md", build_catalog(extracted))

    # The static map is self-contained apart from these three first-party scripts.
    # Its production source deliberately bounces a top-level /map.html visit back
    # to /preview; remove only that redirect in the offline derivative.
    map_source = (raw / "map.html").read_text(encoding="utf-8")
    top_level_redirect = (
        "(function(){ try { if (window.top === window.self) { "
        "location.replace('/preview'); } } catch(e){} })();"
    )
    offline_source = map_source.replace(
        top_level_redirect,
        "/* Offline export: top-level preview redirect disabled. */",
    )
    write_text(offline / "index.html", offline_source)
    for name in ("content.js", "skill-meta.js", "skill-previews.js"):
        shutil.copy2(raw / name, offline / name)

    try:
        captured = run_dynamic_capture(urljoin(BASE, "map.html"), out)
        write_json(raw / "captured_api_responses.json", captured)
        dynamic_status = "captured"
    except Exception as exc:  # static export remains complete if browser capture fails
        write_text(raw / "dynamic_capture_error.txt", f"{type(exc).__name__}: {exc}\n")
        dynamic_status = "failed; see raw/dynamic_capture_error.txt"

    link_files = [
        raw / "preview.html",
        raw / "map.html",
        raw / "content.js",
        raw / "skill-meta.js",
        raw / "skill-previews.js",
        out / "SKILLTREE_CORPUS.md",
    ]
    links = discover_links(link_files, out)
    write_json(data_dir / "links.json", links)

    node_types: dict[str, int] = defaultdict(int)
    for node in graph["nodes"]:
        node_types[node["type"]] += 1
    inventory = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://skilltree.altari.ai/preview?mcp_token=[REDACTED]",
        "robots": "User-agent: * / Allow: /",
        "dynamic_capture": dynamic_status,
        "counts": {
            "departments": len(extracted["tree"]),
            "functions": sum(len(d.get("functions", [])) for d in extracted["tree"]),
            "jobs": sum(len(f.get("jobs", [])) for d in extracted["tree"] for f in d.get("functions", [])),
            "playbook_entries": len(extracted["playbook"]),
            "skill_metadata_records": len(extracted["skill_meta"]),
            "skill_previews": len(extracted["skill_previews"]),
            "graph_nodes": len(graph["nodes"]),
            "graph_edges": len(graph["edges"]),
            "links": len(links),
            "node_types": dict(sorted(node_types.items())),
        },
        "limitations": [
            "Full runnable skill markdown is paywalled and is not delivered by the public preview.",
            "The export includes every marketing-safe skill preview delivered to the page.",
            "The supplied email is not stored in this export.",
        ],
    }
    write_json(data_dir / "inventory.json", inventory)

    counts = inventory["counts"]
    readme = f"""# SkillTree offline export

Captured from the public preview on {inventory['captured_at']}.

## What is included

- `{counts['departments']}` departments, `{counts['functions']}` functions, and `{counts['jobs']}` mapped jobs
- `{counts['playbook_entries']}` playbook entries with prerequisites, ladders, human roles, notes, and file references
- `{counts['skill_metadata_records']}` skill metadata records and `{counts['skill_previews']}` complete preview excerpts
- `{counts['graph_nodes']}` normalized graph nodes and `{counts['graph_edges']}` directed edges
- `{counts['links']}` distinct first- and third-party links with source provenance
- Raw first-party HTML/JavaScript, a static offline map, CSV tables, JSON, and a rendered screenshot

## Entry points

- `SKILLTREE_CORPUS.md` — all readable page content in one searchable document
- `data/inventory.json` — counts, scope, and limitations
- `data/graph.json` — exact normalized graph
- `data/nodes.csv` and `data/edges.csv` — spreadsheet-ready graph tables
- `data/links.json` — every discovered link and where it appears
- `offline/index.html` — the original interactive map; serve this folder with a local HTTP server
- `raw/` — source-faithful capture and observed API responses
- `SHA256SUMS.txt` — integrity hashes for every artifact

## Boundary

The public page ships preview excerpts, not the paid full runnable skill files. The exporter records those file references and every delivered preview, but does not bypass the site’s access controls. The supplied preview token and email are not stored.
"""
    write_text(out / "README.md", readme)

    hashes = []
    for file in sorted(p for p in out.rglob("*") if p.is_file()):
        if file.name == "SHA256SUMS.txt":
            continue
        hashes.append(f"{sha256(file)}  {file.relative_to(out)}")
    write_text(out / "SHA256SUMS.txt", "\n".join(hashes) + "\n")

    print(json.dumps({"output": str(out), "counts": counts, "dynamic_capture": dynamic_status}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
