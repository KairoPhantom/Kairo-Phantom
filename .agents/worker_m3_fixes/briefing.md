# BRIEFING — 2026-06-08T16:17:41Z

## Mission
Resolve the Windows encoding issue in the DSPy prompt optimizer script and implement clean file re-indexing on file modifications in the Document Graph memory.

## 🔒 My Identity
- Archetype: worker_m3_fixes
- Roles: implementer, qa, specialist
- Working directory: c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\.agents\worker_m3_fixes
- Original parent: b5df8d12-1e21-4385-bae1-74656070bebd
- Milestone: Milestone 3 Fixes

## 🔒 Key Constraints
- CODE_ONLY network mode: No external website/service access, no curl/wget/etc. targeting external URLs.
- Only write to our own folder .agents/worker_m3_fixes/ for agent metadata, read any folder. No source code/tests/data files in .agents/.

## Current Parent
- Conversation ID: b5df8d12-1e21-4385-bae1-74656070bebd
- Updated: not yet

## Task Summary
- **What to build**: 
  - Fix Windows encoding error in `scripts/training/dspy_prompt_optimizer.py` by adding `encoding="utf-8"` and `errors="ignore"` to `subprocess.run`.
  - Fix/implement clean file re-indexing on file modification in `phantom-core/src/memory/document_graph.rs` by checking stored file content against newly extracted text, deleting old node and edges if they differ, and re-indexing.
- **Success criteria**: 
  - All Rust tests pass (`cargo test`).
  - Recall benchmark test runs successfully (`cargo test --test kmb1_benchmark`).
  - DSPy prompt optimizer script runs without encoding exceptions on Windows.
- **Interface contracts**: `scripts/training/dspy_prompt_optimizer.py` and `phantom-core/src/memory/document_graph.rs`
- **Code layout**: Standard workspace layout for kairo-phantom repository.

## Key Decisions Made
- Added `encoding="utf-8"` and `errors="ignore"` to the `subprocess.run` invocation inside `scripts/training/dspy_prompt_optimizer.py` to prevent Windows console encoding crashes when benchmark output contains emojis/non-ASCII characters.
- Modified the indexing logic in `phantom-core/src/memory/document_graph.rs` to extract text first, query stored content, and perform a conditional delete of document nodes and outbound edges if the file text changed.
- Added a robust unit test `unit_document_graph_reindexing_on_modification` inside `phantom-core/tests/layer1_unit_tests.rs` with a state-aware mock backend to verify edge/node database cleanup and replacement when files are modified.

## Artifact Index
- `.agents/worker_m3_fixes/handoff.md` — The handoff report documenting observations, logic, conclusions, and verification methods.

## Change Tracker
- **Files modified**:
  - `scripts/training/dspy_prompt_optimizer.py` — Add unicode/encoding args to subprocess.run.
  - `phantom-core/src/memory/document_graph.rs` — Implement file-change-aware node/edge deletion and re-indexing.
  - `phantom-core/tests/layer1_unit_tests.rs` — Add unit test verifying change-aware document graph re-indexing.
- **Build status**: Passed
- **Pending issues**: None

## Quality Status
- **Build/test result**: Passed. All 15 unit tests in layer1_unit_tests, all 3 kmb1_benchmark tests, and the cargo workspace tests pass.
- **Lint status**: Clean (no new lint errors introduced)
- **Tests added/modified**: `unit_document_graph_reindexing_on_modification` verifying correct cleanup of document graph edges and nodes on content change.

## Loaded Skills
- None
