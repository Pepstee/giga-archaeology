# Human artifact-review and approval protocol (staged, not deployed)

Portable findings from ECC Plan Canvas:

1. Review an immutable or hash-addressed artifact, not an unbound chat description.
2. Feedback is structured as comments, anchored annotations and a distinct verdict.
3. Verdicts are `approve`, `request-changes` or `end-without-approval`; silence and session closure
   are not approval.
4. Feedback delivery is durable and deliver-once/drain-once so interrupted polling does not lose or
   duplicate operator input.
5. User-ended sessions remain ended unless explicitly reopened.
6. Edits create a new artifact hash and therefore require a new verdict bound to that version.
7. A browser, chat panel or terminal is only a review surface. The authority comes from the
   version-bound human receipt, not the UI event alone.
8. Local review servers, if ever used, must remain loopback-only, constrain artifact paths and
   defend Host/Origin boundaries. No server is imported here.

Source: ECC `docs/design/plan-canvas.md` at commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`.
