# ECC-derived governance kit (staged candidate)

Status: **not deployed**.

This candidate adapts three useful ECC concepts into small, harness-neutral evidence contracts:

- honest adapter states (`native`, `adapter-backed`, `instruction-backed`, `reference-only`);
- evaluator promotion that requires both an accepted candidate and a rejected negative control;
- source-commit and file-hash provenance for every imported component.

Source: `affaan-m/ECC` at commit `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`, especially
`docs/architecture/harness-adapter-compliance.md` and
`docs/architecture/evaluator-rag-prototype.md`. ECC is MIT licensed. This implementation is an
independent, minimal adaptation rather than a copied runtime.

Run `python3 -m unittest discover -s tests -v` from this directory. Promotion remains a separate,
explicit decision.
