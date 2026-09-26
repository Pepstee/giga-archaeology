"""Versioned implementation catalogue for Archaeology map projections.

The catalogue is executable design, not implementation evidence.  It prevents a
map family from being silently forgotten or renamed while the shared fact store
is built.  ``implementation_state`` describes the current reusable foundation;
it never grants authority or claims that the target projection is complete.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .evidence import seal_document


MAP_CATALOG_SCHEMA = "giga.archaeologist.map-catalog.v1"
QUERY_ROUTE_SCHEMA = "giga.archaeology.mapper-query-route.v1"
TRUTH_CLASSES = (
    "PROVEN",
    "OBSERVED",
    "INFERRED",
    "CONFLICT",
    "UNKNOWN",
    "UNSUPPORTED",
)
COVERAGE_STATES = (
    "COVERED",
    "PARTIAL",
    "FAILED",
    "SKIPPED_POLICY",
    "NOT_APPLICABLE",
    "UNSUPPORTED",
)


def _map(
    identifier: str,
    name: str,
    slice_id: str,
    producer: str,
    dependencies: tuple[str, ...],
    implementation_state: str,
    question: str,
    acceptance: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "name": name,
        "slice": slice_id,
        "producer": producer,
        "dependencies": list(dependencies),
        "implementation_state": implementation_state,
        "question": question,
        "acceptance": acceptance,
        "authority_granted": False,
    }


MAPS = (
    _map(
        "inventory",
        "Complete inventory map",
        "M01",
        "navigation_inventory",
        (),
        "IMPLEMENTED_M01",
        "What exists in the authenticated scan scope?",
        "The federated projection authenticates the exact inventory database, row digest and counts without duplicating its artifact rows.",
    ),
    _map(
        "structure",
        "Repository and structural map",
        "M01",
        "structure_extractor",
        ("inventory",),
        "IMPLEMENTED_M01_PARTIAL",
        "How is the repository physically and logically organised?",
        "Every artifact has exact filesystem ancestry and evidence-bound logical containers.",
    ),
    _map(
        "symbols",
        "Symbol map",
        "M02",
        "symbol_extractor",
        ("inventory", "structure"),
        "IMPLEMENTED_M30_PYTHON_AST_SCIP_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "What definitions and references exist, and where?",
        "Definitions and references have stable IDs, exact spans and explicit syntax coverage.",
    ),
    _map(
        "dependencies",
        "Dependency map",
        "M02",
        "dependency_extractor",
        ("inventory", "structure", "symbols"),
        "IMPLEMENTED_M30_PYTHON_AST_SCIP_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "Which artifacts, modules and packages depend on which others?",
        "Direction, scope, resolution status and unresolved dynamic boundaries are explicit.",
    ),
    _map(
        "types",
        "Type, interface and inheritance map",
        "M02",
        "type_extractor",
        ("symbols", "dependencies"),
        "IMPLEMENTED_M26_PYTHON_AST_AND_SCIP_PARTIAL",
        "Which implementations satisfy which declared contracts?",
        "Declarations, implementations and compiler-derived facts retain exact provenance.",
    ),
    _map(
        "api_events",
        "API, command, route and event map",
        "M02",
        "endpoint_extractor",
        ("symbols", "dependencies"),
        "IMPLEMENTED_M30_PYTHON_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "How can the system be entered and what handler receives each entry?",
        "Official entrypoints resolve to exact handlers and dynamic registrations remain qualified.",
    ),
    _map(
        "calls",
        "Call map",
        "M03",
        "call_extractor",
        ("symbols", "dependencies", "types"),
        "IMPLEMENTED_M30_PYTHON_BASH_AND_JAVASCRIPT_TYPESCRIPT_PARTIAL",
        "Which callable may or did invoke which callable?",
        "Each call has a source span and resolution tier; static and observed calls stay distinct.",
    ),
    _map(
        "control_flow",
        "Control-flow map",
        "M03",
        "control_flow_extractor",
        ("symbols",),
        "IMPLEMENTED_M03_PYTHON_PARTIAL",
        "What branches, exceptional paths and terminal states exist inside a callable?",
        "Supported functions produce deterministic basic-block graphs and explicit unsupported results.",
    ),
    _map(
        "data_flow_taint",
        "Data-flow and taint map",
        "M04",
        "data_flow_extractor",
        ("symbols", "calls", "control_flow"),
        "IMPLEMENTED_M04_PYTHON_PARTIAL",
        "Where can values, untrusted inputs and sensitive data flow?",
        "Source-to-sink results include policy version, sanitizers and every unknown boundary.",
    ),
    _map(
        "database_lineage",
        "Database, schema and data-lineage map",
        "M05",
        "database_extractor",
        ("symbols", "calls", "structure"),
        "IMPLEMENTED_M05_PYTHON_LITERAL_PARTIAL",
        "What data objects exist and which code reads, writes or transforms them?",
        "Schema and query operations resolve to exact sources without exposing unapproved row data.",
    ),
    _map(
        "build_deployment",
        "Build, package and deployment map",
        "M05",
        "build_extractor",
        ("inventory", "structure", "dependencies", "api_events"),
        "IMPLEMENTED_M05_SAFE_DECLARATION_PARTIAL",
        "How does exact source become an artifact, selector, materialisation or deployment?",
        "Every claimed runtime artifact traces through hashes and receipts to exact source or UNKNOWN.",
    ),
    _map(
        "tests_coverage",
        "Test and coverage map",
        "M06",
        "test_coverage_extractor",
        ("symbols", "calls", "control_flow"),
        "IMPLEMENTED_M06_STATIC_AND_COVERAGE_ARTIFACT_PARTIAL",
        "What behaviour is tested or observed executing?",
        "Test ownership and coverage remain bound to the exact source tree and execution command.",
    ),
    _map(
        "quality_findings",
        "Quality and rule-finding map",
        "M06",
        "quality_finding_importer",
        ("inventory", "symbols"),
        "IMPLEMENTED_M51_RECEIPT_CLAIM_CURRENT_PATH_PROVENANCE_PARTIAL",
        "What did bounded analyzers report at which source locations?",
        "Findings retain tool version, configuration, scope, exit status and exact location.",
    ),
    _map(
        "duplicates_similarity",
        "Duplicate and similarity map",
        "M07",
        "similarity_extractor",
        ("inventory", "symbols"),
        "IMPLEMENTED_M29_EXACT_CONTENT_AND_PYTHON_STRUCTURE_PARTIAL",
        "Which artifacts or implementations may be exact or approximate duplicates?",
        "Exact, structural and semantic similarity tiers are distinct and retain unique differences.",
    ),
    _map(
        "git_lineage",
        "Git history and lineage map",
        "M08",
        "history_extractor",
        ("inventory", "symbols"),
        "IMPLEMENTED_M64_SEARCHABLE_LINEAGE_SUMMARY_AND_EXACT_HISTORY_FACTS_PARTIAL",
        "How did an artifact, symbol or capability evolve?",
        "Object-bound history is reproducible and heuristic symbol lineage is confidence-labelled.",
    ),
    _map(
        "reachability",
        "Reachability and disconnected-code map",
        "M07",
        "reachability_extractor",
        ("dependencies", "calls", "api_events", "git_lineage"),
        "IMPLEMENTED_M56_STATIC_AND_USAGE_COUNTEREVIDENCE_PARTIAL",
        "What is reachable from known entrypoints and what merely appears disconnected?",
        "Dynamic/configuration boundaries and counterevidence prevent false dead-code proof.",
    ),
    _map(
        "ownership_canonicality",
        "Ownership, canonicality and variant map",
        "M08",
        "ownership_extractor",
        (
            "structure",
            "symbols",
            "api_events",
            "build_deployment",
            "git_lineage",
        ),
        "IMPLEMENTED_M57_PATH_ROLE_OWNER_DECLARATION_AND_EXACT_VARIANTS_PARTIAL",
        "Which implementation is owner, candidate, copy, generated form, evidence or history?",
        "Canonical claims require governed evidence and every relevant variant is classified.",
    ),
    _map(
        "requirements_decisions",
        "Requirement, order and decision map",
        "M09",
        "decision_extractor",
        ("inventory", "symbols", "ownership_canonicality"),
        "IMPLEMENTED_M54_GOVERNED_MARKDOWN_AND_JSON_PATH_REFERENCE_PARTIAL",
        "Why does behaviour exist and which requirement governs it?",
        "Explicit identifiers and bindings are deterministic; wording similarity remains inferred.",
    ),
    _map(
        "evidence_claims",
        "Evidence, claim and canary map",
        "M09",
        "evidence_extractor",
        ("requirements_decisions", "build_deployment", "tests_coverage"),
        "IMPLEMENTED_M09_SELF_HASH_AND_EXACT_BINDING_PARTIAL",
        "What proves a claim and what operation produced the evidence?",
        "Rejected, stale or incomplete evidence cannot support a PASS claim edge.",
    ),
    _map(
        "runtime_topology",
        "Runtime-topology map",
        "M10",
        "runtime_evidence_importer",
        ("api_events", "database_lineage", "build_deployment", "evidence_claims"),
        "IMPLEMENTED_M10_EXTERNAL_CAPABILITY_GATE_STATUS_PARTIAL",
        "What processes and connections actually existed?",
        "Intended and observed topology are separately reproducible and drift is explicit.",
    ),
    _map(
        "security_capabilities",
        "Security, trust and capability map",
        "M04",
        "capability_extractor",
        (
            "api_events",
            "calls",
            "data_flow_taint",
            "requirements_decisions",
            "evidence_claims",
        ),
        "IMPLEMENTED_M04_PYTHON_PARTIAL",
        "Who or what can cause which effect across which trust boundary?",
        "Effects trace through gates to sinks; hypotheses never mint authority.",
    ),
    _map(
        "semantic_graphify",
        "Semantic concept map (Graphify)",
        "M11",
        "semantic_graph_importer",
        ("inventory", "symbols", "requirements_decisions"),
        "IMPLEMENTED_M11_FEDERATED_LOCAL_GRAPHIFY_PARTIAL",
        "Which concepts and cross-document relationships aid navigation?",
        "Semantic facts bind exact sources/model/confidence and cannot override deterministic facts.",
    ),
)


MAP_ENTITY_KINDS: dict[str, frozenset[str]] = {
    "inventory": frozenset({"ARTIFACT"}),
    "structure": frozenset(
        {"ARTIFACT", "REPOSITORY", "DIRECTORY", "LOGICAL_CONTAINER"}
    ),
    "symbols": frozenset(
        {
            "PYTHON_MODULE",
            "PYTHON_SYMBOL",
            "SHELL_SCRIPT",
            "SHELL_SYMBOL",
            "JAVASCRIPT_MODULE",
            "JAVASCRIPT_SYMBOL",
            "SCIP_SYMBOL",
        }
    ),
    "types": frozenset({"PYTHON_SYMBOL", "SCIP_SYMBOL"}),
    "dependencies": frozenset(
        {
            "PYTHON_MODULE",
            "SHELL_DEPENDENCY",
            "SHELL_SCRIPT",
            "JAVASCRIPT_IMPORT",
            "JAVASCRIPT_MODULE",
            "SCIP_SYMBOL",
        }
    ),
    "api_events": frozenset(
        {
            "PYTHON_MODULE",
            "PYTHON_SYMBOL",
            "SHELL_COMMAND",
            "SHELL_SCRIPT",
            "SHELL_SYMBOL",
            "JAVASCRIPT_CALL",
            "JAVASCRIPT_MODULE",
            "JAVASCRIPT_SYMBOL",
            "ENTRYPOINT",
        }
    ),
    "calls": frozenset(
        {
            "PYTHON_MODULE",
            "PYTHON_SYMBOL",
            "SHELL_COMMAND",
            "SHELL_SCRIPT",
            "SHELL_SYMBOL",
            "JAVASCRIPT_CALL",
            "JAVASCRIPT_MODULE",
            "JAVASCRIPT_SYMBOL",
        }
    ),
    "control_flow": frozenset({"PYTHON_SYMBOL", "CONTROL_NODE"}),
    "data_flow_taint": frozenset(
        {"PYTHON_MODULE", "PYTHON_SYMBOL", "DATA_SOURCE", "SECURITY_EFFECT"}
    ),
    "database_lineage": frozenset({"DATABASE_DECLARATION", "DATA_OBJECT"}),
    "build_deployment": frozenset({"BUILD_ASSET"}),
    "tests_coverage": frozenset({"TEST_CASE_CANDIDATE", "COVERAGE_FILE"}),
    "quality_findings": frozenset({"QUALITY_ARTIFACT", "QUALITY_CHECK_CLAIM"}),
    "duplicates_similarity": frozenset(
        {
            "DUPLICATE_GROUP",
            "DUPLICATE_MEMBER",
            "STRUCTURAL_DUPLICATE_GROUP",
            "STRUCTURAL_DUPLICATE_MEMBER",
        }
    ),
    "reachability": frozenset(
        {
            "PYTHON_MODULE",
            "PYTHON_SYMBOL",
            "SHELL_SCRIPT",
            "SHELL_SYMBOL",
            "JAVASCRIPT_MODULE",
            "JAVASCRIPT_SYMBOL",
            "ENTRYPOINT",
        }
    ),
    "git_lineage": frozenset(
        {
            "DELETED_PATH",
            "DELETED_PYTHON_DECLARATION",
            "GIT_COMMIT",
            "GIT_LINEAGE_SUMMARY",
            "HISTORICAL_PATH",
            "HISTORICAL_SYMBOL_OCCURRENCE",
            "OWNERSHIP_PATH",
        }
    ),
    "ownership_canonicality": frozenset(
        {
            "OWNERSHIP_PATH",
            "CODEOWNER_RULE",
            "CAPABILITY_OWNER_CONTRACT",
            "DECLARED_CAPABILITY_OWNER",
        }
    ),
    "requirements_decisions": frozenset(
        {
            "CONTRACT",
            "DECISION_DOCUMENT",
            "GOVERNED_DECLARATION",
            "GOVERNED_DOCUMENT",
            "GOVERNED_HEADING",
            "GOVERNED_MARKDOWN",
            "GOVERNED_PATH_REFERENCE",
            "GOVERNED_JSON_PATH_REFERENCE",
            "REQUIREMENT_POLICY_DOCUMENT",
            "WORK_ORDER",
        }
    ),
    "evidence_claims": frozenset({"EVIDENCE_DOCUMENT"}),
    "runtime_topology": frozenset(
        {
            "RUNTIME_CAPABILITY",
            "RUNTIME_ENTRYPOINT",
            "RUNTIME_EVIDENCE_POINTER",
            "RUNTIME_REGISTRY",
            "RUNTIME_TRIGGER",
        }
    ),
    "security_capabilities": frozenset(
        {"PYTHON_MODULE", "PYTHON_SYMBOL", "DATA_SOURCE", "SECURITY_EFFECT"}
    ),
    "semantic_graphify": frozenset({"SEMANTIC_CONCEPT"}),
}


DOSSIERS: tuple[dict[str, Any], ...] = (
    {
        "id": "architecture",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "structure",
            "dependencies",
            "api_events",
            "database_lineage",
            "build_deployment",
            "runtime_topology",
            "requirements_decisions",
            "ownership_canonicality",
            "semantic_graphify",
        ],
    },
    {
        "id": "implementation",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "inventory",
            "ownership_canonicality",
            "symbols",
            "types",
            "dependencies",
            "calls",
            "tests_coverage",
            "requirements_decisions",
            "evidence_claims",
            "git_lineage",
            "semantic_graphify",
        ],
    },
    {
        "id": "debugging",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "calls",
            "control_flow",
            "data_flow_taint",
            "runtime_topology",
            "semantic_graphify",
            "tests_coverage",
            "quality_findings",
            "git_lineage",
        ],
    },
    {
        "id": "consolidation",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "ownership_canonicality",
            "duplicates_similarity",
            "symbols",
            "api_events",
            "dependencies",
            "tests_coverage",
            "git_lineage",
            "runtime_topology",
            "semantic_graphify",
        ],
    },
    {
        "id": "archaeology",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "inventory",
            "git_lineage",
            "duplicates_similarity",
            "reachability",
            "ownership_canonicality",
            "requirements_decisions",
            "evidence_claims",
            "semantic_graphify",
        ],
    },
    {
        "id": "deletion_review",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "reachability",
            "runtime_topology",
            "api_events",
            "build_deployment",
            "tests_coverage",
            "git_lineage",
            "ownership_canonicality",
            "semantic_graphify",
        ],
    },
    {
        "id": "security_review",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "security_capabilities",
            "api_events",
            "calls",
            "data_flow_taint",
            "runtime_topology",
            "evidence_claims",
            "semantic_graphify",
        ],
    },
    {
        "id": "claim_review",
        "implementation_state": "IMPLEMENTED_M12_BOUNDED_QUERY_PLANNER",
        "maps": [
            "requirements_decisions",
            "symbols",
            "tests_coverage",
            "build_deployment",
            "runtime_topology",
            "evidence_claims",
            "semantic_graphify",
        ],
    },
)


QUERY_ROUTE_RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "symbol-navigation",
        "terms": (
            "symbol",
            "definition",
            "reference",
            "function",
            "class",
            "method",
            "interface",
            "implementation",
        ),
        "maps": ("symbols", "types"),
    },
    {
        "id": "dependency-navigation",
        "terms": ("dependency", "dependencies", "import", "module", "package"),
        "maps": ("dependencies",),
    },
    {
        "id": "call-navigation",
        "terms": ("call", "caller", "callers", "callee", "callees", "dispatch"),
        "maps": ("calls", "control_flow"),
    },
    {
        "id": "control-flow-navigation",
        "terms": (
            "control flow",
            "branch",
            "branches",
            "loop",
            "exception",
            "exceptions",
            "terminal state",
        ),
        "maps": ("control_flow",),
    },
    {
        "id": "data-and-security-navigation",
        "terms": (
            "data flow",
            "taint",
            "source",
            "sink",
            "egress",
            "untrusted input",
            "trust boundary",
            "capability",
            "permission",
        ),
        "maps": ("data_flow_taint", "security_capabilities"),
    },
    {
        "id": "entrypoint-navigation",
        "terms": (
            "api",
            "endpoint",
            "route",
            "event",
            "handler",
            "command",
            "cli",
            "fastapi",
        ),
        "maps": ("api_events",),
    },
    {
        "id": "database-navigation",
        "terms": (
            "database",
            "sql",
            "table",
            "schema",
            "orm",
            "data lineage",
            "read",
            "reads",
            "write",
            "writes",
        ),
        "maps": ("database_lineage",),
    },
    {
        "id": "build-navigation",
        "terms": (
            "build",
            "deploy",
            "deployment",
            "release",
            "artifact",
            "materialization",
        ),
        "maps": ("build_deployment",),
    },
    {
        "id": "quality-navigation",
        "terms": (
            "test",
            "tests",
            "coverage",
            "quality",
            "lint",
            "failure",
            "failures",
        ),
        "maps": ("tests_coverage", "quality_findings"),
    },
    {
        "id": "similarity-navigation",
        "terms": (
            "duplicate",
            "duplicates",
            "similar",
            "similarity",
            "redundant",
            "copy",
            "copies",
        ),
        "maps": ("duplicates_similarity",),
    },
    {
        "id": "reachability-navigation",
        "terms": (
            "reachability",
            "dead code",
            "unused",
            "unreachable",
            "disconnected",
        ),
        "maps": ("reachability",),
    },
    {
        "id": "history-navigation",
        "terms": (
            "git",
            "history",
            "historical",
            "rename",
            "commit",
            "blame",
            "lineage",
            "deleted",
            "deletion",
            "removed",
            "lost",
            "forgotten",
            "evolution",
            "changed",
            "blob",
        ),
        "maps": ("git_lineage",),
    },
    {
        "id": "ownership-navigation",
        "terms": (
            "owner",
            "ownership",
            "canonical",
            "codeowners",
            "responsibility",
            "variant",
        ),
        "maps": ("ownership_canonicality",),
    },
    {
        "id": "decision-navigation",
        "terms": (
            "requirement",
            "requirements",
            "decision",
            "policy",
            "rationale",
            "order",
        ),
        "maps": ("requirements_decisions",),
    },
    {
        "id": "evidence-navigation",
        "terms": (
            "evidence",
            "claim",
            "receipt",
            "proof",
            "canary",
            "attestation",
        ),
        "maps": ("evidence_claims",),
    },
    {
        "id": "runtime-navigation",
        "terms": (
            "runtime",
            "process",
            "trigger",
            "schedule",
            "liveness",
            "topology",
        ),
        "maps": ("runtime_topology",),
    },
    {
        "id": "semantic-navigation",
        "terms": ("semantic", "concept", "topic", "graphify", "knowledge graph"),
        "maps": ("semantic_graphify",),
    },
)

QUERY_STOP_WORDS = frozenset(
    {
        "a",
        "all",
        "an",
        "and",
        "any",
        "are",
        "every",
        "find",
        "for",
        "from",
        "in",
        "is",
        "locate",
        "of",
        "related",
        "report",
        "show",
        "the",
        "to",
        "where",
        "which",
        "with",
    }
)
QUERY_SEARCHABLE_INTENT_WORDS = frozenset(
    {
        "artifact",
        "attestation",
        "canary",
        "codeowners",
        "coverage",
        "fastapi",
        "graphify",
        "historical",
        "lost",
        "forgotten",
        "deleted",
        "deletion",
        "evolution",
        "changed",
        "blob",
        "receipt",
        "rename",
        "schema",
        "sql",
        "table",
    }
)


def _normalized_words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def _matches_term(words: tuple[str, ...], term: str) -> bool:
    wanted = _normalized_words(term)
    if not wanted or len(wanted) > len(words):
        return False
    width = len(wanted)
    return any(
        words[index : index + width] == wanted
        for index in range(len(words) - width + 1)
    )


def _dependency_closure(selected: set[str]) -> set[str]:
    maps = {str(item["id"]): item for item in MAPS}
    pending = list(selected)
    while pending:
        identifier = pending.pop()
        for dependency in maps[identifier]["dependencies"]:
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    return selected


def _automatic_search_query(
    query: str, words: tuple[str, ...], matched_rules: list[dict[str, Any]]
) -> str:
    if not matched_rules:
        return query
    intent_words = {
        word
        for rule in matched_rules
        for term in rule["matched_terms"]
        for word in _normalized_words(term)
    }
    retained = [
        word
        for word in words
        if word not in QUERY_STOP_WORDS and word not in intent_words
    ]
    if retained:
        return " ".join(retained)
    preferred = [
        word
        for word in words
        if word in intent_words and word in QUERY_SEARCHABLE_INTENT_WORDS
    ]
    return " ".join(dict.fromkeys(preferred)) if preferred else query


def route_query_maps(
    query: str, *, requested_maps: tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Select map views deterministically and disclose the complete decision."""

    if not isinstance(query, str) or not query or "\x00" in query:
        raise ValueError("mapper query must be non-empty")
    registered = tuple(str(item["id"]) for item in MAPS)
    registered_set = set(registered)
    catalog_receipt_sha256 = build_map_catalog()["receipt_sha256"]
    if requested_maps is not None:
        selected = tuple(dict.fromkeys(requested_maps))
        if not selected:
            raise ValueError("at least one mapper view is required")
        unknown = sorted(set(selected) - registered_set)
        if unknown:
            raise ValueError(f"mapper views are not implemented: {', '.join(unknown)}")
        return seal_document(
            {
                "schema": QUERY_ROUTE_SCHEMA,
                "status": "PASS",
                "authority": "non-authoritative-deterministic-query-routing",
                "authority_granted": False,
                "map_catalog_receipt_sha256": catalog_receipt_sha256,
                "mode": "EXPLICIT",
                "query": query,
                "search_query": query,
                "matched_rules": [],
                "selected_maps": list(selected),
                "primary_maps": list(selected),
                "dependency_expansion": False,
                "fallback": None,
            }
        )

    words = _normalized_words(query)
    matched_rules: list[dict[str, Any]] = []
    requested: set[str] = set()
    for rule in QUERY_ROUTE_RULES:
        matched_terms = sorted(
            term for term in rule["terms"] if _matches_term(words, term)
        )
        if not matched_terms:
            continue
        maps = tuple(str(item) for item in rule["maps"])
        requested.update(maps)
        matched_rules.append(
            {"id": rule["id"], "matched_terms": matched_terms, "maps": list(maps)}
        )

    fallback = None
    if requested:
        primary_set = set(requested)
        requested.update({"inventory", "structure"})
        selected_set = _dependency_closure(requested)
    else:
        selected_set = registered_set
        primary_set = registered_set
        fallback = "ALL_REGISTERED_MAPS_NO_INTENT_MATCH"
    selected = [identifier for identifier in registered if identifier in selected_set]
    primary = [identifier for identifier in registered if identifier in primary_set]
    search_query = _automatic_search_query(query, words, matched_rules)
    return seal_document(
        {
            "schema": QUERY_ROUTE_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-deterministic-query-routing",
            "authority_granted": False,
            "map_catalog_receipt_sha256": catalog_receipt_sha256,
            "mode": "AUTO_DETERMINISTIC",
            "query": query,
            "search_query": search_query,
            "matched_rules": matched_rules,
            "selected_maps": selected,
            "primary_maps": primary,
            "dependency_expansion": bool(matched_rules),
            "fallback": fallback,
        }
    )


