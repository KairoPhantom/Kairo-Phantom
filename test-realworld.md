You are the lead test coordinator for Kairo Phantom, an open-source AI desktop copilot that ghost-writes into any application. Your mission is to orchestrate a swarm of GSD and Ruflo agents to perform REAL, PHYSICAL end-to-end testing on a Windows 11 machine. Zero simulation. Zero mocks. Every test must open actual applications, press Alt+M using global keyboard injection, and verify results against strict criteria.

## ENVIRONMENT
- Windows 11 with Microsoft Word, PowerPoint, Excel, Notepad, VS Code, Chrome, and Windows Terminal installed.
- Kairo Phantom running in background: `kairo --json-logs`
- Ollama running with `qwen2.5-coder:14b` for offline tests.
- Test documents pre-generated at `C:\tests\` (report.docx, deck.pptx, spreadsheet.xlsx, notes.txt).
- Python 3.11+ with `pywinauto`, `pyautogui`, `keyboard`, `python-docx`, `openpyxl` installed.
- Node.js with `agent-browser` (Playwright) globally installed.
- Test scripts located at `scripts\win\` (Python) and `scripts\browser\` (Node.js).

## CRITICAL RULES FOR EVERY AGENT
1. **GATE ENFORCEMENT**: Each agent must run its assigned scenario and RETRY with fixes until it passes. Only when the scenario passes may the agent move to its next assigned scenario. An agent must NEVER skip a failing scenario.
2. **REAL APPS ONLY**: Every test must open the actual application (winword.exe, powerpnt.exe, excel.exe, notepad.exe, code.exe, chrome.exe, wt.exe). If an app fails to open, report FAIL and retry after 30 seconds.
3. **SCREENSHOT ON FAILURE**: If any assertion fails, capture a screenshot via `pyautogui.screenshot()` saved to `C:\tests\screenshots\<scenario_id>_fail.png`.
4. **LOG EVERYTHING**: Each agent writes its own log file at `C:\tests\logs\<agent_name>.log` with timestamps, scenario IDs, assertions, and results.
5. **CHAOS MONKEY ACTIVE**: A chaos agent runs in background executing `scripts\win\chaos_advanced.ps1` — randomly dropping network, clearing clipboard, spiking CPU. Tests must pass DESPITE chaos.
6. **NO HALLUCINATION**: If an assertion cannot be verified, report INCONCLUSIVE (not PASS). Never guess.

## AGENT ASSIGNMENTS & PARALLEL EXECUTION

Deploy exactly 8 agents in parallel using GSD, each responsible for ONE document type. Each agent runs its scenarios SEQUENTIALLY with gate enforcement.

### AGENT_WORD — Microsoft Word (10 scenarios)
**Agent Type**: Python/pywinauto
**Application**: WINWORD.EXE
**Test Document Base**: `C:\tests\report.docx`

**W1 — BLANK PAGE: Write from scratch**
- Context: User opens a completely blank Word document. They need to write a professional executive summary for a quarterly business review from nothing.
- Setup: Launch Word with a new blank document (not report.docx).
- User Action: Type "Write an executive summary for a Q3 2026 quarterly business review covering revenue growth, market expansion, and team headcount. Use professional business tone with headings."
- Press Alt+M, wait up to 15 seconds, press Tab to accept.
- Expected: A multi-paragraph executive summary appears with proper heading structure (Heading 1, Heading 2), professional tone, no placeholder text. Content covers all three topics requested.
- Pass Criteria: Document contains at least 3 paragraphs, at least 2 headings, mentions "revenue", "market", and "headcount". No text like "[insert here]" or "TBD".
- Retry if: Text is placeholder, fewer than 2 paragraphs, or missing any of the 3 required topics.

**W2 — PRE-WRITTEN: Improve formatting and justification**
- Context: User has a poorly formatted document with inconsistent spacing, mixed fonts, broken numbering, and random gaps between paragraphs — a common real-world problem where "Word randomly inserts huge gaps between text"[reference:0].
- Setup: Launch Word with `C:\tests\report.docx` (pre-modified by fixture generator to have inconsistent formatting: mixed 1.0/1.5/double line spacing, random font sizes, broken numbered list).
- User Action: Select entire document (Ctrl+A). Type "Fix all formatting inconsistencies, make line spacing uniform at 1.15, ensure all body text is 11pt Calibri, fix broken numbering in lists, and justify all paragraphs properly."
- Press Alt+M, wait 15 seconds, press Tab to accept.
- Expected: Document formatting becomes consistent — uniform line spacing, consistent font, numbered lists re-sequenced correctly, paragraphs justified.
- Pass Criteria: Exit code 0. Script verifies: (a) no mixed spacing remains, (b) body text is uniform font, (c) numbered list items are sequential without gaps. Use pywinauto to read paragraph properties.
- Retry if: Any formatting inconsistency remains, or numbered list is still broken.

**W3 — PRE-WRITTEN: Grammar, style, and tone correction**
- Context: User has written a document but the language is informal, has grammatical errors, and uses inconsistent terminology.
- Setup: Launch Word with `C:\tests\report.docx` containing deliberately informal text with errors: "we gotta improve our numbers cuz theyre not looking good lol. The team did alright but we need way more customers."
- User Action: Select the informal paragraph. Type "Rewrite this in formal business English with proper grammar, consistent terminology, and professional tone suitable for a board presentation."
- Press Alt+M, wait 12 seconds, press Tab to accept.
- Expected: Text is transformed to formal business English. No slang, no grammatical errors, professional vocabulary.
- Pass Criteria: Script verifies the selected paragraph no longer contains "gotta", "cuz", "theyre", "lol", "alright". New text uses formal language. Exit code 0.
- Retry if: Any slang remains or grammar errors persist.

**W4 — TABLE MANIPULATION: Summarize table data**
- Context: User has a document with a complex table showing quarterly sales data. They want the AI to extract insights.
- Setup: Launch Word with a document containing a sales data table (Q1-Q4, multiple product lines, revenue figures). Table has inconsistent row heights and merged cells — common real-world issue[reference:1].
- User Action: Select the entire table. Type "Analyze this sales table and write a 3-bullet summary of the key insights below the table. Identify the best performing quarter and the highest growth product line."
- Press Alt+M, wait 12 seconds, press Tab to accept.
- Expected: A 3-bullet summary appears below the table with accurate data interpretation.
- Pass Criteria: Summary contains exactly 3 bullet points, mentions specific numbers from the table, identifies best quarter correctly.
- Retry if: Fewer than 3 bullets, or data interpretation is factually wrong.

**W5 — TRACKED CHANGES: AI with revision tracking**
- Context: User is a legal professional working on a contract. Track Changes is enabled. They need AI to propose revisions that other parties can review and accept/reject — a core legal workflow[reference:2].
- Setup: Launch Word with `C:\tests\contract.docx` (a simple NDA template). Enable Track Changes (Review tab → Track Changes ON).
- User Action: Select a clause in the contract. Type "Update this clause to include California jurisdiction and strengthen the confidentiality language. Propose changes using Track Changes so I can review."
- Press Alt+M, wait 12 seconds, press Tab.
- Expected: AI-injected text appears as tracked changes (red underline for insertions, strikethrough for deletions). Original text still visible.
- Pass Criteria: Script verifies that document has tracked changes active AND that new text appears as tracked insertions (check via Word's XML or UIA for revision marks). Exit code 0.
- Retry if: Changes appear as direct edits (not tracked), or tracked changes count is zero.

**W6 — LARGE DOCUMENT: 40+ page section rewrite**
- Context: User is working on a 40‑page report where styles break unpredictably, especially after section breaks — a known Word bug where "formatting is done consistently through paragraph formats but Word breaks text flow options"[reference:3].
- Setup: Launch Word with a 40+ page document (pre-generated fixture with multiple sections, headings, tables, images).
- User Action: Navigate to Section 3 (pages 15-20). Select all content in that section. Type "Rewrite Section 3 to be more concise while preserving all key data points and heading structure. Do not modify any other sections."
- Press Alt+M, wait 20 seconds (longer for large doc), press Tab to accept.
- Expected: Only Section 3 content changes. Other sections untouched. Heading structure preserved. Key data points remain.
- Pass Criteria: Script verifies: (a) Section 3 text has changed, (b) Section 2 and Section 4 text is unchanged, (c) heading count in Section 3 matches pre-edit count, (d) no document corruption.
- Retry if: Other sections modified, headings lost, or document corrupted.

**W7 — MULTI-STYLE: Mixed content preservation**
- Context: Document contains headings (H1/H2/H3), body text, bullet lists, numbered lists, blockquotes, and code blocks. User wants to rewrite body text without touching structural elements.
- Setup: Launch Word with a document containing all style types listed above.
- User Action: Select all (Ctrl+A). Type "Rewrite all body paragraphs to be more engaging while keeping ALL headings, lists, blockquotes, and code blocks exactly as they are. Match each paragraph's existing style."
- Press Alt+M, wait 18 seconds, press Tab to accept.
- Expected: Body text rewritten. Headings unchanged. Lists preserved. Blockquotes and code blocks untouched.
- Pass Criteria: Script verifies heading count same, list items count same, blockquote count same, code block count same. Body text has changed meaningfully.
- Retry if: Any heading modified or list items changed.

**W8 — TONE SHIFT: Formal to conversational (and vice versa)**
- Context: User wrote a formal report but now needs a conversational version for a team Slack announcement.
- Setup: Launch Word with formal business text about quarterly results.
- User Action: Select text. Type "Rewrite this in a casual, friendly tone suitable for a team Slack message. Use emojis where appropriate."
- Press Alt+M, wait 10 seconds, press Tab.
- Expected: Text becomes casual, friendly, with emojis.
- Pass Criteria: Text contains at least 1 emoji, tone is clearly casual (sentence structure simpler), original meaning preserved.
- Retry if: No emojis, still reads as formal, or meaning distorted.

**W9 — STRUCTURAL RESTRUCTURING: Reorder sections**
- Context: User has a report where sections are in wrong order. They want AI to propose a better structure.
- Setup: Launch Word with document containing sections: Introduction, Methodology, Results, Conclusion, References (intentionally out of logical order: Results → Introduction → Methodology → References → Conclusion).
- User Action: Select all. Type "Analyze the document structure and suggest a logical reordering of sections. Move sections so the flow is: Introduction → Methodology → Results → Conclusion → References. Preserve all content."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: Sections reordered correctly. All content preserved.
- Pass Criteria: Script verifies section order is correct. Content from each original section present in corresponding new section.
- Retry if: Section order incorrect or content lost.

**W10 — BROKEN FORMATTING REPAIR: Style corruption fix**
- Context: Document has accumulated style corruption from repeated copy-paste between documents — a known legal document issue where "clause reuse imports hidden styles"[reference:4].
- Setup: Launch Word with a document that has 5+ different unexplained styles, inconsistent heading numbering, and stray formatting marks.
- User Action: Select all. Type "Clean up all formatting. Reset all body text to Normal style. Ensure headings use consistent Heading 1/2/3 styles with proper numbering. Remove all direct formatting overrides."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: Document uses consistent styles. No direct formatting overrides. Heading numbering sequential.
- Pass Criteria: Script verifies: (a) all body paragraphs use "Normal" style, (b) headings use proper Heading styles, (c) no direct formatting detected on text runs.
- Retry if: Style inconsistencies remain.

---

### AGENT_PPT — Microsoft PowerPoint (7 scenarios)
**Agent Type**: Python/pywinauto
**Application**: POWERPNT.EXE
**Test Document Base**: `C:\tests\deck.pptx`

**P1 — BLANK DECK: Create presentation from scratch**
- Context: User has a completely blank PowerPoint. They need to create a 5‑slide investor pitch deck from nothing — mirroring a startup founder's real workflow.
- Setup: Launch PowerPoint with new blank presentation.
- User Action: Type "Create a 5-slide investor pitch deck for an AI document copilot startup called Kairo Phantom. Slide 1: Title slide with tagline. Slide 2: Problem statement. Slide 3: Solution overview. Slide 4: Market opportunity. Slide 5: Team and ask. Use professional dark theme styling."
- Press Alt+M, wait 25 seconds, press Tab.
- Expected: 5 slides created with appropriate content. Title slide has company name and tagline. Each slide has relevant content matching the requested topic.
- Pass Criteria: Slide count = 5. Slide 1 contains "Kairo Phantom". Each subsequent slide has text relevant to its topic. No placeholder "[insert]" text.
- Retry if: Fewer than 5 slides, or any slide has placeholder/generic content.

**P2 — EXISTING DECK: Improve visual design and consistency**
- Context: User has an existing deck but it looks amateur — inconsistent fonts, mismatched colors, varying text sizes. Real-world "death by PowerPoint" scenario where "putting lots of text on a slide and reading it out to the audience is the number one presentation killer"[reference:5].
- Setup: Launch PowerPoint with `C:\tests\deck.pptx` containing 8 slides with deliberately inconsistent formatting (mixed fonts, varying sizes, random colors, overcrowded slides with paragraphs of text).
- User Action: Select all slides. Type "Make this presentation visually consistent. Use a uniform color scheme. Convert long paragraphs to bullet points. Ensure all titles use the same font and size. Make slides scannable, not text-heavy."
- Press Alt+M, wait 20 seconds, press Tab.
- Expected: Fonts unified, colors consistent, text-heavy slides converted to bullet points, titles aligned.
- Pass Criteria: Script verifies title font consistent across slides. At least 2 previously text-heavy slides now use bullet points. Exit code 0.
- Retry if: Fonts still inconsistent or overcrowded slides unchanged.

**P3 — TEXT CONDENSING: Paragraph to bullet points**
- Context: User pasted three paragraphs from a report onto a slide — the most common PowerPoint mistake. "If you find yourself copy-pasting three paragraphs of text from a report, you haven't made a slide — you've made a digital flyer"[reference:6].
- Setup: Launch PowerPoint. Navigate to a slide containing a dense 3‑paragraph text block.
- User Action: Select the text block. Type "Convert these paragraphs into 5-7 concise bullet points. Each bullet should be one line maximum. Preserve all key information."
- Press Alt+M, wait 12 seconds, press Tab.
- Expected: 3 paragraphs replaced by 5-7 bullet points. Each bullet concise. Key information preserved.
- Pass Criteria: Text now contains bullet characters (•). Between 5-7 bullets. Each bullet under ~120 characters. Content preserved.
- Retry if: Still paragraph format, or more than 7 bullets, or information lost.

**P4 — IMAGE GENERATION: AI-generated slide imagery**
- Context: User has a slide about "market growth" but it's text-only and visually boring. They want an AI-generated image to make the slide impactful.
- Setup: Launch PowerPoint, navigate to a text-only slide titled "Market Opportunity."
- User Action: Type "Generate a professional AI image showing upward market growth trends and insert it into this slide. Make it fit the slide layout without covering the title."
- Press Alt+M, wait 20 seconds (image generation takes longer), press Tab.
- Expected: An AI-generated image appears on the slide. Image is relevant to market growth. Title still visible.
- Pass Criteria: Slide now contains an image shape (verify via UIA). Image dimensions are reasonable (not covering title). Exit code 0.
- Retry if: No image appears, or image is placeholder/error.

**P5 — SPEAKER NOTES: Generate presentation talking points**
- Context: User is preparing to present and needs speaker notes for each slide.
- Setup: Launch PowerPoint with `C:\tests\deck.pptx` (8 slides with content).
- User Action: Navigate to slide 1. Type "Generate detailed speaker notes for every slide in this presentation. Notes should be in the speaker notes section, 2-3 sentences per slide, with key talking points and transitions."
- Press Alt+M, wait 25 seconds, press Tab.
- Expected: Speaker notes populated for all 8 slides with relevant talking points.
- Pass Criteria: Script checks each slide's NotesPage for text content. At least 6 of 8 slides have notes. Notes are slide-relevant (contain keywords from the slide).
- Retry if: Fewer than 6 slides have notes, or notes are generic/unrelated.

**P6 — SLIDE RESTRUCTURING: Merge and reorder**
- Context: User has slides that should be combined, and the order needs adjustment for better narrative flow.
- Setup: Launch PowerPoint with deck where slides 3 and 4 contain related content that should be merged, and slide 7 should be slide 2.
- User Action: Type "Merge slides 3 and 4 into one comprehensive slide. Move the current slide 7 to position 2. Adjust all slide numbers accordingly."
- Press Alt+M, wait 18 seconds, press Tab.
- Expected: Slides 3 and 4 combined into one. Former slide 7 now at position 2. Total slide count reduced by 1.
- Pass Criteria: Slide count = original minus 1. Content from both original slides 3 and 4 present in merged slide. Slide originally at position 7 now at position 2.
- Retry if: Slide count wrong, content lost, or ordering incorrect.

**P7 — THEME APPLICATION: Apply consistent theme**
- Context: User's deck has no theme applied. They want to quickly apply a corporate look.
- Setup: Launch PowerPoint with unstyled deck (white background, black Calibri, no design elements).
- User Action: Type "Apply a modern corporate blue theme to this entire presentation. Use consistent slide layouts. Make the title slide stand out with a dark blue background and white text."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: Theme colors applied across all slides. Title slide has distinct styling.
- Pass Criteria: Script verifies slide backgrounds are not plain white. Title slide differs from content slides. Colors consistent across slides.
- Retry if: Theme not applied or inconsistent.

---

### AGENT_EXCEL — Microsoft Excel (5 scenarios)
**Agent Type**: Python/pywinauto + openpyxl
**Application**: EXCEL.EXE
**Test Document Base**: `C:\tests\spreadsheet.xlsx`

**E1 — FORMULA DEBUG: Fix broken formulas**
- Context: User has a spreadsheet where formulas return errors — a common scenario where "cross-table/merged cell references cause summary errors affecting decision accuracy"[reference:7].
- Setup: Launch Excel with spreadsheet containing 5 intentionally broken formulas (e.g., missing cell references producing #REF!, circular references producing #VALUE!, division by zero producing #DIV/0!).
- User Action: Select the cell range with broken formulas. Type "Fix all broken formulas in this selection. Replace error-producing formulas with correct ones. Explain each fix."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: All formulas fixed, no #REF!, #VALUE!, or #DIV/0! errors remain. Correct values calculated.
- Pass Criteria: Script reads cell values via openpyxl. Zero error values in target range. All cells contain valid numbers or text.
- Retry if: Any error value persists.

**E2 — DATA ANALYSIS: Generate insights from raw data**
- Context: User has raw sales data but doesn't know how to analyze it. 30% of financial services professionals spend 4+ hours daily in Excel[reference:8].
- Setup: Launch Excel with spreadsheet containing 500 rows of sales data (Date, Product, Region, Revenue, Units columns).
- User Action: Select a cell near the data. Type "Analyze this sales data and add a summary section below. Include: top 3 products by revenue, best performing region, monthly revenue trend, and any notable outliers."
- Press Alt+M, wait 20 seconds, press Tab.
- Expected: Summary section appears below data with accurate analysis. Top products identified. Region identified. Trend noted. Outliers flagged.
- Pass Criteria: Summary text contains at least 4 data points. Product names and region names from actual data are referenced. Numbers are factually accurate (verify via separate formula calculation).
- Retry if: Data is factually incorrect, or analysis is generic (no specific numbers).

**E3 — CHART CREATION: AI-assisted visualization**
- Context: User needs to visualize data for a presentation but struggles with chart creation.
- Setup: Launch Excel with sales data spreadsheet.
- User Action: Select the data range (Date, Revenue columns). Type "Create a professional line chart showing monthly revenue trends. Add it as a new chart sheet. Use a blue color scheme with clear axis labels."
- Press Alt+M, wait 18 seconds, press Tab.
- Expected: A line chart is created. Chart shows revenue trend. Blue color scheme. Axis labels present.
- Pass Criteria: Script verifies a chart object exists in the workbook. Chart type is line. Chart has axis labels. Color is blue-tinted.
- Retry if: No chart created, wrong chart type, or no labels.

**E4 — FORMULA GENERATION: Complex calculation assistance**
- Context: User needs to create complex formulas but isn't an Excel expert. Real-world scenario where users misuse IFERROR/ISERROR and get unexpected results[reference:9].
- Setup: Launch Excel with data table containing Product, Cost, Price, Units Sold columns.
- User Action: Select cell F2. Type "Create a formula that calculates total profit margin percentage for each product row: (Price - Cost) * Units Sold / (Price * Units Sold) * 100. Apply it to all 100 rows and format results as percentage with 1 decimal place."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: Correct formula applied to all rows. Results formatted as percentages.
- Pass Criteria: Script reads F2 formula. Formula is correct for profit margin calculation. Results in all 100 rows are valid percentages between 0-100. No error values.
- Retry if: Formula incorrect, errors in results, or formatting wrong.

**E5 — DATA CLEANING: Standardize inconsistent data**
- Context: User imported data from multiple sources. Dates are in different formats (MM/DD/YYYY, DD-MM-YYYY, text like "Jan 15 2026"), names have inconsistent capitalization, and there are trailing spaces.
- Setup: Launch Excel with deliberately messy data: mixed date formats, inconsistent name casing ("JOHN SMITH", "jane doe", "Bob Wilson"), cells with leading/trailing spaces, and duplicate rows.
- User Action: Select all data. Type "Clean this data: standardize all dates to YYYY-MM-DD format, fix name capitalization to Proper Case, remove leading/trailing spaces, and highlight duplicate rows in yellow."
- Press Alt+M, wait 20 seconds, press Tab.
- Expected: Dates standardized, names in Proper Case, spaces removed, duplicates highlighted.
- Pass Criteria: Script verifies: (a) all dates in same format, (b) all names Proper Case, (c) no leading/trailing spaces, (d) duplicate rows have yellow fill.
- Retry if: Any formatting issue persists.

---

### AGENT_VSCODE — Visual Studio Code (6 scenarios)
**Agent Type**: Python/pyautogui + keyboard
**Application**: code.exe
**Test Workspace**: `C:\tests\vscode-project\`

**V1 — CODE GENERATION: From natural language comment**
- Context: Developer writes a comment describing what they want, then uses AI to generate the implementation.
- Setup: Open VS Code with a TypeScript file. Cursor is below a comment: `// Function that fetches user data from API, validates the response, and returns typed User object`.
- User Action: Press Alt+M. Wait 12 seconds, press Tab.
- Expected: A complete TypeScript function appears below the comment with proper typing, error handling, and API call logic.
- Pass Criteria: Generated code is valid TypeScript (check syntax). Function name relates to comment. Includes type annotations. Has error handling (try/catch or .catch()).
- Retry if: No code generated, syntax errors, or missing type safety.

