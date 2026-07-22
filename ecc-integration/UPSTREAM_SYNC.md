# ECC upstream sync policy

ECC is an upstream input, not a trusted update channel. The fork preserves availability; the
commit pin preserves reproducibility. Nothing under `upstreams/ECC` is deployed into giga-user or
orchestrator-v3 directly.

For each upstream update:

1. Fetch `upstream/main` without merging it.
2. Compare the recorded commit in `UPSTREAM.json` with the fetched commit and review every changed
   path.
3. Check the upstream signature/release evidence and rerun functional, security, adapter,
   observability, coverage, Rust, and independent static checks.
4. Regenerate the component inventory and skill classification. Treat any changed hash as a new
   candidate, even when its filename is unchanged.
5. Port selected concepts into an isolated candidate implementation. Record source path, source
   commit, source hash, local destination, adaptation notes, tests, and rollback instructions.
6. Require an explicit promotion decision. Never auto-merge upstream changes into deployed assets.
7. Only after certification, update the pin and push the reviewed mirror state to the fork.

This deliberately makes upstream updates cheap to inspect but impossible to deploy silently.