def build_map_catalog() -> dict[str, Any]:
    """Return the deterministic, self-hashed mapper implementation contract."""

    return seal_document(
        {
            "schema": MAP_CATALOG_SCHEMA,
            "status": "DESIGN_CONTRACT",
            "authority": "non-authoritative-codebase-navigation-design",
            "authority_granted": False,
            "truth_classes": list(TRUTH_CLASSES),
            "coverage_states": list(COVERAGE_STATES),
            "maps": [dict(item) for item in MAPS],
            "entity_kinds": {
                identifier: sorted(MAP_ENTITY_KINDS[identifier])
                for identifier in (str(item["id"]) for item in MAPS)
            },
            "dossiers": [dict(item) for item in DOSSIERS],
            "query_routing": {
                "schema": QUERY_ROUTE_SCHEMA,
                "default_mode": "AUTO_DETERMINISTIC",
                "unknown_intent_fallback": "ALL_REGISTERED_MAPS_NO_INTENT_MATCH",
                "base_maps": ["inventory", "structure"],
                "dependency_expansion": True,
                "search_derivation": "REMOVE_MATCHED_NAVIGATION_AND_COMMON_QUERY_WORDS_BUT_RETAIN_DOMAIN_TERMS",
                "rules": [
                    {
                        "id": rule["id"],
                        "terms": list(rule["terms"]),
                        "maps": list(rule["maps"]),
                    }
                    for rule in QUERY_ROUTE_RULES
                ],
                "authority_granted": False,
            },
        }
    )


def map_by_id(identifier: str) -> Mapping[str, Any]:
    """Return one registered map without weakening the complete catalogue."""

    for item in MAPS:
        if item["id"] == identifier:
            return dict(item)
    raise KeyError(identifier)
