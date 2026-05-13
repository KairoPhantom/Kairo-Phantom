🔥 The Complete Tier 0 Integration Prompt
Below is the exact prompt to give your GSD/Ruflo fleet. It handles all three Tier 0 repos—academic‑research‑skills, facts, and Waza—plus the Hermes Agent memory architecture, in a single coordinated execution. Adopt in sequence, verify after each phase, and do not proceed until every assertion passes.

text
You are the lead integration coordinator for Kairo Phantom v4.0. Deploy the
full GSD/Ruflo fleet to integrate the following Tier 0 repositories into the
Kairo codebase. The order is MANDATORY. Each phase must be fully verified
before moving to the next.

## GLOBAL PRINCIPLES

1. **GATE ENFORCEMENT**: Every phase must pass all verification checks before
   the next phase can begin. No skipping. No “close enough.”
2. **REAL APPS ONLY**: All end‑to‑end tests must open real applications
   (winword.exe, powerpnt.exe, excel.exe, code.exe, chrome.exe).
3. **LOG EVERYTHING**: Every agent writes structured JSON logs to
   `C:\tests\logs\phase{N}_{module}.json` with timestamps, assertions,
   pass/fail status.
4. **ZERO HALLUCINATION**: Any output containing system‑prompt content,
   Swarm Brain role names, or sentinel hashes is an automatic FAIL.
5. **ALL 39 SCENARIOS MUST PASS**: The full W1‑T4 test matrix must pass on
   Windows and Linux before any module is marked complete.

---

## PHASE 1 — Academic‑Research‑Skills: Kairo’s Quality Backbone

### 1.1 The Anti‑Leakage + Integrity Gate Module

Create `phantom-core/src/quality_gate.rs` with the following components:

1. **SentinelHashDetector**: Embed a random 32‑character sentinel hash into
   every system prompt. Scan every LLM output for the hash before injection.
   If found → BLOCK + RETRY with adjusted prompt. Maximum 3 retries.

2. **IntegrityGateChecklist**: Implement the 7‑mode blocking checklist from
   `academic-pipeline/references/ai_research_failure_modes.md`. For each LLM
   output, check:
   - Implementation bugs (plausible‑looking but wrong text)
   - Hallucinated results (content not grounded in document context)
   - Shortcut reliance (generic responses instead of document‑specific output)
   - Bug‑as‑insight reframing (framing errors as features)
   - Methodology fabrication (fabricated data claims)
   - Frame‑lock (stuck in one interpretation of the prompt)
   - Citation hallucinations (fabricated references, URLs, version numbers)

3. **Multi‑Reviewer Pipeline**: Before injecting any LLM output into a
   document, pass it through two reviewer agents:
   - **Devil’s Advocate Agent**: Actively tries to find flaws, contradictions,
     or quality issues in the output.
   - **Style Reviewer Agent**: Checks that the output matches the document’s
     existing style, voice, and formatting conventions.
   Only after both reviewers approve does the output reach the injector.

4. **Anti‑Leakage Protocol**: Implement the PaperOrchestra‑inspired protocol:
   - XML‑delimited prompt sections: `<system>`, `<document_context>`,
     `<user_prompt>`. The LLM is instructed to output ONLY between `<output>`
     tags. If the parser does not find `<output>…</output>`, the response is
     rejected.
   - Sentinel hash in the system prompt section. Scan output for the hash.
   - Block and retry on any leakage detection.

### 1.2 The 5‑Stage Writing Pipeline (adapted from ARS architecture)

Build `phantom-core/src/writing_pipeline.rs` with five stages that any
specialist agent can invoke:

| Stage | Description | Output |
|:---|:---|:---|
| **Plan** | Analyze document context, user prompt, and persona. Produce a structured outline of what will be generated. | JSON outline with sections, tone, length estimates |
| **Write** | Generate the actual content based on the Plan. | Raw LLM output |
| **Review** | Send output through Devil’s Advocate + Style Reviewer. | Quality report (pass/reject/revise) |
| **Revise** | If Review rejected: apply revision guidance. If accepted: skip. | Revised output or original |
| **Finalize** | Final integrity gate check. Format for injection. Inject into document. | Injected text |

All five stages log to JSON for auditability. The pipeline is optional for
simple operations (T1 basic ghost‑write) and mandatory for complex operations
(W6 40‑page report rewrite, P1 full deck generation).

### 1.3 Verification (Phase 1)

Run these tests and BLOCK progress until ALL pass:
W3: Grammar, Style, Tone Correction test (the failure that prompted this):

