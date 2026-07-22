# Technical report: Building an evidence-backed virtual-twin trust kernel

> **VERIFIED LOCAL DRAFT · publication authority not granted**

A local-first control plane that separates model proposals from deterministic authority and durable evidence.

## Evidence flow

```mermaid
flowchart LR
    A["Approved source"] --> B["Exact evidence match"]
    B --> C["Evidence-linked claim"]
    C --> D["Draft artefacts"]
    D --> E["Human release gate"]
```

## Trust kernel

- **Claim C1:** The implementation uses a local SQLite trust kernel for append-only events, processing attempts, receipts and derived-artifact lineage.

## Replay and integrity

- **Claim C2:** Event replay is idempotent: an unchanged idempotency key returns the existing event, while a changed payload is rejected.
- **Claim C3:** Derived artefacts require a SHA-256 digest and at least one source reference, and their lineage audit detects later source mutation.

## Model authority boundary

- **Claim C4:** Model-generated memory changes receive no direct write authority: proposals are projected into a temporary complete memory copy and validated before commit.

## Current limitation

- **Limitation L1:** The current P2 phase has not yet passed because the first natural post-deployment daily run and full transition fault injection remain outstanding.

## Claim audit

| Claim | Kind | Evidence |
|---|---|---|
| C1 | fact | `twin_core/store.py` (L1, L123, L221; sha256 `0a0502ab06282689556489e77a47b457bbdaf11d27eb38630d1ce447e4924cae`); `architecture/06_IMPLEMENTATION_STATUS.md` (L24; sha256 `96f022de705d7d05e308e5a68beb829ccb890592a9d692ec53480a6a29683281`) |
| C2 | fact | `twin_core/store.py` (L330, L331; sha256 `0a0502ab06282689556489e77a47b457bbdaf11d27eb38630d1ce447e4924cae`); `tests/test_twin_store.py` (L19; sha256 `140b3b044548b59527375d1b2563f93387452200523f338fb6c21a35884251f6`) |
| C3 | fact | `twin_core/store.py` (L578, L580, L769; sha256 `0a0502ab06282689556489e77a47b457bbdaf11d27eb38630d1ce447e4924cae`); `tests/test_twin_store.py` (L94, L125; sha256 `140b3b044548b59527375d1b2563f93387452200523f338fb6c21a35884251f6`) |
| C4 | fact | `twin_core/memory_proposals.py` (L3, L4, L153; sha256 `853369d89c6ee7d845ff6032997d5ca202733d3ec24c296dbdede3afb4535d62`) |
| L1 | limitation | `architecture/06_IMPLEMENTATION_STATUS.md` (L6, L7; sha256 `96f022de705d7d05e308e5a68beb829ccb890592a9d692ec53480a6a29683281`) |
