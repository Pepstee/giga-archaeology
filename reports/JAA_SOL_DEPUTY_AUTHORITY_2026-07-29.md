# JAA Sol deputy authority — 2026-07-29

**Operator decision recorded:** 2026-07-29T09:07:02+01:00  
**Authority expires:** 2026-07-30T04:00:00+01:00

The operator stated:

> OK, let's arm codex to work alone until 4 am BST after which they will
> resume working together.
>
> 5.6 Sol becomes the deputy decision maker until Fable is back.

## Granted authority

Until the expiry above, `gpt-5.6-sol` may act as the sole JAA coordinator and
temporary deputy decision maker when a JAA gate would ordinarily require
Fable. It may:

- adjudicate bounded local design, implementation, testing and compatibility
  questions;
- authorise the smallest evidence-backed repair within the existing JAA build
  plan and safety boundaries;
- implement, test, commit and advance to the next dependent JAA slice when its
  deterministic gates pass;
- record a temporary Sol-deputy acceptance that permits downstream local work.

## Non-negotiable boundaries

- Every deputy decision must be append-only, exact-source bound and labelled
  `TEMPORARY_SOL_DEPUTY_PENDING_FABLE_RATIFICATION`.
- Sol must not describe its own decision as independent Fable certification.
- Existing tests, evidence requirements, auditability, safety and quality
  gates may not be weakened.
- No real job application, account creation, login, credential entry,
  CAPTCHA/MFA action, message, purchase or consequential external action is
  authorised.
- Existing JAA-11 real-canary and application-submission authority remains
  withheld.
- DFI and orchestrator production remain out of scope.

## Expiry and Fable return

At 2026-07-30T04:00:00+01:00 this deputy authority expires automatically.
Before further deputy adjudication, the supervisor must make one serialized
Fable request containing:

- this exact authority document and its SHA-256;
- every Sol deputy decision, source identity, diff, test result and receipt;
- all provisional downstream dependencies and unresolved risks.

Fable must audit, ratify, redirect or reject the provisional lineage and state
the next action. Sol then returns to coordinator/integration duty; Fable
returns as decision authority.
