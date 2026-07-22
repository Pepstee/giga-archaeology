# Selective deployment contract (staged, not deployed)

ECC's installer separation is useful, but its installer is not imported. Giga-user should preserve
the following smaller contract:

1. **Plan is read-only.** Resolve exact source hashes, destinations, overwrites, removals,
   prerequisites and rollback before changing state.
2. **Apply is explicit.** The applied plan has an immutable ID and cannot silently resolve a newer
   upstream commit.
3. **State is complete.** Record installed bytes/hashes, prior state, source commit, adapter state,
   verification commands and operator decision.
4. **Repair is bounded.** Repair may touch only paths owned by that install-state record and must
   reject traversal or symlink escape.
5. **Uninstall preserves neighbours.** Remove only recorded owned artifacts and restore recorded
   prior state where safe.
6. **Updates are candidates.** Fetch and diff are automatic-safe; merge, apply and promotion are
   never automatic.

This adapts the architecture of ECC's `install-plan.js`, `install-apply.js`, install-state and
path-safety modules at commit `96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`. The ECC implementation
itself remains reference-only because it targets global harness homes and overlaps existing
giga-user governance.
