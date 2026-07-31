# Fable ruling: DFI-04 multi-entry settlement recovery

Date: 2026-07-23

## Question

The DFI-04 repository settlement path checked only whether *any* knowledge entry already
existed for a task. If a task produced multiple entries and the process crashed after writing
the first, retry would treat knowledge persistence as complete, skip the remaining entries,
record a successful result and complete the task.

## Authority ruling

This defect blocks DFI-04 certification.

Use per-entry deterministic identity:

1. Every intended knowledge-base entry receives a deterministic identity fixed by the
   settlement input, such as task identity plus stable entry position and semantic content.
2. Settlement verifies and records membership independently for every intended entry.
3. A retry records only missing entries.
4. Result persistence and task completion occur only after all intended entries are present.
5. If an existing deterministic identity has different semantic content, settlement fails
   closed.

Do not impose an adapter-specific one-entry restriction. The repository settlement primitive
must remain correct for generic multi-entry results.

## Minimum behavioural evidence

1. Settle a result containing at least two knowledge entries.
2. Inject a crash after exactly one entry is durably recorded.
3. Restart or reconstruct the repository and retry settlement.
4. Prove that all intended entries exist exactly once and that the task reaches COMPLETE only
   after all entries are durable.
5. Add a second crash-window test after result persistence but before COMPLETE, then prove
   idempotent recovery.

This ruling is narrow to DFI-04. It does not authorise activation, production cutover, DFI-05,
or JAA work.
