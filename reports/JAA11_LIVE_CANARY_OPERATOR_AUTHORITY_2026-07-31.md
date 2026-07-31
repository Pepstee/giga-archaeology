# JAA-11 live-canary operator authority — 2026-07-31

## Operator decision

Artiom Gutu explicitly authorises one real JAA-11 application canary, with the
binding condition:

> I authorise the live canary but don't use the jobs from the top 20.

This authority is narrow and single-use. It expires after one externally
submitted application, or when the JAA-11 canary is independently certified,
whichever occurs first.

## Selection boundary

Before any external form interaction, create and hash a deterministic snapshot
of the then-current ranked eligible-job set. The chosen vacancy:

- must not occupy ranks 1–20 in that snapshot;
- must be ranked 21 or lower;
- must pass the existing eligibility and truthful-evidence gates;
- must be open and offered through an official employer or ATS route;
- must not be selected merely because it is easy to submit;
- must not already have an application receipt or duplicate application;
- must not require payment, CAPTCHA bypass, identity deception, or fabricated
  experience.

Record the ranking algorithm/version, complete ranked snapshot, selected rank,
vacancy identity, URL, retrieval time and content hashes. Ambiguous or missing
rank evidence fails closed.

## Permitted external actions

For the single selected vacancy, JAA may:

- open the official application route;
- populate fields exclusively from the approved evidence ledger;
- upload approved application artefacts;
- accept mandatory application terms required for submission while retaining
  the exact displayed terms as evidence;
- perform the final submission exactly once;
- retain the official receipt/status and bounded screenshots needed for
  certification.

Optional marketing consent must remain declined. If the route requires account
creation, login, MFA, CAPTCHA completion, payment, or facts absent from the
approved evidence ledger, fail closed without submitting and return to Fable
for a bounded ruling. Do not invent an answer or solicit an application outside
this authority.

## Assurance requirements

- Run a complete dry-run/release review before the irreversible click.
- Bind the selected vacancy, approved answers, documents, release token,
  browser actions and receipt to exact hashes.
- Prevent duplicate submission across retries, crashes and supervisor rounds.
- Preserve an append-only record of every external request and state change.
- Treat a missing or ambiguous receipt as unknown, never as success.
- Use the canary only for JAA-11 evidence and downstream certification.
- This authority does not authorise bulk applications or a second canary.

