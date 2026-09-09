"""Deterministic, traceable exports for reviewed personal-research projects."""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any, Mapping, Sequence

from .source_quality import lexical_support

SYNTHESIS_PACKET_SCHEMA = "giga.research-synthesis-packet.v1"
SYNTHESIS_PROPOSAL_SCHEMA = "giga.research-synthesis-proposal.v1"
OUTLINE_PROPOSAL_SCHEMA = "giga.research-outline-proposal.v1"
CITATION_TRACE_VIEW_RECEIPT_SCHEMA = "giga.research-citation-trace-view-receipt.v1"
PLAN_MIND_MAP_RECEIPT_SCHEMA = "giga.research-plan-mind-map-receipt.v1"
_CITATION_GRAPH_SCHEMA = "giga.research-citation-graph.v1"
_TRACE_NODE_TYPES = frozenset({"subquestion", "source", "evidence", "claim"})
_PLAN_MAP_SCHEMA = "giga.research-plan-mind-map.v1"
_PLAN_MAP_NODE_TYPES = frozenset({"project", "perspective", "subquestion"})


class ResearchExportError(ValueError):
    """A research export cannot preserve its evidence or authority boundary."""


def _safe(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _safe_url(value: Any) -> str:
    return _safe(value).replace("(", "%28").replace(")", "%29").replace(" ", "%20")


def _safe_proposal_text(value: Any) -> str:
    """Render external model text as plain Markdown text, never as links or formatting."""
    return (
        _safe(value)
        .replace("`", "\\`")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("*", "\\*")
        .replace("_", "\\_")
    )


def _claim_section(
    title: str, claims: list[Mapping[str, Any]], source_labels: dict[str, str]
) -> str:
    lines = [f"## {title}", ""]
    if not claims:
        return "\n".join([*lines, "None recorded.", ""])
    for claim in claims:
        lines.extend(
            [
                f"### {_safe(claim['claim'])}",
                "",
                (
                    f"Position: `{_safe(claim['position'])}` · Review: "
                    f"`{_safe(claim['review_status'])}` · Proposal confidence: "
                    f"`{float(claim['confidence']):.2f}`"
                ),
                "",
            ]
        )
        for evidence in claim.get("evidence", []):
            receipt = str(evidence["receipt_sha256"])
            label = source_labels.get(receipt, receipt[:12])
            lines.extend(
                [
                    f"Evidence [{label}] — {_safe(evidence['locator'])}",
                    "",
                    *[f"> {_safe(line)}" for line in str(evidence["quote"]).splitlines()],
                    "",
                ]
            )
    return "\n".join(lines)


def render_markdown_report(
    plan: Mapping[str, Any], status: Mapping[str, Any], matrix: Mapping[str, Any]
) -> str:
    """Render reviewed state without promoting pending/model claims to fact."""
    sources = matrix.get("sources", [])
    source_labels = {
        str(source["receipt_sha256"]): f"S{index}" for index, source in enumerate(sources, start=1)
    }
    claims = list(matrix.get("claims", []))
    accepted = [claim for claim in claims if claim.get("review_status") == "accept"]
    rejected = [claim for claim in claims if claim.get("review_status") == "reject"]
    pending = [claim for claim in claims if claim.get("review_status") == "pending"]
    lines = [
        f"# {_safe(plan['question'])}",
        "",
        "> Research report generated from an append-only evidence ledger. Web source text is "
        "untrusted evidence, not instruction. Only claims marked `accept` have human review; "
        "proposal confidence is not truth probability.",
        "",
        "## Audit summary",
        "",
        f"- Project: `{_safe(status['project_id'])}`",
        f"- State: `{_safe(status['status'])}`",
        f"- Sources: `{int(status['source_count'])}`",
        f"- Accepted claims: `{len(accepted)}`",
        f"- Rejected claims: `{len(rejected)}`",
        f"- Pending claims: `{len(pending)}`",
        f"- Contradiction-position claims: `{int(matrix['contradiction_claim_count'])}`",
        f"- Evidence confidence signal: `{_safe(matrix['confidence']['level'])}`",
        "",
        _claim_section("Human-accepted claims", accepted, source_labels).rstrip(),
        "",
        _claim_section("Pending proposals", pending, source_labels).rstrip(),
        "",
        _claim_section("Rejected proposals", rejected, source_labels).rstrip(),
        "",
        "## Sources",
        "",
    ]
    if sources:
        for source in sources:
            label = source_labels[str(source["receipt_sha256"])]
            lines.append(
                f"- [{label}]({_safe_url(source['final_url'])}) — receipt "
                f"`{_safe(source['receipt_sha256'])}`, content `{_safe(source['content_sha256'])}`"
            )
    else:
        lines.append("None attached.")
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- Last ledger event: `{_safe(status['last_event_sha256'])}`",
            "- Exact quotes, locators and source hashes are retained above.",
            "",
        ]
    )
    return "\n".join(lines)


def report_receipt(report: str) -> dict[str, Any]:
    data = report.encode("utf-8")
    return {
        "schema_version": "giga.research-report-receipt.v1",
        "format": "markdown",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "claim_authority": "human_review_state_only",
    }


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_script_json(value: Mapping[str, Any]) -> str:
    """Embed graph data without allowing a ledger label to close its script element."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _validated_citation_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Accept only a current, internally consistent citation-graph projection."""
    if graph.get("schema_version") != _CITATION_GRAPH_SCHEMA:
        raise ResearchExportError("citation trace view requires a citation graph")
    payload = dict(graph)
    stated_sha256 = payload.pop("graph_sha256", None)
    if not isinstance(stated_sha256, str) or stated_sha256 != _canonical_sha256(payload):
        raise ResearchExportError("citation graph hash mismatch")
    if not isinstance(payload.get("project_id"), str) or not payload["project_id"]:
        raise ResearchExportError("citation graph requires a project id")
    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ResearchExportError("citation graph requires node and edge lists")
    nodes: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, Mapping):
            raise ResearchExportError(f"citation graph node {index} must be an object")
        identifier = raw_node.get("id")
        node_type = raw_node.get("type")
        label = raw_node.get("label")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
            or not isinstance(node_type, str)
            or node_type not in _TRACE_NODE_TYPES
            or not isinstance(label, str)
        ):
            raise ResearchExportError(f"citation graph node {index} is invalid")
        identifiers.add(identifier)
        nodes.append(dict(raw_node))
    edges: list[dict[str, Any]] = []
    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            raise ResearchExportError(f"citation graph edge {index} must be an object")
        source = raw_edge.get("source")
        target = raw_edge.get("target")
        relation = raw_edge.get("relation")
        if (
            not isinstance(source, str)
            or source not in identifiers
            or not isinstance(target, str)
            or target not in identifiers
            or not isinstance(relation, str)
            or not relation
        ):
            raise ResearchExportError(f"citation graph edge {index} is invalid")
        edges.append(dict(raw_edge))
    counts = payload.get("counts")
    if not isinstance(counts, Mapping) or counts.get("nodes") != len(nodes) or counts.get(
        "edges"
    ) != len(edges):
        raise ResearchExportError("citation graph counts differ from its contents")
    return {**payload, "nodes": nodes, "edges": edges, "graph_sha256": stated_sha256}