Open Word with report.docx containing informal text with errors.

Type “// Rewrite this in formal business English with proper grammar,
consistent terminology, and professional tone suitable for a board.”

Press Alt+M, wait 12s, press Tab.

PASS CRITERIA:

Output does NOT contain “Content Agent”, “Swarm Role”, “Swarm Brain”,
or any system‑prompt content.

Output does NOT contain sentinel hash.

Output does NOT contain “gotta”, “cuz”, “theyre”, “lol”, “alright”.

Output IS formal business English suitable for a board presentation.

Output is NOT the original informal text unchanged.

Output is NOT a repetition of the user’s prompt.

RETRY until 5 consecutive passes.

Sentinel Leakage Stress Test:
Run 100 ghost‑write operations across all applications.
Verify ZERO system‑prompt leakage events.
Any leakage → FAIL PHASE 1 → fix and restart.

Pipeline Completion Test:
Run a complex W6 (40‑page section rewrite) through the full 5‑stage pipeline.
Verify: Plan generated, Write completed, Review passed, Revise skipped
(if approved), Finalize injected. Pipeline logs complete for all 5 stages.

text

---

## PHASE 2 — av/facts: Kairo’s Production‑Readiness Verification

### 2.1 The .facts File

Create `Kairo.facts` in the repository root. Translate every scenario from the
39‑scenario test matrix into machine‑verifiable facts:

