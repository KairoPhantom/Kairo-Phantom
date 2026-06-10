## 2026-06-07T08:21:05Z
Implement the prompt variable injection order, JSON reminder formatting, and LLM caller retry logic fixes to resolve the remaining non-compliant areas.

Target Files:
1. `kairo-sidecar/sidecar/masters/other_masters.py`
2. `kairo-sidecar/sidecar/masters/word_prompt_builder.py`
3. `kairo-sidecar/sidecar/llm_caller.py`

Tasks to perform:
1. In `other_masters.py`, refactor the prompt builder logic for the following masters:
   - BrowserMaster
   - TerminalMaster
   - EmailMaster
   - NotesMaster
   - DesignMaster
   - MediaMaster
   - DataMaster
   Ensure they all:
   - Formally partition active prompt variables into separate blocks: `=== APP CONTEXT ===`, `=== DOCUMENT CONTEXT ===`, `=== MEMORY CONTEXT ===`, and `=== INTENT CLASSIFICATION ===`.
   - Inject context blocks in the exact order: `App context` -> `Doc context` -> `Mem context` -> `Classification` -> `User prompt last`.
   - Place the exact JSON reminder string:
     `REMINDER: Your entire response must be a single JSON object. First character must be {. Last character must be }.`
     immediately before the user instruction block.
   - End the prompt with:
     ```
     USER INSTRUCTION: {user_instruction}
     OUTPUT (JSON only):
     ```
     (Note: for MediaMaster and DataMaster, change 'User Instruction' to uppercase 'USER INSTRUCTION', add the intent classification block if missing, and ensure the prompt ends with 'OUTPUT (JSON only):').
   - In NotesMaster, resolve the duplicate/broken string literal syntax bug at the end of the return statement.

2. In `word_prompt_builder.py`, check that the prompt formatting conforms exactly to the order and reminder placement as the other master prompts.

3. In `llm_caller.py`, check the JSONDecodeError retry. Ensure that on the first attempt, if a `json.JSONDecodeError` is raised, it retries with the exact text:
   `Your previous response was not valid JSON. Output ONLY the JSON object, nothing else.`
   Ensure it does not append dynamic details (like {decode_err}) to the prompt on decode error, but rather uses that exact literal string for the retry. (Wait, check if it's already implemented; if not, modify it to be exactly correct).

4. Run the full pytest suite `python -m pytest kairo-sidecar/tests/` to verify that all 261+ tests pass cleanly after your changes.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work.

Write your handoff report to `.agents/worker_1/handoff.md` with:
- Detailed explanation of what was changed and why.
- Output/logs of the test execution showing passing tests.
- Verify that no other code files are modified.

## 2026-06-07T08:30:33Z
**Context**: Checking status of implementation tasks.
**Content**: Please report your current progress on prompt compliance and LLM caller retry logic implementation.
**Action**: Reply with your current status and estimated time of completion.
