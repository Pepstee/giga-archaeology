# Virtual Artiom — Fine-tuning Readiness

**Status:** two strictly local experimental runs were authorised by the operator on
26 July 2026; **promotion remains blocked** pending held-out behavioural and privacy review.
**Trigger:** both Discord accounts, Telegram, full two-sided Instagram, Claude and both
ChatGPT accounts are now unified in the provenance-bearing memory database.
**Objective:** make each arrival a deterministic import into versioned candidate datasets,
then train only after privacy, mode, leakage and evaluation gates pass.

## The governing distinction

Fine-tuning is for relatively stable **behaviour**:

- register, brevity, rhythm and multilingual code-switching;
- how Artiom critiques, corrects, accepts, questions and redirects;
- recurring reasoning procedures and challenge thresholds;
- mode selection when the mode is explicitly supplied.

It is not the memory system. Current facts, plans, relationships, travel, work state and
standing decisions remain in `CONTEXT.md` and `memory/`, retrieved at inference time. Baking
them into weights would create an undebuggable stale-memory layer.

## Do not train one undifferentiated “Artiom” first

The ratified modes remain separate:

| Mode | Primary evidence | First training use |
|---|---|---|
| `casual-general` | non-intimate Instagram threads; current Discord where context exists | contextual reply style |
| `partner-intimate` | partner/flirty conversations | separate adapter or explicit mode tag |
| `work-directive` | work prompts, briefs and implementation corrections | instruction/constraint steering |
| `reasoning-critique` | Artiom's next turn after an AI answer | correction, acceptance and inquiry behaviour |
| `historical-casual-YYYY` | one-sided Discord export | style-only auxiliary corpus, era conditioned |

The present Instagram pair corpus is not a clean general-casual dataset: its largest
relationship contributes about half the examples. A private operator-reviewed mode map is
therefore a gate, not an optional refinement.

Copy `corpus/training/mode_map.template.json` to a private reviewed map and pass it through
`--mode-map`. `--only-mode` can then build separate versioned datasets without teaching a
general-casual adapter from intimate correspondence.

## What is ready now

### 26 July experimental datasets and runs

The operator explicitly directed the system to plan and proceed with LoRA tuning. That
authorises local experimentation on the exact manifests below; it does not waive privacy,
semantic-boundary or promotion gates.

`scripts/prepare_persona_lora.py` creates two non-interchangeable datasets directly from the
read-only unified evidence layer:

| Dataset | Train | Valid | Locked test | Quarantine | Semantic boundary |
|---|---:|---:|---:|---:|---|
| `speech-current-experimental-v1` | 21,346 | 319 | 1,849 | 7 | Real third-party→Artiom Telegram/Instagram reply bursts |
| `reasoning-steering-experimental-v1` | 6,983 | 299 | 591 | 680 | Model answer→Artiom critique/refinement/next instruction |

The speech test SHA-256 is
`76edb90d6b8236d3bb47aca083c35f211ae729cc778535bc38085feefcf70a11`.
The reasoning test SHA-256 is
`77cafdaea09a5dd3d7c54cf2163460290aacf24506f220fdd541c2cb95a43e3c`.
Neither test file enters training.

The preparation pass removes exact duplicates, rejects runtime-injection wrappers, screens
credentials, code and logs, and quarantines any operator-labelled target that exactly matches
a model-authored message elsewhere in the unified corpus. This last check addresses the
provider-role failure where pasted AI output is technically stored as a human turn.

The base is the locally cached `mlx-community/Qwen2.5-3B-Instruct-4bit`. Training uses MLX,
LoRA over 16 layers, prompt masking and local-private data. The runs are separate adapters so
casual speech and reasoning-steering cannot silently define one undifferentiated persona.
See `corpus/training/LORA_PLAN_AND_RUN_20260726.md` for immutable commands and results.

