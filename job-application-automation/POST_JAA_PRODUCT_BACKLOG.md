# Post-JAA product backlog

## Dubbing Studio release hardening

**Status:** DEFERRED UNTIL JAA IS FINISHED  
**Priority after JAA:** first product-polish task  
**Decision date:** 22 July 2026

The public GitHub baseline has been placed on the UK laptop at:

`C:\Users\gutua\Documents\Projects\dubbing-studio`

Pinned source:

- Repository: `https://github.com/Pepstee/dubbing-studio`
- Commit: `7dcfd63ef1239eed176e8725a9f790164936a0ca`
- Retrieval marker: `GITHUB_SOURCE.txt` in the UK-laptop checkout

Do not send this project back through the active JAA factory or let it compete for JAA capacity.
Resume only after JAA completion.

### Known baseline

- 709 tests pass on the audited public checkout.
- Real CLI synthesis produced a timeline-correct 17-second WAV on macOS.
- The production tree has real macOS `say` and Piper backends; the obsolete `tts_studio` and
  shipped mock backend criticised by the 9 June ledger are absent.
- The real web acceptance currently fails because `/dub` returns an HTML result page while
  `acceptance.py` still attempts to parse that response as JSON. The endpoint itself returned
  HTTP 200 and rendered audio before the harness failed.

### Post-JAA finish gate

1. Reconcile the pulled public baseline with any surviving pre-format/full archive on the UK
   laptop; preserve both before choosing a canonical branch.
2. Repair the CLI/web acceptance contract and require the real acceptance script to exit zero.
3. Add Windows-capable real synthesis or clearly document the supported runtime boundary; do not
   pretend the macOS `say` backend works on the UK Windows host.
4. Add GitHub Actions for lint and the full deterministic test suite.
5. Replace Flask's development server for a release deployment, or explicitly scope the product
   as a local desktop/developer MVP.
6. Add a licence, screenshots/demo recording, release notes and a tagged release.
7. Run an operator acceptance session and record explicit sign-off separately from automated tests.
8. Only then update LinkedIn/GitHub portfolio language from “working MVP/factory output” to a
   finished released product.

This backlog is release hardening, not a declaration that the product was never finished. Artiom
previously described Dubbing Studio as finished on another computer; the purpose here is to recover,
reconcile and release the strongest surviving version with current evidence.
