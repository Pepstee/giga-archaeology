# Immutable-evidence preflight

This directory is the read-only discovery and acceptance package for GIGA User's
source exports. It does not move, extract, normalise, chmod, or rewrite source
material.

## Files

- `RAW_SOURCE_EXPORT_LEDGER.json` — machine-readable inventory of source
  authorities, extracted originals, every archive-like file discovered in scope,
  consumers, baseline coverage, and known protection gaps.
- `IMMUTABLE_EVIDENCE_PREFLIGHT.md` — human-readable findings and blockers.
- `IMMUTABLE_VAULT_MIGRATION_CONTRACT.md` — required vault, migration, and
  restore-drill acceptance contract.
- `validate_evidence_ledger.py` — deterministic inventory and acceptance
  validator.
- `test_validate_evidence_ledger.py` — isolated unit tests using temporary
  synthetic files only.

## Commands

Run the inexpensive current-state inventory check:

```bash
python3 architecture/modularization/preflight/evidence/validate_evidence_ledger.py
```

Re-read every ZIP member and compressed stream:

```bash
python3 architecture/modularization/preflight/evidence/validate_evidence_ledger.py --full-crc
```

Test migration readiness. This is expected to fail until the blockers in the
preflight report are resolved:

```bash
python3 architecture/modularization/preflight/evidence/validate_evidence_ledger.py \
  --mode acceptance --full-crc
```

Run the isolated validator tests:

```bash
python3 -m unittest \
  architecture/modularization/preflight/evidence/test_validate_evidence_ledger.py
```

