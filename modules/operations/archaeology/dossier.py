"""Bounded model-facing dossiers over the authenticated Archaeology mapper."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Collection, Mapping, Sequence
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .evidence import seal_document
from .map_catalog import DOSSIERS, MAP_ENTITY_KINDS, route_query_maps
from .mapper import MapperError, current_mapper_run, query_mapper


DOSSIER_SCHEMA = "giga.archaeologist.mapper-dossier.v2"
CONTEXT_SCHEMA = "giga.archaeologist.mapper-context.v1"
_LEXICAL_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|[^\s]")
_RANK_PREDICATES = (
    "CALLS",
    "DECLARES_ENTRYPOINT",
    "IMPORTS",
    "MAY_CAUSE_EFFECT",
    "MAY_READ_DATA_OBJECT",
    "MAY_WRITE_DATA_OBJECT",
    "STATICALLY_CALLS_TEST_TARGET",
    "STATICALLY_IMPORTS_TEST_TARGET",
)
_DOSSIERS = {item["id"]: tuple(item["maps"]) for item in DOSSIERS}
_HISTORY_PARTS = {
    ".git",
    "archive",
    "archives",
    "backup",
    "backups",
    "history",
    "historical",
    "evidence",
    "runtime_evidence",
    "receipts",
    "reports",
    "snapshots",
    "work_orders",
}
_TEMPORARY_PARTS = {".work", "staging", "worktrees"}
_NON_CONTEXT_ARTIFACT_REASONS = {
    "dependency-or-build-tree",
    "generated-or-runtime-output",
    "non-regular-file",
    "private-canary-evidence",
    "sensitive-path",
}


class DossierError(ValueError):
    """A requested dossier cannot be produced without misleading the caller."""


def lexical_token_count(value: str) -> int:
    """Count deterministic lexical units; this is not a model-token estimate."""

    return len(_LEXICAL_TOKEN_RE.findall(value))


def _closed_terms(terms: Sequence[str]) -> tuple[str, ...]:
    if isinstance(terms, (str, bytes)):
        raise DossierError("dossier search terms must be a sequence")
    result: list[str] = []
    for value in terms:
        if (
            not isinstance(value, str)
            or not value.strip()
            or "\x00" in value
            or len(value) > 200
        ):
            raise DossierError("dossier search terms must be non-empty bounded strings")
        normalized = value.strip()
        if normalized not in result:
            result.append(normalized)
    if not result or len(result) > 16:
        raise DossierError("dossier requires between 1 and 16 unique search terms")
    return tuple(result)


def _location_class(path: str | None) -> str:
    if not path:
        return "UNSOURCED_SEMANTIC_CONCEPT"
    parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
    if any(part.startswith(".codex-tmp-") for part in parts):
        return "TEMPORARY_WORKING_COPY"
    if any(part in _TEMPORARY_PARTS for part in parts):
        return "TEMPORARY_WORKING_COPY"
    if any(part in _HISTORY_PARTS for part in parts):
        return "HISTORY_OR_EVIDENCE_PATH"
    return "ACTIVE_TREE_PATH_CANDIDATE"


def _compact_result(item: Mapping[str, Any], *, include_facts: bool) -> dict[str, Any]:
    source = item.get("source")
    source_path = source.get("path") if isinstance(source, Mapping) else None
    compact = {
        "entity_id": item["entity_id"],
        "kind": item["kind"],
        "name": item["name"],
        "qualified_name": item["qualified_name"],
        "truth_class": item["truth_class"],
        "privacy_class": item["privacy_class"],
        "source": dict(source) if isinstance(source, Mapping) else None,
        "location_class": _location_class(source_path),
        "attributes": dict(item.get("attributes", {})),
    }
    if include_facts and "facts" in item:
        compact["facts"] = item["facts"]
    return compact


def _model_facing_candidate(item: Mapping[str, Any]) -> bool:
    """Keep complete inventory searchable without feeding known noise to models."""

    if item.get("kind") != "ARTIFACT":
        return True
    attributes = item.get("attributes")
    return not (
        isinstance(attributes, Mapping)
        and attributes.get("semantic_eligible") == 0
        and attributes.get("semantic_reason") in _NON_CONTEXT_ARTIFACT_REASONS
    )


def build_dossier(
    store: Path,
    dossier_id: str,
    terms: Sequence[str],
    *,
    limit_per_term: int = 100,
    overall_limit: int = 500,
    fact_limit: int = 20,
    include_semantic: bool = True,
    include_facts: bool = False,
) -> dict[str, Any]:
    """Build one compact, source-located cross-map dossier without reading source files."""

    if dossier_id not in _DOSSIERS:
        raise DossierError(f"unknown dossier: {dossier_id}")
    search_terms = _closed_terms(terms)
    if isinstance(limit_per_term, bool) or not 1 <= limit_per_term <= 500:
        raise DossierError("limit_per_term must be between 1 and 500")
    if isinstance(overall_limit, bool) or not 1 <= overall_limit <= 2000:
        raise DossierError("overall_limit must be between 1 and 2000")
    if isinstance(fact_limit, bool) or not 1 <= fact_limit <= 500:
        raise DossierError("fact_limit must be between 1 and 500")
    run = current_mapper_run(store)
    base_maps = [
        map_id
        for map_id in _DOSSIERS[dossier_id]
        if include_semantic or map_id != "semantic_graphify"
    ]
    term_routes = [route_query_maps(term) for term in search_terms]
    routed_maps = [
        map_id
        for route in term_routes
        if route["matched_rules"]
        for map_id in route["primary_maps"]
        if include_semantic or map_id != "semantic_graphify"
    ]
    maps = list(dict.fromkeys([*base_maps, *routed_maps]))
    maps_added_by_term_routing = [map_id for map_id in maps if map_id not in base_maps]

    merged: dict[str, dict[str, Any]] = {}
    query_receipts: list[dict[str, Any]] = []
    coverage_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    any_truncated = False
    # One authenticated database scan per term replaces the former map-by-map
    # scans. The union result is deliberately capped and therefore marks the
    # dossier partial when it cannot prove that every per-map tail was seen.
    batch_limit = min(1000, limit_per_term * len(maps))
    for term, route in zip(search_terms, term_routes, strict=True):
        try:
            result = query_mapper(
                store,
                term,
                maps=maps,
                limit=batch_limit,
                fact_limit=fact_limit,
                include_facts=include_facts,
                include_ancestors=False,
                _authenticated_run=run,
            )
        except MapperError as exc:
            raise DossierError(f"mapper query refused for {term!r}: {exc}") from exc
        query_receipts.append(
            {
                "map_ids": maps,
                "primary_map_ids": route["primary_maps"],
                "routing_receipt_sha256": route["receipt_sha256"],
                "term": term,
                "receipt_sha256": result["receipt_sha256"],
                "result_count": result["result_count"],
                "truncated": result["truncated"],
            }
        )
        any_truncated = any_truncated or result["truncated"]
        for coverage in result["coverage"]:
            key = (
                coverage["map_id"],
                coverage["fact_class"],
                coverage["scope"],
            )
            coverage_by_key[key] = coverage
        for item in result["results"]:
            identity = item["entity_id"]
            item_maps = [
                map_id for map_id in maps if item["kind"] in MAP_ENTITY_KINDS[map_id]
            ]
            if not item_maps:
                raise DossierError(
                    f"mapper returned an entity outside the requested map kinds: {item['kind']}"
                )
            if identity not in merged:
                merged[identity] = {
                    **_compact_result(item, include_facts=include_facts),
                    "matched_terms": [],
                    "primary_map_matched_terms": [],
                    "map_ids": [],
                }
            if term not in merged[identity]["matched_terms"]:
                merged[identity]["matched_terms"].append(term)
            if (
                set(item_maps) & set(route["primary_maps"])
                and term not in merged[identity]["primary_map_matched_terms"]
            ):
                merged[identity]["primary_map_matched_terms"].append(term)
            for map_id in item_maps:
                if map_id not in merged[identity]["map_ids"]:
                    merged[identity]["map_ids"].append(map_id)

    ownership_by_path: dict[str, dict[str, Any]] = {}
    for item in merged.values():
        if item["kind"] == "OWNERSHIP_PATH" and item["source"]:
            ownership_by_path[item["source"]["path"]] = {
                "role": item["attributes"].get("role"),
                "role_basis": item["attributes"].get("role_basis"),
                "canonicality_claimed": item["attributes"].get(
                    "canonicality_claimed", False
                ),
            }
    for item in merged.values():
        source = item["source"]
        item["ownership"] = (
            ownership_by_path.get(source["path"], {"role": "UNKNOWN"})
            if source
            else {"role": "UNKNOWN"}
        )
        item["matched_terms"].sort(key=str.casefold)
        item["primary_map_matched_terms"].sort(key=str.casefold)
        item["map_ids"].sort()

    navigation_policy_omitted = sorted(
        item["entity_id"]
        for item in merged.values()
        if not _model_facing_candidate(item)
    )

    ordered = sorted(
        (item for item in merged.values() if _model_facing_candidate(item)),
        key=lambda item: (
            {
                "ACTIVE_TREE_PATH_CANDIDATE": 0,
                "HISTORY_OR_EVIDENCE_PATH": 1,
                "TEMPORARY_WORKING_COPY": 2,
                "UNSOURCED_SEMANTIC_CONCEPT": 3,
            }[item["location_class"]],
            0 if item["ownership"].get("role") == "CANONICAL_SOURCE_CANDIDATE" else 1,
            item["kind"],
            item["qualified_name"],
        ),
    )
    budget_omitted = max(0, len(ordered) - overall_limit)
    if budget_omitted:
        reserve = max(1, min(50, overall_limit // 10))
        selected_ids: set[str] = set()
        selected_per_class: dict[str, int] = {}
        for location_class in (
            "ACTIVE_TREE_PATH_CANDIDATE",
            "HISTORY_OR_EVIDENCE_PATH",
            "TEMPORARY_WORKING_COPY",
            "UNSOURCED_SEMANTIC_CONCEPT",
        ):
            for item in ordered:
                if len(selected_ids) >= overall_limit:
                    break
                if (
                    item["location_class"] == location_class
                    and item["entity_id"] not in selected_ids
                    and selected_per_class.get(location_class, 0) < reserve
                ):
                    selected_ids.add(item["entity_id"])
                    selected_per_class[location_class] = (
                        selected_per_class.get(location_class, 0) + 1
                    )
        for item in ordered:
            if len(selected_ids) >= overall_limit:
                break
            selected_ids.add(item["entity_id"])
        results = [item for item in ordered if item["entity_id"] in selected_ids]
    else:
        results = ordered
    consulted_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for item in results:
        source = item["source"]
        if not source or not source.get("path"):
            continue
        key = (source["path"], source["identity_sha256"])
        consulted_sources[key] = {
            "path": source["path"],
            "identity_sha256": source["identity_sha256"],
            "source_location": source.get("source_location"),
            "location_class": item["location_class"],
            "ownership": item["ownership"],
        }
    coverage = [coverage_by_key[key] for key in sorted(coverage_by_key)]
    incomplete = [
        {
            "map_id": item["map_id"],
            "disposition": item["disposition"],
            "scope": item["scope"],
            "details": item["details"],
        }
        for item in coverage
        if item["disposition"] != "COVERED"
    ]
    completeness = (
        "PARTIAL"
        if incomplete or any_truncated or budget_omitted
        else "COVERED_WITHIN_DECLARED_MAP_SCOPE"
    )
    return seal_document(
        {
            "schema": DOSSIER_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-model-facing-codebase-dossier",
            "authority_granted": False,
            "dossier": dossier_id,
            "terms": list(search_terms),
            "options": {
                "maps": maps,
                "base_maps": base_maps,
                "maps_added_by_term_routing": maps_added_by_term_routing,
                "limit_per_term": limit_per_term,
                "overall_limit": overall_limit,
                "fact_limit": fact_limit,
                "include_semantic": include_semantic,
                "include_facts": include_facts,
            },
            "mapper": {
                "run_id": run.manifest["run_id"],
                "manifest_receipt_sha256": run.manifest["receipt_sha256"],
                "inventory_run_id": run.manifest["inventory"]["run_id"],
                "inventory_receipt_sha256": run.manifest["inventory"]["receipt_sha256"],
            },
            "query_receipts": query_receipts,
            "term_routes": term_routes,
            "routing_policy": {
                "algorithm": "giga.dossier-term-route-union.v1",
                "fallback_routes_expand_dossier": False,
                "matched_primary_maps_expand_dossier": True,
                "fixed_dossier_maps_preserved": True,
                "derived_not_fact": True,
            },
            "results": results,
            "result_count": len(results),
            "consulted_sources": [
                consulted_sources[key] for key in sorted(consulted_sources)
            ],
            "consulted_source_count": len(consulted_sources),
            "coverage": coverage,
            "completeness": completeness,
            "incomplete_boundaries": incomplete,
            "omissions": {
                "subquery_truncated": any_truncated,
                "results_omitted_by_overall_budget": budget_omitted,
                "navigation_policy_entity_ids": navigation_policy_omitted,
                "navigation_policy_count": len(navigation_policy_omitted),
            },
            "claims": {
                "complete_inventory_allowed": False,
                "current_architecture_allowed": False,
                "eligible_for_separate_adoption_gate": completeness
                == "COVERED_WITHIN_DECLARED_MAP_SCOPE",
                "no_feature_loss_allowed": False,
                "canonical_owner_asserted": False,
                "deletion_authority_granted": False,
                "execution_authority_granted": False,
            },
        }
    )


def _file_graph_rank(
    database_path: Path,
    *,
    personalized_paths: Mapping[str, float],
    damping: float = 0.85,
    iterations: int = 40,
) -> tuple[dict[str, float], dict[str, int]]:
    """Rank source paths from the authenticated relation graph.

    The graph is intentionally file-level.  It excludes control-flow expansion,
    which otherwise overwhelms repository orientation, and reduces ubiquitous
    destinations by their distinct incoming-file fan-in.
    """

    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        placeholders = ",".join("?" for _ in _RANK_PREDICATES)
        rows = connection.execute(
            f"""SELECT ss.path AS subject_path,so.path AS object_path,
                       r.predicate AS predicate
                  FROM relations r
                  JOIN entities es ON es.entity_id=r.subject_id
                  JOIN entities eo ON eo.entity_id=r.object_id
                  JOIN sources ss ON ss.source_id=es.source_id
                  JOIN sources so ON so.source_id=eo.source_id
                 WHERE r.predicate IN ({placeholders})
                   AND ss.path<>so.path
                 ORDER BY ss.path,so.path,r.predicate,r.relation_id""",
            _RANK_PREDICATES,
        ).fetchall()
    finally:
        connection.close()

    edge_counts: dict[tuple[str, str], int] = defaultdict(int)
    incoming_sources: dict[str, set[str]] = defaultdict(set)
    nodes = set(personalized_paths)
    for row in rows:
        subject = row["subject_path"]
        object_ = row["object_path"]
        edge_counts[(subject, object_)] += 1
        incoming_sources[object_].add(subject)
        nodes.update((subject, object_))
    if not nodes:
        return {}, {"nodes": 0, "edges": 0}
    ordered_nodes = sorted(nodes)

    outgoing: dict[str, dict[str, float]] = defaultdict(dict)
    for (subject, object_), count in sorted(edge_counts.items()):
        # Anti-ubiquity weighting prevents common helpers from absorbing the map.
        fan_in = max(1, len(incoming_sources[object_]))
        outgoing[subject][object_] = float(count) / float(fan_in)

    personalization = {
        node: max(0.0, float(personalized_paths.get(node, 0.0)))
        for node in ordered_nodes
    }
    personalization_total = sum(personalization.values())
    if personalization_total == 0.0:
        personalization = {node: 1.0 for node in ordered_nodes}
        personalization_total = float(len(ordered_nodes))
    personalization = {
        node: value / personalization_total for node, value in personalization.items()
    }
    rank = dict(personalization)
    for _ in range(iterations):
        dangling = sum(rank[node] for node in ordered_nodes if not outgoing.get(node))
        updated = {
            node: (1.0 - damping) * personalization[node]
            + damping * dangling * personalization[node]
            for node in ordered_nodes
        }
        for subject in sorted(outgoing):
            weights = outgoing[subject]
            total_weight = sum(weights.values())
            if total_weight == 0.0:
                continue
            for object_, weight in sorted(weights.items()):
                updated[object_] += damping * rank[subject] * weight / total_weight
        rank = updated
    return (
        {path: round(value, 15) for path, value in rank.items()},
        {"nodes": len(ordered_nodes), "edges": len(edge_counts)},
    )


def _entity_graph_rank(
    database_path: Path,
    *,
    personalized_entities: Mapping[str, float],
    damping: float = 0.85,
    iterations: int = 40,
) -> tuple[dict[str, float], dict[str, int]]:
    """Rank exact mapper entities without promoting the derived score to fact."""

    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        placeholders = ",".join("?" for _ in _RANK_PREDICATES)
        rows = connection.execute(
            f"""SELECT subject_id,object_id
                  FROM relations
                 WHERE predicate IN ({placeholders})
                   AND subject_id<>object_id
                 ORDER BY subject_id,object_id,relation_id""",
            _RANK_PREDICATES,
        ).fetchall()
    finally:
        connection.close()

    edge_counts: dict[tuple[str, str], int] = defaultdict(int)
    incoming_subjects: dict[str, set[str]] = defaultdict(set)
    nodes = set(personalized_entities)
    for subject, object_ in rows:
        edge_counts[(subject, object_)] += 1
        incoming_subjects[object_].add(subject)
        nodes.update((subject, object_))
    if not nodes:
        return {}, {"nodes": 0, "edges": 0}
    ordered_nodes = sorted(nodes)

    outgoing: dict[str, dict[str, float]] = defaultdict(dict)
    for (subject, object_), count in sorted(edge_counts.items()):
        fan_in = max(1, len(incoming_subjects[object_]))
        outgoing[subject][object_] = float(count) / float(fan_in)
    personalization = {
        node: max(0.0, float(personalized_entities.get(node, 0.0)))
        for node in ordered_nodes
    }
    total = sum(personalization.values())
    if total == 0.0:
        personalization = {node: 1.0 for node in ordered_nodes}
        total = float(len(ordered_nodes))
    personalization = {node: value / total for node, value in personalization.items()}
    rank = dict(personalization)
    for _ in range(iterations):
        dangling = sum(rank[node] for node in ordered_nodes if not outgoing.get(node))
        updated = {
            node: (1.0 - damping) * personalization[node]
            + damping * dangling * personalization[node]
            for node in ordered_nodes
        }
        for subject in sorted(outgoing):
            weights = outgoing[subject]
            total_weight = sum(weights.values())
            if total_weight == 0.0:
                continue
            for object_, weight in sorted(weights.items()):
                updated[object_] += damping * rank[subject] * weight / total_weight
        rank = updated
    return (
        {identifier: round(value, 15) for identifier, value in rank.items()},
        {"nodes": len(ordered_nodes), "edges": len(edge_counts)},
    )


def _relation_neighbors(
    database_path: Path,
    *,
    seed_items: Sequence[Mapping[str, Any]],
    maps: Sequence[str],
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Return one-hop source entities without rereading repository files."""

    seed_ids = {item["entity_id"] for item in seed_items}
    if not seed_ids or limit <= 0:
        return [], False
    allowed_kinds = {
        kind for map_id in maps for kind in MAP_ENTITY_KINDS.get(map_id, frozenset())
    }
    placeholders = ",".join("?" for _ in seed_ids)
    predicate_placeholders = ",".join("?" for _ in _RANK_PREDICATES)
    parameters = (*_RANK_PREDICATES, *sorted(seed_ids), *sorted(seed_ids))
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        relations = connection.execute(
            f"""SELECT subject_id,predicate,object_id
                  FROM relations
                 WHERE predicate IN ({predicate_placeholders})
                   AND (subject_id IN ({placeholders})
                    OR object_id IN ({placeholders}))
                 ORDER BY predicate,subject_id,object_id""",
            parameters,
        ).fetchall()
        context_by_neighbor: dict[str, list[dict[str, str]]] = defaultdict(list)
        for relation in relations:
            subject = relation["subject_id"]
            object_ = relation["object_id"]
            if subject in seed_ids and object_ not in seed_ids:
                context_by_neighbor[object_].append(
                    {
                        "direction": "OUTBOUND",
                        "predicate": relation["predicate"],
                        "seed_entity_id": subject,
                    }
                )
            if object_ in seed_ids and subject not in seed_ids:
                context_by_neighbor[subject].append(
                    {
                        "direction": "INBOUND",
                        "predicate": relation["predicate"],
                        "seed_entity_id": object_,
                    }
                )
        neighbor_ids = sorted(context_by_neighbor)
        if not neighbor_ids:
            return [], False
        truncated = len(neighbor_ids) > limit
        neighbor_ids = neighbor_ids[:limit]
        entity_placeholders = ",".join("?" for _ in neighbor_ids)
        rows = connection.execute(
            f"""SELECT e.*,s.path AS source_path,
                       s.identity_sha256 AS source_sha256
                  FROM entities e
                  LEFT JOIN sources s ON s.source_id=e.source_id
                 WHERE e.entity_id IN ({entity_placeholders})
                 ORDER BY e.entity_id""",
            neighbor_ids,
        ).fetchall()
        paths = sorted({row["source_path"] for row in rows if row["source_path"]})
        ownership_by_path: dict[str, dict[str, Any]] = {}
        if paths:
            path_placeholders = ",".join("?" for _ in paths)
            for row in connection.execute(
                f"""SELECT s.path,e.attributes_json
                       FROM entities e JOIN sources s ON s.source_id=e.source_id
                      WHERE e.entity_kind='OWNERSHIP_PATH'
                        AND s.path IN ({path_placeholders})
                      ORDER BY s.path,e.entity_id""",
                paths,
            ):
                attributes = json.loads(row["attributes_json"])
                ownership_by_path[row["path"]] = {
                    "role": attributes.get("role"),
                    "role_basis": attributes.get("role_basis"),
                    "canonicality_claimed": attributes.get(
                        "canonicality_claimed", False
                    ),
                }
    finally:
        connection.close()

    results = []
    for row in rows:
        kind = row["entity_kind"]
        if kind not in allowed_kinds:
            continue
        source_path = row["source_path"]
        source = (
            {
                "path": source_path,
                "identity_sha256": row["source_sha256"],
            }
            if source_path
            else None
        )
        item_maps = [
            map_id
            for map_id in maps
            if kind in MAP_ENTITY_KINDS.get(map_id, frozenset())
        ]
        results.append(
            {
                "entity_id": row["entity_id"],
                "kind": kind,
                "name": row["name"],
                "qualified_name": row["qualified_name"],
                "truth_class": row["truth_class"],
                "privacy_class": row["privacy_class"],
                "source": source,
                "location_class": _location_class(source_path),
                "attributes": json.loads(row["attributes_json"]),
                "matched_terms": [],
                "map_ids": sorted(item_maps),
                "ownership": ownership_by_path.get(source_path, {"role": "UNKNOWN"}),
                "relation_context": sorted(
                    context_by_neighbor[row["entity_id"]],
                    key=lambda value: (
                        value["predicate"],
                        value["direction"],
                        value["seed_entity_id"],
                    ),
                ),
            }
        )
    return results, truncated