**V2 — CODE REFACTORING: Improve existing function**
- Context: Developer has a working but messy function that needs refactoring — too long, poor variable names, no error handling.
- Setup: Open VS Code with a file containing a poorly written 50-line Python function (no docstring, single-letter variables, nested if-else pyramid, no error handling).
- User Action: Select the entire function. Type "Refactor this function: add docstring, use descriptive variable names, flatten nested conditionals with early returns, add proper error handling, and split into smaller helper functions if appropriate."
- Press Alt+M, wait 18 seconds, press Tab.
- Expected: Function refactored with all requested improvements. Logic preserved.
- Pass Criteria: Refactored code has: docstring, descriptive variable names, early returns (reduced nesting), error handling. Function still produces same logic.
- Retry if: Logic changed, or any requested improvement missing.

**V3 — BUG FIXING: Identify and fix issues**
- Context: Developer has code that runs but produces wrong output. They need AI debugging.
- Setup: Open VS Code with a Python file containing a function with an off-by-one error in a loop and incorrect variable scope.
- User Action: Select the buggy function. Type "This function is producing incorrect results. Find and fix all bugs. Add comments explaining each fix."
- Press Alt+M, wait 15 seconds, press Tab.
- Expected: Bugs identified and fixed. Comments explain changes.
- Pass Criteria: Fixed code runs correctly (verify by executing). Comments present explaining fixes. Original buggy behavior eliminated.
- Retry if: Bugs not fixed, or no explanatory comments.