The validation-selected speech checkpoint is
`corpus/training/adapters/speech-current-experimental-v1a-best-0200/`. On the same 50 locked
test batches it reduced loss from 6.311 (base) to 2.973. Synthetic evaluation confirms much
shorter, more natural Russian/English replies and no disclosure on a privacy canary, but it
also invented an unspecified CI/CD cause in a professional boundary test. This is useful
evidence that voice transfer worked and equally useful evidence that promotion has not.

The reasoning-steering checkpoint is
`corpus/training/adapters/reasoning-steering-experimental-v1-best-0100/`. A seeded replay
reproduced the validation-best iteration exactly and reduced 50-batch locked-test loss from
5.833 to 3.113. Behaviourally, however, it learned terse questioning more successfully than
evidence-sensitive reasoning: it missed the repository/run-log request and responded to
unauthorised deletion with an irrelevant user-count question. It therefore failed the current
reasoning-promotion suite and is only a research artefact for correction cadence.

### Versioned pair preparation

`scripts/prepare_finetune_data.py prepare-pairs` now:

- validates chat records;
- removes exact duplicate pairs;
- quarantines possible credential-bearing examples;
- records privacy and quality flags without reproducing them in reports;
- provides separate local and cloud privacy profiles;
- creates deterministic relationship/conversation-month splits;
- coalesces identical input contexts into one split to stop prompt leakage;
- strips metadata from model input while retaining a provenance ledger;
- writes a source-hashed manifest with `training_authorised: false` by default.

The first build is `corpus/training/prepared/casual-current-v1/`:

| Split | Examples |
|---|---:|
| Train | 6,490 |
| Validation | 100 |
| Locked test | 468 |
| Quarantine | 1 possible credential-bearing record |

Three exact duplicates were removed. Contact/URL/handle flags remain review queues, not
confirmed privacy violations. The local build retains them; the cloud profile redacts common
email, phone, URL and handle forms but still requires a third-party-data review.

The 468-example test split is now hash-locked by `test.lock.json` and governed by
`corpus/training/EVALUATION_CONTRACT.md`. It may never enter training. Because the current
mode is still `unassigned`, this is a mixed-Instagram leakage-resistant baseline—not yet a
mode-balanced promotion suite. Reasoning needs its own later locked suite.

### Reasoning candidate extraction

`transcript-candidates` reverses the AI-chat perspective:

- the preceding AI answer becomes the stimulus (`user`);
- Artiom's next message becomes the target (`assistant`);
- the original conversation, timestamp, source and semantic limitation are preserved.

This produces **operator reaction/critique** examples, not proof that Artiom independently
solved the original task. Current dry run:

| Source | Candidates | Important quality warning |
|---|---:|---|
| ChatGPT historical transcript | 14,361 | 3,739 very long; 206 pasted-code targets |
| Second ChatGPT account (`gpt2_2026`) | 6,168 | Mixed 2023–26 operator reactions; pasted/third-party/model-authored targets still require authorship and function triage |
| Claude transcript | 1,861 | 583 very long |

These land under `corpus/training/candidates/` and are deliberately unapproved. They need
quality selection, mode labelling and a held-out reasoning evaluation before splitting.

### Discord landing

The Discord account export landed on 19 Jul 2026 as `package.zip` (SHA-256
`6fdf33df674d77badc830d8720b63f0ad9ebab3412f39ebcaf304c78c9050583`). The canonical
messages-only view contains 83,779 records across 391 channels from 11 Aug 2022 through
7 Jul 2026. The extractor intentionally ignores account, billing and analytics payloads.

The first audit found 79,246 text-bearing records, 4,533 empty/attachment-only records,
13,588 normalised duplicate excess and 19 possible credential-bearing texts. It is not yet a
training candidate dataset. Discord proves that the account sent a message, not that Artiom
composed it: the export visibly contains copypasta, forwarded messages, lesson material,
commands, documents and AI-formatted output. Every record is therefore marked
`composition_status: unverified` pending function/authorship triage.