def _definition_projection(item: Mapping[str, Any]) -> tuple[str, str | None]:
    attributes = item.get("attributes")
    if not isinstance(attributes, Mapping):
        return item["qualified_name"], None
    definitions = attributes.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        return item["qualified_name"], None
    definition = definitions[0]
    if not isinstance(definition, Mapping):
        return item["qualified_name"], None
    signature = definition.get("signature")
    returns = definition.get("returns")
    label = item["qualified_name"]
    if isinstance(signature, str):
        label += f"({signature})"
    if isinstance(returns, str) and returns:
        label += f" -> {returns}"
    span = definition.get("span")
    if not isinstance(span, Mapping):
        return label, None
    start = span.get("line_start")
    end = span.get("line_end")
    if not isinstance(start, int) or not isinstance(end, int):
        return label, None
    return label, f"L{start}" if start == end else f"L{start}-L{end}"


def _context_line(item: Mapping[str, Any]) -> str:
    source = item.get("source")
    path = source.get("path") if isinstance(source, Mapping) else None
    label, span = _definition_projection(item)
    location = path or "<unsourced>"
    if span:
        location += f":{span}"
    return f"{location} | {item['kind']} | {label}"


def _ranking_multiplier(item: Mapping[str, Any]) -> float:
    location = {
        "ACTIVE_TREE_PATH_CANDIDATE": 1.0,
        "HISTORY_OR_EVIDENCE_PATH": 0.30,
        "TEMPORARY_WORKING_COPY": 0.10,
        "UNSOURCED_SEMANTIC_CONCEPT": 0.05,
    }[item["location_class"]]
    ownership = item.get("ownership")
    role = ownership.get("role") if isinstance(ownership, Mapping) else "UNKNOWN"
    role_weight = {
        "CANONICAL_SOURCE_CANDIDATE": 1.50,
        "HISTORICAL_OR_ARCHIVED_COPY": 0.50,
        "GENERATED_OR_DERIVED": 0.40,
        "TEMPORARY_OR_WORKTREE_COPY": 0.25,
    }.get(role, 1.0)
    return location * role_weight


