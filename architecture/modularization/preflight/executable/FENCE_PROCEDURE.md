# Live-writer fence procedure

This procedure is mandatory immediately before a root migration batch. The
Wave 0E manifest is a point-in-time observation and is not itself a fence.

1. Acquire the atomic root-move lock defined in
   `../authority/ROOT_MOVE_LOCK.md`. Bind host, boot identity, PID, root inode,
   branch, HEAD, worktree digest, authority-map digest, and batch ID.
2. Regenerate `WORKTREE_PROMOTION_ALLOWLIST.json` and
   `LIVE_WRITER_GATE.json`; validate both. Any classification drift or
   repository-bound process fails closed.
3. Inspect launchd and process command lines again. A related service is
   stopped only if its executable or working directory resolves inside this
   repository. Record the exact label, prior state, stop result, and restart
   command in the batch receipt.
4. Do not stop Codex, Claude, unrelated Market Aligner, Dubbing Studio, or
   independent-workspace processes merely because their names are similar.
5. Take a fresh recoverability seal after all preflight output is final.
6. Execute exactly one validated migration batch. No other agent may write
   root paths while the lock exists.
7. Run compatibility updates, focused tests, full tests, immutable-evidence
   checks, and the root-layout audit before retiring the source path.
8. If any check fails, follow the batch's rollback checks and preserve the
   failed candidate plus receipt. Never delete a stale lock without the
   recovery receipt required by the lock contract.

Current policy is fail-closed: an observed repository-bound writer, worktree
drift, missing source, changed destination, or hash mismatch prevents a move.