def render_citation_trace_view(graph: Mapping[str, Any]) -> str:
    """Render an offline, interactive projection of reviewed claim/evidence lineage.

    The graph is data, not instruction. All ledger strings remain in JSON and are
    assigned through DOM textContent, so untrusted quotations cannot become markup.
    """
    validated = _validated_citation_graph(graph)
    graph_data = _safe_script_json(validated)
    counts = validated["counts"]
    question_count = sum(
        node["type"] == "subquestion" for node in validated["nodes"]
    )
    project_id = html.escape(str(validated["project_id"]), quote=True)
    graph_sha256 = html.escape(str(validated["graph_sha256"]), quote=True)
    claim_boundary = html.escape(str(validated.get("claim_boundary", "")), quote=True)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; '
        'img-src data:; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">\n'
        f"  <title>Claim and evidence trace · {project_id}</title>\n"
        "  <style>\n"
        "    :root {\n"
        "      color-scheme: light;\n"
        "      --bg: oklch(1 0 0);\n"
        "      --surface: oklch(0.975 0.006 240);\n"
        "      --surface-strong: oklch(0.94 0.014 240);\n"
        "      --ink: oklch(0.22 0.026 240);\n"
        "      --muted: oklch(0.48 0.03 240);\n"
        "      --primary: oklch(0.35 0.078 240);\n"
        "      --accent: oklch(0.58 0.12 190);\n"
        "      --danger: oklch(0.5 0.17 25);\n"
        "      --warning: oklch(0.62 0.13 78);\n"
        "      --line: oklch(0.83 0.018 240);\n"
        "      --focus: oklch(0.45 0.14 240);\n"
        "      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;\n"
        "    }\n"
        "    * { box-sizing: border-box; }\n"
        "    body { margin: 0; background: var(--bg); color: var(--ink); }\n"
        "    button, input { font: inherit; }\n"
        "    button:focus-visible, input:focus-visible, .trace-node:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }\n"
        "    .app { max-width: 1800px; margin: 0 auto; padding: 28px; }\n"
        "    .topbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 32px; align-items: end; border-bottom: 1px solid var(--line); padding-bottom: 24px; }\n"
        "    .kicker { color: var(--primary); font-size: .78rem; font-weight: 750; letter-spacing: .08em; margin: 0 0 8px; text-transform: uppercase; }\n"
        "    h1 { font-size: 2rem; letter-spacing: -.025em; line-height: 1.1; margin: 0; text-wrap: balance; }\n"
        "    .lede { color: var(--muted); line-height: 1.55; margin: 12px 0 0; max-width: 70ch; text-wrap: pretty; }\n"
        "    .summary { display: flex; flex-wrap: wrap; gap: 10px; justify-content: end; margin: 0; }\n"
        "    .summary div { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; min-width: 86px; padding: 10px 12px; }\n"
        "    .summary dt { color: var(--muted); font-size: .72rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }\n"
        "    .summary dd { font-size: 1.2rem; font-weight: 760; margin: 3px 0 0; }\n"
        "    .boundary { background: oklch(0.97 0.017 190); border: 1px solid oklch(0.81 0.07 190); border-radius: 10px; color: oklch(0.28 0.055 190); line-height: 1.45; margin: 20px 0; padding: 13px 15px; }\n"
        "    .workspace { display: grid; gap: 18px; grid-template-columns: 232px minmax(0, 1fr) 300px; }\n"
        "    .panel { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; min-width: 0; }\n"
        "    .controls, .detail { align-self: start; padding: 18px; position: sticky; top: 16px; }\n"
        "    .controls h2, .detail h2, .map-heading h2 { font-size: 1rem; letter-spacing: -.01em; margin: 0; }\n"
        "    .controls label { color: var(--muted); display: block; font-size: .78rem; font-weight: 700; margin: 18px 0 7px; }\n"
        "    .controls input { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; color: var(--ink); padding: 9px 10px; width: 100%; }\n"
        "    .filter-list { display: grid; gap: 7px; margin-top: 11px; }\n"
        "    .filter { align-items: center; background: transparent; border: 1px solid var(--line); border-radius: 8px; color: var(--ink); cursor: pointer; display: flex; font-size: .86rem; gap: 8px; justify-content: space-between; padding: 8px 10px; text-align: left; }\n"
        "    .filter[aria-pressed=\"true\"] { background: var(--bg); border-color: var(--primary); color: var(--primary); }\n"
        "    .filter-count { color: var(--muted); font-variant-numeric: tabular-nums; }\n"
        "    .microcopy { color: var(--muted); font-size: .78rem; line-height: 1.45; margin: 18px 0 0; }\n"
        "    .hash { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; line-height: 1.4; overflow-wrap: anywhere; padding: 9px; }\n"
        "    .copy { background: var(--primary); border: 0; border-radius: 8px; color: white; cursor: pointer; font-weight: 700; margin-top: 9px; padding: 9px 11px; width: 100%; }\n"
        "    .map-panel { overflow: hidden; }\n"
        "    .map-heading { align-items: start; border-bottom: 1px solid var(--line); display: flex; gap: 16px; justify-content: space-between; padding: 18px 20px; }\n"
        "    .map-heading p { color: var(--muted); font-size: .84rem; line-height: 1.45; margin: 5px 0 0; }\n"
        "    .live-count { color: var(--muted); font-size: .82rem; margin: 3px 0 0; text-align: right; white-space: nowrap; }\n"
        "    .canvas { max-height: 72vh; min-height: 520px; overflow: auto; padding: 18px; }\n"
        "    svg { display: block; min-width: 960px; overflow: visible; }\n"
        "    .edge { fill: none; opacity: .72; stroke: oklch(0.62 0.03 240); stroke-width: 1.5; }\n"
        "    .edge.relation-contradicts { stroke: var(--danger); stroke-width: 2.2; }\n"
        "    .edge.relation-supports { stroke: var(--accent); stroke-width: 2.2; }\n"
        "    .edge.relation-qualifies { stroke: var(--warning); stroke-width: 2.2; }\n"
        "    .edge.relation-duplicates { stroke-dasharray: 5 5; }\n"
        "    .trace-node { cursor: pointer; }\n"
        "    .trace-node rect { fill: var(--bg); stroke: var(--line); stroke-width: 1.3; }\n"
        "    .trace-node:hover rect, .trace-node.is-selected rect { stroke: var(--primary); stroke-width: 2.4; }\n"
        "    .trace-node.type-subquestion rect { fill: oklch(0.95 0.035 240); }\n"
        "    .trace-node.type-claim rect { fill: oklch(0.97 0.018 190); }\n"
        "    .trace-node.type-evidence rect { fill: oklch(0.985 0.014 78); }\n"
        "    .trace-node.type-source rect { fill: oklch(0.97 0.008 240); }\n"
        "    .trace-node.type-claim.review-reject rect { fill: oklch(0.965 0.026 25); }\n"
        "    .node-type { fill: var(--muted); font-size: 10px; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }\n"
        "    .node-label { fill: var(--ink); font-size: 13px; font-weight: 700; }\n"
        "    .node-meta { fill: var(--muted); font-size: 11px; }\n"
        "    .legend { border-top: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 13px; padding: 13px 20px; }\n"
        "    .legend span { align-items: center; color: var(--muted); display: inline-flex; font-size: .76rem; gap: 6px; }\n"
        "    .legend i { background: var(--line); border-radius: 50%; display: inline-block; height: 9px; width: 9px; }\n"
        "    .legend .claim { background: var(--accent); } .legend .evidence { background: var(--warning); } .legend .source { background: var(--muted); } .legend .question { background: var(--primary); }\n"
        "    .detail-empty { color: var(--muted); font-size: .9rem; line-height: 1.55; margin: 14px 0 0; }\n"
        "    .detail dl { margin: 16px 0 0; }\n"
        "    .detail dt { color: var(--muted); font-size: .72rem; font-weight: 750; letter-spacing: .055em; margin-top: 12px; text-transform: uppercase; }\n"
        "    .detail dd { line-height: 1.5; margin: 3px 0 0; overflow-wrap: anywhere; }\n"
        "    .connections { border-top: 1px solid var(--line); margin: 18px 0 0; padding-top: 14px; }\n"
        "    .connections h3 { font-size: .84rem; margin: 0 0 9px; }\n"
        "    .connection { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; font-size: .78rem; line-height: 1.4; margin: 7px 0; padding: 8px; }\n"
        "    .empty-state { color: var(--muted); display: grid; min-height: 360px; place-items: center; text-align: center; }\n"
        "    .empty-state p { max-width: 35ch; }\n"
        "    @media (max-width: 1400px) { .workspace { grid-template-columns: 210px minmax(0, 1fr); } .detail { grid-column: 1 / -1; position: static; } }\n"
        "    @media (max-width: 760px) { .app { padding: 16px; } .topbar { grid-template-columns: 1fr; } .summary { justify-content: start; } .workspace { grid-template-columns: 1fr; } .controls { position: static; } .canvas { max-height: 60vh; padding: 10px; } h1 { font-size: 1.65rem; } }\n"
        "    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; transition: none !important; } }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main class=\"app\">\n"
        "    <header class=\"topbar\">\n"
        "      <section>\n"
        "        <p class=\"kicker\">Research review ledger</p>\n"
        "        <h1>Claim and evidence trace</h1>\n"
        "        <p class=\"lede\">Follow every reviewed claim through its cited evidence and archived source. This view navigates the ledger; it does not grant truth or approval.</p>\n"
        "      </section>\n"
        "      <dl class=\"summary\">\n"
        f"        <div><dt>Questions</dt><dd>{question_count}</dd></div>\n"
        f"        <div><dt>Claims</dt><dd>{int(counts.get('claims', 0))}</dd></div>\n"
        f"        <div><dt>Evidence</dt><dd>{int(counts.get('evidence_spans', 0))}</dd></div>\n"
        f"        <div><dt>Sources</dt><dd>{int(counts.get('sources', 0))}</dd></div>\n"
        "      </dl>\n"
        "    </header>\n"
        f"    <p class=\"boundary\">{claim_boundary}</p>\n"
        "    <section class=\"workspace\" aria-label=\"Citation graph trace\">\n"
        "      <aside class=\"controls panel\">\n"
        "        <h2>Explore the trace</h2>\n"
        "        <label for=\"search\">Find a node</label>\n"
        "        <input id=\"search\" type=\"search\" autocomplete=\"off\" placeholder=\"Claim, quote, source…\">\n"
        "        <label>Show node types</label>\n"
        "        <div class=\"filter-list\" id=\"filters\"></div>\n"
        "        <p class=\"microcopy\">Select a node to inspect its immutable identifier, review state and direct ledger links.</p>\n"
        "        <label>Graph receipt</label>\n"
        f"        <div class=\"hash\" id=\"graph-hash\">{graph_sha256}</div>\n"
        "        <button class=\"copy\" id=\"copy-hash\" type=\"button\">Copy graph hash</button>\n"
        "      </aside>\n"
        "      <section class=\"map-panel panel\">\n"
        "        <header class=\"map-heading\"><div><h2>Provenance map</h2><p>Questions → claims → evidence → archived sources. Claim relations retain their human-review state.</p></div><p class=\"live-count\" id=\"live-count\"></p></header>\n"
        "        <div class=\"canvas\" id=\"canvas\"><svg id=\"trace\" role=\"img\" aria-label=\"Interactive claim and evidence graph\"></svg><section class=\"empty-state\" id=\"empty\" hidden><p>No nodes match the active filters. Clear the search or re-enable a type to restore the trace.</p></section></div>\n"
        "        <footer class=\"legend\"><span><i class=\"question\"></i>Question</span><span><i class=\"claim\"></i>Claim</span><span><i class=\"evidence\"></i>Evidence</span><span><i class=\"source\"></i>Source</span></footer>\n"
        "      </section>\n"
        "      <aside class=\"detail panel\" aria-live=\"polite\"><h2>Node details</h2><p class=\"detail-empty\" id=\"detail-empty\">Choose any visible node. Its content stays evidence or proposal data until the ledger records a human decision.</p><section id=\"detail-content\" hidden></section></aside>\n"
        "    </section>\n"
        "  </main>\n"
        f"  <script id=\"citation-graph-data\" type=\"application/json\">{graph_data}</script>\n"
        "  <script>\n"
        "    (() => {\n"
        "      'use strict';\n"
        "      const graph = JSON.parse(document.getElementById('citation-graph-data').textContent);\n"
        "      const nodeTypes = ['subquestion', 'claim', 'evidence', 'source'];\n"
        "      const typeLabels = { subquestion: 'Questions', claim: 'Claims', evidence: 'Evidence', source: 'Sources' };\n"
        "      const relationClass = value => 'relation-' + String(value || 'unknown').replace(/[^a-z0-9_-]/gi, '-').toLowerCase();\n"
        "      const nodeById = new Map(graph.nodes.map(node => [node.id, node]));\n"
        "      const enabled = new Set(nodeTypes);\n"
        "      const filters = document.getElementById('filters');\n"
        "      const search = document.getElementById('search');\n"
        "      const svg = document.getElementById('trace');\n"
        "      const empty = document.getElementById('empty');\n"
        "      const liveCount = document.getElementById('live-count');\n"
        "      const detailEmpty = document.getElementById('detail-empty');\n"
        "      const detail = document.getElementById('detail-content');\n"
        "      let selectedId = null;\n"
        "      const svgElement = (name, attributes = {}) => { const element = document.createElementNS('http://www.w3.org/2000/svg', name); Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value))); return element; };\n"
        "      const short = (value, length = 42) => { const text = String(value || '').replace(/\\s+/g, ' ').trim(); return text.length > length ? text.slice(0, length - 1) + '…' : text || 'Untitled'; };\n"
        "      const titleCase = value => String(value || '').replace(/_/g, ' ').replace(/\\b\\w/g, letter => letter.toUpperCase());\n"
        "      const matches = node => { const query = search.value.trim().toLocaleLowerCase(); return enabled.has(node.type) && (!query || JSON.stringify(node).toLocaleLowerCase().includes(query)); };\n"
        "      const visible = () => graph.nodes.filter(matches);\n"
        "      const field = (list, name, value) => { const term = document.createElement('dt'); term.textContent = titleCase(name); const description = document.createElement('dd'); description.textContent = typeof value === 'object' ? JSON.stringify(value) : String(value); list.append(term, description); };\n"
        "      const renderDetails = () => {\n"
        "        detail.replaceChildren();\n"
        "        if (!selectedId || !nodeById.has(selectedId)) { detail.hidden = true; detailEmpty.hidden = false; return; }\n"
        "        const node = nodeById.get(selectedId); const heading = document.createElement('p'); heading.className = 'kicker'; heading.textContent = titleCase(node.type); const title = document.createElement('h3'); title.textContent = node.label || node.id; const list = document.createElement('dl');\n"
        "        ['id', 'review_status', 'effective_authority', 'authority', 'position', 'confidence', 'trust_class', 'authority_tier', 'locator', 'quote_sha256', 'receipt_sha256'].forEach(key => { if (node[key] !== undefined && node[key] !== null) field(list, key, node[key]); });\n"
        "        const linked = graph.edges.filter(edge => edge.source === node.id || edge.target === node.id); const links = document.createElement('section'); links.className = 'connections'; const linksTitle = document.createElement('h3'); linksTitle.textContent = `Direct ledger links (${linked.length})`; links.append(linksTitle);\n"
        "        linked.forEach(edge => { const otherId = edge.source === node.id ? edge.target : edge.source; const other = nodeById.get(otherId); const row = document.createElement('button'); row.type = 'button'; row.className = 'connection'; row.textContent = `${titleCase(edge.relation)} · ${short(other ? other.label : otherId, 76)}`; row.addEventListener('click', () => { selectedId = otherId; render(); }); links.append(row); });\n"
        "        detail.append(heading, title, list, links); detail.hidden = false; detailEmpty.hidden = true;\n"
        "      };\n"
        "      const render = () => {\n"
        "        const nodes = visible(); const ids = new Set(nodes.map(node => node.id)); const grouped = new Map(nodeTypes.map(type => [type, nodes.filter(node => node.type === type)])); const order = new Map(nodeTypes.map((type, index) => [type, index]));\n"
        "        grouped.forEach(rows => rows.sort((left, right) => left.id.localeCompare(right.id))); const maxRows = Math.max(1, ...[...grouped.values()].map(rows => rows.length)); const width = 1120; const height = Math.max(520, 104 + maxRows * 106); const positions = new Map();\n"
        "        grouped.forEach((rows, type) => rows.forEach((node, index) => positions.set(node.id, { x: 42 + order.get(type) * 270, y: 66 + index * 106 })));\n"
        "        svg.replaceChildren(); svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.setAttribute('width', width); svg.setAttribute('height', height);\n"
        "        const defs = svgElement('defs'); const marker = svgElement('marker', { id: 'arrow', markerWidth: 9, markerHeight: 7, refX: 8, refY: 3.5, orient: 'auto' }); marker.append(svgElement('path', { d: 'M0,0 L9,3.5 L0,7 z', fill: 'currentColor' })); defs.append(marker); svg.append(defs);\n"
        "        nodeTypes.forEach(type => { const header = svgElement('text', { x: 42 + order.get(type) * 270, y: 28, class: 'node-type' }); header.textContent = typeLabels[type]; svg.append(header); });\n"
        "        graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target)).forEach(edge => { const start = positions.get(edge.source); const end = positions.get(edge.target); const sameColumn = start.x === end.x; const path = svgElement('path', { class: `edge ${relationClass(edge.relation)}`, d: sameColumn ? `M ${start.x + 208} ${start.y + 30} C ${start.x + 258} ${start.y + 30}, ${end.x + 258} ${end.y + 30}, ${end.x + 208} ${end.y + 30}` : `M ${start.x + 208} ${start.y + 30} C ${start.x + 225} ${start.y + 30}, ${end.x - 18} ${end.y + 30}, ${end.x} ${end.y + 30}`, 'marker-end': 'url(#arrow)' }); path.style.color = edge.relation === 'contradicts' ? 'var(--danger)' : edge.relation === 'supports' ? 'var(--accent)' : 'oklch(0.62 0.03 240)'; svg.append(path); });\n"
        "        nodes.forEach(node => { const position = positions.get(node.id); const group = svgElement('g', { class: `trace-node type-${node.type}${node.id === selectedId ? ' is-selected' : ''}${node.type === 'claim' && node.review_status ? ` review-${node.review_status}` : ''}`, role: 'button', tabindex: 0, 'aria-label': `${titleCase(node.type)}: ${short(node.label, 120)}` }); const box = svgElement('rect', { x: position.x, y: position.y, width: 208, height: 64, rx: 9 }); const type = svgElement('text', { x: position.x + 12, y: position.y + 17, class: 'node-type' }); type.textContent = node.type === 'claim' && node.review_status ? `${node.type} · ${node.review_status}` : node.type; const label = svgElement('text', { x: position.x + 12, y: position.y + 37, class: 'node-label' }); label.textContent = short(node.label); const meta = svgElement('text', { x: position.x + 12, y: position.y + 54, class: 'node-meta' }); meta.textContent = node.type === 'claim' ? (node.position || 'proposal') : node.id.split(':')[0]; group.append(box, type, label, meta); const choose = () => { selectedId = node.id; render(); }; group.addEventListener('click', choose); group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); } }); svg.append(group); });\n"
        "        liveCount.textContent = `${nodes.length} of ${graph.nodes.length} nodes visible`; empty.hidden = nodes.length !== 0; svg.hidden = nodes.length === 0; if (selectedId && !ids.has(selectedId)) selectedId = null; renderDetails();\n"
        "      };\n"
        "      nodeTypes.forEach(type => { const button = document.createElement('button'); const label = document.createElement('span'); const count = document.createElement('span'); button.type = 'button'; button.className = 'filter'; button.setAttribute('aria-pressed', 'true'); label.textContent = typeLabels[type]; count.className = 'filter-count'; count.textContent = String(graph.nodes.filter(node => node.type === type).length); button.append(label, count); button.addEventListener('click', () => { if (enabled.has(type)) { enabled.delete(type); button.setAttribute('aria-pressed', 'false'); } else { enabled.add(type); button.setAttribute('aria-pressed', 'true'); } render(); }); filters.append(button); });\n"
        "      search.addEventListener('input', render);\n"
        "      document.getElementById('copy-hash').addEventListener('click', async event => { const button = event.currentTarget; try { await navigator.clipboard.writeText(graph.graph_sha256); button.textContent = 'Graph hash copied'; } catch (_) { button.textContent = 'Copy unavailable'; } window.setTimeout(() => { button.textContent = 'Copy graph hash'; }, 1800); });\n"
        "      render();\n"
        "    })();\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )


