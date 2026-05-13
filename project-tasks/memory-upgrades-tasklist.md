# Kairo Phantom Memory Upgrades Task List

## Phase 1: Ground-Truth-Preserving Architecture (MemMachine-Style)
### [ ] Task 1.1: Schema Update for Ground-Truth
Update `semantic_memory` table to include `full_episode` (BLOB/JSON) and `is_ground_truth` flag.
### [ ] Task 1.2: Episode Storage Logic
Modify `MemMachine::remember` to store the raw interaction (prompt + response) as ground-truth.
### [ ] Task 1.3: Contextualized Retrieval
Implement `MemMachine::recall_contextualized` which expands matches with surrounding episodes.

## Phase 2: Cognitive Forgetting Curves (Alaya)
### [ ] Task 2.1: Alaya Crate Integration
Add `alaya` crate to `Cargo.toml`.
### [ ] Task 2.2: Dual-Strength Memory Logic
Implement `storage_strength` and `retrieval_strength` in `semantic_memory` table.
### [ ] Task 2.3: Forgetting Background Task
Implement a background job that calls `alaya::forget()` to decay old memories.

## Phase 3: Multi-Granularity Memory (MemGAS Pattern)
### [ ] Task 3.1: Context Key Schema Update
Add `context_key` (e.g., slide_type, section_type) to `semantic_memory`.
### [ ] Task 3.2: Entropy-Based Routing
Implement logic to identify the most informative granularity for a given prompt.
### [ ] Task 3.3: Hierarchical Retrieval
Implement fallback logic from specific sub-context to general app-context.

## Phase 4: Dual-Channel Feedback (Meta PAHF)
### [ ] Task 4.1: Feedback Classifier
Implement a module to analyze user corrections (diffing rejected vs. rewritten text).
### [ ] Task 4.2: Feedback Channel Storage
Store explicit feedback signals (format_changed, tone_mismatch, etc.) in memory.

## Phase 5: Two-Stage Optimization Loop (MemCoE / PRIME Pattern)
### [ ] Task 5.1: MemoryOptimizer Implementation
Create `MemoryOptimizer` to track policy performance.
### [ ] Task 5.2: Policy A/B Testing
Implement background policy experiments (varying thresholds and sample sizes).
### [ ] Task 5.3: Policy Auto-Adoption
Logic to switch to the winning memory update policy automatically.

## Phase 6: Vector Activation & Final Benchmarking
### [ ] Task 6.1: Full Vector Integration
Wire `hnswlib-rs` or `faer-rs` for fast semantic search.
### [ ] Task 6.2: Final Memory Benchmark
Run `memory_benchmark` and verify score >= 0.95.
