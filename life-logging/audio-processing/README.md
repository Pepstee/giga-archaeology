# Audio Processing

This subproject owns the private runtime data and policy for life-logging audio.
`Dubbing Studio` remains the reusable audio engine; it reads from and writes to the
paths defined here.

## Canonical hierarchy

```text
giga-user/
└── life-logging/
    └── audio-processing/
        ├── config/                 tracked configuration and path contracts
        ├── scripts/                tracked operational helpers
        ├── recordings/             private audio bytes; never tracked by Git
        │   ├── inbox/              completed uploads waiting to be claimed
        │   └── archive/            optional retained originals, partitioned by date
        ├── processing/             checkpoints, staging files and retryable jobs
        ├── outputs/                generated evidence; never permanent memory by itself
        │   └── packages/           capture-ID packages with explicit state manifests
        ├── outbox/
        │   └── giga/               idempotent approved events for the GIGA adapter
        └── state/                  SQLite ledger, health state and local logs
```

`recordings` is preferred to `files`: it states what the bytes are. Generic `files`
becomes ambiguous once transcripts, translations, manifests and checkpoints also exist.

## Host roots

| Host | Canonical root |
|---|---|
| Mac | `/Users/admin/Documents/giga-user/life-logging/audio-processing` |
| Gigabyte WSL (certified release target) | `/home/gutua/software-factory/giga-user/life-logging/audio-processing` |

The Mac is the development authority while Dubbing Studio is being completed and
certified. Do not mirror working-tree changes to the Gigabyte. Once Dubbing Studio
has full certification—or the operator explicitly declares it ready and mature—
publish a versioned GitHub release and deploy that release to the Gigabyte.

Raw recordings are private runtime data and are not part of the GitHub release.
Their transfer and retention policy must be defined separately before production
capture begins.

## Lifecycle

```text
recordings/inbox
  -> source hash and stability check
  -> processing/<capture-id>
  -> outputs/packages/<capture-id> [state=review]
  -> operator approve | reject
  -> same immutable-ID package [state=approved|rejected]
  -> outbox/giga/<event-id>.json
  -> separate GIGA ingestion gate
```

Rules:

1. Uploads land only in `recordings/inbox`, never in the `giga-user` root.
2. Inbox originals remain immutable until an explicit retention job archives or deletes them.
3. Temporary decoding and checkpoints stay in `processing`.
4. Generated transcripts are derived evidence, not memory.
5. Nothing reaches `outbox/giga` without explicit operator approval.
6. The GIGA adapter must verify hashes and idempotency before promotion.
7. Runtime directories are excluded from Git. No raw audio, transcript, database or
   processing log may be committed.
8. Package state changes in its manifest and SQLite ledger; directory moves are avoided so
   provenance paths remain stable.
9. Retention and deletion operate by capture ID across every derived layer.

## Bootstrap

On either canonical host:

```bash
python3 life-logging/audio-processing/scripts/bootstrap_paths.py
```

Use `--root` only for an intentional test or migration:

```bash
python3 life-logging/audio-processing/scripts/bootstrap_paths.py \
  --root /temporary/test/audio-processing
```
