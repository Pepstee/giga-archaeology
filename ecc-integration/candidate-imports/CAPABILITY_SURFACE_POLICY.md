# Capability surface and token-tax policy (staged, not deployed)

Choose the narrowest surface that preserves correctness:

| Need | Preferred surface |
|---|---|
| Deterministic invariant on every matching path/event | deterministic gate or scoped rule |
| Cheap one-shot local transformation/check | local CLI or repository script |
| On-demand playbook or judgement-heavy workflow | skill |
| Narrow remote step within a larger workflow | direct API adapter |
| Long-lived, stateful, structured, repeated cross-client interaction | MCP |

Decision order:

1. Can deterministic code do it reliably? Use that first.
2. Does it need to be always-on? Use a narrow gate, not a large prompt.
3. Is it guidance required only for some tasks? Load it on demand.
4. Does it genuinely benefit from a persistent structured server? Only then use MCP.

Every persistent connector pays four taxes: tool-schema tokens, runtime operations, supply-chain
surface and credential/privacy exposure. Popularity alone does not justify that tax. Prefer a CLI
or direct adapter for stateless request/response work.

Workspace audits must distinguish:

- available and usable now;
- available only as a primitive without an operator workflow;
- missing and requiring integration.

They may report secret/key names and whether configuration exists, never secret values.

Sources: ECC `docs/capability-surface-selection.md`, `docs/MCP-CONNECTOR-POLICY.md`, and
`skills/workspace-surface-audit/SKILL.md` at commit
`96789caaf90501ff9b55bf1b00f1c28cf3fccbeb`.