def _kind_multiplier(kind: str) -> float:
    return {
        "ENTRYPOINT": 1.25,
        "PYTHON_SYMBOL": 1.15,
        "SHELL_SYMBOL": 1.15,
        "JAVASCRIPT_SYMBOL": 1.15,
        "RUNTIME_ENTRYPOINT": 1.15,
        "RUNTIME_CAPABILITY": 1.10,
        "PYTHON_MODULE": 1.05,
        "SHELL_SCRIPT": 1.05,
        "JAVASCRIPT_MODULE": 1.05,
        "SHELL_COMMAND": 1.00,
        "JAVASCRIPT_CALL": 1.00,
        "CONTRACT": 1.05,
        "ARTIFACT": 0.90,
        "OWNERSHIP_PATH": 0.85,
        "DATABASE_DECLARATION": 0.80,
        "DATA_OBJECT": 0.80,
    }.get(kind, 1.0)


def _projectable_item(item: Mapping[str, Any]) -> bool:
    if item["kind"] not in {
        "PYTHON_SYMBOL",
        "SHELL_SYMBOL",
        "JAVASCRIPT_SYMBOL",
    }:
        return True
    attributes = item.get("attributes")
    symbol_kind = (
        attributes.get("symbol_kind") if isinstance(attributes, Mapping) else None
    )
    return symbol_kind not in {"PARAMETER", "VARIABLE"}


