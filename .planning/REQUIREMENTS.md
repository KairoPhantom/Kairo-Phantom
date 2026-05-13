# REQUIREMENTS: Kairo 100x Production Hardening

## R1: Security & Prompt Integrity
- **R1.1**: Implement `SentinelLeakGuard` (clawdstrike/zeph-sanitizer patterns) to prevent system prompt leakage.
- **R1.2**: Implement the `//` Delimiter Protocol for command/content separation.
- **R1.3**: Rigid XML framing for LLM prompts (`<system>`, `<document_context>`, `<user_prompt>`, `<output>`).
- **R1.4**: Output sanitization to detect and block role-playing or instruction leakage.

## R2: Universal Document Understanding
- **R2.1**: Replace `office_oxide` with `Kreuzberg` as the primary extraction backbone (97+ formats).
- **R2.2**: Integrate `spdf` for spatial fidelity in PDF extraction.
- **R2.3**: Implement structure-preserving chunking (SPIRE/text-splitter).
- **R2.4**: Support for 305 programming languages via `tree-sitter`.

## R3: Specialized Swarm Agents
- **R3.1**: Refactor into 5 specialists: Word, PPT, Excel, Design, Code.
- **R3.2**: PPT Specialist integration with `DeepPresenter` (9B model) and `open-design`.
- **R3.3**: Excel Specialist with formula sandbox and cross-sheet integrity.
- **R3.4**: Design Specialist with `Penpot` bridge and `open-pencil`.

## R4: Accuracy & Memory
- **R4.1**: `Context7` integration for ground-truth technical documentation.
- **R4.2**: `Alaya` SQLite-backed persistent memory for cross-session learning.
- **R4.3**: `Codemem` project-level discovery memory.

## R5: Production Performance
- **R5.1**: Zero-alloc async pipeline using `Lazy` global runtime.
- **R5.2**: SIMD-accelerated text diffs and token scanning.
- **R5.3**: `WGPU` native GPU rendering for effects.
- **R5.4**: Hardened `WASM` plugin sandbox with signature verification.

## R6: Verification (Gauntlet)
- **R6.1**: Success rate of 95%+ across 39 scenarios.
- **R6.2**: Chaos resilience (network drops, clipboard wipes, CPU spikes).
