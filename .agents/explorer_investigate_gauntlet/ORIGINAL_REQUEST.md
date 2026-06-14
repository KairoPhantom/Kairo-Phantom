## 2026-06-13T22:35:51Z

Perform a detailed codebase research for the following Kairo Phantom components:
1. WordMaster, ExcelMaster, PptxMaster (in sidecar/masters/): understand how they run document operations, how they take a scenario prompt, and how they write the output files.
2. Legal redline parser: where is it defined, how to invoke it, and how to verify tracked-change markers are present.
3. CUA gate logic: where is it defined, how to invoke it to verify if it blocks/allows based on prompt content (headless, no UI).
4. SecurityAuditor: where is it defined, how to invoke it, and how to verify strict mode blocks/allows.
5. MemSyncManager: where is it defined, how to write a preference, and how to verify recall.
6. Offline mode: where is self_check or offline mode check defined in sidecar, how does setting KAIRO_OFFLINE=1 affect it, and how does it prevent external calls?
7. Degradation: how do missing-domain errors surface (e.g., structure of the response with ok: False and error field).
8. Performance: context assembly for a 100-page document stub (where is context_assembler or similar, how to stub a 100-page document, how to time it under 2 seconds).

Provide the file paths, classes, and method signatures for each component.
Suggest a design/strategy for scripts/run_kairoreal_gauntlet.py and kairo-sidecar/tests/test_kairoreal_gauntlet.py.
Write your findings to handoff.md in your working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\explorer_investigate_gauntlet.