def citation_trace_view_receipt(graph: Mapping[str, Any], document: str) -> dict[str, Any]:
    """Return a machine-readable receipt for a deterministic trace-view export."""
    validated = _validated_citation_graph(graph)
    data = document.encode("utf-8")
    return {
        "schema_version": CITATION_TRACE_VIEW_RECEIPT_SCHEMA,
        "format": "self_contained_html",
        "project_id": validated["project_id"],
        "graph_sha256": validated["graph_sha256"],
        "trace_view_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "nodes": len(validated["nodes"]),
        "edges": len(validated["edges"]),
        "interaction": ["search", "type_filter", "node_inspection", "graph_hash_copy"],
        "network_policy": "none; no external scripts, styles, images, or fetches",
        "claim_authority": "human_review_state_only",
    }


def _validated_plan_mind_map(plan_map: Mapping[str, Any]) -> dict[str, Any]:
    """Accept only a current, internally consistent project-plan map."""
    if plan_map.get("schema_version") != _PLAN_MAP_SCHEMA:
        raise ResearchExportError("mind-map view requires a project-plan map")
    payload = dict(plan_map)
    stated_sha256 = payload.pop("plan_map_sha256", None)
    if not isinstance(stated_sha256, str) or stated_sha256 != _canonical_sha256(payload):
        raise ResearchExportError("project-plan map hash mismatch")
    if not isinstance(payload.get("project_id"), str) or not payload["project_id"]:
        raise ResearchExportError("project-plan map requires a project id")
    if not isinstance(payload.get("plan_sha256"), str) or len(payload["plan_sha256"]) != 64:
        raise ResearchExportError("project-plan map requires a plan hash")
    if not isinstance(payload.get("plan_approved"), bool) or not isinstance(
        payload.get("plan_status"), str
    ):
        raise ResearchExportError("project-plan map requires plan review state")
    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ResearchExportError("project-plan map requires node and edge lists")
    nodes: list[dict[str, Any]] = []
    node_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, Mapping):
            raise ResearchExportError(f"project-plan map node {index} must be an object")
        identifier = raw_node.get("id")
        node_type = raw_node.get("type")
        label = raw_node.get("label")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in node_by_id
            or not isinstance(node_type, str)
            or node_type not in _PLAN_MAP_NODE_TYPES
            or not isinstance(label, str)
        ):
            raise ResearchExportError(f"project-plan map node {index} is invalid")
        node = dict(raw_node)
        node_by_id[identifier] = node
        nodes.append(node)
    if sum(node["type"] == "project" for node in nodes) != 1:
        raise ResearchExportError("project-plan map requires exactly one project node")
    edges: list[dict[str, Any]] = []
    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            raise ResearchExportError(f"project-plan map edge {index} must be an object")
        source = raw_edge.get("source")
        target = raw_edge.get("target")
        relation = raw_edge.get("relation")
        if (
            not isinstance(source, str)
            or source not in node_by_id
            or not isinstance(target, str)
            or target not in node_by_id
            or not isinstance(relation, str)
            or not relation
        ):
            raise ResearchExportError(f"project-plan map edge {index} is invalid")
        edges.append(dict(raw_edge))
    counts = payload.get("counts")
    if (
        not isinstance(counts, Mapping)
        or counts.get("nodes") != len(nodes)
        or counts.get("edges") != len(edges)
        or counts.get("perspectives")
        != sum(node["type"] == "perspective" for node in nodes)
        or counts.get("subquestions")
        != sum(node["type"] == "subquestion" for node in nodes)
    ):
        raise ResearchExportError("project-plan map counts differ from its contents")
    if not isinstance(payload.get("plan_boundary"), str):
        raise ResearchExportError("project-plan map requires an authority boundary")
    return {**payload, "nodes": nodes, "edges": edges, "plan_map_sha256": stated_sha256}


