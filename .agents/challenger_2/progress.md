# Progress Log

Last visited: 2026-06-07T08:33:04Z

- [x] Search the repository to identify the location of the 12 domain prompt builders and `llm_caller.py`.
- [x] Understand the structure and variable ordering of the domain prompt builders.
- [x] Verify if they order variables as: App Context -> Document Context -> Memory Context -> Intent Classification -> User Instruction.
- [x] Verify if they contain the exact JSON reminder string: 'REMINDER: Your entire response must be a single JSON object. First character must be {. Last character must be }.' immediately preceding the User Instruction.
- [x] Understand how `llm_caller.py` implements JSON Decode Error retry logic.
- [x] Write a verification script to instantiate prompt builders, test variable ordering, and assert JSON reminder string and its placement.
- [x] Write a pytest or mock-based test to verify the JSON Decode Error retry logic in `llm_caller.py` is working as expected (mock HTTP response to return invalid JSON on first attempt and check retry request payload).
- [ ] Run pytest to verify all sidecar tests pass.
- [ ] Document findings in handoff report.
