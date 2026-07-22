# GitHub portfolio audit

**Account:** [Pepstee](https://github.com/Pepstee)

**Audit date:** 22 July 2026

**Decision:** keep three flagship LinkedIn projects; use selected repositories as supporting proof.

## Verdict

Do not replace the Microsoft Teams Transcript Extractor with another repository simply to keep four projects. The strongest immediate slate is:

1. Market Aligner
2. Multi-agent software factory / Orchestrator
3. SCAFAD

Three coherent projects are stronger than a longer list of disconnected prototypes. The public GitHub account does contain two promising candidates, but neither should be promoted as an independent flagship yet.

## Strongest additional candidates

### Dubbing Studio

Repository: [Pepstee/dubbing-studio](https://github.com/Pepstee/dubbing-studio)

This is the strongest current public secondary codebase. It has a composable subtitle-to-audio pipeline, pluggable speech backends, timing and assembly logic, web limits, a CLI and a large test suite. The audited checkout passed 709 tests. Structural analysis found 135 code nodes and 505 relationships, centred on the pipeline, backend interface, segment model, aligner and assembler.

The limitation matters: 89 of the 98 commits are authored as `orchestrator`, with another three attributed to `Overseer`. That makes Dubbing Studio strong evidence that the software factory can produce and refine a non-trivial system. It does not automatically establish that Artiom personally implemented every component.

Artiom confirmed on 22 July 2026 that Dubbing Studio was produced fully autonomously and had been
finished on another computer. The public checkout was re-audited that day: all 709 tests pass, real
CLI synthesis produces a timeline-correct WAV, and the obsolete shipped mock/dead duplicate criticised
by the 9 June ledger is absent. The web product also renders audio, but its real acceptance script is
stale: `/dub` now returns an HTML result page while `acceptance.py` expects JSON. The public baseline at
commit `7dcfd63ef1239eed176e8725a9f790164936a0ca` was copied to the UK laptop under
`C:\Users\gutua\Documents\Projects\dubbing-studio`; post-JAA reconciliation and release hardening are
tracked in `POST_JAA_PRODUCT_BACKLOG.md`.

Decision: include it in the Orchestrator case study as a factory output and describe the current
public state as a working MVP. After JAA, reconcile any surviving fuller archive, repair the web
acceptance contract, add CI and release evidence, and record explicit operator sign-off. It can receive
a separate Projects entry after that release-hardening gate, but the description must state that it
was autonomously produced through Artiom's software factory and distinguish product direction, system
operation and validation from direct implementation.

### Learning Accelerator

Repository: [Pepstee/learning-accelerator](https://github.com/Pepstee/learning-accelerator)

This is the best strategic candidate for future promotion. It combines LLM-assisted question generation, spaced repetition, review sessions, persistence and analytics. The audited checkout passed 847 tests, although it produced Python datetime deprecation warnings. Structural analysis found 124 nodes and 414 relationships across the CLI, models, review session, LLM interface, generator and scheduling logic.

All 58 commits are attributed to `orchestrator`, and there is no verified deployment or learner outcome. As it stands, it is a tested factory prototype.

Decision: turn it into a real Excellence Exalted product. Pilot it with one or more learners, record the input material, usage period, feedback and measurable outcome, and document Artiom's role. At that point it can become the fourth flagship project and a legitimate company software delivery.

## Repositories that support existing flagship projects

- [Pepstee/claude-orchestrator-deprecated](https://github.com/Pepstee/claude-orchestrator-deprecated) is substantial evidence for the software-factory architecture, but the repository name and public hygiene make it a poor recruiter landing page. Publish a clean Orchestrator v3 repository or case study instead.
- [Pepstee/scafad-delta](https://github.com/Pepstee/scafad-delta) supports SCAFAD. It is part of that research project, not a separate portfolio item. Add a root README that explains provenance, scope, how to run it and which claims are research-only before featuring it.

## Do not feature

- `Teams-Transcript-Extractor`, `Packet_Sniffer`, `webscraper`, `Trivia-Basic` and `Liltimer`: too small for a flagship slot.
- `8-puzzle`, `Dice-Roller`, `Mobile-BistroRater`, `Mobile-ChatApp`, `Robotics` and `language_S`: useful learning evidence, but they read as coursework beside the stronger systems.
- `NLPartner-v3.0`: empty.
- `deal-sniper`, `edge`, `writing-assistant`, `travel-designer` and `japan-2026-trip`: prototypes or specialised artefacts that fragment the AI automation narrative. `edge` has a passing suite, but its bias and propaganda claims would need a credible evaluation before promotion. The `deal-sniper` checkout also collected failing acceptance tests from an embedded `projects/edge` path, and the writing-assistant acceptance demo depended on an unavailable external Claude CLI call.

## GitHub hygiene issues

These matter more than adding another LinkedIn project:

1. The authenticated GitHub profile has no display name. Add `Artiom Gutu`, a short AI automation and Python bio, the UK location and the LinkedIn URL.
2. Create a profile README and pin the public proof for the three flagship stories when those artefacts are ready.
3. Review [Pepstee/NLPartner](https://github.com/Pepstee/NLPartner) immediately. The public repository contains a roughly 10.6 MB parsed-conversation JSON file and a 6.6 MB sales-conversation CSV covering 3,411 conversations, with no README explaining source, licence, consent or anonymisation. Unless public-release rights are documented, make the repository private and remove the raw dataset from Git history before using the account in applications.
4. Clean recruiter-facing repositories of local settings, generated coverage files, databases and internal orchestration artefacts. The deprecated orchestrator repository needs this review before it is linked publicly.
5. Add concise READMEs, licences, setup commands, screenshots and continuous integration to every repository selected for public proof.

## Corrected portfolio strategy

Use projects for depth and case studies for breadth:

- LinkedIn Projects: Market Aligner, Orchestrator and SCAFAD.
- Orchestrator case study: show Dubbing Studio as one inspected output and state exactly what the agents did, what Artiom specified, what he reviewed and which tests passed.
- Excellence Exalted case study: deploy Learning Accelerator with real learners, then promote it using verified usage and outcomes.
- GitHub pins: only clean, documented repositories that a recruiter can run or inspect without guessing.

This preserves a single career story: Artiom builds and evaluates reliable AI automation systems, then applies them to concrete domains such as job intelligence, serverless telemetry and education.