def render_plan_mind_map(plan_map: Mapping[str, Any]) -> str:
    """Render an offline interactive map of one exact reviewed research plan."""
    validated = _validated_plan_mind_map(plan_map)
    data = _safe_script_json(validated)
    counts = validated["counts"]
    project_id = html.escape(str(validated["project_id"]), quote=True)
    map_sha256 = html.escape(str(validated["plan_map_sha256"]), quote=True)
    boundary = html.escape(str(validated["plan_boundary"]), quote=True)
    approval = "Approved plan" if validated["plan_approved"] else "Awaiting approval"
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; '
        'img-src data:; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">\n'
        f"  <title>Research plan map · {project_id}</title>\n"
        "  <style>\n"
        "    :root { color-scheme: light; --bg: oklch(1 0 0); --surface: oklch(.975 .006 240); --surface-strong: oklch(.94 .014 240); --ink: oklch(.22 .026 240); --muted: oklch(.48 .03 240); --primary: oklch(.35 .078 240); --accent: oklch(.58 .12 190); --line: oklch(.83 .018 240); --focus: oklch(.45 .14 240); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }\n"
        "    * { box-sizing: border-box; } body { margin: 0; background: var(--bg); color: var(--ink); } button, input { font: inherit; } button:focus-visible, input:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; } .app { max-width: 1480px; margin: 0 auto; padding: 28px; } .topbar { align-items: end; border-bottom: 1px solid var(--line); display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr) auto; padding-bottom: 24px; } .kicker { color: var(--primary); font-size: .78rem; font-weight: 760; letter-spacing: .08em; margin: 0 0 8px; text-transform: uppercase; } h1 { font-size: 2rem; letter-spacing: -.025em; line-height: 1.1; margin: 0; text-wrap: balance; } .lede { color: var(--muted); line-height: 1.55; margin: 12px 0 0; max-width: 68ch; } .summary { display: flex; flex-wrap: wrap; gap: 9px; margin: 0; } .summary div { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; min-width: 91px; padding: 9px 11px; } .summary dt { color: var(--muted); font-size: .7rem; font-weight: 760; letter-spacing: .055em; text-transform: uppercase; } .summary dd { font-size: 1.15rem; font-weight: 780; margin: 2px 0 0; } .boundary { background: oklch(.97 .017 190); border: 1px solid oklch(.81 .07 190); border-radius: 10px; color: oklch(.28 .055 190); line-height: 1.5; margin: 20px 0; padding: 13px 15px; } .workspace { display: grid; gap: 18px; grid-template-columns: minmax(0, 1fr) 310px; } .panel { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; min-width: 0; } .map-panel { padding: 20px; } .tools { align-items: end; display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; } .tools label { color: var(--muted); display: block; font-size: .78rem; font-weight: 740; margin-bottom: 6px; } .tools input { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; color: var(--ink); padding: 9px 10px; width: min(340px, 100%); } .live { color: var(--muted); font-size: .82rem; margin: 0; } .map { display: grid; gap: 18px; margin-top: 22px; } .root-row { display: flex; justify-content: center; } .lanes { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); position: relative; } .lane { border-left: 2px solid var(--line); padding-left: 14px; } .node { background: var(--bg); border: 1px solid var(--line); border-radius: 10px; color: var(--ink); cursor: pointer; display: block; padding: 12px; text-align: left; width: 100%; } .node:hover, .node.is-selected { border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary); } .node.project { background: oklch(.95 .035 240); max-width: 620px; } .node.perspective { background: oklch(.97 .018 190); } .node.question { margin-top: 10px; } .node-type { color: var(--muted); display: block; font-size: .68rem; font-weight: 780; letter-spacing: .075em; text-transform: uppercase; } .node-label { display: block; font-size: .95rem; font-weight: 760; line-height: 1.35; margin-top: 4px; } .node-meta { color: var(--muted); display: block; font-size: .76rem; line-height: 1.35; margin-top: 5px; } .empty { color: var(--muted); margin: 18px 0 0; } .detail { align-self: start; padding: 18px; position: sticky; top: 16px; } .detail h2 { font-size: 1rem; margin: 0; } .detail-empty { color: var(--muted); line-height: 1.55; margin: 14px 0 0; } .detail dl { margin: 16px 0 0; } .detail dt { color: var(--muted); font-size: .7rem; font-weight: 760; letter-spacing: .055em; margin-top: 12px; text-transform: uppercase; } .detail dd { line-height: 1.5; margin: 3px 0 0; overflow-wrap: anywhere; } .hash { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; line-height: 1.4; margin-top: 18px; overflow-wrap: anywhere; padding: 9px; } .copy { background: var(--primary); border: 0; border-radius: 8px; color: white; cursor: pointer; font-weight: 720; margin-top: 9px; padding: 9px 11px; width: 100%; } @media (max-width: 900px) { .workspace { grid-template-columns: 1fr; } .detail { position: static; } } @media (max-width: 680px) { .app { padding: 16px; } .topbar { grid-template-columns: 1fr; } h1 { font-size: 1.65rem; } } @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; transition: none !important; } }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main class=\"app\">\n"
        "    <header class=\"topbar\"><section><p class=\"kicker\">Reviewed research plan</p><h1>Research plan map</h1><p class=\"lede\">Inspect how the exact project question branches through its perspectives and bounded subquestions. This map is navigational, not generative.</p></section><dl class=\"summary\"><div><dt>Plan state</dt><dd>"
        f"{approval}</dd></div><div><dt>Perspectives</dt><dd>{int(counts['perspectives'])}</dd></div><div><dt>Questions</dt><dd>{int(counts['subquestions'])}</dd></div></dl></header>\n"
        f"    <p class=\"boundary\">{boundary}</p>\n"
        "    <section class=\"workspace\" aria-label=\"Research plan map\"><section class=\"map-panel panel\"><div class=\"tools\"><div><label for=\"search\">Find a perspective or subquestion</label><input id=\"search\" type=\"search\" autocomplete=\"off\" placeholder=\"Question, term or source type…\"></div><p class=\"live\" id=\"live\"></p></div><div class=\"map\"><div class=\"root-row\" id=\"root\"></div><div class=\"lanes\" id=\"lanes\"></div><p class=\"empty\" id=\"empty\" hidden>No perspectives or subquestions match this search.</p></div></section><aside class=\"detail panel\" aria-live=\"polite\"><h2>Plan node details</h2><p class=\"detail-empty\" id=\"detail-empty\">Select a project, perspective or subquestion to inspect the exact approved-plan metadata.</p><section id=\"detail\" hidden></section><div class=\"hash\" id=\"map-hash\">"
        f"{map_sha256}</div><button class=\"copy\" id=\"copy-hash\" type=\"button\">Copy plan-map hash</button></aside></section>\n"
        "  </main>\n"
        f"  <script id=\"plan-map-data\" type=\"application/json\">{data}</script>\n"
        "  <script>\n"
        "    (() => { 'use strict'; const map = JSON.parse(document.getElementById('plan-map-data').textContent); const nodes = new Map(map.nodes.map(node => [node.id, node])); const root = [...nodes.values()].find(node => node.type === 'project'); const perspectives = [...nodes.values()].filter(node => node.type === 'perspective').sort((a, b) => a.id.localeCompare(b.id)); const questions = [...nodes.values()].filter(node => node.type === 'subquestion').sort((a, b) => a.id.localeCompare(b.id)); const questionsByPerspective = new Map(perspectives.map(perspective => [perspective.id, new Set()])); map.edges.filter(edge => edge.relation === 'investigates' && questionsByPerspective.has(edge.source) && nodes.get(edge.target)?.type === 'subquestion').forEach(edge => questionsByPerspective.get(edge.source).add(edge.target)); const search = document.getElementById('search'); const rootTarget = document.getElementById('root'); const lanes = document.getElementById('lanes'); const live = document.getElementById('live'); const empty = document.getElementById('empty'); const detail = document.getElementById('detail'); const detailEmpty = document.getElementById('detail-empty'); let selected = null; const title = value => String(value || '').replace(/_/g, ' ').replace(/\\b\\w/g, letter => letter.toUpperCase()); const field = (list, name, value) => { const term = document.createElement('dt'); term.textContent = title(name); const description = document.createElement('dd'); description.textContent = Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : String(value); list.append(term, description); }; const nodeButton = (node, className) => { const button = document.createElement('button'); const kind = document.createElement('span'); const label = document.createElement('span'); const meta = document.createElement('span'); button.type = 'button'; button.className = `node ${className}${selected === node.id ? ' is-selected' : ''}`; kind.className = 'node-type'; kind.textContent = node.type; label.className = 'node-label'; label.textContent = node.label; meta.className = 'node-meta'; meta.textContent = node.type === 'subquestion' ? `Priority ${node.priority} · ${node.source_types.join(', ')}` : node.type === 'perspective' ? node.rationale : node.approval_status; button.append(kind, label, meta); button.addEventListener('click', () => { selected = node.id; render(); }); return button; }; const renderDetails = () => { detail.replaceChildren(); if (!selected || !nodes.has(selected)) { detail.hidden = true; detailEmpty.hidden = false; return; } const node = nodes.get(selected); const heading = document.createElement('p'); heading.className = 'kicker'; heading.textContent = title(node.type); const name = document.createElement('h3'); name.textContent = node.label; const list = document.createElement('dl'); ['id', 'approval_status', 'project_status', 'plan_sha256', 'rationale', 'perspective_id', 'priority', 'search_terms', 'source_types'].forEach(key => { if (node[key] !== undefined && node[key] !== null) field(list, key, node[key]); }); detail.append(heading, name, list); detail.hidden = false; detailEmpty.hidden = true; }; const matches = node => { const query = search.value.trim().toLocaleLowerCase(); return !query || JSON.stringify(node).toLocaleLowerCase().includes(query); }; const render = () => { rootTarget.replaceChildren(nodeButton(root, 'project')); lanes.replaceChildren(); let visibleQuestions = 0; let visiblePerspectives = 0; perspectives.forEach(perspective => { const children = questions.filter(question => questionsByPerspective.get(perspective.id).has(question.id) && matches(question)); if (!matches(perspective) && children.length === 0) return; visiblePerspectives += 1; const lane = document.createElement('section'); lane.className = 'lane'; lane.append(nodeButton(perspective, 'perspective')); children.forEach(question => { lane.append(nodeButton(question, 'question')); visibleQuestions += 1; }); if (children.length === 0) { const note = document.createElement('p'); note.className = 'node-meta'; note.textContent = 'Perspective matches; no subquestion matches.'; lane.append(note); } lanes.append(lane); }); live.textContent = `${visibleQuestions} of ${questions.length} subquestions across ${visiblePerspectives} perspectives`; empty.hidden = visiblePerspectives !== 0; if (selected && !nodes.has(selected)) selected = null; renderDetails(); }; search.addEventListener('input', render); document.getElementById('copy-hash').addEventListener('click', async event => { const button = event.currentTarget; try { await navigator.clipboard.writeText(map.plan_map_sha256); button.textContent = 'Plan-map hash copied'; } catch (_) { button.textContent = 'Copy unavailable'; } window.setTimeout(() => { button.textContent = 'Copy plan-map hash'; }, 1800); }); render(); })();\n"
        "  </script>\n"
        "</body>\n"
        "</html>\n"
    )


