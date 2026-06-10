## 2026-06-07T07:58:50Z
Audit the codebase in c:\Users\praja\OneDrive\Desktop\test-env\repositories\kairo-phantom for compliance with v3.9.0 requirements.
Specifically:
1. Run the test suite by executing `python -m pytest kairo-sidecar/tests/` and see the results (how many tests pass, fail, or error).
2. Check if the prompt variable injection order (App context, Doc context, Mem context, Classification, User prompt last) is enforced for all domain master prompts (Word, Excel, PowerPoint, Code, PDF, Browser, Terminal, Email, Notes, Design, Media, and Data).
3. Check if the JSON reminder 'REMINDER: Your entire response must be a single JSON object. First character must be {. Last character must be }.' appears immediately before the user instruction in all domain master prompts.
4. Check if `llm_caller.py` strips markdown fences and retries once with the exact message 'Your previous response was not valid JSON. Output ONLY the JSON object, nothing else.' when `json.JSONDecodeError` is raised.
5. Check if `WordWriter._insert_paragraph()` uses XML-level `ref_para._element.addnext(new_para._element)` and operations are sorted in reverse index order.
6. Check if `WordWriter.apply_operations()` uses the tmp+rename pattern (`.kairo_tmp` saved and then `os.replace` to original) with a `.kairo_bak` backup.

Create a directory `.agents/explorer_v2_1/` first and write your results to `.agents/explorer_v2_1/analysis.md`, then send a message back with the path.
