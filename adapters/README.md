# GIGA adapter evidence

Adapter manifests are capability claims, not executable configuration. The deterministic compiler
validates exact fields, root-contained proof files, SHA-256 hashes, timestamps, authority and
freshness. It never executes `onramp` or `verification_commands` strings.

Compile the registry with:

```bash
python3 scripts/compile_adapter_evidence.py
```

An adapter that becomes stale is reduced to `reference-only` in the compiled registry. Missing,
malformed, duplicated, future-dated or path-escaping evidence fails closed. An adapter manifest
does not grant tool access and cannot promote a SkillTree capability by itself.

An adapter registry must not hash an output that consumes that same registry. This prevents a
circular hash dependency in which compiling either file immediately invalidates the other.