def plan_mind_map_receipt(plan_map: Mapping[str, Any], document: str) -> dict[str, Any]:
    """Return a machine-readable receipt for one deterministic plan mind-map."""
    validated = _validated_plan_mind_map(plan_map)
    data = document.encode("utf-8")
    return {
        "schema_version": PLAN_MIND_MAP_RECEIPT_SCHEMA,
        "format": "self_contained_html",
        "project_id": validated["project_id"],
        "plan_sha256": validated["plan_sha256"],
        "plan_map_sha256": validated["plan_map_sha256"],
        "mind_map_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "nodes": len(validated["nodes"]),
        "edges": len(validated["edges"]),
        "interaction": ["search", "node_inspection", "plan_map_hash_copy"],
        "network_policy": "none; no external scripts, styles, images, or fetches",
        "plan_authority": "human_approval_only",
        "claim_authority": "none",
    }


def _validated_packet_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema_version") != SYNTHESIS_PACKET_SCHEMA:
        raise ResearchExportError("invalid synthesis packet schema")
    payload = dict(packet)
    stated_sha256 = payload.pop("packet_sha256", None)
    if stated_sha256 != _canonical_sha256(payload):
        raise ResearchExportError("synthesis packet hash mismatch")
    return payload


def validate_outline_proposal(
    packet: Mapping[str, Any], proposal: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind one complete reordered outline proposal to an exact evidence packet."""
    _validated_packet_payload(packet)
    if proposal.get("schema_version") != OUTLINE_PROPOSAL_SCHEMA:
        raise ResearchExportError("invalid outline proposal schema")
    if proposal.get("packet_sha256") != packet.get("packet_sha256"):
        raise ResearchExportError("outline proposal is bound to a different evidence packet")
    if proposal.get("project_id") != packet.get("project_id"):
        raise ResearchExportError("outline proposal is bound to a different project")
    if proposal.get("run_id") != packet.get("run_id"):
        raise ResearchExportError("outline proposal is bound to a different run")
    packet_outline = packet.get("outline")
    proposed_sections = proposal.get("sections")
    if not isinstance(packet_outline, list) or not packet_outline:
        raise ResearchExportError("synthesis packet has no outline sections")
    if not isinstance(proposed_sections, list) or not proposed_sections:
        raise ResearchExportError("outline proposal sections must be a non-empty array")
    known = {str(row["section_id"]): row for row in packet_outline}
    proposed_ids: list[str] = []
    sections: list[dict[str, str]] = []
    for index, section in enumerate(proposed_sections):
        if not isinstance(section, Mapping):
            raise ResearchExportError(f"outline section {index} must be an object")
        section_id = section.get("section_id")
        if not isinstance(section_id, str) or section_id not in known:
            raise ResearchExportError("outline proposal references an unknown section")
        if section_id in proposed_ids:
            raise ResearchExportError("outline proposal section ids must be unique")
        heading = section.get("heading")
        rationale = section.get("rationale")
        if not isinstance(heading, str) or not heading.strip() or len(heading.strip()) > 500:
            raise ResearchExportError("outline section heading must be 1 to 500 characters")
        if (
            not isinstance(rationale, str)
            or not rationale.strip()
            or len(rationale.strip()) > 2_000
        ):
            raise ResearchExportError("outline section rationale must be 1 to 2000 characters")
        source = known[section_id]
        proposed_ids.append(section_id)
        sections.append(
            {
                "section_id": section_id,
                "heading": heading.strip(),
                "perspective_id": str(source["perspective_id"]),
                "source_project_id": str(source["source_project_id"]),
                "rationale": rationale.strip(),
            }
        )
    if set(proposed_ids) != set(known):
        raise ResearchExportError(
            "outline proposal must include every evidence-packet section exactly once"
        )
    result = {
        "schema_version": OUTLINE_PROPOSAL_SCHEMA,
        "packet_sha256": str(packet["packet_sha256"]),
        "project_id": str(packet["project_id"]),
        "run_id": str(packet["run_id"]),
        "sections": sections,
        "claim_authority": False,
    }
    return {**result, "outline_sha256": _canonical_sha256(result)}


def apply_reviewed_outline(
    packet: Mapping[str, Any], reviewed_outline: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply one human-accepted outline only to the packet it was reviewed against."""
    payload = _validated_packet_payload(packet)
    if reviewed_outline.get("packet_sha256") != packet.get("packet_sha256"):
        raise ResearchExportError("reviewed outline is stale for this evidence packet")
    if reviewed_outline.get("decision") != "accept":
        raise ResearchExportError("only a human-accepted outline can be applied")
    proposal = {
        "schema_version": OUTLINE_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "project_id": packet["project_id"],
        "run_id": packet["run_id"],
        "sections": reviewed_outline.get("sections"),
    }
    validated = validate_outline_proposal(packet, proposal)
    if reviewed_outline.get("outline_sha256") != validated["outline_sha256"]:
        raise ResearchExportError("reviewed outline hash differs from its sections")
    reviewer_kind = reviewed_outline.get("reviewer_kind", "human")
    if reviewer_kind not in {"human", "controlled_canary"}:
        raise ResearchExportError("reviewed outline has an invalid reviewer kind")
    payload["outline"] = validated["sections"]
    payload["outline_review"] = {
        "state": (
            "human_accepted"
            if reviewer_kind == "human"
            else "controlled_canary_accepted"
        ),
        "outline_id": str(reviewed_outline["outline_id"]),
        "outline_sha256": validated["outline_sha256"],
        "review_event_sha256": str(reviewed_outline["review_event_sha256"]),
        "reviewed_by": str(reviewed_outline["reviewed_by"]),
        "reviewer_kind": reviewer_kind,
        "notes": str(reviewed_outline["notes"]),
        "base_packet_sha256": str(packet["packet_sha256"]),
    }
    return {**payload, "packet_sha256": _canonical_sha256(payload)}


def build_synthesis_packet(
    plan: Mapping[str, Any],
    run: Mapping[str, Any],
    *,
    supplements: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] = (),
) -> dict[str, Any]:
    """Bind one or more ordered research runs to one model-neutral synthesis request."""
    components = [(plan, run), *supplements]
    composite = len(components) > 1
    evidence: list[dict[str, Any]] = []
    component_runs: list[dict[str, str]] = []
    outline: list[dict[str, str]] = []
    seen_passages: set[tuple[str, str, int, int]] = set()
    for component_plan, component_run in components:
        if component_run.get("schema_version") != "giga.research-run.v1":
            raise ResearchExportError("synthesis requires GIGA research-run bundles")
        project_id = str(component_plan.get("project_id", ""))
        run_id = str(component_run.get("run_id", ""))
        if not project_id or not run_id:
            raise ResearchExportError("synthesis component requires project and run ids")
        if component_run.get("project_id") != project_id:
            raise ResearchExportError("synthesis plan and run project ids differ")
        specification = component_run.get("specification", {})
        if isinstance(specification, Mapping) and specification.get("project_id") not in {
            None,
            project_id,
        }:
            raise ResearchExportError("synthesis run specification project id differs")
        component_runs.append(
            {
                "project_id": project_id,
                "run_id": run_id,
                "plan_sha256": str(
                    specification.get("plan_sha256", "")
                    if isinstance(specification, Mapping)
                    else ""
                ),
                "run_bundle_sha256": _canonical_sha256(component_run),
            }
        )
        for row in component_plan.get("subquestions", []):
            subquestion_id = str(row["id"])
            outline.append(
                {
                    "section_id": (
                        f"{project_id}:{subquestion_id}" if composite else subquestion_id
                    ),
                    "heading": str(row["question"]),
                    "perspective_id": str(row["perspective_id"]),
                    "source_project_id": project_id,
                }
            )
        sources = {
            str(row["receipt_sha256"]): row
            for row in component_run.get("acquisitions", [])
            if row.get("status") == "acquired" and row.get("receipt_sha256")
        }
        for retrieval in component_run.get("retrievals", []):
            subquestion_id = str(retrieval.get("subquestion_id", ""))
            for passage in retrieval.get("result", {}).get("results", []):
                receipt_sha = str(passage.get("receipt_sha256", ""))
                source = sources.get(receipt_sha)
                if source is None:
                    raise ResearchExportError("retrieved passage lacks an acquired source")
                text = str(passage.get("text", "")).strip()
                if not text:
                    raise ResearchExportError("synthesis evidence text must be non-empty")
                start = int(passage.get("start", 0))
                end = int(passage.get("end", 0))
                fingerprint = (receipt_sha, str(passage.get("text_sha256", "")), start, end)
                if fingerprint in seen_passages:
                    continue
                seen_passages.add(fingerprint)
                evidence.append(
                    {
                        "evidence_id": f"E{len(evidence) + 1}",
                        "subquestion_id": (
                            f"{project_id}:{subquestion_id}" if composite else subquestion_id
                        ),
                        "source_project_id": project_id,
                        "source_run_id": run_id,
                        "passage_id": str(passage.get("passage_id", "")),
                        "receipt_sha256": receipt_sha,
                        "content_sha256": str(source.get("content_sha256", "")),
                        "fetched_at": source.get("fetched_at") or source.get("archived_at"),
                        "transport": source.get("transport"),
                        "text_sha256": str(passage.get("text_sha256", "")),
                        "source_url": str(source.get("final_url", "")),
                        "start": start,
                        "end": end,
                        "text": text,
                    }
                )
    if not evidence:
        raise ResearchExportError("synthesis requires at least one retrieved evidence passage")
    packet_run_id = str(run.get("run_id", ""))
    if composite:
        packet_run_id = f"composite-{_canonical_sha256({'components': component_runs})}"
    packet: dict[str, Any] = {
        "schema_version": SYNTHESIS_PACKET_SCHEMA,
        "run_id": packet_run_id,
        "component_runs": component_runs,
        "project_id": str(plan.get("project_id", "")),
        "question": str(plan.get("question", "")),
        "outline": outline,
        "outline_review": {
            "state": "approved_plan_projection",
            "claim_authority": False,
        },
        "evidence": evidence,
        "output_contract": {
            "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
            "sections_require_exact_outline": True,
            "paragraphs_require_evidence_ids": True,
            "paragraphs_require_lexical_support": True,
            "claim_authority": False,
            "instruction": (
                "Write a concise answer in the question's language. Use only the supplied "
                "evidence. Put each assertion in a paragraph with one or more evidence_ids; "
                "state uncertainty and missing coverage explicitly."
            ),
        },
    }
    packet["packet_sha256"] = _canonical_sha256(packet)
    return packet


