You are the master testing coordinator for Kairo Phantom v4.0. Deploy 12
parallel GSD/Ruflo agents on Windows 11 — one agent per application. Every
agent opens REAL applications, loads REAL documents, presses Alt+M, and
verifies output against the strict criteria below. Zero simulation. Zero mocks.

═══════════════════════════════════════════════════════════════════════════
GLOBAL RULES (EVERY AGENT MUST OBEY)
═══════════════════════════════════════════════════════════════════════════

1. GATE ENFORCEMENT: Run each scenario. If it fails → RETRY up to 3 times
   with 30-second cooldown. Only move to next scenario when current passes.
2. REAL APPS ONLY: Each test opens winword.exe, powerpnt.exe, excel.exe,
   chrome.exe, code.exe, wt.exe, notepad.exe, or the respective app.
3. OUTPUT QUALITY VERIFICATION: Every test checks that the output is
   RELEVANT to the user prompt — not system prompt leakage, not role
   descriptions, not sentinel hashes. This is a HARD FAIL condition.
4. // PROTOCOL: User prompts must be preceded by //. Document text without
   // is pure context — Kairo must never treat it as a command.
5. SCREENSHOT ON FAILURE: pyautogui.screenshot() to C:\tests\screenshots\
6. LOG EVERYTHING: Structured JSON to C:\tests\logs\{agent_name}.json
7. CHAOS MONKEY: scripts\win\chaos_advanced.ps1 runs in background on
   every machine, randomly dropping network, clearing clipboard, spiking CPU.
8. ALL SCENARIOS MUST PASS before Kairo Phantom is declared production-ready.

═══════════════════════════════════════════════════════════════════════════
PREREQUISITES (Run setup_fixtures.py before testing)
═══════════════════════════════════════════════════════════════════════════

Generate these documents at C:\tests\ before testing begins:
- report.docx: 15-page formal report with H1/H2/H3 headings, 3 tables,
  inconsistent formatting (mixed fonts, broken numbered list)
- report_informal.docx: Contains: "we gotta improve our numbers cuz theyre
  not looking good lol. The team did alright but we need way more customers."
