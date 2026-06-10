"""Single-scenario tester. Usage: python test_scenario.py W1 [W2 W3 ...]
Run all: python test_scenario.py ALL
"""
import sys, requests, time, re, os

API = "http://127.0.0.1:7437"

def ask(prompt, context=""):
    full = f"{context}\n\n{prompt}" if context else prompt
    try:
        r = requests.post(f"{API}/ask", json={"prompt": f"// {full}"}, timeout=90)
        out = r.json().get("response", "") if r.status_code == 200 else f"ERR:{r.status_code}"
        out = re.sub(r'</?output>', '', out).strip().removeprefix('[REPLACE]').strip()
        return out
    except Exception as e:
        return f"EXCEPTION:{e}"

def chk(fn, desc):
    """Wrap a lambda into a (bool, desc) checker."""
    return lambda o: (bool(fn(o)), desc)

def notes():
    p = "C:/tests/notes.txt"
    return open(p).read() if os.path.exists(p) else "Meeting: launch Kairo, fix memory bug, review investor deck"

def buggy():
    p = "C:/tests/vscode-buggy/buggy.py"
    return open(p).read() if os.path.exists(p) else "def avg(nums):\n  for i in range(len(nums)+1):\n    total+=nums[i]"

SCENARIOS = {
# ── WORD ──────────────────────────────────────────────────────────────────────
"W1": {
  "prompt": "Write an executive summary for a Q3 2026 quarterly business review covering revenue growth, market expansion, and team headcount. Use professional business tone with headings.",
  "checks": [
    chk(lambda o: "revenue" in o.lower(), "has 'revenue'"),
    chk(lambda o: "market" in o.lower(), "has 'market'"),
    chk(lambda o: "headcount" in o.lower() or "team" in o.lower(), "has headcount/team"),
    chk(lambda o: len(o) > 200, "length > 200 chars"),
    chk(lambda o: not any(x in o for x in ["Content Agent","Swarm Role","[insert here]","TBD"]), "no leakage"),
  ]
},
"W2": {
  "prompt": "Fix all formatting inconsistencies: make line spacing 1.15, ensure body text is 11pt Calibri, fix broken numbering in lists, justify all paragraphs. Describe what changes to make.",
  "checks": [
    chk(lambda o: len(o) > 50, "has content"),
    chk(lambda o: "calibri" in o.lower() or "font" in o.lower() or "spacing" in o.lower(), "mentions formatting"),
    chk(lambda o: not any(x in o for x in ["Content Agent","Swarm Role"]), "no leakage"),
  ]
},
"W3": {
  "context": "we gotta improve our numbers cuz theyre not looking good lol. The team did alright but we need way more customers.",
  "prompt": "Rewrite this in formal business English with proper grammar, consistent terminology, and professional tone suitable for a board presentation.",
  "checks": [
    chk(lambda o: not any(w in o.lower() for w in ["gotta","cuz","lol","alright"]), "no slang"),
    chk(lambda o: len(o) > 30, "has content"),
    chk(lambda o: any(w in o.lower() for w in ["improve","performance","results","customers","growth"]), "has formal words"),
  ]
},
"W4": {
  "context": "Table: Q1 Sales: North $1.2M, South $0.9M, East $1.4M, West $0.7M. Total: $4.2M",
  "prompt": "Summarize this table data into 3 bullet points highlighting key insights and totals.",
  "checks": [
    chk(lambda o: any(x in o for x in ["•","- ","* ","1.","2.","3."]), "has bullets"),
    chk(lambda o: any(c.isdigit() for c in o), "has numbers"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
"W5": {
  "context": "NON-DISCLOSURE AGREEMENT — Section 5: TERM. This Agreement shall remain in effect for 3 years from signing.",
  "prompt": "Add a clause after Section 5 stating that both parties agree to a 90-day review period before the agreement expires.",
  "checks": [
    chk(lambda o: "90" in o or "ninety" in o.lower(), "has 90-day"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
"W6": {
  "prompt": "Write a concise Section 3: Market Expansion Strategy for a business report. Include sub-sections for target markets, expansion timeline, and success metrics. Keep all heading structure.",
  "checks": [
    chk(lambda o: "market" in o.lower() or "expansion" in o.lower(), "mentions market/expansion"),
    chk(lambda o: len(o) > 100, "substantial content"),
  ]
},
"W7": {
  "context": "Document has: 3 headings (Introduction, Analysis, Conclusion), 2 bullet lists, 1 blockquote, 1 code block, 5 body paragraphs describing Q3 results.",
  "prompt": "Rewrite only the body paragraphs in a more concise style. Keep all headings, lists, blockquotes, and code blocks exactly as they are.",
  "checks": [
    chk(lambda o: len(o) > 50, "has content"),
    chk(lambda o: not any(x in o for x in ["Content Agent","Swarm Role"]), "no leakage"),
  ]
},
"W8": {
  "context": "Our Q3 revenue achieved $2.3M representing a 15% year-over-year growth rate. The organization successfully expanded into three new geographic markets.",
  "prompt": "Rewrite this in a casual, friendly tone for a team Slack message. Add emojis to make it engaging.",
  "checks": [
    chk(lambda o: any(e in o for e in ["🎉","💪","🚀","✅","🔥","👏","📈","🌟","😊","⭐","🎊","💰"]), "has emoji"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
"W9": {
  "prompt": "Restructure a business report so sections appear in this exact order: Introduction, Methodology, Results, Conclusion, References. Provide the restructured outline with brief description of each section.",
  "checks": [
    chk(lambda o: all(s in o for s in ["Introduction","Methodology","Results","Conclusion"]), "has all sections"),
    chk(lambda o: len(o) > 80, "substantial outline"),
  ]
},
"W10": {
  "prompt": "Describe how to fix style corruption in a Word document: all body text to Normal style, headings to Heading 1/2/3, maximum 5 distinct styles total.",
  "checks": [
    chk(lambda o: any(x in o.lower() for x in ["normal","heading","style"]), "mentions styles"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
# ── NOTEPAD ───────────────────────────────────────────────────────────────────
"N1": {
  "context": notes(),
  "prompt": "Expand these brief meeting notes into full meeting minutes with action items clearly marked. Use [ACTION ITEM] prefix for tasks.",
  "checks": [
    chk(lambda o: len(o) > 100, "output longer than input"),
    chk(lambda o: any(x in o.lower() for x in ["action","task","[action"]), "has action items"),
  ]
},
"N2": {
  "prompt": "Write a short poem (4 stanzas) about artificial intelligence and human creativity working together.",
  "checks": [
    chk(lambda o: len(o) > 50, "has content"),
    chk(lambda o: not any(x in o for x in ["Content Agent","Swarm Role"]), "no leakage"),
  ]
},
"N3": {
  "context": "He said \u201cHello\u201d and she replied \u2018yes\u2019 \u2014 they agreed on the plan.",
  "prompt": "Replace all smart/curly quotes with straight ASCII quotes and all em-dashes with regular hyphens. Return only the corrected text.",
  "checks": [
    chk(lambda o: "\u201c" not in o and "\u201d" not in o and "\u2018" not in o and "\u2019" not in o, "no smart quotes"),
    chk(lambda o: len(o) > 5, "has content"),
  ]
},
"N4": {
  "prompt": "Plain text test — no double-slash prefix — what happens?",
  "checks": [
    chk(lambda o: len(o) < 1000, "response under 1000 chars (minimal action)"),
  ]
},
# ── EXCEL ─────────────────────────────────────────────────────────────────────
"E1": {
  "context": "Spreadsheet errors:\nRow3: formula =D3/E3 shows #DIV/0! (E3 is 0)\nRow4: formula =D4*E4 shows #VALUE! (E4 contains #REF!)\nRow5: formula =D5/0 shows #DIV/0!",
  "prompt": "Explain each formula error and provide the corrected formula for each row.",
  "checks": [
    chk(lambda o: "#DIV/0!" in o or "divide" in o.lower() or "division" in o.lower(), "explains DIV/0"),
    chk(lambda o: "#VALUE!" in o or "value" in o.lower(), "explains VALUE"),
    chk(lambda o: len(o) > 80, "detailed response"),
  ]
},
"E2": {
  "context": "Monthly sales data: Jan $45K, Feb $52K, Mar $48K, Apr $61K, May $58K, Jun $67K. Target was $50K/month.",
  "prompt": "Analyze this sales data and provide 4+ key insights with specific numbers. Note trends, above/below target months.",
  "checks": [
    chk(lambda o: any(c.isdigit() for c in o), "has numbers"),
    chk(lambda o: len(o) > 100, "substantial insights"),
    chk(lambda o: "trend" in o.lower() or "growth" in o.lower() or "target" in o.lower(), "mentions trends/target"),
  ]
},
"E3": {
  "context": "Columns: Month, Revenue($K): Jan 45, Feb 52, Mar 48, Apr 61, May 58, Jun 67",
  "prompt": "Describe step-by-step how to create a line chart in Excel showing monthly revenue trend with axis labels and chart title 'H1 2026 Revenue'.",
  "checks": [
    chk(lambda o: "line" in o.lower() or "chart" in o.lower(), "mentions chart"),
    chk(lambda o: "title" in o.lower() or "label" in o.lower() or "axis" in o.lower(), "mentions title/labels"),
  ]
},
"E4": {
  "context": "Columns: B=Cost, C=Price, D=Units Sold. Data starts at row 2.",
  "prompt": "Create an Excel formula for profit margin %: (Price-Cost)*Units/(Price*Units)*100. Show the complete formula for row 2.",
  "checks": [
    chk(lambda o: "=" in o, "has formula character"),
    chk(lambda o: len(o) > 10, "has content"),
  ]
},
"E5": {
  "context": "Data has mixed date formats (01/15/2026, Jan 15 2026, 2026.01.15), names in all caps or all lowercase, and extra leading/trailing spaces.",
  "prompt": "Describe how to: standardize dates to YYYY-MM-DD, convert names to Proper Case, remove extra spaces, highlight duplicate rows in yellow.",
  "checks": [
    chk(lambda o: "yyyy" in o.lower() or "yyyy-mm-dd" in o.lower() or "date" in o.lower(), "mentions date format"),
    chk(lambda o: "proper" in o.lower() or "case" in o.lower() or "proper case" in o.lower(), "mentions proper case"),
  ]
},
"E6": {
  "context": "Sheet1 column A has Employee IDs. Sheet2 has ID in column A and Name in column B. Some IDs in Sheet1 may not exist in Sheet2.",
  "prompt": "Write the VLOOKUP formula to pull employee names from Sheet2 into Sheet1 column B. Handle missing IDs gracefully.",
  "checks": [
    chk(lambda o: "vlookup" in o.lower(), "has VLOOKUP"),
    chk(lambda o: "n/a" in o.lower() or "#n/a" in o.lower() or "iferror" in o.lower() or "ifna" in o.lower(), "handles missing IDs"),
  ]
},
"E7": {
  "context": "Spreadsheet has 200 rows with columns: Region (North/South/East/West), Product (A/B/C), Month, Revenue.",
  "prompt": "Describe how to create a pivot table showing Revenue by Region (rows) and Product (columns) with grand totals. Put it on a new sheet called 'Summary'.",
  "checks": [
    chk(lambda o: "pivot" in o.lower(), "mentions pivot table"),
    chk(lambda o: "region" in o.lower() and "product" in o.lower(), "mentions region and product"),
  ]
},
# ── POWERPOINT ────────────────────────────────────────────────────────────────
"P1": {
  "prompt": "Write content for a 5-slide investor pitch deck for 'Kairo Phantom' AI document copilot. Include: Slide 1: Title+tagline. Slide 2: Problem. Slide 3: Solution. Slide 4: Market. Slide 5: Team/Ask.",
  "checks": [
    chk(lambda o: "Kairo" in o, "mentions Kairo"),
    chk(lambda o: ("Slide 1" in o or "Slide 2" in o or "slide 1" in o.lower()
                   or '"slide"' in o.lower() or 'title' in o.lower()), "has slide structure"),
    chk(lambda o: len(o) > 200, "substantial content"),
  ]
},
"P2": {
  "prompt": "Describe how to fix formatting inconsistencies in a PowerPoint: make all title fonts 28pt Bold, ensure text-heavy slides have max 5 bullets each, standardize accent color to #1E3A5F.",
  "checks": [
    chk(lambda o: "font" in o.lower() or "title" in o.lower() or "28" in o, "mentions font/size"),
    chk(lambda o: len(o) > 50, "has content"),
  ]
},
"P3": {
  "context": "Our platform grew 45% to $12M ARR. Expanded from 100 to 350 enterprise clients (250% growth). Deployed in 14 countries. Processing 2M documents/month.",
  "prompt": "Convert this into 5-7 concise bullet points for a slide. Each bullet max one line.",
  "checks": [
    chk(lambda o: any(x in o for x in ["•","- ","* ","1.","2."]), "has bullets"),
    chk(lambda o: any(x in o for x in ["45","12M","350","14","2M"]), "preserves key data"),
  ]
},
"P4": {
  "prompt": "Write a detailed DALL-E / image generation prompt for a PowerPoint slide hero image: 'AI-powered document intelligence' — modern, professional, tech style with blues and whites.",
  "checks": [
    chk(lambda o: len(o) > 50, "substantial image prompt"),
    chk(lambda o: "ai" in o.lower() or "document" in o.lower() or "intelligence" in o.lower(), "relevant content"),
  ]
},
"P5": {
  "context": "Slide 1: Market - $50B TAM. Slide 2: Product Demo. Slide 3: Competition vs Copilot. Slide 4: GTM strategy. Slide 5: Financials $2.3M ARR.",
  "prompt": "Generate speaker notes for each of these 5 slides. Each should be 3-4 sentences with a transition to the next slide.",
  "checks": [
    chk(lambda o: len(o) > 200, "substantial notes"),
    chk(lambda o: "slide" in o.lower() or "next" in o.lower() or "transition" in o.lower(), "has slide structure"),
  ]
},
"P6": {
  "context": "Current 7 slides: 1=Intro, 2=Problem, 3=Feature A, 4=Feature B, 5=Market, 6=Team, 7=Financials",
  "prompt": "Merge slides 3 and 4 into one 'Features' slide and move slide 7 (Financials) to position 2. Describe the new slide order.",
  "checks": [
    chk(lambda o: "feature" in o.lower() or "financ" in o.lower(), "mentions features/financials"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
"P7": {
  "prompt": "Describe how to apply a corporate theme to PowerPoint: dark navy (#1E3A5F) title slides, white content slides, accent color #F5A623. What specific elements to change.",
  "checks": [
    chk(lambda o: "navy" in o.lower() or "1e3a5f" in o.lower() or "theme" in o.lower(), "mentions theme/color"),
    chk(lambda o: len(o) > 30, "has content"),
  ]
},
# ── VSCODE ────────────────────────────────────────────────────────────────────
"V1": {
  "context": "// TypeScript: fetch user from API, validate, return typed User",
  "prompt": "Write a TypeScript async function fetchUser(id: number) that calls GET /api/users/:id, validates the response has required fields (id, name, email), and returns a typed User object. Include try/catch error handling.",
  "checks": [
    chk(lambda o: "async" in o or "await" in o, "has async/await"),
    chk(lambda o: any(x in o for x in ["try","catch","throw","Error"]), "has error handling"),
    chk(lambda o: any(x in o for x in ["User","interface","type "]), "has User type"),
  ]
},
"V2": {
  "context": "function calc(a,b,c){if(a>0){if(b>0){if(c>0){return a+b+c}else{return a+b}}else{return a}}else{return 0}}",
  "prompt": "Refactor this function: add JSDoc comments, use descriptive variable names, apply early returns to reduce nesting. Output must have same behavior.",
  "checks": [
    chk(lambda o: "/**" in o or "@param" in o or "@returns" in o, "has JSDoc"),
    chk(lambda o: "return" in o, "has return statements"),
  ]
},
"V3": {
  "context": buggy(),
  "prompt": "Find and fix all bugs in this Python code. Add a comment on each fixed line explaining what was wrong.",
  "checks": [
    chk(lambda o: "range(len(" in o or "fix" in o.lower() or "bug" in o.lower(), "mentions fix"),
    chk(lambda o: "#" in o, "has code comments"),
  ]
},
"V4": {
  "prompt": "Show a VS Code extension snippet that uses the Kairo Phantom MCP server to ghost-write text into the active editor at the cursor position.",
  "checks": [
    chk(lambda o: "mcp" in o.lower() or "kairo" in o.lower(), "mentions MCP/Kairo"),
    chk(lambda o: len(o) > 50, "has content"),
  ]
},
"V5": {
  "context": "Project: utils.ts (formatCurrency, validateEmail, debounce), api.ts (fetchUser using validateEmail), main.ts (calls fetchUser), tsconfig.json",
  "prompt": "Analyze this TypeScript project. Identify concerns about code organization, missing error handling, and suggest concrete improvements.",
  "checks": [
    chk(lambda o: any(f in o for f in ["utils","api","main"]), "mentions project files"),
    chk(lambda o: len(o) > 100, "substantial analysis"),
  ]
},
"V6": {
  "context": "export function formatCurrency(amount: number): string { return '$' + amount.toFixed(2); }\nexport function validateEmail(email: string): boolean { return /^[^@]+@[^@]+$/.test(email); }",
  "prompt": "Write comprehensive Jest unit tests for both functions. Cover normal cases, edge cases (null, undefined, 0, negative, empty string), and error conditions. Use describe/it blocks.",
  "checks": [
    chk(lambda o: any(x in o for x in ["describe(","it(","test("]), "has Jest describe/it"),
    chk(lambda o: any(x in o for x in ["expect(","toBe(","toEqual(","toThrow("]), "has expect assertions"),
    chk(lambda o: any(x in o for x in ["null","undefined","empty","NaN","-1","0"]), "has edge cases"),
  ]
},
# ── TERMINAL ─────────────────────────────────────────────────────────────────
"T1": {
  "prompt": "Give me the PowerShell one-liner to find all *.ts files modified in the last 7 days, recursively from current directory, sorted by file size descending. Show path and size.",
  "checks": [
    chk(lambda o: any(x in o for x in ["Get-ChildItem","gci","*.ts",".ts"]), "has PowerShell file search"),
    chk(lambda o: "sort" in o.lower() or "Sort-Object" in o, "has sorting"),
    chk(lambda o: "7" in o or "LastWriteTime" in o or "days" in o.lower(), "has date filter"),
  ]
},
"T2": {
  "prompt": "Write a PowerShell deployment script with 4 steps: npm install, npm test, npm run build, deploy to server. Include error handling after each step and progress echo messages.",
  "checks": [
    chk(lambda o: "npm" in o and "install" in o, "has npm install"),
    chk(lambda o: "test" in o.lower(), "has test step"),
    chk(lambda o: "build" in o.lower(), "has build step"),
    chk(lambda o: any(x in o for x in ["if (","$LASTEXITCODE","$?","try {"]), "has error handling"),
  ]
},
"T3": {
  "context": "npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE unable to resolve dependency tree\nnpm ERR! Found: react@18.2.0\nnpm ERR! Could not resolve dependency: peer react@^17.0.0",
  "prompt": "Explain what caused this npm ERESOLVE error and provide the exact command(s) to fix it.",
  "checks": [
    chk(lambda o: "dependency" in o.lower() or "peer" in o.lower() or "conflict" in o.lower(), "explains the error"),
    chk(lambda o: "--legacy-peer-deps" in o or "--force" in o or "npm install" in o, "provides fix command"),
  ]
},
"T4": {
  "prompt": "Write a PowerShell script for a 4-step deployment: 1) git pull, 2) npm run build, 3) npm test, 4) copy to server. Confirm before each step. Stop on any failure.",
  "checks": [
    chk(lambda o: all(x in o.lower() for x in ["git","build","test"]), "has all steps"),
    chk(lambda o: any(x in o for x in ["Read-Host","Write-Host","confirm","Confirm"]), "has confirmation prompts"),
    chk(lambda o: any(x in o for x in ["if (","exit","throw","$LASTEXITCODE"]), "has error handling"),
  ]
},
"T5": {
  "context": "CI Pipeline Log:\nStep 1 - Install: SUCCESS\nStep 2 - Build: SUCCESS\nStep 3 - Test: FAILED\nError: Cannot find module './config'\n  at Object.<anonymous> (dist/server.js:3:18)\nExit code: 1",
  "prompt": "Analyze this CI log. Identify the specific error, its root cause, and provide a concrete fix.",
  "checks": [
    chk(lambda o: "config" in o.lower() or "module" in o.lower() or "cannot find" in o.lower(), "identifies the error"),
    chk(lambda o: len(o) > 50, "provides substantial analysis"),
  ]
},
}

ALL_IDS = ["W1","W2","W3","W4","W5","W6","W7","W8","W9","W10",
           "N1","N2","N3","N4",
           "E1","E2","E3","E4","E5","E6","E7",
           "P1","P2","P3","P4","P5","P6","P7",
           "V1","V2","V3","V4","V5","V6",
           "T1","T2","T3","T4","T5"]

def run(sid):
    s = SCENARIOS.get(sid)
    if not s:
        print(f"[{sid}] SKIP — not in local scenarios")
        return None
    for attempt in range(1, 4):
        print(f"\n[{sid}] Attempt {attempt}/3...")
        out = ask(s["prompt"], s.get("context",""))
        print(f"  Response ({len(out)} chars): {repr(out[:150])}")
        ok_all = True
        for chkfn in s["checks"]:
            try:
                ok, desc = chkfn(out)
                print(f"  {'PASS' if ok else 'FAIL'}: {desc}")
                if not ok:
                    ok_all = False
            except Exception as e:
                print(f"  ERR in check: {e}")
                ok_all = False
        if ok_all:
            print(f"  [PASS] [{sid}] PASSED (attempt {attempt})")
            return True
        if attempt < 3:
            print(f"  Retrying in 10s...")
            time.sleep(10)
    print(f"  [FAIL] [{sid}] FAILED after 3 attempts")
    return False

if __name__ == "__main__":
    ids = sys.argv[1:] if len(sys.argv) > 1 else ["W1"]
    if ids == ["ALL"]:
        ids = ALL_IDS
    results = {}
    for sid in ids:
        results[sid] = run(sid)
    print("\n=== SUMMARY ===")
    passed = [k for k,v in results.items() if v is True]
    failed = [k for k,v in results.items() if v is False]
    skipped = [k for k,v in results.items() if v is None]
    for sid, ok in results.items():
        mark = "[PASS]" if ok else ("[FAIL]" if ok is False else "[SKIP]")
        print(f"  {mark} {sid}")
    total = len(passed) + len(failed)
    print(f"\n  Score: {len(passed)}/{total} ({100*len(passed)//total if total else 0}%)")
    if skipped:
        print(f"  Skipped: {skipped}")
    import sys as _sys; _sys.exit(0 if not failed else 1)
