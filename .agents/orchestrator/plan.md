# Project Implementation Plan - Kairo Phantom Advanced Capabilities Integration

This plan covers integrating and refining the three advanced capabilities (Autonomous Skill Creation, Document Graph Memory, and Feynman Verification Agent) into Kairo Phantom following strict architectural boundaries, and updating licensing attribution.

## Gaps Identified for Implementation

### Gap 1: R1 Autonomous Skill Creation Overlay Text
- **File**: `phantom-core/src/main.rs`
- **Action**: Change the overlay body text shown on line 3463 from `"Task complete! Press Tab to save as a custom skill 🌟"` to exactly: `"Save this workflow as a skill? [Tab] Yes"`.

### Gap 2: R2 Document Graph Memory - petgraph In-Memory Graph Operations
- **File**: `phantom-core/src/memory/document_graph.rs`
- **Action**: Modify `query_entity` and `enrich_context` (and any other graph query logic) to utilize `petgraph`'s `DiGraph` for in-memory graph operations (e.g. node lookup, neighbor traversal, edge weight lookup) rather than querying SQLite via raw JOIN queries directly. SQLite should only be used as database persistence (e.g. indexing, loading nodes/edges to `DiGraph`, and fetching text content by ID).

### Gap 3: R2 Document Graph Memory - Intent Gate Integration
- **Files**: 
  - `phantom-core/src/intent_gate.rs`
  - `phantom-core/src/main.rs`
  - `phantom-core/tests/pipeline/test_three_layer_pipeline.rs`
- **Action**:
  1. Add `graph_context: Option<String>` to `IntentAnalysis` struct in `intent_gate.rs`.
  2. Modify `IntentGate::analyze` signature in `intent_gate.rs` to take `document_graph: Option<&crate::memory::document_graph::DocumentGraph>`.
  3. Inside `IntentGate::analyze`, if `document_graph` is provided, query the graph using `enrich_context` to populate `graph_context`.
  4. Update all `IntentGate::analyze` call sites in `intent_gate.rs` tests, `main.rs`, and `test_three_layer_pipeline.rs` to pass the appropriate `document_graph` reference (or `None`).

---

## Milestones

### Milestone 1: Initial Exploration, Test Baseline & Licensing
- **Status**: DONE (Baseline verified via `worker_baseline` and `explorer_1/3`, licensing verified in `THIRD_PARTY_NOTICES.md`).

### Milestone 2: Implementation of Gaps (R1 Prompt, R2 Petgraph, R2 Intent Gate)
- **Status**: DONE (Implemented and verified via `worker_m2_gaps` with passing tests/benchmarks).

### Milestone 3: Additional Bug Fixes (Subprocess Decode Error & Document Graph Re-indexing Gap)
- **Status**: DONE (Resolved Windows encoding issue in `dspy_prompt_optimizer.py` and implemented re-indexing in `document_graph.rs` on file modifications, verified via new unit tests).

### Milestone 4: E2E and Compliance Audit
- **Status**: DONE (Forensic compliance audit successfully passed with a CLEAN verdict, all tests passed, and memory benchmark score at 1.0 verified).