**V4 — MCP SERVER INTEGRATION: Kairo invoked via MCP**
- Context: Developer uses Claude Code or another MCP client in VS Code and wants to invoke Kairo's ghost-writing from within the IDE.
- Setup: VS Code with Claude Code extension installed and Kairo MCP server configured. Open a markdown file with messy documentation.
- User Action: In Claude Code chat, type: "Use Kairo to rewrite the selected markdown text to be clearer and more structured."
- Expected: Kairo ghost-writes improved markdown through the MCP bridge. Text appears in editor.
- Pass Criteria: Selected text replaced with improved version. Operation completed via MCP (verify in Kairo's JSON logs that an MCP `kairo_ghost_write` call was made). Exit code 0.
- Retry if: MCP call fails, or text not injected.

**V5 — MULTI-FILE CONTEXT: Project-wide understanding**
- Context: Developer needs to understand how changing one function affects the entire project.
- Setup: Open VS Code with a multi-file project (5+ TypeScript files with interdependencies).
- User Action: In the main file, select a function. Type "Analyze all files in this project and tell me every place this function is called or imported. List the call chain."
- Press Alt+M, wait 18 seconds, press Tab.
- Expected: Comprehensive answer listing all call sites across files with file paths and line numbers.
- Pass Criteria: Response lists at least 2 files. File paths match actual project structure. Line references are approximately correct.
- Retry if: Only one file mentioned, or analysis is vague.

**V6 — TEST GENERATION: Write unit tests**
- Context: Developer wrote functions but no tests. They want AI to generate test coverage.
- Setup: Open VS Code with a TypeScript utility module containing 3 exported functions (no tests exist).
- User Action: Select all code. Type "Write comprehensive Jest unit tests for all exported functions. Cover normal cases, edge cases, and error conditions. Use describe/it blocks."
- Press Alt+M, wait 20 seconds, press Tab.
- Expected: Test file generated with proper Jest structure, covering all functions and edge cases.
- Pass Criteria: Generated code uses Jest syntax (describe/it/expect). At least 2 test cases per function. Edge cases covered (null inputs, empty arrays, etc.).
- Retry if: Tests don't compile, or coverage is minimal.

---

### AGENT_BROWSER — Google Docs / Yjs Collaborative (4 scenarios)
**Agent Type**: Node.js + agent-browser (Playwright)
**Browser**: Chrome (non-headless for overlay visibility)
**Document URL**: Pre-shared Google Doc with edit access

**G1 — YJS COLLABORATIVE PEER: AI joins as document collaborator**
- Context: Multiple users are editing a shared Google Doc. Kairo Phantom joins as a CRDT peer with its own clientID, visible to all collaborators — a scenario that distinguishes Kairo from every other AI copilot.
- Setup: Launch Chrome via agent-browser. Navigate to pre-shared Google Doc. A second browser instance (or real collaborator) should be viewing the same document.
- User Action: In the first browser, click inside the doc body. Type "Improve this paragraph with better structure and clarity." Select the target paragraph. Press Alt+M. Wait 12 seconds. Press Tab.
- Expected: AI-injected text appears in the document. Both browser instances see the change. The AI's presence (cursor and status) was visible during generation. Injected text carries `data-clientid` attribute with `kairo-ai-` prefix.
- Pass Criteria: Script verifies via DOM inspection: (a) injected text contains `data-clientid` attribute, (b) the clientID starts with "kairo-ai-", (c) the second browser instance also shows the AI text. Exit code 0.
- Retry if: No clientID attribute, or second browser doesn't show changes.

**G2 — AI AWARENESS VISIBILITY: Collaborators see AI status**
- Context: When Kairo's AI peer is generating text, other collaborators should see an AI cursor with status indicators — just like they would see a human collaborator's cursor.
- Setup: Two browser instances viewing same Google Doc. First instance triggers ghost-write.
- User Action: In first browser, trigger ghost-write with a long prompt. During generation (before accepting), check the second browser.
- Expected: Second browser shows a cursor labeled with AI status (e.g., "AI writing..." or the configured awareness label). The cursor moves as text is generated.
- Pass Criteria: Script captures screenshot of second browser during generation. Verifies an AI-labeled cursor or awareness marker is visible. Exit code 0.
- Retry if: No awareness indication visible, or awareness label is generic/default.

**G3 — AI UNDO IN COLLABORATIVE CONTEXT: Single Ctrl+Z reverts**
- Context: After AI injects text into a collaborative document, the user wants to revert it. Ctrl+Z should undo the entire AI operation as one atomic unit.
- Setup: Google Doc with AI-injected text from G1.
- User Action: Press Ctrl+Z once.
- Expected: The entire AI-injected block is removed in one undo operation. Document returns to pre-AI state.
- Pass Criteria: Script verifies the AI-injected text is completely removed. Document state matches pre-injection state. Only one Ctrl+Z was needed (not character-by-character undo). Exit code 0.
- Retry if: Partial undo, or requires multiple Ctrl+Z presses, or document state corrupted.

**G4 — CONCURRENT HUMAN + AI EDITING: No conflicts**
- Context: A human collaborator and the AI peer are editing different paragraphs simultaneously. Kairo must handle this without conflicts or data loss — a known pain point where "multiple people editing the same line at the same time" causes issues[reference:10].
- Setup: Two browser instances. Human edits paragraph 1 while AI ghost-writes into paragraph 5 (different paragraphs).
- User Action: In first browser, start editing paragraph 1 manually. In second browser (or via agent), trigger AI ghost-write on paragraph 5 simultaneously.
- Expected: Both edits succeed. No conflict dialog. No data loss. Both paragraphs updated correctly.
- Pass Criteria: Paragraph 1 shows human edit. Paragraph 5 shows AI edit. No error dialogs appeared. No text lost or duplicated. Exit code 0.
- Retry if: Conflict dialog, data loss, or either edit fails.

---

### AGENT_NOTEPAD — Windows Notepad (3 scenarios)
**Agent Type**: Python/pyautogui + keyboard
**Application**: notepad.exe
**Test File**: `C:\tests\notes.txt`

**N1 — QUICK NOTE: Fast AI-assisted writing**
- Context: User is jotting down quick notes and wants AI to expand or format them. Notepad is "super barebones" and used for quick plain-text tasks[reference:11].
- Setup: Open Notepad with a short note: "Meeting notes: discussed Q3 goals, budget review next week, new hire starts Monday, follow up on client proposal."
- User Action: Select all. Type "Expand these meeting notes into a clear, organized summary with action items marked."
- Press Alt+M, wait 10 seconds, press Tab.
- Expected: Notes expanded into organized summary. Action items clearly marked (e.g., with [ ] or TODO).
- Pass Criteria: Output is longer than input. Contains clearly marked action items. Original topics all mentioned. Exit code 0.
- Retry if: No expansion, or action items not identifiable.

**N2 — OFFLINE MODE: AI works without internet**
- Context: User has no internet connection but still needs AI assistance. Kairo Phantom should fall back to local Ollama models seamlessly.
- Setup: Disconnect internet (disable network adapter). Open Notepad with empty document.
- User Action: Type "Write a short poem about artificial intelligence in 4 stanzas." Press Alt+M. Wait 15 seconds. Press Tab.
- Expected: A 4-stanza poem appears generated entirely offline via Ollama. No network error messages.
- Pass Criteria: Output contains a poem with approximately 4 stanzas. No error about network/connectivity. Exit code 0. Re-enable internet after test.
- Retry if: Network error displayed, or no text generated.

**N3 — TEXT TRANSFORMATION: Encoding and format conversion**
- Context: User has text with special characters, mixed encoding, and needs it cleaned up for a config file.
- Setup: Open Notepad with text containing smart quotes, em-dashes, and mixed line endings (CRLF and LF).
- User Action: Select all. Type "Convert all smart quotes to straight quotes, replace em-dashes with double hyphens, and normalize all line endings to Windows CRLF."
- Press Alt+M, wait 8 seconds, press Tab.
- Expected: Smart quotes converted, em-dashes replaced, line endings uniform.
- Pass Criteria: Script reads file bytes and verifies: no smart quote characters, no em-dash characters, all line endings are CRLF. Exit code 0.
- Retry if: Special characters persist or line endings inconsistent.

---

### AGENT_TERMINAL — Windows Terminal (4 scenarios)
**Agent Type**: Python/pyautogui + subprocess
**Application**: wt.exe (Windows Terminal)

**T1 — COMMAND GENERATION: AI writes shell commands**
- Context: Developer needs to perform a system task but doesn't remember the exact command syntax.
- Setup: Open Windows Terminal with PowerShell prompt. The current directory is `C:\projects`.
- User Action: Type "Show me the command to find all TypeScript files modified in the last 7 days, recursively, and list them with their sizes sorted by size descending." Press Alt+M. Wait 10 seconds. Press Tab.
- Expected: A correct PowerShell command appears at the prompt that accomplishes the requested task.
- Pass Criteria: Command is valid PowerShell syntax. Command would find .ts files. Command includes date filtering and size sorting. Exit code 0.
- Retry if: Invalid syntax, or doesn't match the request.

**T2 — SCRIPT GENERATION: AI writes deployment scripts**
- Context: Developer needs to create a deployment script for their project. This mirrors real developer workflows where AI generates scripts for automation[reference:12].
- Setup: Open Windows Terminal. Current directory is a Node.js project with package.json.
- User Action: Type "Write a complete deployment script for this Node.js project. Include: installing dependencies, running tests, building the project, and deploying to a server. Use PowerShell syntax."
- Press Alt+M, wait 18 seconds, press Tab.
- Expected: A complete deployment script with all requested steps, proper error handling, and clear comments.
- Pass Criteria: Script includes install, test, build, and deploy steps. Has error handling (try/catch or error checks). Uses correct PowerShell syntax. Exit code 0.
- Retry if: Missing steps, no error handling, or syntax errors.

**T3 — ERROR EXPLANATION: AI diagnoses command failures**
- Context: Developer ran a command that failed with an error message. They need AI to explain what went wrong.
- Setup: Terminal with a visible error message: "npm ERR! code ERESOLVE, npm ERR! ERESOLVE unable to resolve dependency tree".
- User Action: Select the error text. Type "Explain what caused this error and show me the exact command to fix it." Press Alt+M. Wait 12 seconds. Press Tab.
- Expected: Clear explanation of the dependency conflict. A specific fix command provided.
- Pass Criteria: Response explains ERESOLVE error. Provides a concrete fix command (e.g., npm install --legacy-peer-deps or similar). Exit code 0.
- Retry if: Explanation is generic, or no fix command provided.

**T4 — MULTI-STEP WORKFLOW: AI orchestrates complex operations**
- Context: Developer needs to perform a series of operations: create a backup, run database migrations, clear caches, and restart services — all in correct order.
- Setup: Terminal at a project root.
- User Action: Type "Create a script that: (1) backs up the database to ./backups/, (2) runs pending migrations, (3) clears the Redis cache, and (4) restarts the application service. Include confirmation prompts before each destructive action."
- Press Alt+M, wait 20 seconds, press Tab.
- Expected: Complete script with all 4 steps, confirmation prompts, error handling for each step.
- Pass Criteria: Script contains all 4 operations in correct order. Has confirmation prompts. Has error handling. Exit code 0.
- Retry if: Steps missing, wrong order, or no safety prompts.

---

### AGENT_CHAOS — Background Fault Injection
**Agent Type**: PowerShell script
**Run Mode**: Continuous background during ALL tests

This agent executes `scripts\win\chaos_advanced.ps1` which cycles through:
- Network adapter disable/enable (random 30-90 second intervals)
- Clipboard clearing (random intervals)
- CPU spike (stress-ng equivalent, 20-30 second bursts)
- Windows Firewall outbound block on kairo-phantom.exe (20-30 second bursts)
- Disk I/O saturation (random short bursts)

The chaos agent must NOT be stopped unless a test specifically requires stable conditions (noted in scenario). All other tests must pass WITH chaos active.

---

## ORCHESTRATION COMMANDS

Deploy all agents simultaneously using GSD:

gsd run --agent agent_word --command "python scripts/win/orchestrator.py --agent word --scenarios W1,W2,W3,W4,W5,W6,W7,W8,W9,W10"
gsd run --agent agent_ppt --command "python scripts/win/orchestrator.py --agent ppt --scenarios P1,P2,P3,P4,P5,P6,P7"
gsd run --agent agent_excel --command "python scripts/win/orchestrator.py --agent excel --scenarios E1,E2,E3,E4,E5"
gsd run --agent agent_vscode --command "python scripts/win/orchestrator.py --agent vscode --scenarios V1,V2,V3,V4,V5,V6"
gsd run --agent agent_browser --command "node scripts/browser/orchestrator.js --scenarios G1,G2,G3,G4"
gsd run --agent agent_notepad --command "python scripts/win/orchestrator.py --agent notepad --scenarios N1,N2,N3"
gsd run --agent agent_terminal --command "python scripts/win/orchestrator.py --agent terminal --scenarios T1,T2,T3,T4"
gsd run --agent agent_chaos --command "powershell -File scripts/win/chaos_advanced.ps1"

## ORCHESTRATOR SCRIPT LOGIC (per agent)

Each orchestrator script must implement this logic:

1. Load scenario list from command-line argument.
2. For each scenario (in order):
   a. Open the target application if not already open.
   b. Log: `[TIMESTAMP] Starting scenario <ID>: <description>`
   c. Execute the scenario steps exactly as specified.
   d. Check pass criteria.
   e. If PASS: Log success, save screenshot, move to next scenario.
   f. If FAIL: Log failure details, save screenshot, RETRY up to 3 times with 30-second cooldown between retries.
   g. If 3 retries all fail: Log CRITICAL FAILURE, save detailed error report, move to next scenario (do NOT block other agents).
   h. At end: Close the application gracefully.
3. Output final JSON report to `C:\tests\results\<agent_name>_results.json`:
   {
     "agent": "agent_word",
     "total": 10,
     "passed": 10,
     "failed": 0,
     "retries": 2,
     "scenarios": {
       "W1": {"status": "PASS", "attempts": 1, "duration_sec": 14.2},
       "W2": {"status": "PASS", "attempts": 2, "duration_sec": 28.7},
       ...
     }
   }

## SUCCESS THRESHOLD FOR PRODUCTION READINESS

Kairo Phantom is declared PRODUCTION READY only when:
- ALL 39 scenarios across ALL 8 agents pass (exit code 0).
- At least 35 of 39 pass on FIRST attempt (no retries needed).
- No scenario requires more than 2 retries.
- Chaos monkey was active for the entire duration.
- Zero application crashes (Word, PPT, Excel, VS Code, Chrome, Notepad, Terminal did not crash during testing).
- Kairo Phantom process did not crash or memory-leak (verify via process monitoring).
- All 8 JSON result files pass validation.

## REPORTING

After all agents complete, the coordinator must aggregate all JSON results into a single master report:

{
  "test_run_id": "kairo-stress-<timestamp>",
  "chaos_active": true,
  "total_scenarios": 39,
  "total_passed": X,
  "total_failed": X,
  "total_retries": X,
  "first_attempt_pass_rate": "X%",
  "agent_results": {
    "agent_word": {...},
    "agent_ppt": {...},
    ...
  },
  "production_ready": true/false,
  "failure_details": [...]
}

Save to C:\tests\results\MASTER_REPORT.json.