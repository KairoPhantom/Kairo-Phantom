## 2026-06-07T08:33:04Z

Empirically verify the prompt variable ordering, JSON reminder formatting, and LLM caller retry prompt logic.
1. Write a script to programmatically instantiate all 12 domain prompt builders and assert that the generated prompts:
   - Order variables as App Context -> Document Context -> Memory Context -> Intent Classification -> User Instruction.
   - Contain the exact JSON reminder string: 'REMINDER: Your entire response must be a single JSON object. First character must be {. Last character must be }.' immediately preceding the User Instruction.
2. Test the JSON Decode Error retry logic in `llm_caller.py` by mocking the HTTP response to return invalid JSON on the first attempt and verify the correct retry request payload is sent.
3. Run pytest `python -m pytest kairo-sidecar/tests/` to make sure everything passes.
Write your findings to `.agents/challenger_2/handoff.md`.