The old/teen account subsequently landed as `package(1).zip` (SHA-256
`c9396462fb02dbb4ed75161582c0c9d07c707dcb597d0613291754850cceef4f`). A
Russian-localised structural extraction produced 248,752 account-sent records across 485
populated channels, spanning 25 June 2018 to 29 May 2026 and overwhelmingly concentrated in
2019–22. Its 240,253 text-bearing records include 66,579 normalised duplicate excess and three
possible-credential candidates. The same one-sided and composition-unverified limits apply.
It has therefore informed developmental chronology and speech-pattern analysis but remains
excluded from contextual reply SFT.

### Second ChatGPT export landed and isolated

The separate account archive landed on 19 Jul 2026 and was extracted on 20 Jul using the
`gpt2_2026` namespace without replacing the established canonical transcript:

```bash
python3 scripts/extract_chatgpt.py \
  --archive "/Users/admin/Documents/giga-user/1916b63abd801fbb5abf9b44f98d87a68ccd5db992b2a4d30567dd8a4ed29a85-2026-07-19-08-37-41-df72519dd898472489071b0441745ac3.zip" \
  --namespace gpt2_2026 \
  --stamp 20260720
```

This writes:

- `corpus/raw/chatgpt_prompts_gpt2_2026_<date>.jsonl`
- `corpus/transcripts/chatgpt_conversations_gpt2_2026.jsonl`

Every record carries `export_namespace: gpt2_2026`.
`scripts/extract_prompts.py` now selects the newest snapshot independently for each namespace,
so daily canonical harvesting joins both accounts instead of allowing the second filename to
displace the first.

The immutable archive is 1.17 GB with SHA-256
`f766b446d9a7deb7e5e3b833fe968b44db94102190128959b9c9612d8e586652`; ZIP CRC and path
safety checks passed. The canonical text view contains 15,214 turns from 1,199 text-bearing
conversations, spanning 26 Mar 2023 to 19 Jul 2026. Its SHA-256 is
`b340343acc90e2936011b6e708dbaade13eefc609ca01c5150dd34caf88d5302`. The full chronological
provenance review is `retrospectives/gpt2_2026-2023-03_to_2026-07-forward-ledger.md`.

## Arrival runbook

### Second GPT export — completed import and remaining work

Completed: untouched archive retained; SHA-256 and source label recorded; namespace-isolated
canonical transcript extracted; schema/count/span/non-text exclusions verified; every populated
month reviewed forwards; reasoning candidates produced:

   ```bash
   python3 scripts/prepare_finetune_data.py transcript-candidates \
     --input corpus/transcripts/chatgpt_conversations_gpt2_2026.jsonl \
     --output corpus/training/candidates/gpt2-2026-reasoning-v0.jsonl \
     --mode reasoning-steering
   ```

Remaining:

1. Preserve non-canonical/retry branches separately if the export contains them. Branch
   selection is only a weak preference signal; it must not automatically become chosen versus
   rejected data without explicit correction or rating evidence.
2. Deduplicate across accounts only by exact content/provenance rules. Do not collapse two
   people/accounts merely because titles or timestamps resemble each other.
3. Label direct operator reactions separately from pasted model reports, third-party material,
   fiction, roleplay and requested drafts before any dataset split or training authorisation.

### Discord landed — completed import steps and remaining work

Completed: raw package hashed; messages-only canonical view extracted; counts verified by
year; style/privacy audit written. Reproduction commands:

```bash
   python3 scripts/prepare_finetune_data.py audit-style \
     --input corpus/raw/discord_messages_primary_20260719.jsonl \
     --report corpus/training/candidates/discord-style-primary-20260719.audit.json
```

Remaining:

1. Keep every message era-tagged. Historical Discord must never silently update the current
   casual mode.
2. Label likely-original, forwarded/quoted, copypasta/performance, AI-assisted,
   code/reference, attachment-only and ambiguous records.
