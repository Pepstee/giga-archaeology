# Status contract

The registry is derived from the immutable public export plus the repository-owned evidence map.

| Status | Deterministic meaning |
|---|---|
| `implemented` | Every required path in an explicit evidence declaration exists. |
| `partial` | At least one, but not every, required path exists, or the declaration explicitly marks the node partial. |
| `available` | A matching installed/deployed skill can help, but no complete giga-user workflow is evidenced. |
| `external` | An explicit declaration points to a separate canonical system that owns the capability. |
| `blocked` | An explicit declaration records a blocker and no complete local implementation exists. |
| `documented` | The public export describes the node, but none of the stronger states is proven. |

Precedence is `implemented`, `external`, `partial`, `blocked`, `available`, `documented`.

Local evidence declarations use exact repository-relative paths. Directories must exist and contain at least one non-hidden entry. Globs are forbidden. Declared evidence existence is resolved inside the audit's `--evidence-root`, which defaults to the source root and is read-only; paths that escape it (including through symlinks) fail closed. Generated outputs are constrained to the source root. `external` declarations may additionally use exact absolute `external_evidence` paths; these prove a live seam but never count as local implementation, and their resolution is unchanged by the evidence root. Generated registry files never count as implementation evidence.

The generated registry and the canonical human surface (`skilltree/IMPLEMENTATION_STATUS.md`) are written as one atomic pair with rollback; `skilltree/IMPLEMENTATION_REPORT.md` is a tracked symlink to the canonical file. The audit's `--check` mode regenerates in memory and refuses a missing or divergent tracked file, or any compatibility path that is not that exact symlink.

An installed skill is availability evidence only. It becomes implementation evidence after a real workflow consumes it, produces durable output, and its acceptance contract is recorded in the evidence map.
