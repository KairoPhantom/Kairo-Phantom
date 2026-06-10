## 2026-06-07T06:35:00Z
Objective:
Refactor the Word domain prompt builder to enforce the strict variable injection sequence required by the R1 specifications.

Target Files:
1. `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\kairo-sidecar\sidecar\masters\word_prompt_builder.py`
2. `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\kairo-sidecar\sidecar\prompt_builder.py`
3. `c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom\PROJECT.md`

Tasks:
1. In `word_prompt_builder.py`, modify the `build_word_prompt` function to format and inject prompt variables in this exact sequence:
   (1) App Context: `=== APP CONTEXT ===` containing App Name, App Type, and File Path.
   (2) Document Context: `=== DOCUMENT CONTEXT ===` containing document purpose, available styles, paragraph count, cursor position, surrounding paragraphs (JSON), and table count.
   (3) Memory Context: `=== MEMORY CONTEXT ===` containing writing preferences from MemMachine.
   (4) Classification: `=== INTENT CLASSIFICATION ===` containing classification intent.
   (5) User Prompt (Last): `USER INSTRUCTION: {user_instruction}`.
   Ensure all parameters (`user_instruction`, `context`, `mem_context`, `file_path`, `app_name`, `app_type`, `intent_classification`) are properly used and formatted.
2. In `prompt_builder.py`, modify the `build_word_prompt` wrapper function to extract the classification and file_path fields from its inputs and pass them as arguments to `_build_word` (which is `build_word_prompt` from `word_prompt_builder.py`).
3. Run the pytest suite (`python -m pytest kairo-sidecar`) to verify that your refactored code passes all existing tests.
4. Run the PR gate runner (`python kairo-sidecar/pr_gate_runner.py`) to verify that the automated gates are not broken by the prompt change.
5. Update `PROJECT.md` at the repository root to mark Milestones 4, 5, and 6 as DONE, and Milestone 7 as IN_PROGRESS.
6. Write a handoff report documenting the changes and outcomes.
