# Independent-product integration boundary (staged, not deployed)

An external product can contribute useful workflows without being absorbed into giga-user.

Every integration separates:

- a public/local path that works without private credentials;
- a gated path for live account data or actions;
- ownership, billing and support responsibilities;
- sanitized fixtures and public documentation;
- evaluation, risk and authority gates;
- receipts proving any completed external action.

Private keys, account state and proprietary strategy remain outside public workflows and prompts.
Patterns learned from real usage may return only as sanitized examples, tests or generic contracts.
An integration does not transfer product ownership, source-of-truth status or action authority.

This reinforces giga-user's existing Market Aligner boundary: consume stable events and receipts
through adapters later; do not merge the active product.

Source: ECC `docs/architecture/platform-value-loop.md` at commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`.