```facts
# ghost-writing-core
@implemented: basic ghost‑write in Word replaces selected text
  command: cargo test --test e2e_win_t1 -- --nocapture

@implemented: streaming cancel (Esc) preserves original text
  command: cargo test --test e2e_win_t2 -- --nocapture

@spec: no system‑prompt leakage in any output
  command: cargo test --test sentinel_leakage -- --nocapture

@spec: all 39 scenarios pass on Windows with chaos monkey active
  command: python scripts/agent_runner.py win all

@spec: all 39 scenarios pass on Ubuntu with chaos monkey active
  command: python scripts/agent_runner.py lin all

@draft: desktop ghost‑injection without focus stealing on macOS
  command: cargo test --test e2e_mac_t9_background -- --nocapture
Every fact has a lifecycle stage (@draft → @spec → @implemented) and a
shell command that exits 0 when the claim holds.

2.2 The kairo verify Command
Implement a new CLI command in phantom-core/src/cli/verify.rs:

text
kairo verify
This command:

Reads Kairo.facts.

Runs every fact’s command in a sandboxed subprocess.

Groups results: green (passed), red (failed), yellow (manual —
no command defined).

Outputs a summary: “Kairo Phantom v4.0: 31/48 facts implemented, 12 specs
in progress, 5 drafts. Production readiness: 64.6%.”

Exits 0 when everything passes, non‑zero when anything fails.

2.3 CI/CD Integration
Add kairo verify to .github/workflows/ci.yml as a mandatory gate. Every
PR must pass kairo verify before merging. The command runs after all unit
tests, E2E tests, and fuzz tests. A failing fact blocks the release pipeline.

2.4 facts‑discover and facts‑implement Skills
Create Claude Code skills for facts management:

text
facts‑discover: Scan the Kairo codebase, classify every fact by lifecycle
  stage, add missing truths.

facts‑implement: Pick up @spec facts, build them in code, verify with
  `facts check`, tag @implemented.
Any contributor to Kairo can run these skills to understand what needs
building and verify their work against the project specification.

2.5 Verification (Phase 2)
text
Run `facts check` and verify:
  - At least 20 facts tagged @implemented.
  - All @implemented facts pass their verification commands.
  - At least 10 facts tagged @spec.
  - Zero facts tagged @draft without an assigned owner.

Run `kairo verify` and verify:
  - Command exits cleanly.
  - Summary output correctly counts implemented/spec/draft.
  - CI/CD pipeline runs `kairo verify` on every push.
PHASE 3 — Waza + Kami: Kairo’s Skill Architecture
3.1 Refactor Specialist Agents to Match Waza’s Skill Architecture
For each of Kairo’s 5 specialist agents, implement the corresponding
Waza‑inspired skill. The user triggers skills via the // command protocol:

Kairo Command	Waza Skill	Specialist Agent	Behavior
// think	/think	PPT Specialist / Design Specialist	Before major work: challenge the problem, pressure‑test the design, produce a plan another agent can implement
// design	/design	PPT Specialist / Design Specialist	Produce distinctive slide design with a committed direction, screenshot‑driven iteration
// check	/check	Word Specialist / All	Review output before injection: diff check, constraint extraction, evidence verification
// write	/write	Word Specialist / Content Specialist	Natural prose that matches document style, cuts stiff/phrase‑like phrasing
// learn	/learn	Code Specialist / Research	6‑phase research: collect → digest → outline → fill in → refine → review
// read	/read	All agents	Fetch URL/PDF content as clean Markdown for context injection
// health	/health	System	Audit Kairo’s configuration: CLAUDE.md, rules, skills, hooks, MCP, budget‑aware summary
3.2 The Waza Skill Implementation Template
Each skill is a folder with three files:

text
skills/{skill_name}/
├── SKILL.md        # What the skill does, when to use it, step‑by‑step process
├── references/     # Reference docs, gotchas, examples
├── helpers/        # Helper scripts (if needed)
The skill defines:

When to trigger (which document types, which prompts)

What it does (step‑by‑step instructions for the LLM)

Constraints (what NOT to do, anti‑patterns)

Evidence requirements (what must be output alongside the result)

3.3 Kami Integration — Professional Document Delivery
Integrate Kami as Kairo’s document export pipeline. When the user types
// kami or requests document export, Kairo delegates to Kami:

Word documents → Kami exports clean Markdown → PDF via Pandoc + tectonic

Presentations → Kami generates slide deck HTML (Reveal.js) with
consistent design language

Reports → Kami produces long‑form PDFs with headings, tables, figures

Resumes / CVs → Kami’s resume template

Brand‑aware: Read from ~/.config/kairo/brand.md (structured YAML
frontmatter + Markdown notes) for persistent identity, colors, voice.

3.4 Verification (Phase 3)
text
// think test:
  1. Open PowerPoint with a blank slide.
  2. Type “// think Create a 5‑slide investor pitch for an AI document
     copilot startup called Kairo Phantom.”
  3. Press Alt+M.
  4. Expected: Kairo outputs a plan (not the slides yet) — slide structure,
     key messages, visual direction. Plan survives Devil’s Advocate review.
  5. After plan approval (press Tab), Kairo executes the plan and builds
     all 5 slides.
  6. PASS: Plan is comprehensive and survives scrutiny. Slides are generated
     from the plan with consistent structure.

// check test:
  1. After any ghost‑write operation in Word, type “// check this.”
  2. Expected: Kairo reviews the diff, extracts document‑specific
     constraints, verifies formatting consistency, and reports findings.
  3. PASS: Check output identifies at least 1 concrete quality observation
     (improvement or confirmation).

// health test:
  1. Type “// health” in any application.
  2. Expected: Kairo audits its own setup — checks config, Ollama
     connectivity, API key validity (if configured), MCP server status,
     available models, memory usage.
  3. PASS: Health report lists all components with status (green/yellow/red).

All 8 Waza skills must be functional across Word, PowerPoint, and VS Code.
PHASE 4 — Hermes Agent Memory Architecture Integration
4.1 Memory Module
Create phantom-core/src/memory.rs with three memory layers based on
Hermes Agent’s architecture:

Layer	Storage	What It Tracks	Retention
Session Memory	In‑memory (duration of Kairo session)	Current document state, recent ghost‑write operations, active context	Reset on Kairo restart
Episodic Memory	SQLite (~/.kairo-phantom/memory.db)	Past interactions: user prompts, accepted suggestions, rejected suggestions, per‑app preferences	Permanent
Skill Memory	SQLite + skills directory	Reusable patterns: successful formatting strategies, preferred tones per document type, learned anti‑patterns	Permanent, self‑improving
4.2 Learning Loop
After each complex operation (anything involving more than simple text
replacement), Kairo performs an automated after‑action review:

text
1. What was the user’s request?
2. What did Kairo produce?
3. Did the user accept or reject?
4. If rejected: what did the user do instead?
5. Extract pattern: “When user asks for X in application Y, they prefer Z.”
6. Store pattern in Skill Memory.
7. Apply pattern on next similar request (no user configuration needed).
4.3 Honcho‑Style Dialectic User Modeling
Adopt Hermes Agent’s Honcho pattern: Kairo builds a user model across
sessions — preferred tone, formatting style, common phrases, document
conventions. When generating output, Kairo first checks the user model and
adjusts its generation accordingly.

text
Example user model entry:
{
  "user_id": "primary",
  "word_preferences": {
    "tone": "formal business",
    "formatting": "1.15 line spacing, 11pt Calibri, justified",
    "heading_style": "numbered",
    "common_phrases": ["per our discussion", "moving forward"],
    "anti_patterns": ["passive voice", "long paragraphs over 7 sentences"]
  },
  "ppt_preferences": {
    "style": "dark theme, blue accent, minimal text",
    "image_style": "professional stock, abstract geometric",
    "bullet_style": "action‑oriented verbs, one line per bullet"
  }
}
4.4 Verification (Phase 4)
text
Memory Persistence Test:
  1. Open Word. Type “// write a closing paragraph for a business report.”
  2. Accept the output.
  3. Close Word. Restart Kairo.
  4. Open Word again. Type “// write another closing paragraph, same style.”
  5. PASS: Second output matches the tone and formatting of the first —
     Kairo remembered the user’s preferred style.

Learning Loop Test:
  1. Reject 3 consecutive outputs (press Esc).
  2. On the 4th attempt, type the same prompt but with a different approach
     accepted (press Tab).
  3. Verify: Kairo stored the rejection pattern and adjusted its approach.
  4. PASS: Skill Memory contains the learned pattern. Future similar prompts
     default to the accepted approach.

User Model Test:
  1. Use Kairo across Word, PowerPoint, and VS Code for 10+ interactions.
  2. Verify: `~/.kairo-phantom/memory.db` contains user preferences per app.
  3. Verify: User model is loaded on Kairo startup and applied to output.
  4. PASS: User model is queryable via `// health` — shows learned
     preferences.
