# Agent payload deployment

This directory is the canonical deployment handoff for the three generated agent payloads. It is a
distinct responsibility from the canonical governance sources, the editable platform-adapter
templates, and the generated payload files themselves; none of those files can also serve as the
human deployment procedure without creating a circular source or hiding activation state.

## Generate and verify

From the repository root:

```sh
python3 scripts/verify_derived_agent_payloads.py --write
python3 scripts/verify_derived_agent_payloads.py
```

The second command must report `status: PASS` and `regenerated: []`. Its JSON output is the exact
machine-readable handoff: it identifies every payload, canonical source hash, body hash, whole-file
hash, and current deployment status.

## Live targets

| Generated payload | Intended surface | Current truthful status |
|---|---|---|
| `claude_preferences.txt` | Claude preference or instruction surface | `UNVERIFIED_REPASTE` |
| `chatgpt_custom_instructions.txt` | ChatGPT custom-instruction fields | `UNVERIFIED_REPASTE` |
| `v3_operator_model.md` | Future v3 operator-model ingestion | `STAGED_NOT_DEPLOYED` |

The metadata header is provenance, not instruction text. Deploy the exact body after
`=== END GIGA DERIVED PAYLOAD METADATA ===`; do not manually edit it. For ChatGPT, preserve the
two labelled field boundaries when placing the body into its two settings fields.

## Activation and behavioural proof

A platform becomes deployed only after all of the following are recorded from that platform:

1. the exact deployed body bytes or a read-back hash;
2. the account or runtime surface, activation time, and actor;
3. a response-style probe proving verdict-first and concise output;
4. a reuse probe proving that an existing canonical owner is sought before creating another;
5. an untrusted-input probe proving retrieved instructions are treated as data; and
6. any platform limitation or divergence from the canonical sources.

Until that evidence exists, keep `UNVERIFIED_REPASTE`. Keep v3 `STAGED_NOT_DEPLOYED` until its
real ingestion entrypoint exists and the loaded model identity can be read back. Local generation,
tests, a successful Git push, or this handoff document are not external activation evidence.