def validate_synthesis_proposal(
    packet: Mapping[str, Any], proposal: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless every proposed paragraph cites lexically supporting evidence."""
    _validated_packet_payload(packet)
    if proposal.get("schema_version") != SYNTHESIS_PROPOSAL_SCHEMA:
        raise ResearchExportError("invalid synthesis proposal schema")
    if proposal.get("packet_sha256") != packet.get("packet_sha256"):
        raise ResearchExportError("synthesis proposal is bound to a different evidence packet")
    if proposal.get("run_id") != packet.get("run_id"):
        raise ResearchExportError("synthesis proposal is bound to a different run")
    known = {str(row["evidence_id"]): row for row in packet.get("evidence", [])}
    expected_outline = packet.get("outline")
    sections = proposal.get("sections")
    if not isinstance(expected_outline, list) or not expected_outline:
        raise ResearchExportError("synthesis packet requires an outline")
    if not isinstance(sections, list) or not sections:
        raise ResearchExportError("synthesis proposal requires sections")
    if len(sections) != len(expected_outline):
        raise ResearchExportError("synthesis proposal must cover every outline section")
    clean_sections: list[dict[str, Any]] = []
    support_scores: list[float] = []
    cited: set[str] = set()
    for section_index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            raise ResearchExportError(f"sections[{section_index}] must be an object")
        expected_section = expected_outline[section_index]
        section_id = str(section.get("section_id", ""))
        heading = str(section.get("heading", "")).strip()
        paragraphs = section.get("paragraphs")
        if not heading or not isinstance(paragraphs, list) or not paragraphs:
            raise ResearchExportError(f"sections[{section_index}] requires heading and paragraphs")
        if section_id != str(expected_section["section_id"]):
            raise ResearchExportError("synthesis proposal section order differs from the outline")
        if heading != str(expected_section["heading"]):
            raise ResearchExportError("synthesis proposal heading differs from the outline")
        clean_paragraphs: list[dict[str, Any]] = []
        for paragraph_index, paragraph in enumerate(paragraphs):
            if not isinstance(paragraph, Mapping):
                raise ResearchExportError("synthesis paragraph must be an object")
            text = str(paragraph.get("text", "")).strip()
            evidence_ids = paragraph.get("evidence_ids")
            if not text or not isinstance(evidence_ids, list) or not evidence_ids:
                raise ResearchExportError(
                    "every synthesis paragraph requires text and evidence_ids"
                )
            identifiers = [str(value) for value in evidence_ids]
            if len(identifiers) != len(set(identifiers)) or any(
                value not in known for value in identifiers
            ):
                raise ResearchExportError("synthesis paragraph cites unknown or duplicate evidence")
            if any(
                str(known[value]["subquestion_id"]) != section_id
                for value in identifiers
            ):
                raise ResearchExportError(
                    "synthesis paragraph cites evidence outside its outline section"
                )
            support = lexical_support(
                text, " ".join(str(known[value]["text"]) for value in identifiers)
            )
            if support <= 0:
                raise ResearchExportError(
                    f"sections[{section_index}].paragraphs[{paragraph_index}] has no lexical support"
                )
            support_scores.append(support)
            cited.update(identifiers)
            clean_paragraphs.append(
                {"text": text, "evidence_ids": identifiers, "lexical_support": support}
            )
        clean_sections.append(
            {"section_id": section_id, "heading": heading, "paragraphs": clean_paragraphs}
        )
    return {
        "schema_version": SYNTHESIS_PROPOSAL_SCHEMA,
        "packet_sha256": packet["packet_sha256"],
        "run_id": packet["run_id"],
        "sections": clean_sections,
        "validation": {
            "paragraph_count": len(support_scores),
            "citation_coverage": 1.0,
            "mean_lexical_support": sum(support_scores) / len(support_scores),
            "evidence_utilisation": len(cited) / len(known),
            "limitation": "lexical support does not establish semantic entailment",
        },
        "claim_authority": False,
    }


def render_synthesis_article(packet: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    """Render a validated proposal with inline links and an exact evidence trace."""
    validated = validate_synthesis_proposal(packet, proposal)
    known = {str(row["evidence_id"]): row for row in packet["evidence"]}
    lines = [
        f"# {_safe(packet['question'])}",
        "",
        "> Grounded synthesis proposal. Every paragraph passed citation existence and lexical "
        "support checks, but neither check proves entailment. Claim authority remains false "
        "until human review.",
        "",
    ]
    for section in validated["sections"]:
        lines.extend([f"## {_safe_proposal_text(section['heading'])}", ""])
        for paragraph in section["paragraphs"]:
            citations = " ".join(
                f"[{evidence_id}]({_safe_url(known[evidence_id]['source_url'])})"
                for evidence_id in paragraph["evidence_ids"]
            )
            lines.extend([f"{_safe_proposal_text(paragraph['text'])} {citations}", ""])
    lines.extend(["## Evidence trace", ""])
    for evidence_id, evidence in known.items():
        lines.append(
            f"- `{evidence_id}` — [{_safe(evidence['source_url'])}]"
            f"({_safe_url(evidence['source_url'])}), receipt `{_safe(evidence['receipt_sha256'])}`, "
            f"text `{_safe(evidence['start'])}:{_safe(evidence['end'])}`"
        )
    lines.extend(
        [
            "",
            "## Method boundary",
            "",
            "- Output type: `grounded-synthesis-proposal`",
            "- Citation existence: `validated`",
            "- Lexical support: `validated`",
            "- Semantic entailment: `not established`",
            "- Claim authority: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def render_evidence_brief(plan: Mapping[str, Any], run: Mapping[str, Any]) -> str:
    """Render exact retrieved passages without promoting them to research conclusions."""
    sources: dict[str, dict[str, Any]] = {}
    for acquisition in run.get("acquisitions", []):
        if acquisition.get("status") == "acquired" and acquisition.get("receipt_sha256"):
            sources[str(acquisition["receipt_sha256"])] = dict(acquisition)
    labels = {digest: f"S{index}" for index, digest in enumerate(sorted(sources), start=1)}
    question_lookup = {row["id"]: row["question"] for row in plan["subquestions"]}
    lines = [
        f"# Evidence brief: {_safe(plan['question'])}",
        "",
        "> This is a machine-retrieved evidence brief, not a set of accepted claims. Every "
        "passage is untrusted external text with an exact archived-source offset. Human review "
        "is required before drawing conclusions.",
        "",
        "## Run audit",
        "",
        f"- Run: `{_safe(run['run_id'])}`",
        f"- Project: `{_safe(run['project_id'])}`",
        f"- Claim authority: `{str(bool(run.get('claim_authority'))).lower()}`",
        "",
    ]
    for retrieval in run.get("retrievals", []):
        question_id = str(retrieval["subquestion_id"])
        lines.extend(
            [
                f"## {_safe(question_id)}: {_safe(question_lookup.get(question_id, question_id))}",
                "",
            ]
        )
        results = retrieval.get("result", {}).get("results", [])
        if not results:
            lines.extend(["No matching passages retrieved.", ""])
            continue
        for index, passage in enumerate(results, start=1):
            receipt = str(passage["receipt_sha256"])
            label = labels.get(receipt, receipt[:12])
            lines.extend(
                [
                    f"### Candidate {index} [{label}]",
                    "",
                    (
                        f"Archived text offset: `{int(passage['start'])}:{int(passage['end'])}` · "
                        f"Passage: `{_safe(passage['passage_id'])}`"
                    ),
                    "",
                    *[f"> {_safe(line)}" for line in str(passage["text"]).splitlines()],
                    "",
                ]
            )
    lines.extend(["## Sources", ""])
    if not sources:
        lines.append("None acquired.")
    else:
        for digest in sorted(sources):
            source = sources[digest]
            lines.append(
                f"- [{labels[digest]}]({_safe_url(source['final_url'])}) — receipt "
                f"`{_safe(digest)}`, content `{_safe(source['content_sha256'])}`"
            )
    lines.extend(
        [
            "",
            "## Review boundary",
            "",
            "- Retrieved passages are evidence candidates only.",
            "- No claim in this brief has been proposed, accepted or rejected.",
            "- Use the project claim-review ledger before treating an interpretation as a result.",
            "",
        ]
    )
    return "\n".join(lines)


def render_extractive_article(plan: Mapping[str, Any], run: Mapping[str, Any]) -> str:
    """Render a citation-linked article from verbatim passages without invented synthesis."""
    sources = {
        str(row["receipt_sha256"]): dict(row)
        for row in run.get("acquisitions", [])
        if row.get("status") == "acquired" and row.get("receipt_sha256")
    }
    labels = {digest: index for index, digest in enumerate(sorted(sources), start=1)}
    question_lookup = {str(row["id"]): str(row["question"]) for row in plan["subquestions"]}
    lines = [
        f"# {_safe(plan['question'])}",
        "",
        "> Extractive research article: each evidence passage below is reproduced from an "
        "immutable archived source. This article does not add model-generated conclusions; "
        "the passages remain evidence candidates pending human review.",
        "",
    ]
    passage_count = 0
    for retrieval in run.get("retrievals", []):
        question_id = str(retrieval["subquestion_id"])
        lines.extend(
            [
                f"## {_safe(question_lookup.get(question_id, question_id))}",
                "",
            ]
        )
        for passage in retrieval.get("result", {}).get("results", []):
            digest = str(passage["receipt_sha256"])
            source = sources.get(digest)
            if source is None:
                continue
            passage_count += 1
            label = labels[digest]
            lines.extend(
                [
                    f"### Evidence passage {passage_count}",
                    "",
                    *[_safe(line) for line in str(passage["text"]).splitlines()],
                    "",
                    f"[Source {label}]({_safe_url(source['final_url'])})",
                    "",
                ]
            )
    lines.extend(["## Sources", ""])
    for digest in sorted(sources):
        source = sources[digest]
        lines.append(
            f"{labels[digest]}. [{_safe(source['final_url'])}]({_safe_url(source['final_url'])})"
        )
    if not sources:
        lines.append("No source was acquired.")
    lines.extend(
        [
            "",
            "## Method boundary",
            "",
            f"- Extracted passages: `{passage_count}`",
            "- Generation mode: `deterministic-extractive`",
            "- Claim authority: `false`",
            "",
        ]
    )
    return "\n".join(lines)