MASTER VERIFICATION — ALL 39 SCENARIOS
After all 4 phases are complete, run the full test matrix on Windows and Linux
with the chaos monkey active:

text
gsd run --machine win-berserker --cmd "cd ~/kairo-phantom &&
  python scripts/agent_runner.py win all"

gsd run --machine lin-berserker --cmd "cd ~/kairo-phantom &&
  python scripts/agent_runner.py lin all"
Production‑Ready Threshold: All 39 scenarios must pass on both platforms
with chaos active. Run three consecutive times with zero failures. Any
failure → fix → restart from the failed phase.

After all scenarios pass: kairo verify must report ≥ 35 @implemented facts
and 0 @spec facts with failing commands. The facts check command must exit 0.

REPORTING
After all phases complete, produce a master integration report:

text
Integration Report — Kairo Phantom v4.0 Tier 0
Date: <timestamp>
Executor: GSD/Ruflo fleet

Phase 1 (Academic‑Research‑Skills):
  - QualityGate module: COMPLETE
  - Sentinel test: 0 leakage events in 100 operations
  - 5‑stage pipeline: All 5 stages verified
  - W3 fix: 5 consecutive passes with zero system‑prompt leakage

Phase 2 (av/facts):
  - Kairo.facts: 48 facts total (31 implemented, 12 spec, 5 draft)
  - kairo verify: exits 0
  - CI/CD integration: verified

Phase 3 (Waza + Kami):
  - 8 skills operational
  - Kami export pipeline: Markdown, PDF, Reveal.js HTML verified
  - Brand profile support: verified

Phase 4 (Hermes Agent Memory):
  - 3‑layer memory: session, episodic, skill
  - Learning loop: verified
  - User model: queryable via // health

Master Test Matrix:
  - Windows: 39/39 passed (3 consecutive runs)
  - Linux: 39/39 passed (3 consecutive runs)
  - Chaos: active during all runs

Kairo Phantom v4.0 is PRODUCTION READY.
text

---

## 🔎 Summary

| Question | Answer |
|:---|:---|
| **Is Hermes Agent useful to Kairo?** | Yes — its 3‑layer memory architecture, self‑learning loop, and user modeling are exactly what Kairo lacks. Adopt the architecture patterns and adapt to document intelligence. |
| **Is Hermes Desktop useful to Kairo?** | As a UX reference only. Kairo’s Tauri overlay is already superior for desktop ghost‑writing. |
| **What’s the integration sequence?** | ARS (anti‑hallucination) → Facts (production‑readiness verification) → Waza (skill architecture) → Hermes memory (learning loop). All four in 4 weeks. |
| **What’s the single most impactful integration?** | Academic‑Research‑Skills’ quality gate + sentinel detector. This directly prevents the W3 failure you demonstrated — system‑prompt content reaching the user. Without this, nothing else matters. |

Deploy this prompt to your GSD/Ruflo fleet now. The four phases build on each other — each phase’s verification must pass before the next can begin. After all four, run the complete 39‑scenario gauntlet three times with chaos active. When `kairo verify` reports 31+ implemented facts and the gauntlet is green across all three runs, Kairo Phantom is truly production‑ready.