# Blind Opus portfolio review protocol

Date: 25 July 2026

## Question

How would a technically competent employer evaluate each orchestrator repository if it
appeared in a candidate's portfolio without the surrounding GIGA narrative?

## Experimental arms

| Arm | Repository snapshot | Commit |
|---|---|---|
| V2 | clean clone of frozen `agentic-orchestrator` | `32efb0797905078a6917d748ce93efd46f7527be` |
| V3 | clean clone of frozen production `orchestrator-v3` | `35efb19b07867bb58e1288479513078cf9ab65e4` |

The arms are evaluated independently. Neither reviewer is told that another repository,
version, reviewer, comparison, GIGA programme, efficiency audit, JAA project, DFI programme,
or prior verdict exists.

## Independence controls

- Two distinct `claude --print` invocations pinned to the explicit provider model identifier
  `claude-opus-5`. The generic `opus` alias is not accepted as proof of model identity.
- `--safe-mode`: disables auto-memory, `CLAUDE.md` discovery, hooks, plugins, skills, MCP,
  workflows and other customisations.
- `--no-session-persistence`: neither session is stored or resumable.
- Unique ephemeral home directory per invocation containing only the OAuth credential file.
- No user history, Claude memory, GIGA files, other orchestrator repository, external reports
  or web access is mounted into either sandbox.
- Each immutable Git clone is mounted read-only at `/workspace`; `/tmp` is the only writable
  analysis area.
- The same prompt bytes and tool policy are used for both arms.
- Outputs, stderr, timing, exit status, prompt hash, source commit and source cleanliness are
  recorded independently.
- The two outputs remain separate. No synthesis or ranking is supplied to either reviewer.

## Employer-review rubric supplied to each reviewer

The reviewer acts as a senior engineering hiring panel assessing an anonymous portfolio
submission, not as the candidate's assistant. It must:

1. inspect the repository rather than trust its README;
2. distinguish demonstrated evidence from claims;
3. assess architecture, implementation, tests, reliability, operability, documentation,
   originality, maintainability and commercial readiness;
4. identify over-engineering, generated-code smell, unverifiable claims and authorship or
   comprehension risk;
5. cite concrete paths, symbols, tests and commits;
6. state what the candidate would have to explain or reproduce in an interview;
7. score the artifact and issue role- and level-specific hiring recommendations;
8. recommend the smallest portfolio improvements with the highest employer impact; and
9. disclose commands run, failures and evidence limitations.

No candidate biography, intended career narrative or desired verdict is supplied.

## Interpretation rule

The reports measure portfolio signal from two clean repository snapshots. They do not prove
authorship, production deployment, business value or the candidate's live understanding.
Those are deliberately included as interview risks for the employer-reviewer to assess.