def _redundant_local_scip_symbols(
    candidates: Sequence[Mapping[str, Any]],
) -> set[str]:
    """Suppress only local SCIP definitions already represented by exact AST facts.

    SCIP remains queryable in the fact store and remains available when it adds
    precision the AST producer lacks.  The compact model context should not spend
    its budget on a second representation of the same local Python declaration.
    """

    python_definitions = {
        (item["source"]["path"], item["name"])
        for item in candidates
        if item.get("kind") == "PYTHON_SYMBOL"
        and isinstance(item.get("source"), Mapping)
        and isinstance(item["source"].get("path"), str)
    }
    redundant: set[str] = set()
    for item in candidates:
        if item.get("kind") != "SCIP_SYMBOL":
            continue
        attributes = item.get("attributes")
        definitions = (
            attributes.get("definition_paths")
            if isinstance(attributes, Mapping)
            else None
        )
        if not isinstance(definitions, list) or not all(
            isinstance(path, str) for path in definitions
        ):
            continue
        if any((path, item["name"]) in python_definitions for path in definitions):
            redundant.add(item["entity_id"])
    return redundant


def build_context_projection(
    store: Path,
    dossier_id: str,
    terms: Sequence[str],
    *,
    token_budget: int = 1000,
    limit_per_term: int = 100,
    candidate_limit: int = 2000,
    fact_limit: int = 20,
    include_semantic: bool = True,
    allowed_source_paths: Collection[str] | None = None,
) -> dict[str, Any]:
    """Render ranked, source-linked mapper facts inside a deterministic budget.

    ``token_budget`` limits only the ``context`` string under the declared
    lexical tokenizer.  It is deliberately not presented as a model-specific
    token count.
    """

    if isinstance(token_budget, bool) or not 32 <= token_budget <= 65_536:
        raise DossierError("token_budget must be between 32 and 65536")
    dossier = build_dossier(
        store,
        dossier_id,
        terms,
        limit_per_term=limit_per_term,
        overall_limit=candidate_limit,
        fact_limit=fact_limit,
        include_semantic=include_semantic,
        include_facts=False,
    )
    run = current_mapper_run(store)
    database_path = run.run_directory / "facts.sqlite3"
    admitted_paths = (
        set(allowed_source_paths) if allowed_source_paths is not None else None
    )
    non_live_source_ids: list[str] = []

    def source_is_admitted(item: Mapping[str, Any]) -> bool:
        if admitted_paths is None:
            return True
        source = item.get("source")
        path = source.get("path") if isinstance(source, Mapping) else None
        attributes = item.get("attributes")
        semantic_current = bool(
            item.get("kind") != "SEMANTIC_CONCEPT"
            or (
                isinstance(attributes, Mapping)
                and attributes.get("source_freshness") == "CURRENT_SOURCE_MATCH"
            )
        )
        if isinstance(path, str) and path in admitted_paths and semantic_current:
            return True
        non_live_source_ids.append(item["entity_id"])
        return False

    direct_results = [
        {**item, "relation_context": []}
        for item in dossier["results"]
        if source_is_admitted(item)
    ]
    neighbor_capacity = max(0, candidate_limit - len(direct_results))
    neighbors, neighbor_truncated = _relation_neighbors(
        database_path,
        seed_items=direct_results,
        maps=dossier["options"]["maps"],
        limit=neighbor_capacity,
    )
    candidates = [
        *direct_results,
        *(item for item in neighbors if source_is_admitted(item)),
    ]
    redundant_precision_ids = _redundant_local_scip_symbols(candidates)
    personalized_paths: dict[str, float] = defaultdict(float)
    personalized_entities: dict[str, float] = defaultdict(float)
    for item in direct_results:
        source = item.get("source")
        path = source.get("path") if isinstance(source, Mapping) else None
        if path:
            personalized_paths[path] += 1.0 + float(len(item["matched_terms"]))
        personalized_entities[item["entity_id"]] += 1.0 + float(
            len(item["matched_terms"])
        )
    path_rank, graph = _file_graph_rank(
        database_path,
        personalized_paths=personalized_paths,
    )
    entity_rank, entity_graph = _entity_graph_rank(
        database_path,
        personalized_entities=personalized_entities,
    )

    ranked = []
    unprojectable_ids: list[str] = []
    for item in candidates:
        if item["entity_id"] in redundant_precision_ids:
            continue
        if not _projectable_item(item):
            unprojectable_ids.append(item["entity_id"])
            continue
        source = item.get("source")
        path = source.get("path") if isinstance(source, Mapping) else None
        graph_rank = path_rank.get(path, 0.0) if path else 0.0
        symbol_rank = entity_rank.get(item["entity_id"], 0.0)
        exact_term_matches = sum(
            term.casefold()
            in {item["name"].casefold(), item["qualified_name"].casefold()}
            for term in item["matched_terms"]
        )
        primary_map_term_matches = len(item.get("primary_map_matched_terms", ()))
        direct_match = (
            10.0 * (1.0 + float(len(item["matched_terms"])))
            + 1000.0 * float(primary_map_term_matches)
            + 100.0 * float(exact_term_matches)
            if item["matched_terms"]
            else 0.25
        )
        provenance_multiplier = _ranking_multiplier(item)
        kind_multiplier = _kind_multiplier(item["kind"])
        score = (
            (direct_match + 50.0 * graph_rank + 200.0 * symbol_rank)
            * provenance_multiplier
            * kind_multiplier
        )
        ranked.append(
            {
                **item,
                "ranking": {
                    "score": round(score, 12),
                    "file_graph_rank": round(graph_rank, 15),
                    "entity_graph_rank": round(symbol_rank, 15),
                    "direct_term_matches": len(item["matched_terms"]),
                    "primary_map_term_matches": primary_map_term_matches,
                    "exact_term_matches": exact_term_matches,
                    "provenance_multiplier": provenance_multiplier,
                    "kind_multiplier": kind_multiplier,
                },
                "context_line": _context_line(item),
            }
        )
    ranked.sort(
        key=lambda item: (
            -item["ranking"]["score"],
            item["location_class"],
            item["kind"],
            item["qualified_name"],
            item["entity_id"],
        )
    )

    selected: list[dict[str, Any]] = []
    context_lines: list[str] = []
    seen_projection_keys: set[tuple[str | None, str]] = set()
    entries_by_source: dict[str, int] = defaultdict(int)
    redundant_ids: list[str] = []
    diversity_ids: list[str] = []
    budget_ids: list[str] = []
    used = 0
    for item in ranked:
        source = item.get("source")
        path = source.get("path") if isinstance(source, Mapping) else None
        projection_key = (path, item["qualified_name"])
        if projection_key in seen_projection_keys:
            redundant_ids.append(item["entity_id"])
            continue
        if path and entries_by_source[path] >= 5:
            diversity_ids.append(item["entity_id"])
            continue
        line = item["context_line"]
        cost = lexical_token_count(line)
        if used + cost > token_budget:
            budget_ids.append(item["entity_id"])
            continue
        selected.append(item)
        context_lines.append(line)
        seen_projection_keys.add(projection_key)
        if path:
            entries_by_source[path] += 1
        used += cost
    selected_ids = {item["entity_id"] for item in selected}
    omitted = [*unprojectable_ids]
    omitted.extend(
        item["entity_id"] for item in ranked if item["entity_id"] not in selected_ids
    )
    context = "\n".join(context_lines)
    if lexical_token_count(context) != used:
        raise DossierError("context lexical-token accounting mismatch")

    return seal_document(
        {
            "schema": CONTEXT_SCHEMA,
            "status": "PASS",
            "authority": "non-authoritative-ranked-codebase-context",
            "authority_granted": False,
            "dossier": dossier_id,
            "terms": dossier["terms"],
            "mapper": dossier["mapper"],
            "ranking": {
                "algorithm": (
                    "giga.personalized-file-rank.v3-precision-deduplicated-map-aware"
                ),
                "damping": 0.85,
                "iterations": 40,
                "predicates": list(_RANK_PREDICATES),
                "anti_ubiquity": "divide edge weight by distinct incoming-file fan-in",
                "location_and_ownership_weighted": True,
                "kind_weighted": True,
                "exact_name_or_qualified_name_boost": 100.0,
                "maximum_entries_per_source": 5,
                "definition_projection": "exclude Python parameter and variable symbols",
                "precision_deduplication": (
                    "local SCIP definitions already represented by exact Python AST facts"
                ),
                "graph": graph,
                "entity_graph": entity_graph,
                "one_hop_relation_expansion": {
                    "added_entities": len(neighbors),
                    "truncated": neighbor_truncated,
                },
                "derived_not_authoritative": True,
            },
            "budget": {
                "unit": "giga.lexical-token.v1",
                "requested": token_budget,
                "used": used,
                "applies_to": "context field only",
                "model_token_equivalence_claimed": False,
            },
            "context": context,
            "entries": selected,
            "entry_count": len(selected),
            "candidate_count": len(candidates),
            "non_live_source_candidates_excluded": len(non_live_source_ids),
            "projectable_candidate_count": len(ranked),
            "omissions": {
                "entity_ids_omitted_by_context_budget": omitted,
                "count": len(omitted),
                "redundant_projection_entity_ids": redundant_ids,
                "redundant_precision_entity_ids": sorted(redundant_precision_ids),
                "source_diversity_entity_ids": diversity_ids,
                "lexical_budget_entity_ids": budget_ids,
                "non_definition_entity_ids": unprojectable_ids,
                "non_live_source_entity_ids": non_live_source_ids,
                "upstream_dossier": dossier["omissions"],
                "relation_expansion_truncated": neighbor_truncated,
            },
            "query_receipts": dossier["query_receipts"],
            "term_routes": dossier["term_routes"],
            "routing_policy": dossier["routing_policy"],
            "coverage": dossier["coverage"],
            "completeness": (
                "PARTIAL" if omitted or neighbor_truncated else dossier["completeness"]
            ),
            "claims": {
                "complete_inventory_allowed": False,
                "current_architecture_allowed": False,
                "no_feature_loss_allowed": False,
                "canonical_owner_asserted": False,
                "deletion_authority_granted": False,
                "execution_authority_granted": False,
            },
        }
    )
