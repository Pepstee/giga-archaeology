# Fable ruling — DFI-05 post-Codex budget overflow

Date: 2026-07-23

## Verdict

`GO_DELETION_REFRACTOR`

The 521-line interrupted state does not prove the 350-line ceiling is too
small. It is quarantined, unreviewed repair output and may be used only as a
read-only source while a sole writer rebuilds from the exact preserved
348-line patch. It may not become the editing base or be copied wholesale.

## Binding conditions

- Final accounting remains net production diff from `dcf5097`.
- Ceiling remains at most 350 lines; 351 stops for re-adjudication.
- DFI-15 remains 150; the programme cap remains 3,330.
- All four Codex authority findings must be repaired.
- DFI-05 validates canonical cohort-seal identity and rejects pre-seal or
  foreign-cohort admission, but does not implement activation-soak rate
  evaluation. The later soak stage owns denominator/minimum/ceiling
  evaluation; DFI-05 must carry the required fields.
- Default-off behavior, STOP, JAA isolation, and existing JSONL authorities
  remain unchanged.
- Evidence must be fresh on final bytes: focused/affected tests, Ruff, diff
  hygiene, Sonnet coherence, new Codex PASS, then Fable milestone ruling.
- No commit before certification.

## Ordered repair

1. Rebuild from the hash-verified 348-line patch.
2. Repair embedded repository bindings and full replay bindings first.
3. Move complete fallback validation ahead of model invocation, deleting the
   now-redundant schema-only pre-check.
4. Substitute canonical cohort seal/pre-seal/foreign validation for the
   hash-shape check; do not add rate evaluation.
5. Consult quarantined bytes selectively, never copy whole files.
6. Stop explicitly with per-finding line cost if the complete result exceeds
   350.

