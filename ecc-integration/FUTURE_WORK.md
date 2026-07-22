# ECC extraction boundary and deferred deterministic enforcement

## Deferred until extraction is complete

Repository-wide deterministic enforcement is necessary if “deterministic first” is to become a
guarantee rather than a convention. It is deliberately deferred until the useful ECC extraction
is complete.

The later enforcement slice should require every official execution path to:

1. resolve a registered deterministic adapter before considering an LLM;
2. validate current evidence, freshness and authority;
3. treat model output as a proposal rather than verified evidence;
4. refuse unavailable or unauthorised work instead of bypassing the registry;
5. emit a deterministic receipt for every accepted transition;
6. fail CI when an official entry point bypasses the execution gate.

## Freeze during extraction

Until the extraction-complete decision is recorded:

- do not rewire all giga-user CLIs, scheduled jobs, Jarvis or external adapters;
- do not introduce a global execution gateway;
- do not claim the current adapter registry universally enforces deterministic routing;
- stage portable ECC findings only under `ecc-integration/`;
- allow only validation and documentation changes needed to prove the extraction itself.

## Extraction-complete gate

The freeze can be lifted only after the pinned ECC source has:

- complete file and skill disposition coverage;
- a portable-finding ledger with source hashes and explicit import/defer/reject decisions;
- staged artifacts for every imported finding;
- tests proving staged contracts are internally consistent and non-executable;
- an explicit list of remaining on-demand material rather than an undefined “more to inspect.”

Lifting the freeze authorises design review, not automatic deployment.
