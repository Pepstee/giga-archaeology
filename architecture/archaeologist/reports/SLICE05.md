# Slice 05 report — deterministic fail-closed Judge

## Outcome

Slice 05 is independently useful now. `giga-archaeologist judge` is the only
Archaeologist component that can classify an observation as a quarantine
candidate. It validates and cross-binds the inventory, scanner hypotheses,
counterevidence and historical evidence before applying a fixed policy.

The live GIGA run evaluated 881 scanner hypotheses:

- 878 became `CONFLICT` because positive usage or historical/parallel variant
  evidence exists;
- 3 remain `UNKNOWN` because required proof is incomplete;
- 0 became `VERIFIED_CANDIDATE`.

The Judge receipt is
`0fb11ce5fdf83d8a4c452f41f7b1b1a64bc746a78d55ac5098ce2694e87fbbf6`.
Complete private evidence is stored at
`/Users/admin/Documents/developer-tools/giga-archaeologist-evidence/slice05-7d2cb912/judge`.

## Deterministic decision law

A normalized subject can become `VERIFIED_CANDIDATE` only when all of these
conditions are simultaneously true:

1. at least two distinct scanner tools independently report the same subject;
2. every linked observation has a complete runtime trace establishing no use;
3. all entrypoint scope is explicitly complete;
4. every supplied Git/ref/rename and comparison-repository absence proof is
   complete; and
5. no positive counterevidence or related historical variant exists.

Any positive counterevidence or history is `CONFLICT`. Any missing or partial
proof is `UNKNOWN`. Duplicate IDs, forged observation IDs, unknown records,
authority-bearing inputs, self-hash drift and cross-document hash drift refuse
the whole decision. Scanner confidence and AI prose are not Judge inputs.

`VERIFIED_CANDIDATE` grants only eligibility for Slice 06's disposable,
automatically restored quarantine canary. Every decision carries
`cleanup_permitted=false` and `deletion_permitted=false`.

## Verification and scope

Six focused Judge tests prove the complete positive path, counterevidence and
history conflicts, missing evidence, duplicate-record refusal and private
create-once output. The complete operations suite passes 61 tests; foundation,
lint, formatting, compilation and diff checks also pass.

The canonical owner remains `modules/operations/archaeologist`; no parallel
scanner or cleanup owner was created. The run did not import target code,
quarantine a file, delete anything, modify GIGA source, integrate a protected
branch or deploy.

## Knowledge graph status

The folder-navigation graph remains `STALE/PARTIAL`. Judge decisions preserve
exact source paths and evidence links that the future graph can index, but the
Judge is not a graph and neither graph state nor Graphify output can authorize
a lifecycle transition.