3. Resolve the possible-credential queue before any training or upload.
4. Because the official package contains only account-sent messages, treat it as style-only
   text. Do not invent prompts or pretend it contains context→reply supervision.
5. If contextual Discord history is later recovered from another authorised source, build a
   separate paired dataset with participant provenance and privacy review.

## Gates before any training command runs

### G0 — Source integrity

- Raw archive hashed, dated and inventoried.
- Extractor produces reproducible counts and no unexplained losses.
- Source account, era and register present on every candidate.

### G1 — Privacy and authority

- Credential quarantine empty or manually resolved.
- Third-party words reviewed for the intended execution environment.
- Local-only and cloud-uploadable datasets are separate artefacts.
- No dataset is uploaded merely because a provider supports fine-tuning.

### G2 — Semantic correctness

- Every target is genuinely Artiom-authored.
- `direct-reply`, `operator-next-turn` and `style-only` are never conflated.
- Pasted documents, generated prose and quotations are excluded or explicitly labelled.
- Current and historical modes are separated.

### G3 — Distribution

- Operator-reviewed thread→mode map complete.
- Relationship dominance measured and intentionally weighted.
- Language, year, mode and target-length distributions documented.
- No source is duplicated through raw, transcript and pair views.

### G4 — Frozen evaluation

Before training, lock evaluations that the trainer cannot see:

1. **Casual reply:** 60–100 real incoming messages balanced across general, group and intimate
   modes. Artiom blind-ranks base, prompted base and adapter replies.
2. **Reasoning critique:** 40–60 flawed or incomplete AI answers. Score whether the model finds
   the same missing constraint, rejects the same assumption or asks the same decisive question.
3. **Register routing:** prompts where work/casual/intimate responses must not bleed together.
4. **Privacy:** canary prompts for memorised phone numbers, credentials, booking references and
   third-party text. Any reproduction is a stop condition.
5. **Memory separation:** current-fact questions must be answered from retrieval; the adapter
   must not confidently produce historical facts from weights.

Exact wording is not the sole target. Score constraint recognition, decision direction,
register, brevity and unacceptable leakage separately.

### G5 — Baseline and promotion rule

Evaluate at least:

- the base model;
- base model + charter/context/retrieval;
- fine-tuned model + the identical inference packet.

Fine-tuning ships only if it beats the strongest non-fine-tuned baseline on a locked test set
without worsening privacy, factual calibration or cross-mode contamination. More imitation
alone is not sufficient.

### G6 — Versioned training and rollback

Every run records:

- base model and immutable revision;
- dataset manifest hashes and mode mix;
- code revision and hyperparameters;
- hardware/runtime and duration;
- train/validation curves;
- locked evaluation results;
- adapter hash and promotion verdict.

Adapters are append-only versions. Never overwrite a promoted or rejected adapter.

## Current blockers to promotion

1. The speech adapter deliberately uses a mixed-private experimental mode. A private
   operator-reviewed thread→mode map is still required before a general-casual adapter can be
   promoted.
2. Discord remains style-only and is not in either reply-supervision dataset. Historical
   causal-style training still needs composition/function triage and era conditioning.
3. Locked automatic loss evaluation exists, but blind operator ranking across general,
   intimate, group and work registers remains outstanding.
4. Privacy canaries, memorisation checks, register-routing tests and current-fact
   memory-separation tests must pass.
5. The adapter must beat the same base model with charter/context/retrieval, not merely the
   unprompted base.
6. Reasoning-steering may only be described as learning operator reactions to model output.
   It cannot be promoted or marketed as a clone of independent hidden reasoning.

## Definition of ready

GIGA is now operationally ready to ingest, build evidence, and run local experimental LoRA
training without ad-hoc source rewriting. It is ready to **promote** an adapter only when the
remaining G3–G5 behavioural, mode, privacy and baseline comparisons are recorded as PASS.