- contract.docx: Simple NDA template with 8 clauses
- deck.pptx: 8-slide presentation, inconsistent fonts, overcrowded text
- blank_deck.pptx: Empty presentation
- spreadsheet.xlsx: 500-row sales data (Date, Product, Region, Revenue, Units)
- spreadsheet_broken.xlsx: 5 intentionally broken formulas (#REF!, #VALUE!,
  #DIV/0!), inconsistent date formats, mixed name casing
- notes.txt: Short meeting note
- vscode-project\: Multi-file TypeScript project with interdependencies
- vscode-buggy\: Python file with off-by-one error and incorrect variable scope

═══════════════════════════════════════════════════════════════════════════
DEPLOY THE 12 AGENTS IN PARALLEL
═══════════════════════════════════════════════════════════════════════════

AGENT_WORD — Microsoft Word (10 scenarios)
AGENT_PPT — Microsoft PowerPoint (7 scenarios)
AGENT_EXCEL — Microsoft Excel (7 scenarios)
AGENT_BROWSER — Google Docs / Yjs Collaborative (6 scenarios)
AGENT_VSCODE — Visual Studio Code (6 scenarios)
AGENT_TERMINAL — Windows Terminal (5 scenarios)
AGENT_NOTEPAD — Windows Notepad (4 scenarios)
AGENT_OBSIDIAN — Obsidian (5 scenarios)
AGENT_NOTION — Notion (4 scenarios)
AGENT_FIGMA — Figma (5 scenarios)
AGENT_SLACK — Slack/Email (5 scenarios)
AGENT_PDF — PDF Documents (5 scenarios)
AGENT_CHAOS — Background Fault Injection (1 continuous)

═══════════════════════════════════════════════════════════════════════════
AGENT_WORD — Microsoft Word (10 Scenarios)
═══════════════════════════════════════════════════════════════════════════

W1 — BLANK PAGE: Write from scratch
PREREQUISITE: Launch Word with a completely blank document.
USER ACTION: Type "// Write an executive summary for a Q3 2026 quarterly
business review covering revenue growth, market expansion, and team
headcount. Use professional business tone with headings."
Press Alt+M. Wait up to 15 seconds. Press Tab to accept.
EXPECTED: Multi-paragraph executive summary with proper heading structure
(H1, H2). Professional tone. Content covers all three topics requested.
PASS CRITERIA:
  - Document contains ≥ 3 paragraphs AND ≥ 2 headings
  - Content mentions "revenue", "market", and "headcount"
  - NO text like "[insert here]", "TBD", or placeholder
  - NO "Content Agent", "Swarm Role", or system prompt content
  - Output is NOT a repetition of the user's prompt
RETRY IF: Fewer than 2 paragraphs, missing any of 3 required topics, or
  system prompt leakage detected.

W2 — PRE-WRITTEN: Fix formatting inconsistencies
CONTEXT: User has a poorly formatted document — inconsistent spacing,
mixed fonts, broken numbering. A known real-world issue where "Word
randomly inserts huge gaps between text" and formatting breaks across
section boundaries[reference:2].
PREREQUISITE: Launch Word with C:\tests\report.docx (pre-modified by
fixture generator to have: mixed 1.0/1.5/double line spacing, random
font sizes, broken numbered list, stray formatting marks).
USER ACTION: Select entire document (Ctrl+A). Type "// Fix all formatting
inconsistencies, make line spacing uniform at 1.15, ensure all body text
is 11pt Calibri, fix broken numbering in lists, and justify all paragraphs
properly. Preserve all content and heading structure."
Press Alt+M. Wait 20 seconds. Press Tab to accept.
EXPECTED: Uniform line spacing, consistent font, numbered lists
re-sequenced, paragraphs justified. All content preserved. Headings
unchanged.
PASS CRITERIA:
  - No mixed spacing remains (UIA verify paragraph properties)
  - Body text uses uniform font
  - Numbered list items are sequential without gaps
  - Heading count matches pre-edit count (verify via UIA)
  - Original body content preserved (not replaced with new content)
RETRY IF: Formatting inconsistency remains, numbered list broken, or
  content lost (the "de novo generation" failure where AI "prioritizes
  professional layout over data extraction"[reference:3]).

W3 — PRE-WRITTEN: Grammar, style, and tone correction
CONTEXT: User wrote informal text with grammatical errors. They need it
converted to formal business English for a board presentation.
PREREQUISITE: Launch Word with C:\tests\report_informal.docx containing:
"we gotta improve our numbers cuz theyre not looking good lol. The team
did alright but we need way more customers."
USER ACTION: Select the informal paragraph. Type "// Rewrite this in
formal business English with proper grammar, consistent terminology,
and professional tone suitable for a board presentation."
Press Alt+M. Wait 12 seconds. Press Tab to accept.
EXPECTED: Text transformed to formal business English. No slang, no
grammatical errors, professional vocabulary.
PASS CRITERIA:
  - Output does NOT contain "gotta", "cuz", "theyre", "lol", "alright"
  - Output does NOT contain "Content Agent", "Swarm Role", or system
    prompt content
  - Output is formal business English suitable for a board
  - Output is NOT the original informal text unchanged
  - Output is NOT a repetition of the user's prompt
  - Memory vault records: format="prose", tone="formal"
RETRY IF: Any slang remains, grammar errors persist, or system prompt
  leakage detected. This is the canonical W3 test — 5 consecutive passes
  required before marking this scenario COMPLETE.

W4 — TABLE MANIPULATION: Summarize table data
CONTEXT: User has a document with a complex sales data table. They want
AI to extract and summarize insights.
PREREQUISITE: Launch Word with a document containing a sales data table
(Q1-Q4, multiple product lines, revenue figures). Table has inconsistent
row heights and merged cells.
USER ACTION: Select the entire table. Type "// Analyze this sales table
and write a 3-bullet summary of the key insights below the table.
Identify the best performing quarter and the highest growth product line."
Press Alt+M. Wait 12 seconds. Press Tab to accept.
EXPECTED: 3-bullet summary below table with accurate data interpretation.
PASS CRITERIA:
  - Summary contains exactly 3 bullet points
  - Mentions specific numbers from the table
  - Identifies best quarter correctly (verify against table data)
  - Bullets appear BELOW the table, not replacing it
RETRY IF: Fewer than 3 bullets, data interpretation factually wrong, or
  table content overwritten.

W5 — TRACKED CHANGES: AI with revision tracking
CONTEXT: Legal professional working on a contract with Track Changes
enabled. AI must propose revisions that can be reviewed and accepted/
rejected by other parties — a core legal workflow[reference:4].
PREREQUISITE: Launch Word with C:\tests\contract.docx (simple NDA).
Enable Track Changes (Review tab → Track Changes ON).
USER ACTION: Select a clause. Type "// Update this clause to include
California jurisdiction and strengthen the confidentiality language.
Propose changes using Track Changes so I can review."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: AI-injected text appears as tracked changes (red underline for
insertions, strikethrough for deletions). Original text still visible.
PASS CRITERIA:
  - Document has tracked changes active
  - New text appears as tracked insertions (verify via Word UIA or XML
    for revision marks)
  - Original text preserved with strikethrough
  - Changes are substantive (not just formatting)
RETRY IF: Changes appear as direct edits (not tracked), tracked changes
  count is zero, or original text is lost.

W6 — LARGE DOCUMENT: 40+ page section rewrite
CONTEXT: User working on a 40-page report where styles break
unpredictably after section breaks. A known Word failure mode where
"formatting is done consistently through paragraph formats but Word
breaks text flow options"[reference:5].
PREREQUISITE: Launch Word with a 40+ page document (pre-generated with
multiple sections, headings, tables, images).
USER ACTION: Navigate to Section 3 (pages 15-20). Select all content in
that section. Type "// Rewrite Section 3 to be more concise while
preserving all key data points and heading structure. Do not modify any
other sections."
Press Alt+M. Wait 25 seconds. Press Tab to accept.
EXPECTED: Only Section 3 content changes. Other sections untouched.
Heading structure preserved. Key data points remain.
PASS CRITERIA:
  - Section 3 text has changed (different from original)
  - Section 2 and Section 4 text is unchanged
  - Heading count in Section 3 matches pre-edit count
  - No document corruption (verify file opens cleanly after edit)
RETRY IF: Other sections modified, headings lost, or document corrupted.

W7 — MULTI-STYLE: Mixed content preservation
CONTEXT: Document contains headings (H1/H2/H3), body text, bullet lists,
numbered lists, blockquotes, code blocks. User wants body text rewritten
without touching structural elements.
PREREQUISITE: Launch Word with document containing all style types above.
USER ACTION: Select all (Ctrl+A). Type "// Rewrite all body paragraphs to
be more engaging while keeping ALL headings, lists, blockquotes, and code
blocks exactly as they are. Match each paragraph's existing style."
Press Alt+M. Wait 18 seconds. Press Tab to accept.
EXPECTED: Body text rewritten. Headings unchanged. Lists preserved.
Blockquotes and code blocks untouched.
PASS CRITERIA:
  - Heading count same as before
  - List item count same as before
  - Blockquote count same as before
  - Code block count same as before
  - Body text has changed meaningfully (verified by diff)
RETRY IF: Any heading modified, list items changed, or structural
  element altered.

W8 — TONE SHIFT: Formal to conversational
CONTEXT: User wrote a formal report but now needs a casual version for
a team Slack announcement.
PREREQUISITE: Launch Word with formal business text about quarterly results.
USER ACTION: Select text. Type "// Rewrite this in a casual, friendly
tone suitable for a team Slack message. Use emojis where appropriate.
Keep the key information intact."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Text becomes casual, friendly, with emojis. Key info preserved.
PASS CRITERIA:
  - Text contains at least 1 emoji
  - Tone is clearly casual (shorter sentences, informal vocabulary)
  - Original key data points preserved
RETRY IF: No emojis, still reads as formal, or meaning distorted.

W9 — STRUCTURAL RESTRUCTURING: Reorder sections
CONTEXT: User has a report with sections in wrong logical order.
PREREQUISITE: Launch Word with document where sections are intentionally
out of order: Results → Introduction → Methodology → References →
Conclusion.
USER ACTION: Select all. Type "// Analyze the document structure and
suggest a logical reordering. Move sections so the flow is: Introduction
→ Methodology → Results → Conclusion → References. Preserve all content."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Sections reordered correctly. All content preserved.
PASS CRITERIA:
  - Section order is now Introduction → Methodology → Results →
    Conclusion → References
  - Content from each original section present in corresponding new section
  - No content duplication or loss
RETRY IF: Section order incorrect or content lost.

W10 — BROKEN FORMATTING REPAIR: Style corruption fix
CONTEXT: Document accumulated style corruption from repeated copy-paste
between documents. A known legal document issue where "clause reuse
imports hidden styles."
PREREQUISITE: Launch Word with document having 5+ different unexplained
styles, inconsistent heading numbering, stray formatting marks.
USER ACTION: Select all. Type "// Clean up all formatting. Reset all body
text to Normal style. Ensure headings use consistent Heading 1/2/3 styles
with proper numbering. Remove all direct formatting overrides."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Document uses consistent styles. No direct formatting overrides.
Heading numbering sequential.
PASS CRITERIA:
  - All body paragraphs use "Normal" style
  - Headings use proper Heading styles (verify via UIA)
  - No direct formatting detected on text runs
  - Style count reduced to ≤ 5 distinct styles
RETRY IF: Style inconsistencies remain or direct formatting persists.

═══════════════════════════════════════════════════════════════════════════
AGENT_PPT — Microsoft PowerPoint (7 Scenarios)
═══════════════════════════════════════════════════════════════════════════

P1 — BLANK DECK: Create presentation from scratch
PREREQUISITE: Launch PowerPoint with new blank presentation.
USER ACTION: Type "// Create a 5-slide investor pitch deck for an AI
document copilot startup called Kairo Phantom. Slide 1: Title slide with
tagline. Slide 2: Problem statement. Slide 3: Solution overview. Slide 4:
Market opportunity. Slide 5: Team and ask. Use professional dark theme
styling. Generate relevant AI images for slides where appropriate."
Press Alt+M. Wait 30 seconds. Press Tab.
EXPECTED: 5 slides created with appropriate content. Title slide has
company name and tagline. Each slide has relevant content. Images
generated where requested.
PASS CRITERIA:
  - Slide count = 5
  - Slide 1 contains "Kairo Phantom"
  - Each subsequent slide has text relevant to its topic
  - No placeholder "[insert]" text
  - At least 1 slide has an AI-generated image (verify image shape exists)
RETRY IF: Fewer than 5 slides, any slide has placeholder/generic content,
  or no images generated.

P2 — EXISTING DECK: Improve visual design and consistency
CONTEXT: User's deck looks amateur — inconsistent fonts, mismatched
colors, varying text sizes. The #1 presentation mistake: "putting lots of
text on a slide and reading it out to the audience."
PREREQUISITE: Launch PowerPoint with C:\tests\deck.pptx (8 slides with
deliberately inconsistent formatting: mixed fonts, varying sizes, random
colors, overcrowded slides with paragraphs of text).
USER ACTION: Select all slides. Type "// Make this presentation visually
consistent. Use a uniform color scheme. Convert long paragraphs to bullet
points. Ensure all titles use the same font and size. Make slides
scannable, not text-heavy. Preserve all key information."
Press Alt+M. Wait 25 seconds. Press Tab.
EXPECTED: Fonts unified, colors consistent, text-heavy slides converted
to bullet points, titles aligned. All key info preserved.
PASS CRITERIA:
  - Title font consistent across slides (verify via UIA)
  - At least 2 previously text-heavy slides now use bullet points
  - Color scheme is uniform (not random per slide)
  - Key data points from original slides preserved
RETRY IF: Fonts still inconsistent, overcrowded slides unchanged, or
  content lost.

P3 — TEXT CONDENSING: Paragraph to bullet points
CONTEXT: User pasted three paragraphs from a report onto a slide — the
most common PowerPoint mistake. "If you find yourself copy-pasting three
paragraphs of text from a report, you haven't made a slide — you've made
a digital flyer."
PREREQUISITE: PowerPoint slide with a dense 3-paragraph text block.
USER ACTION: Select the text block. Type "// Convert these paragraphs
into 5-7 concise bullet points. Each bullet should be one line maximum.
Preserve all key information."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: 3 paragraphs replaced by 5-7 bullet points. Each bullet
concise. Key information preserved.
PASS CRITERIA:
  - Text now contains bullet characters (•)
  - Between 5-7 bullets
  - Each bullet under ~120 characters
  - Key info from original paragraphs preserved (verify specific data)
RETRY IF: Still paragraph format, more than 7 bullets, or information lost.

P4 — IMAGE GENERATION: AI-generated slide imagery
CONTEXT: User has a slide about "market growth" but it's text-only and
visually boring.
PREREQUISITE: PowerPoint slide titled "Market Opportunity" with text only.
USER ACTION: Type "// Generate a professional AI image showing upward
market growth trends and insert it into this slide. Make it fit the slide
layout without covering the title or key text."
Press Alt+M. Wait 25 seconds. Press Tab.
EXPECTED: AI-generated image appears on the slide. Relevant to market
growth. Title still visible.
PASS CRITERIA:
  - Slide now contains an image shape (verify via UIA/powerpoint object
    model)
  - Image dimensions reasonable (not covering title)
  - Image is non-placeholder (actual content, not default clipart)
RETRY IF: No image appears, image is placeholder/error, or title covered.

P5 — SPEAKER NOTES: Generate presentation talking points
CONTEXT: User preparing to present, needs speaker notes for every slide.
PREREQUISITE: PowerPoint with C:\tests\deck.pptx (8 slides with content).
USER ACTION: Navigate to slide 1. Type "// Generate detailed speaker
notes for every slide in this presentation. Notes should be in the
speaker notes section, 2-3 sentences per slide, with key talking points
and transitions between slides."
Press Alt+M. Wait 25 seconds. Press Tab.
EXPECTED: Speaker notes populated for all 8 slides with relevant points.
PASS CRITERIA:
  - At least 6 of 8 slides have speaker notes
  - Notes are slide-relevant (contain keywords from the slide)
  - Notes include transition phrases between slides
  - Notes are in the speaker notes section, not on the slide
RETRY IF: Fewer than 6 slides have notes, or notes are generic/unrelated.

P6 — SLIDE RESTRUCTURING: Merge and reorder
CONTEXT: User has slides that should be combined, order needs adjustment
for better narrative flow.
PREREQUISITE: PowerPoint deck where slides 3 and 4 contain related content
that should be merged, and slide 7 should logically be slide 2.
USER ACTION: Type "// Merge slides 3 and 4 into one comprehensive slide.
Move the current slide 7 to position 2. Adjust all slide numbers
accordingly. Preserve all content."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Slides 3 and 4 combined into one. Former slide 7 now at
position 2. Total slide count reduced by 1.
PASS CRITERIA:
  - Slide count = original minus 1
  - Content from both original slides 3 and 4 present in merged slide
  - Slide originally at position 7 now at position 2
  - No content lost
RETRY IF: Slide count wrong, content lost, or ordering incorrect.

P7 — THEME APPLICATION: Apply consistent corporate theme
CONTEXT: User's deck has no theme applied. Need quick corporate look.
PREREQUISITE: PowerPoint with unstyled deck (white background, black
Calibri, no design elements).
USER ACTION: Type "// Apply a modern corporate blue theme to this entire
presentation. Use consistent slide layouts. Make the title slide stand
out with a dark blue background and white text. Apply to all slides."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Theme colors applied across all slides. Title slide distinct.
PASS CRITERIA:
  - Slide backgrounds are not plain white
  - Title slide differs from content slides visually
  - Colors consistent across slides (not random)
  - Content preserved through theme change
RETRY IF: Theme not applied, inconsistent, or content lost.

═══════════════════════════════════════════════════════════════════════════
AGENT_EXCEL — Microsoft Excel (7 Scenarios)
═══════════════════════════════════════════════════════════════════════════

E1 — FORMULA DEBUG: Fix broken formulas
CONTEXT: User has spreadsheet where formulas return errors. Common
scenario where "cross-table/merged cell references cause summary errors
affecting decision accuracy."
PREREQUISITE: Launch Excel with C:\tests\spreadsheet_broken.xlsx
containing 5 intentionally broken formulas (#REF!, #VALUE!, #DIV/0!).
USER ACTION: Select cell range with broken formulas. Type "// Fix all
broken formulas in this selection. Replace error-producing formulas with
correct ones. Add comments explaining each fix."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: All formulas fixed, no errors remain. Correct values calculated.
PASS CRITERIA:
  - Zero error values (#REF!, #VALUE!, #DIV/0!) in target range
  - All cells contain valid numbers or text
  - Formulas produce correct results (verify via openpyxl or manual)
RETRY IF: Any error value persists or formula produces wrong result.

E2 — DATA ANALYSIS: Generate insights from raw data
CONTEXT: User has raw sales data but doesn't know how to analyze it.
PREREQUISITE: Launch Excel with C:\tests\spreadsheet.xlsx (500 rows of
sales data: Date, Product, Region, Revenue, Units columns).
USER ACTION: Select a cell near the data. Type "// Analyze this sales
data and add a summary section below the data. Include: top 3 products
by revenue, best performing region, monthly revenue trend, and any
notable outliers. Use actual data values in the analysis."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Summary section appears with accurate analysis. Specific
numbers from the dataset. Outliers flagged.
PASS CRITERIA:
  - Summary contains at least 4 specific data points
  - Product names and region names match actual data
  - Numbers are factually accurate (verify via formula calculation)
  - Outliers identified with specific values
RETRY IF: Data factually incorrect, or analysis generic (no specific
  numbers from the dataset).

E3 — CHART CREATION: AI-assisted visualization
CONTEXT: User needs to visualize data for a presentation.
PREREQUISITE: Launch Excel with C:\tests\spreadsheet.xlsx.
USER ACTION: Select data range (Date, Revenue columns). Type "// Create a
professional line chart showing monthly revenue trends. Add it as a new
chart sheet. Use a blue color scheme with clear axis labels and a title."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Line chart created with revenue trend, blue color scheme, axis
labels, title.
PASS CRITERIA:
  - Chart object exists in workbook (verify via openpyxl or VBA)
  - Chart type is line
  - Chart has axis labels AND title
  - Color is blue-tinted (not default)
RETRY IF: No chart created, wrong chart type, or no labels.

E4 — FORMULA GENERATION: Complex calculation assistance
CONTEXT: User needs complex formulas but isn't an Excel expert.
PREREQUISITE: Launch Excel with data table (Product, Cost, Price, Units
Sold columns across 100 rows).
USER ACTION: Select cell F2. Type "// Create a formula that calculates
total profit margin percentage for each product row: (Price - Cost) *
Units Sold / (Price * Units Sold) * 100. Apply to all 100 rows and format
results as percentage with 1 decimal place. Verify the formula works."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Correct formula applied to all rows. Results formatted as
percentages. No error values.
PASS CRITERIA:
  - Formula in F2 is correct for profit margin calculation
  - Results in all 100 rows are valid percentages (0-100%)
  - No #REF!, #VALUE!, #DIV/0! errors
  - Cells formatted as percentage with 1 decimal
RETRY IF: Formula incorrect, errors in results, or formatting wrong.

E5 — DATA CLEANING: Standardize inconsistent data
CONTEXT: User imported data from multiple sources with inconsistent
formats — mixed dates, name casing, trailing spaces, duplicates.
PREREQUISITE: Launch Excel with deliberately messy data: mixed date
formats (MM/DD/YYYY, DD-MM-YYYY, text like "Jan 15 2026"), inconsistent
name casing ("JOHN SMITH", "jane doe", "Bob Wilson"), leading/trailing
spaces, duplicate rows.
USER ACTION: Select all data. Type "// Clean this data: standardize all
dates to YYYY-MM-DD format, fix name capitalization to Proper Case,
remove leading/trailing spaces, and highlight duplicate rows in yellow.
Do not delete any rows."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Dates standardized, names in Proper Case, spaces removed,
duplicates highlighted.
PASS CRITERIA:
  - All dates in same format (YYYY-MM-DD)
  - All names in Proper Case (verify specific cells)
  - No leading or trailing spaces in any cell
  - Duplicate rows have yellow fill (not deleted)
RETRY IF: Any formatting issue persists or duplicate rows deleted.

E6 — CROSS-SHEET FORMULA: Multi-sheet VLOOKUP
CONTEXT: User needs data from Sheet2 pulled into Sheet1 based on a key.
PREREQUISITE: Excel workbook with Sheet1 (Product ID, Product Name,
Revenue) and Sheet2 (Product ID, Cost, Margin). Some Product IDs in
Sheet1 don't exist in Sheet2 (should show "N/A").
USER ACTION: Select cell D2 in Sheet1. Type "// Create a VLOOKUP formula
that pulls Cost from Sheet2 into this column for each Product ID. If the
Product ID doesn't exist in Sheet2, show N/A. Apply to all rows."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Correct VLOOKUP with IFERROR/IFNA handling. Missing IDs show
"N/A" not #N/A error.
PASS CRITERIA:
  - Formula uses VLOOKUP or XLOOKUP correctly
  - Missing IDs display "N/A" (string), not #N/A error
  - Results verified for 5 random rows (compare against Sheet2 manually)
RETRY IF: #N/A errors instead of "N/A", or wrong values pulled.

E7 — PIVOT TABLE: AI-assisted data summarization
CONTEXT: User needs a pivot table to summarize sales by Region and Product.
PREREQUISITE: Launch Excel with C:\tests\spreadsheet.xlsx.
USER ACTION: Type "// Create a pivot table summarizing total Revenue by
Region (rows) and Product (columns). Place it on a new sheet. Include
grand totals for both rows and columns."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Pivot table created on new sheet with correct structure.
PASS CRITERIA:
  - New sheet created with pivot table
  - Rows = Region, Columns = Product
  - Values = Sum of Revenue
  - Grand totals present for rows AND columns
  - Spot-check 3 values against manual SUMIF calculation
RETRY IF: Pivot table not created, structure wrong, or totals missing.

═══════════════════════════════════════════════════════════════════════════
AGENT_BROWSER — Google Docs / Yjs Collaborative (6 Scenarios)
═══════════════════════════════════════════════════════════════════════════

G1 — YJS COLLABORATIVE PEER: AI joins as document collaborator
CONTEXT: Multiple users editing a shared Google Doc. Kairo joins as a
CRDT peer with its own clientID — the differentiating feature from every
other AI copilot[reference:6].
PREREQUISITE: Two browser instances via agent-browser viewing the same
shared Google Doc. Both signed in with edit access.
USER ACTION (Browser 1): Click inside doc body. Type "// Improve this
paragraph with better structure and clarity." Select target paragraph.
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: AI-injected text appears in BOTH browser instances. AI's cursor
was visible during generation. Injected text carries data-clientid
attribute with "kairo-ai-" prefix.
PASS CRITERIA:
  - Injected text visible in both Browser 1 AND Browser 2
  - DOM inspection finds data-clientid attribute starting with "kairo-ai-"
  - Browser 2 saw AI cursor/awareness during generation (screenshot)
  - Original text replaced, not duplicated
RETRY IF: No clientID attribute, second browser doesn't show changes, or
  text duplicated.

G2 — AI AWARENESS VISIBILITY: Collaborators see AI status
CONTEXT: When Kairo generates text, other collaborators see AI cursor
with status indicator — just like a human collaborator.
PREREQUISITE: Two browser instances on same Google Doc. Browser 1
triggers ghost-write with a long prompt.
USER ACTION: In Browser 1, trigger ghost-write. During generation
(before accepting), check Browser 2.
EXPECTED: Browser 2 shows a cursor/awareness marker labeled with AI
status (e.g., "AI writing..." or configured label).
PASS CRITERIA:
  - Screenshot of Browser 2 during generation shows AI-labeled cursor or
    awareness marker
  - Awareness label is specific (not generic/empty)
  - Cursor disappears after generation completes
RETRY IF: No awareness indication visible, or label is generic.

G3 — AI UNDO IN COLLABORATIVE CONTEXT: Single Ctrl+Z reverts
CONTEXT: After AI injects text, user wants to revert. Ctrl+Z should undo
the ENTIRE AI operation as one atomic unit.
PREREQUISITE: Google Doc with AI-injected text from G1.
USER ACTION: Press Ctrl+Z once.
EXPECTED: Entire AI-injected block removed in one undo. Document returns
to pre-AI state. NOT character-by-character undo.
PASS CRITERIA:
  - AI-injected text completely removed
  - Document state matches pre-injection state (compare snapshots)
  - Only ONE Ctrl+Z was needed
  - No residual formatting or artifacts
RETRY IF: Partial undo, requires multiple Ctrl+Z, or document corrupted.

G4 — CONCURRENT HUMAN + AI EDITING: No conflicts
CONTEXT: Human and AI editing DIFFERENT paragraphs simultaneously. Must
handle without conflicts — a known failure point where "multiple people
editing the same line at the same time causes issues."
PREREQUISITE: Two browser instances. Human (Browser 1) edits paragraph 1
manually while AI ghost-writes into paragraph 5 simultaneously.
USER ACTION: Browser 1 edits paragraph 1 manually. Browser 2 triggers AI
ghost-write on paragraph 5 simultaneously. Both operations happen within
3 seconds of each other.
EXPECTED: Both edits succeed. No conflict dialog. No data loss. Both
paragraphs updated correctly with proper attribution.
PASS CRITERIA:
  - Paragraph 1 shows human edit
  - Paragraph 5 shows AI edit
  - No error dialogs appeared
  - No text lost or duplicated
  - Attribution correct (human edit shows human clientID, AI edit shows
    kairo-ai- clientID)
RETRY IF: Conflict dialog, data loss, or either edit fails.

G5 — AI INJECTION WITH MEMORY: Personal style remembered
CONTEXT: User consistently rejects bullet format in Google Docs and
rewrites as prose. Memory vault should learn this preference.
PREREQUISITE: Clean memory vault for this test. Google Doc with text.
USER ACTION:
  Session 1-3: Trigger ghost-write. When AI outputs bullet points, press
  Esc (reject). Manually type prose version.
  Session 4: Trigger ghost-write with similar prompt. Verify AI now
  outputs prose by default.
EXPECTED: By session 4, AI defaults to prose format for this user in
Google Docs.
PASS CRITERIA:
  - Session 4 output is prose (not bullet points)
  - Memory vault records show preference update
  - PAHF confidence > 0.7 for prose format
RETRY IF: AI still outputs bullet points after 3 rejections.

G6 — OFFLINE GOOGLE DOCS: Kairo works when browser is offline
CONTEXT: User has no internet but needs AI assistance in browser-based
editor. Kairo should fall back to local Ollama.
PREREQUISITE: Browser-based editor that supports offline mode. Kairo
configured with Ollama. Disconnect network.
USER ACTION: Type in the offline editor. "// Summarize this paragraph in
one sentence." Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: AI response generated via local Ollama. No network error.
PASS CRITERIA:
  - Text injected successfully
  - No "network error" or "API unavailable" message
  - Generation time within 20 seconds
RETRY IF: Network error displayed or no text generated.

═══════════════════════════════════════════════════════════════════════════
AGENT_VSCODE — Visual Studio Code (6 Scenarios)
═══════════════════════════════════════════════════════════════════════════

V1 — CODE GENERATION: From natural language comment
PREREQUISITE: Open VS Code with a TypeScript file. Cursor below comment:
"// Function that fetches user data from API, validates the response,
and returns typed User object".
USER ACTION: Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Complete TypeScript function with proper typing, error handling,
API call logic.
PASS CRITERIA:
  - Generated code is valid TypeScript (run tsc --noEmit)
  - Function name relates to comment
  - Includes type annotations (not `any`)
  - Has error handling (try/catch or .catch())
  - No hallucinated API methods (verify against actual fetch/axios API)
RETRY IF: No code generated, syntax errors, missing type safety, or
  hallucinated API.

V2 — CODE REFACTORING: Improve existing function
PREREQUISITE: VS Code with poorly written 50-line Python function (no
docstring, single-letter variables, nested if-else pyramid, no error
handling).
USER ACTION: Select entire function. Type "// Refactor this function: add
docstring, use descriptive variable names, flatten nested conditionals
with early returns, add proper error handling, and split into smaller
helper functions if appropriate. Preserve original logic."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Function refactored with all improvements. Logic preserved.
PASS CRITERIA:
  - Refactored code has docstring
  - Descriptive variable names (not a, b, c, x)
  - Early returns reduce nesting depth
  - Error handling present
  - Logic produces same output as original (run both, compare)
RETRY IF: Logic changed, or any improvement missing.

V3 — BUG FIXING: Identify and fix issues
PREREQUISITE: VS Code with Python file containing off-by-one error in
loop and incorrect variable scope bug.
USER ACTION: Select buggy function. Type "// This function produces
incorrect results. Find and fix all bugs. Add comments explaining each
fix. Verify the fix is correct."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Bugs identified and fixed. Comments explain changes. Code runs
correctly.
PASS CRITERIA:
  - Fixed code runs without errors (execute with python)
  - Produces correct output (compare against expected)
  - Comments explain EACH fix
  - Original buggy behavior eliminated
RETRY IF: Bugs not fixed, no explanatory comments, or still produces
  wrong output.

V4 — MCP SERVER INTEGRATION: Kairo invoked via MCP
PREREQUISITE: VS Code with Claude Code extension. Kairo MCP server
configured. Open markdown file with messy documentation.
USER ACTION: In Claude Code chat, type: "Use Kairo to rewrite the selected
markdown text to be clearer and more structured."
EXPECTED: Kairo ghost-writes improved markdown through MCP bridge. Text
appears in editor.
PASS CRITERIA:
  - Selected text replaced with improved version
  - Kairo JSON logs confirm an MCP kairo_ghost_write call
  - Improvement is substantive (not cosmetic)
RETRY IF: MCP call fails or text not injected.

V5 — MULTI-FILE CONTEXT: Project-wide understanding
PREREQUISITE: VS Code with multi-file TypeScript project (5+ files with
interdependencies).
USER ACTION: In main file, select a function. Type "// Analyze all files
in this project and tell me every place this function is called or
imported. List the full call chain with file paths and line numbers."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Comprehensive answer listing all call sites across files.
PASS CRITERIA:
  - Response lists at least 2 different files
  - File paths match actual project structure
  - Line references are approximately correct (±5 lines)
  - No hallucinated files that don't exist
RETRY IF: Only one file mentioned, analysis vague, or hallucinated files.

V6 — TEST GENERATION: Write unit tests
PREREQUISITE: VS Code with TypeScript utility module containing 3
exported functions (no tests exist).
USER ACTION: Select all code. Type "// Write comprehensive Jest unit
tests for all exported functions. Cover normal cases, edge cases (null,
undefined, empty arrays), and error conditions. Use describe/it blocks.
Tests must pass when run."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Test file with proper Jest structure, covering all functions
and edge cases.
PASS CRITERIA:
  - Generated code uses Jest syntax (describe/it/expect)
  - At least 2 test cases per function
  - Edge cases covered (null inputs, empty arrays, boundary values)
  - Tests pass when run (npx jest)
RETRY IF: Tests don't compile, coverage minimal, or tests fail.

═══════════════════════════════════════════════════════════════════════════
AGENT_TERMINAL — Windows Terminal (5 Scenarios)
═══════════════════════════════════════════════════════════════════════════

T1 — COMMAND GENERATION: AI writes shell commands
PREREQUISITE: Open Windows Terminal with PowerShell prompt. Directory:
C:\projects.
USER ACTION: Type "// Show me the command to find all TypeScript files
modified in the last 7 days, recursively, and list them with their sizes
sorted by size descending."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Correct PowerShell command that accomplishes the task.
PASS CRITERIA:
  - Command is valid PowerShell syntax (verify via PowerShell parser)
  - Command would find .ts files
  - Command includes date filtering AND size sorting
  - Does NOT auto-execute — just appears at prompt
RETRY IF: Invalid syntax, doesn't match request, or auto-executes.

T2 — SCRIPT GENERATION: AI writes deployment scripts
PREREQUISITE: Windows Terminal. Current directory is Node.js project
with package.json.
USER ACTION: Type "// Write a complete deployment script for this Node.js
project. Include: installing dependencies, running tests, building the
project, and deploying. Use PowerShell syntax with error handling. Add
comments explaining each step."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Complete deployment script with all steps, error handling,
comments.
PASS CRITERIA:
  - Script includes install, test, build, deploy steps
  - Has error handling (try/catch or $ErrorActionPreference)
  - Uses correct PowerShell syntax
  - Contains comments explaining each step
RETRY IF: Missing steps, no error handling, or syntax errors.

T3 — ERROR EXPLANATION: AI diagnoses command failures
PREREQUISITE: Terminal showing error: "npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree".
USER ACTION: Select error text. Type "// Explain what caused this error
and show me the exact command to fix it."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Clear explanation of dependency conflict. Specific fix command.
PASS CRITERIA:
  - Response explains ERESOLVE error in plain English
  - Provides concrete fix command (e.g., npm install --legacy-peer-deps)
  - Command is correct and would resolve the error
RETRY IF: Explanation generic, no fix command, or fix command wrong.

T4 — MULTI-STEP WORKFLOW: AI orchestrates complex operations
PREREQUISITE: Terminal at project root.
USER ACTION: Type "// Create a script that: (1) backs up database to
./backups/, (2) runs pending migrations, (3) clears Redis cache, and
(4) restarts application service. Include confirmation prompts before
each destructive action and error handling for each step."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Complete script with all 4 steps, confirmation prompts, error
handling.
PASS CRITERIA:
  - Script contains all 4 operations in correct order
  - Has confirmation prompts (Read-Host or similar)
  - Has error handling for each step
  - Step 1 runs before step 2, etc.
RETRY IF: Steps missing, wrong order, or no safety prompts.

T5 — PIPELINE DEBUGGING: AI analyzes log output
PREREQUISITE: Terminal showing CI/CD pipeline failure log (50+ lines).
USER ACTION: Paste a failing CI log. Type "// Analyze this CI failure log
and identify the root cause. Suggest the specific fix."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Root cause identified. Specific fix suggested. Not generic
"check your configuration" advice.
PASS CRITERIA:
  - Response identifies a specific error in the log
  - Suggests a concrete, actionable fix
  - Does not suggest restarting CI as the only solution
RETRY IF: Analysis generic, no specific error identified, or fix vague.

═══════════════════════════════════════════════════════════════════════════
AGENT_OBSIDIAN — Obsidian (5 Scenarios)
═══════════════════════════════════════════════════════════════════════════

O1 — DAILY NOTE: AI expands meeting bullets
PREREQUISITE: Open Obsidian. Active note is a daily note with raw meeting
notes: "Discussed Q3 goals, budget review next week, new hire starts
Monday, follow up on client proposal."
USER ACTION: Type "// Expand these meeting notes into organized summary
with action items clearly marked. Use Obsidian's [[wikilink]] format for
any references to other notes."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Notes expanded into organized summary with action items.
PASS CRITERIA:
  - Output is longer than input (expanded, not just reformatted)
  - Action items clearly marked (checkboxes or TODO)
  - Uses [[wikilink]] syntax where appropriate
  - Original topics all mentioned
RETRY IF: No expansion, action items not identifiable, or no wikilinks.

O2 — NOTE LINKING: AI suggests backlinks
PREREQUISITE: Obsidian vault with 10+ interconnected notes. User opens
note about "Q3 Planning."
USER ACTION: Type "// Analyze this note and suggest 5 relevant backlinks
to other notes in my vault that I should connect to. Include the
reasoning for each suggestion."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: 5 relevant backlink suggestions with reasoning.
PASS CRITERIA:
  - Exactly 5 suggestions provided
  - Each suggestion references a real note in the vault
  - Each has reasoning (not just a note name)
  - Suggestions are contextually relevant to Q3 Planning
RETRY IF: Fewer than 5 suggestions, notes don't exist in vault, or no
  reasoning provided.

O3 — LONG-FORM WRITING: AI structures research notes into article
PREREQUISITE: Obsidian note with 1000+ words of unstructured research
notes on a topic.
USER ACTION: Type "// Structure these research notes into a publishable
article outline with Introduction, 3-4 main sections, and Conclusion.
Add placeholder [[links]] for references I need to add later."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Structured article outline derived from the research notes.
PASS CRITERIA:
  - Output has clear Introduction, Body sections, Conclusion
  - Content drawn from original research notes (not invented)
  - Placeholder [[links]] indicated for missing references
  - Structure is logical and flows naturally
RETRY IF: Output generic/unrelated to research notes, no structure, or
  invented content not in original notes.

O4 — KNOWLEDGE GRAPH: AI extracts key concepts
PREREQUISITE: Obsidian vault with notes across multiple topics.
USER ACTION: Open a long note. Type "// Extract the 5 most important
concepts from this note and format them as atomic notes in Zettelkasten
style. Each concept should be a standalone idea."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: 5 atomic concept extractions in Zettelkasten format.
PASS CRITERIA:
  - 5 distinct concepts identified
  - Each concept is atomic (one idea per concept)
  - Derived from note content (not invented)
  - Suitable for individual note creation
RETRY IF: Fewer than 5 concepts, concepts not atomic, or invented.

O5 — TEMPLATE FILLING: AI fills Obsidian template
PREREQUISITE: Obsidian with a meeting note template (frontmatter with
YAML fields: date, attendees, agenda, decisions, action_items).
USER ACTION: Type "// Fill this meeting template for a 30-minute sync
with the engineering team about Q3 migration progress. Populate all
frontmatter fields with realistic content."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Template fields populated with relevant content.
PASS CRITERIA:
  - All frontmatter fields populated (no empty fields)
  - Content relevant to "Q3 migration" topic
  - Realistic attendee names, agenda items, decisions
  - YAML syntax valid (no parse errors)
RETRY IF: Fields left empty, content generic/unrelated, or YAML broken.

═══════════════════════════════════════════════════════════════════════════
AGENT_FIGMA — Figma (5 Scenarios)
═══════════════════════════════════════════════════════════════════════════

F1 — TEXT CONTENT: AI ghost-writes into Figma text layer
PREREQUISITE: Figma file open with a text layer selected (hero title).
USER ACTION: With text layer selected. Type "// Rewrite this hero title
to be more compelling: 'AI Document Copilot'. Make it benefit-focused
and memorable. Keep it under 60 characters."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Text layer content replaced with compelling, benefit-focused
hero title. Under 60 characters.
PASS CRITERIA:
  - Text layer content changed
  - New text is benefit-focused (not feature-description)
  - Text under 60 characters
  - Font/styling preserved (text layer properties unchanged)
RETRY IF: Text unchanged, over 60 chars, or font properties modified.

F2 — DESIGN GENERATION: AI creates a section from description
PREREQUISITE: Figma file with blank frame selected.
USER ACTION: Type "// Create a SaaS hero section in this frame with:
headline text, subheadline text, and a CTA button. Use modern clean
design with proper spacing and hierarchy."
Press Alt+M. Wait 20 seconds. Press Tab.
EXPECTED: Frame populated with text elements and a button component.
PASS CRITERIA:
  - Frame now contains at least 3 text elements
  - Button element exists (or text styled as CTA)
  - Elements have reasonable positioning (not overlapping)
  - Design hierarchy clear (headline larger than subheadline)
RETRY IF: Frame empty, elements missing, or layout broken.

F3 — DESIGN SYSTEM: AI applies consistent styles
PREREQUISITE: Figma file with 5 text layers using inconsistent fonts,
colors, and sizes.
USER ACTION: Select all text layers. Type "// Apply consistent typography:
all headings to Inter Bold 32px #1A1A1A, all body text to Inter Regular
16px #333333. Preserve the text content."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: All text layers updated with consistent typography. Content
preserved.
PASS CRITERIA:
  - All heading text layers now Inter Bold 32px #1A1A1A
  - All body text layers now Inter Regular 16px #333333
  - Text content unchanged
  - No layers skipped
RETRY IF: Styles inconsistent, content changed, or layers missed.

F4 — COMPONENT VARIANT: AI creates component variants
PREREQUISITE: Figma file with a button component (single variant).
USER ACTION: Type "// Create 3 additional variants for this button
component: Hover state (slightly darker), Disabled state (grayed out),
and Loading state (with spinner indicator)."
Press Alt+M. Wait 18 seconds. Press Tab.
EXPECTED: Button component now has 4 variants including the 3 new states.
PASS CRITERIA:
  - Component now has 4 variants (verify via Figma API)
  - Hover variant has darker background
  - Disabled variant has reduced opacity or gray colors
  - Loading variant has some indicator of progress
RETRY IF: Variants not created, fewer than 3 new variants, or states wrong.

F5 — AUTO LAYOUT: AI applies responsive layout
PREREQUISITE: Figma frame with 5 elements manually positioned (not using
Auto Layout).
USER ACTION: Select frame. Type "// Apply Auto Layout to this frame with:
vertical direction, 24px gap between items, 40px padding on all sides,
and center alignment. Preserve all content and element order."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Frame now uses Auto Layout with specified properties. Content
preserved.
PASS CRITERIA:
  - Frame has Auto Layout enabled
  - Direction is vertical
  - Gap is 24px, padding is 40px
  - Elements in original order
  - Content unchanged
RETRY IF: Auto Layout not applied, properties wrong, or content shifted.

═══════════════════════════════════════════════════════════════════════════
AGENT_SLACK — Slack/Email (5 Scenarios)
═══════════════════════════════════════════════════════════════════════════

S1 — SLACK MESSAGE: AI drafts a team announcement
PREREQUISITE: Slack desktop app open. Channel input focused.
USER ACTION: Type "// Draft a team announcement: we shipped the new
feature, deployment starts Friday 8 PM PST, rollback plan in place,
thanks to the engineering team for the late nights. Make it appreciative
but concise. Include relevant emojis."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Concise, appreciative team announcement with emojis. All key
info included.
PASS CRITERIA:
  - Message mentions the feature launch AND Friday deployment
  - Contains at least 2 relevant emojis
  - Tone is appreciative (mentions team effort)
  - Under 500 characters (Slack-friendly)
RETRY IF: Missing key info, no emojis, or tone inappropriate.

S2 — EMAIL: AI drafts a professional client email
PREREQUISITE: Outlook/Gmail compose window open.
USER ACTION: Type "// Draft a professional email to a client about a
project delay. Acknowledge the delay, provide a brief reason (supply
chain issue), propose a new timeline (2 weeks extension), and offer a
15% discount on the next invoice as compensation. Maintain a
professional, solution-oriented tone."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Professional email with all elements: acknowledgment, reason,
new timeline, compensation offer. Professional tone.
PASS CRITERIA:
  - Has subject line (auto-extracted or generated)
  - Acknowledges delay directly
  - Mentions supply chain issue
  - Proposes 2-week extension
  - Offers 15% discount
  - Tone is professional, not defensive
RETRY IF: Missing any required element, tone inappropriate, or subject
  line missing.

S3 — MEETING SUMMARY: AI summarizes long thread
PREREQUISITE: Slack with long thread (15+ messages) discussing a
technical decision.
USER ACTION: Type "// Summarize this thread in 3 key decisions made and 2
open questions that still need resolution. Use bullet points."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: 3 decisions and 2 open questions extracted from the thread.
PASS CRITERIA:
  - Exactly 3 decisions listed
  - Exactly 2 open questions listed
  - Content drawn from actual thread messages
  - Bullet point format
  - No invented decisions
RETRY IF: Wrong count, invented content, or not bullet format.

S4 — MULTILINGUAL: AI translates message
PREREQUISITE: Slack DM with message in Spanish from a colleague.
USER ACTION: Type "// Translate this message to English and draft a
polite reply in Spanish confirming I'll attend the meeting at 3 PM."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: English translation provided. Reply drafted in Spanish
confirming attendance.
PASS CRITERIA:
  - English translation is accurate (verify with translation tool)
  - Reply is in Spanish
  - Reply confirms 3 PM meeting
  - Reply is polite and grammatically correct
RETRY IF: Translation inaccurate, reply in wrong language, or missing
  meeting confirmation.

S5 — CRISIS COMMUNICATION: AI handles urgent message
PREREQUISITE: Slack/email. Urgent situation.
USER ACTION: Type "// Draft a calm, clear incident notification for the
#incidents channel. Service X is degraded (increased latency, not
completely down), engineering team is investigating, ETA 30 minutes for
update. Do not cause panic."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Calm, clear incident notification. Accurate status. No panic
language.
PASS CRITERIA:
  - Clearly states service is DEGRADED (not down)
  - Mentions engineering investigating
  - Provides ETA (30 min for next update)
  - Tone is calm and factual
  - No hyperbolic language ("CRITICAL", "EMERGENCY", "DISASTER")
RETRY IF: Overstates severity, missing ETA, or causes unnecessary alarm.

═══════════════════════════════════════════════════════════════════════════
AGENT_PDF — PDF Documents (5 Scenarios)
═══════════════════════════════════════════════════════════════════════════

PDF1 — TEXT EXTRACTION: AI reads and summarizes PDF
PREREQUISITE: Open a PDF in browser/reader. Kairo's UIA captures the
visible text.
USER ACTION: Type "// Read the visible content of this PDF and summarize
it in one paragraph. Include the document title and author if visible."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Summary paragraph with title and author if available.
PASS CRITERIA:
  - Summary is a single paragraph
  - Content matches visible PDF text (not invented)
  - Title extracted if visible
  - Author extracted if visible
RETRY IF: Summary unrelated to PDF content, or hallucinated metadata.

PDF2 — FORM FILLING: AI helps complete PDF form
PREREQUISITE: Open a fillable PDF form with empty fields.
USER ACTION: Type "// Read the form fields visible in this PDF and
suggest what to fill in each field based on context. I am John Smith,
Software Engineer, 5 years experience."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Suggestions for form fields based on user context.
PASS CRITERIA:
  - Addresses each visible form field
  - Uses provided context (John Smith, Software Engineer)
  - Suggestions are appropriate for the field type
  - Does not invent information beyond what was provided
RETRY IF: Generic suggestions, ignores user context, or invents data.

PDF3 — CONTRACT REVIEW: AI flags risky clauses
PREREQUISITE: Open a contract PDF. User wants risk assessment.
USER ACTION: Type "// Review the visible contract text and flag any
clauses that could be risky for a small business signing with a large
vendor. Identify at least 3 potential concerns if present."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: At least 3 flagged concerns with specific clause references.
PASS CRITERIA:
  - At least 3 potential concerns identified
  - Each concern references specific clause text
  - Explanations are business-relevant (not generic legal warnings)
  - Does not flag standard boilerplate as risky
RETRY IF: Fewer than 3 concerns, explanations generic, or flags innocuous
  clauses.

PDF4 — DATA EXTRACTION: AI extracts structured data from PDF
PREREQUISITE: Open a PDF containing a table or structured data.
USER ACTION: Type "// Extract the table data visible in this PDF and
format it as a CSV-ready text block with headers. Preserve all numeric
values exactly as shown."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: CSV-ready text with headers. Numeric values preserved.
PASS CRITERIA:
  - Output contains comma-separated values or clear table structure
  - Headers present
  - Numeric values match visible PDF content
  - Row count matches visible table
RETRY IF: Data format wrong, numbers changed, or rows missing.

PDF5 — ANNOTATION: AI suggests PDF annotations
PREREQUISITE: Open a research paper PDF.
USER ACTION: Type "// Read the visible section and suggest 3 annotations
I should add: one question, one connection to another topic, and one key
takeaway. Format as: Q: [...], Connection: [...], Key: [...]"
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: 3 annotations in specified format, derived from content.
PASS CRITERIA:
  - Question, Connection, and Key sections all present
  - Content derived from PDF text (not generic)
  - Format matches Q:/Connection:/Key: structure
RETRY IF: Missing sections, generic content, or wrong format.

═══════════════════════════════════════════════════════════════════════════
AGENT_NOTEPAD — Windows Notepad (4 Scenarios)
═══════════════════════════════════════════════════════════════════════════

N1 — QUICK NOTE: AI expands brief notes
PREREQUISITE: Open Notepad with: "Meeting notes: discussed Q3 goals,
budget review next week, new hire starts Monday, follow up on client
proposal."
USER ACTION: Type "// Expand these notes into a clear summary with
action items clearly marked."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Notes expanded. Action items marked.
PASS CRITERIA:
  - Output longer than input
  - Action items clearly marked ([ ] or TODO)
  - Original topics all mentioned
RETRY IF: No expansion or action items not identifiable.

N2 — OFFLINE MODE: AI works without internet
PREREQUISITE: Disconnect network. Open Notepad.
USER ACTION: Type "// Write a short poem about AI in 4 stanzas."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: 4-stanza poem via local Ollama. No network error.
PASS CRITERIA:
  - Poem with approximately 4 stanzas
  - No network/connectivity error
  - Generated in under 20 seconds
RETRY IF: Network error or no text generated.

N3 — TEXT TRANSFORMATION: Encoding fix
PREREQUISITE: Notepad with text containing smart quotes, em-dashes,
mixed line endings (CRLF and LF).
USER ACTION: Type "// Convert smart quotes to straight quotes, em-dashes
to double hyphens, normalize line endings to CRLF."
Press Alt+M. Wait 8 seconds. Press Tab.
EXPECTED: Smart quotes converted, em-dashes replaced, line endings uniform.
PASS CRITERIA:
  - No smart quote characters remain
  - No em-dash characters remain
  - All line endings are CRLF
RETRY IF: Special characters persist or line endings inconsistent.

N4 — PROMPT DELIMITER TEST: Kairo ignores text without //
PREREQUISITE: Notepad with text: "I think we should improve this section
but I'm not sure how." (NO // prefix).
USER ACTION: Press Alt+M WITHOUT typing //. Just have regular text in
Notepad. Then press Alt+M.
EXPECTED: NOTHING happens. Kairo stays silent because no // delimiter.
PASS CRITERIA:
  - No ghost overlay appears
  - No text injected
  - Kairo remains idle
  - No error messages
RETRY IF: Kairo activates without // delimiter.

═══════════════════════════════════════════════════════════════════════════
AGENT_NOTION — Notion (4 Scenarios)
═══════════════════════════════════════════════════════════════════════════

NO1 — PAGE CREATION: AI generates structured page
PREREQUISITE: Notion workspace open. User in a database or page.
USER ACTION: Type "// Create a project kickoff page with sections for:
Objectives, Timeline, Team, Risks, and Success Metrics. Use Notion's
toggle blocks for each section."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Structured page with all sections as toggles.
PASS CRITERIA:
  - All 5 sections present
  - Sections use toggle structure (or equivalent)
  - Content relevant to "project kickoff"
  - No empty sections
RETRY IF: Sections missing, not toggles, or empty.

NO2 — DATABASE ENTRY: AI populates database row
PREREQUISITE: Notion database with columns: Task Name, Assignee, Due
Date, Priority, Status.
USER ACTION: Type "// Create a new entry: 'Review Q3 vendor contracts',
assigned to Legal Team, due next Friday, High priority, Not started."
Press Alt+M. Wait 10 seconds. Press Tab.
EXPECTED: Database row created with specified values.
PASS CRITERIA:
  - Task Name: "Review Q3 vendor contracts"
  - Assignee: Legal Team
  - Due Date: next Friday (correct date)
  - Priority: High
  - Status: Not started
RETRY IF: Values wrong, row not created, or fields mismatched.

NO3 — WIKI UPDATE: AI enhances documentation
PREREQUISITE: Notion wiki page with outdated content.
USER ACTION: Type "// Update this documentation page to reflect that
the API v2 endpoint has been deprecated and replaced with v3. Add a
deprecation notice at the top."
Press Alt+M. Wait 12 seconds. Press Tab.
EXPECTED: Deprecation notice added. Content updated to reference v3.
PASS CRITERIA:
  - Deprecation notice at top of page
  - Content now references v3 (not v2)
  - Notice is clearly visible (callout or colored block)
RETRY IF: No deprecation notice, still references v2, or notice hidden.

NO4 — MEETING NOTES: AI structures raw notes into Notion page
PREREQUISITE: Raw meeting notes pasted into Notion.
USER ACTION: Type "// Structure these raw notes into a Notion page with:
Meeting Details (date, attendees), Discussion Points, Decisions Made,
Action Items (with @mentions for assignees)."
Press Alt+M. Wait 15 seconds. Press Tab.
EXPECTED: Structured page with all sections. @mentions for action items.
PASS CRITERIA:
  - All 4 sections present
  - Date and attendees populated
  - Action items have @mentions
  - Content derived from raw notes
RETRY IF: Sections missing, no @mentions, or content unrelated.

═══════════════════════════════════════════════════════════════════════════
AGENT_CHAOS — Background Fault Injection
═══════════════════════════════════════════════════════════════════════════

Run scripts\win\chaos_advanced.ps1 continuously on every test machine.
Cycle through:
- Network adapter disable/enable (30-90 second random intervals)
- Clipboard clearing (random intervals)
- CPU spike (20-30 second bursts)
- Windows Firewall outbound block on kairo-phantom.exe (20-30 sec bursts)
- Randomly suspend Kairo process for 5 seconds

The chaos agent must NOT be stopped. All tests must pass WITH chaos active.

═══════════════════════════════════════════════════════════════════════════
SUCCESS THRESHOLD FOR PRODUCTION READINESS
═══════════════════════════════════════════════════════════════════════════

Kairo Phantom is declared PRODUCTION READY only when:
- ALL 76 scenarios across ALL 12 agents pass (exit code 0)
- At least 70 of 76 pass on FIRST attempt (no retries)
- No scenario requires more than 2 retries
- Chaos monkey was active for entire duration
- Zero application crashes during testing
- Kairo Phantom process did not crash or memory-leak
- Zero system prompt leakage events across ALL scenarios
- // delimiter protocol works correctly (N4 passes)
- Memory vault records correct preferences after each session

═══════════════════════════════════════════════════════════════════════════
ORCHESTRATION COMMANDS
═══════════════════════════════════════════════════════════════════════════

Deploy all agents simultaneously via GSD:

gsd deploy agent_word --scenarios W1,W2,W3,W4,W5,W6,W7,W8,W9,W10
gsd deploy agent_ppt --scenarios P1,P2,P3,P4,P5,P6,P7
gsd deploy agent_excel --scenarios E1,E2,E3,E4,E5,E6,E7
gsd deploy agent_browser --scenarios G1,G2,G3,G4,G5,G6
gsd deploy agent_vscode --scenarios V1,V2,V3,V4,V5,V6
gsd deploy agent_terminal --scenarios T1,T2,T3,T4,T5
gsd deploy agent_notepad --scenarios N1,N2,N3,N4
gsd deploy agent_obsidian --scenarios O1,O2,O3,O4,O5
gsd deploy agent_notion --scenarios NO1,NO2,NO3,NO4
gsd deploy agent_figma --scenarios F1,F2,F3,F4,F5
gsd deploy agent_slack --scenarios S1,S2,S3,S4,S5
gsd deploy agent_pdf --scenarios PDF1,PDF2,PDF3,PDF4,PDF5
gsd deploy agent_chaos --continuous

═══════════════════════════════════════════════════════════════════════════
REPORTING
═══════════════════════════════════════════════════════════════════════════

After all agents complete, aggregate into:
{
  "test_run_id": "kairo-full-gauntlet-<timestamp>",
  "chaos_active": true,
  "total_scenarios": 76,
  "passed": X,
  "failed": X,
  "first_attempt_pass_rate": "X%",
  "system_prompt_leakage_events": X,
  "production_ready": true/false,
  "agent_results": {
    "agent_word": {"passed": X, "failed": X, "scenarios": {...}},
    "agent_ppt": {...},
    ...
  }
}

Save to C:\tests\results\MASTER_GAUNTLET_REPORT.json