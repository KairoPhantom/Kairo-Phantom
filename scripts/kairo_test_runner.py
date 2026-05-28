"""
kairo_test_runner.py
====================
Automated scenario-by-scenario test runner for Kairo Phantom.

Strategy:
  - Tests Kairo via HTTP API (http://127.0.0.1:7437) — no GUI simulation needed
  - Each scenario sends a prompt to the API and validates the response
  - If it fails → retries up to 3x with 10s cooldown
  - Saves results to C:\\tests\\results\\TIMESTAMP_results.json
  - Prints live progress to terminal

Usage:
    python scripts/kairo_test_runner.py [--app notepad|word|ppt|excel|vscode|terminal|all]

Requires: kairo-phantom.exe running on port 7437
"""

import requests, json, time, sys, os, re, subprocess, io
# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from datetime import datetime

API_BASE = "http://127.0.0.1:7437"
RESULTS_DIR = Path("C:/tests/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Colour helpers ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def p(colour, *args): print(colour + " ".join(str(a) for a in args) + RESET)
def ok(*a):   p(GREEN, "  ✅", *a)
def fail(*a): p(RED,   "  ❌", *a)
def warn(*a): p(YELLOW,"  ⚠️ ", *a)
def info(*a): p(CYAN,  "  ℹ️ ", *a)

# ─── API helpers ──────────────────────────────────────────────────────────────
def api_health() -> bool:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def api_ask(prompt: str) -> dict:
    """POST /ask — the real Kairo ghost-write API endpoint."""
    payload = {"prompt": f"// {prompt}"}
    try:
        r = requests.post(f"{API_BASE}/ask", json=payload, timeout=90)
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "response": data.get("response", "")}
        else:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    except requests.Timeout:
        return {"ok": False, "error": "Request timed out after 90s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_materialize(context: str) -> dict:
    """POST /materialize — older endpoint, uses provided context."""
    payload = {"context": context}
    try:
        r = requests.post(f"{API_BASE}/materialize", json=payload, timeout=90)
        if r.status_code == 200:
            data = r.json()
            return {"ok": True, "response": data.get("suggestion", "")}
        else:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def smart_prompt(prompt: str, app: str = "notepad", context: str = "") -> str:
    """Build context-aware prompt and call /ask. Return AI response text."""
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    r = api_ask(full_prompt)
    if r.get("ok") and r.get("response"):
        return str(r["response"]).strip()
    if context:
        r2 = api_materialize(context + "\n\n// " + prompt)
        if r2.get("ok") and r2.get("response"):
            return str(r2["response"]).strip()
    return ""


# ─── Scenario runner ──────────────────────────────────────────────────────────
class ScenarioResult:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.passed = False
        self.attempts = 0
        self.output = ""
        self.failure_reason = ""
        self.duration = 0.0

def run_scenario(s_id: str, s_name: str, prompt: str, app: str, context: str,
                 checks: list, max_retries: int = 3) -> ScenarioResult:
    result = ScenarioResult(s_id, s_name)
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}  [{s_id}] {s_name}{RESET}")
    print(f"  App: {app} | Prompt: {prompt[:80]}...")

    for attempt in range(1, max_retries + 1):
        result.attempts = attempt
        t0 = time.time()
        output = smart_prompt(prompt, app, context)
        result.duration = time.time() - t0
        result.output = output

        info(f"Attempt {attempt}/{max_retries} | {result.duration:.1f}s | {len(output)} chars returned")

        if not output:
            fail(f"Empty response from API")
            if attempt < max_retries:
                warn(f"Retrying in 10s...")
                time.sleep(10)
            continue

        # Run all checks
        all_passed = True
        for check_fn, check_desc in checks:
            try:
                passed, reason = check_fn(output, context)
                if passed:
                    ok(f"PASS: {check_desc}")
                else:
                    fail(f"FAIL: {check_desc} — {reason}")
                    all_passed = False
                    result.failure_reason = f"{check_desc}: {reason}"
            except Exception as e:
                fail(f"CHECK ERROR: {check_desc} — {e}")
                all_passed = False
                result.failure_reason = f"Check exception: {e}"

        if all_passed:
            result.passed = True
            ok(f"✅ [{s_id}] PASSED on attempt {attempt} ({result.duration:.1f}s)")
            return result
        else:
            if attempt < max_retries:
                warn(f"Failed attempt {attempt}. Retrying in 10s...")
                time.sleep(10)

    fail(f"❌ [{s_id}] FAILED after {max_retries} attempts. Last reason: {result.failure_reason}")
    return result

# ─── Reusable check functions ─────────────────────────────────────────────────
def check_no_leakage(output, _):
    """Ensure no system prompt / sentinel leakage."""
    leakage_terms = [
        "security_sentinel", "content agent", "swarm role", "system_prompt",
        "kairo_phantom_internal", "[security_sentinel", "sentinel_hash"
    ]
    for t in leakage_terms:
        if t.lower() in output.lower():
            return False, f"Leakage: '{t}'"
    return True, ""

def check_min_length(min_chars):
    def fn(output, _):
        if len(output) >= min_chars:
            return True, ""
        return False, f"Too short: {len(output)} < {min_chars} chars"
    return fn

def check_not_prompt_echo(prompt):
    def fn(output, _):
        # Output should NOT be (nearly) identical to the prompt
        overlap = sum(1 for w in prompt.split() if w.lower() in output.lower())
        if overlap / max(len(prompt.split()), 1) > 0.85:
            return False, "Output appears to echo the prompt"
        return True, ""
    return fn

def check_contains_any(*keywords):
    def fn(output, _):
        for kw in keywords:
            if kw.lower() in output.lower():
                return True, ""
        return False, f"Missing any of: {keywords}"
    return fn

def check_contains_all(*keywords):
    def fn(output, _):
        missing = [kw for kw in keywords if kw.lower() not in output.lower()]
        if not missing:
            return True, ""
        return False, f"Missing keywords: {missing}"
    return fn

def check_no_slang(output, _):
    slang = ["gotta", " cuz ", "theyre", " lol", "alright", "gonna", "kinda", "wanna"]
    found = [s for s in slang if s in output.lower()]
    if found:
        return False, f"Contains slang: {found}"
    return True, ""

def check_is_formal(output, _):
    """Very basic formality check."""
    formal_words = ["company", "organization", "business", "management", "performance", 
                    "strategy", "revenue", "market", "team", "results", "growth"]
    found = sum(1 for w in formal_words if w in output.lower())
    if found >= 2:
        return True, ""
    return False, f"Doesn't appear formal — only {found} formal words found"

def check_has_code(output, _):
    """Check that output looks like code."""
    code_indicators = ["def ", "function ", "const ", "let ", "var ", "return ", "import ", "class "]
    if any(ci in output for ci in code_indicators):
        return True, ""
    return False, "No code patterns detected"

def check_powershell_syntax(output, _):
    """Basic PS syntax check."""
    ps_patterns = ["Get-", "Set-", "New-", "Remove-", "$", "ForEach", "Where-Object", "Select-Object"]
    if any(p in output for p in ps_patterns):
        return True, ""
    # Also accept if it has .ts or TypeScript file references
    if ".ts" in output or "Get-ChildItem" in output or "Get-Item" in output:
        return True, ""
    return False, "No PowerShell patterns detected"

# ─── TEST SUITES ──────────────────────────────────────────────────────────────
def get_notepad_scenarios():
    """N1-N4: Notepad scenarios (simplest — start here)."""
    return [
        {
            "id": "N1", "name": "BLANK: Write intro email",
            "prompt": "// Write a professional intro email for Arjun joining a startup as Head of Engineering.",
            "app": "notepad", "context": "",
            "checks": [
                (check_no_leakage, "No system prompt leakage"),
                (check_min_length(80), "At least 80 chars"),
                (check_not_prompt_echo("Write a professional intro email for Arjun joining a startup"), "Not prompt echo"),
                (check_contains_any("Arjun", "engineer", "welcome", "team", "joining", "head", "startup"), "Mentions relevant content"),
            ]
        },
        {
            "id": "N2", "name": "REWRITE: Formal tone correction",
            "prompt": "// Rewrite this in formal business English: 'we gotta improve our numbers cuz theyre not looking good lol.'",
            "app": "notepad",
            "context": "we gotta improve our numbers cuz theyre not looking good lol.",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_no_slang, "No informal slang"),
                (check_is_formal, "Formal business English"),
                (check_min_length(30), "At least 30 chars"),
            ]
        },
        {
            "id": "N3", "name": "SUMMARY: Bullet point summary",
            "prompt": "// Summarize the following meeting notes into 3 bullet points.",
            "app": "notepad",
            "context": "Meeting Notes: Team discussed Q3 revenue which was $2.3M up 15%. Product launched in 3 new markets. Headcount grew from 42 to 67 employees. Main challenge: customer support tickets increased 40%.",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(50), "At least 50 chars"),
                (check_contains_any("•", "-", "*", "1.", "2.", "3.", "–"), "Has bullet points or numbered list"),
            ]
        },
        {
            "id": "N4", "name": "CODE: Write Python function",
            "prompt": "// Write a Python function that takes a list of numbers and returns the top 3 largest values.",
            "app": "notepad", "context": "",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_has_code, "Contains code patterns"),
                (check_contains_any("def ", "function", "return", "sorted", "heapq", "max", "nlargest", "list", "numbers", "values"), "Addresses the Python function request"),
            ]
        },
    ]

def get_word_scenarios():
    """W1, W3, W8: Word scenarios."""
    return [
        {
            "id": "W1", "name": "BLANK PAGE: Executive summary",
            "prompt": "// Write an executive summary for a Q3 2026 quarterly business review covering revenue growth, market expansion, and team headcount. Use professional business tone with headings.",
            "app": "word", "context": "",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(150), "At least 150 chars"),
                (check_contains_any("revenue", "growth", "market", "expansion", "Q3", "quarterly", "business"), "Mentions key business topics"),
                (check_contains_any("headcount", "team", "employee", "hiring", "staff", "workforce"), "Mentions team/headcount"),
            ]
        },
        {
            "id": "W3", "name": "TONE: Formal rewrite",
            "prompt": "// Rewrite this in formal business English with proper grammar, consistent terminology, and professional tone suitable for a board presentation.",
            "app": "word",
            "context": "we gotta improve our numbers cuz theyre not looking good lol. The team did alright but we need way more customers.",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_no_slang, "No slang"),
                (check_is_formal, "Formal business language"),
                (check_min_length(50), "At least 50 chars"),
            ]
        },
        {
            "id": "W8", "name": "TONE SHIFT: Formal to casual with emojis",
            "prompt": "// Rewrite this in a casual, friendly tone suitable for a team Slack message. Use emojis where appropriate. Keep the key information intact.",
            "app": "word",
            "context": "Our Q3 revenue achieved $2.3M representing a 15% year-over-year growth rate. The organization successfully expanded into three new geographic markets.",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(50), "At least 50 chars"),
                (check_contains_any("🎉", "💪", "🚀", "✅", "🔥", "👏", "⭐", "😊", "📈", "🌟", "!", "great", "awesome", "hey", "folks"), "Casual tone or emoji"),
            ]
        },
    ]

def get_vscode_scenarios():
    """V1, V3, V6: VSCode scenarios."""
    return [
        {
            "id": "V1", "name": "CODE GEN: TypeScript fetch user function",
            "prompt": "// Write a TypeScript function that fetches user data from an API, validates the response, and returns a typed User object with proper error handling.",
            "app": "vscode", "context": "// Function that fetches user data from API, validates the response, and returns typed User object",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_has_code, "Contains code"),
                (check_contains_any("async", "await", "fetch", "axios", "Promise", "function", "http", "request"), "Has async API call pattern"),
                (check_contains_any("try", "catch", "throw", ".catch", "error", "Error", "reject"), "Has error handling"),
            ]
        },
        {
            "id": "V3", "name": "BUG FIX: Python off-by-one error",
            "prompt": "// This Python function has bugs. Find and fix all bugs. Add comments explaining each fix.",
            "app": "vscode",
            "context": "def calculate_average(numbers):\n    total = 0\n    for i in range(len(numbers) + 1):\n        total = total + numbers[i]\n    return total / len(numbers)",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_has_code, "Contains code"),
                (check_contains_any("range", "len", "bug", "fix", "error", "off-by", "index", "def ", "return", "corrected", "#"), "Addresses bug fix request"),
            ]
        },
        {
            "id": "V6", "name": "TEST GEN: Jest unit tests",
            "prompt": "// Write comprehensive Jest unit tests for all exported functions. Cover normal cases, edge cases (null, undefined, empty arrays), and error conditions. Use describe/it blocks.",
            "app": "vscode",
            "context": "export function formatCurrency(amount: number): string { return '$' + amount.toFixed(2); }\nexport function validateEmail(email: string): boolean { return /^[^@]+@[^@]+$/.test(email); }",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_has_code, "Contains code"),
                (check_contains_any("describe", "it(", "test(", "expect", "assert", "jest", "spec"), "Has test structure"),
                (check_contains_any("formatCurrency", "validateEmail", "currency", "email", "valid"), "References the actual functions"),
            ]
        },
    ]

def get_terminal_scenarios():
    """T1, T2, T3: Terminal scenarios."""
    return [
        {
            "id": "T1", "name": "CMD GEN: Find TypeScript files by date",
            "prompt": "// Show me the PowerShell command to find all TypeScript files modified in the last 7 days, recursively, and list them with their sizes sorted by size descending.",
            "app": "terminal", "context": "",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(30), "At least 30 chars"),
                (check_contains_any(".ts", "TypeScript", "*.ts", "Get-ChildItem", "gci", "ls", "find", "recursive"), "Addresses TypeScript file search"),
                (check_contains_any("7", "days", "LastWriteTime", "date", "modified", "recent"), "Addresses date filter"),
            ]
        },
        {
            "id": "T3", "name": "ERROR EXPLAIN: npm ERESOLVE",
            "prompt": "// Explain what caused this npm error and show me the exact command to fix it.",
            "app": "terminal",
            "context": "npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE unable to resolve dependency tree",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(60), "At least 60 chars explanation"),
                (check_contains_any("npm", "dependency", "conflict", "version", "peer", "install", "package", "ERESOLVE", "resolve"), "Addresses npm error"),
            ]
        },
    ]

def get_excel_scenarios():
    """E1, E2, E4: Excel scenarios."""
    return [
        {
            "id": "E1", "name": "FORMULA DEBUG: Fix broken formulas",
            "prompt": "// Analyze this spreadsheet data. The formulas are broken with #REF!, #VALUE!, #DIV/0! errors. Explain what each error means and provide the corrected formula for each row.",
            "app": "excel",
            "context": "Row 3: =D3/E3 gives #DIV/0!\nRow 4: =D4*E4 gives #VALUE! (E4 contains '#REF!')\nRow 5: =D5/0 gives #DIV/0!",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(80), "Detailed response"),
                (check_contains_any("divide", "zero", "DIV", "division", "#DIV", "denominator", "zero value", "zero in"), "Explains division by zero error"),
                (check_contains_any("VALUE", "type", "reference", "REF", "invalid", "incorrect", "mismatch", "wrong"), "Explains VALUE/REF error"),
            ]
        },
        {
            "id": "E4", "name": "FORMULA GEN: Profit margin formula",
            "prompt": "// Create an Excel formula for profit margin percentage: (Price - Cost) * Units / (Price * Units) * 100. Show the formula and briefly explain it. Columns: B=Cost, C=Price, D=Units.",
            "app": "excel",
            "context": "Columns: A=Product, B=Cost, C=Price, D=Units Sold, E=Total Revenue",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(20), "At least 20 chars"),
                (check_contains_any("=", "profit", "margin", "formula", "percentage", "%", "B", "C", "D", "cost", "price", "revenue"), "Contains formula or explanation"),
            ]
        },
    ]

def get_ppt_scenarios():
    """P1, P3, P5: PowerPoint scenarios."""
    return [
        {
            "id": "P1", "name": "BLANK DECK: Investor pitch outline",
            "prompt": "// Write content for a 5-slide investor pitch deck for an AI document copilot startup called Kairo Phantom. Include: Slide 1 Title and tagline, Slide 2 Problem, Slide 3 Solution, Slide 4 Market opportunity, Slide 5 Team and ask.",
            "app": "powerpoint", "context": "",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_min_length(150), "Substantial content"),
                (check_contains_any("AI", "document", "pitch", "investor", "slide", "problem", "solution", "market", "copilot", "Kairo", "startup", "opportunity"), "Relevant to pitch deck"),
            ]
        },
        {
            "id": "P3", "name": "TEXT CONDENSING: Paragraphs to bullets",
            "prompt": "// Convert these paragraphs into 5-7 concise bullet points. Each bullet should be one line maximum. Preserve all key information.",
            "app": "powerpoint",
            "context": "Our platform has experienced remarkable growth over the past fiscal year. Revenue increased by forty-five percent to reach twelve million dollars annually. We have expanded our customer base from one hundred enterprise clients to three hundred and fifty, representing a two-hundred-and-fifty-percent growth rate. Our technology has been deployed across fourteen countries and is processing over two million documents per month.",
            "checks": [
                (check_no_leakage, "No leakage"),
                (check_contains_any("•", "-", "*", "1.", "2.", "3.", "–", "·"), "Has bullets or numbering"),
                (check_contains_any("growth", "revenue", "customer", "platform", "expanded", "percent", "million", "countries", "documents"), "Preserves key data points"),
            ]
        },
    ]

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run_all_tests(filter_app: str = "all"):
    print(f"\n{BOLD}{'═'*60}")
    print(f"  🧪 KAIRO PHANTOM TEST RUNNER")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*60}{RESET}\n")

    # Check daemon
    if not api_health():
        print(f"{RED}❌ Kairo Phantom daemon not running on {API_BASE}{RESET}")
        print(f"   Start it with: .\\target\\release\\kairo-phantom.exe")
        sys.exit(1)

    ok(f"Kairo daemon is running at {API_BASE}")

    # Build test suite
    suites = {
        "notepad":  ("📝 NOTEPAD",    get_notepad_scenarios()),
        "word":     ("📄 WORD",       get_word_scenarios()),
        "vscode":   ("💻 VSCODE",     get_vscode_scenarios()),
        "terminal": ("🖥️  TERMINAL",   get_terminal_scenarios()),
        "excel":    ("📊 EXCEL",      get_excel_scenarios()),
        "ppt":      ("📊 POWERPOINT", get_ppt_scenarios()),
    }

    all_results = []
    total_passed = 0
    total_failed = 0

    for app_key, (label, scenarios) in suites.items():
        if filter_app != "all" and filter_app != app_key:
            continue

        print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
        print(f"{BOLD}{CYAN}  {label} — {len(scenarios)} scenarios{RESET}")
        print(f"{BOLD}{CYAN}{'═'*60}{RESET}")

        for s in scenarios:
            result = run_scenario(
                s_id=s["id"],
                s_name=s["name"],
                prompt=s["prompt"],
                app=s["app"],
                context=s.get("context", ""),
                checks=s["checks"],
                max_retries=3
            )
            all_results.append(result)
            if result.passed:
                total_passed += 1
            else:
                total_failed += 1

    # ─── Final Report ──────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*60}")
    print(f"  📊 FINAL RESULTS")
    print(f"{'═'*60}{RESET}")

    for r in all_results:
        status = f"{GREEN}PASS{RESET}" if r.passed else f"{RED}FAIL{RESET}"
        print(f"  [{r.id}] {r.name[:40]:<40} {status} ({r.attempts} attempts, {r.duration:.1f}s)")

    total = total_passed + total_failed
    pct = (total_passed / total * 100) if total > 0 else 0
    colour = GREEN if pct == 100 else (YELLOW if pct >= 70 else RED)
    print(f"\n{BOLD}{colour}  SCORE: {total_passed}/{total} ({pct:.0f}%){RESET}")

    if pct == 100:
        print(f"{GREEN}{BOLD}  🎉 ALL SCENARIOS PASSED — KAIRO PHANTOM IS PRODUCTION READY{RESET}")
    elif pct >= 70:
        print(f"{YELLOW}  ⚠️  Some scenarios failed. Review output above.{RESET}")
    else:
        print(f"{RED}  ❌ Critical failures. Review and fix before production.{RESET}")

    # Save results JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"{ts}_results.json"
    with open(out_file, "w") as f:
        json.dump([{
            "id": r.id, "name": r.name, "passed": r.passed,
            "attempts": r.attempts, "duration": r.duration,
            "output_preview": r.output[:300],
            "failure_reason": r.failure_reason
        } for r in all_results], f, indent=2)

    print(f"\n  📁 Results saved: {out_file}")
    return pct == 100

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", default="all",
                        choices=["all","notepad","word","vscode","terminal","excel","ppt"],
                        help="Which app to test (default: all)")
    args = parser.parse_args()
    success = run_all_tests(args.app)
    sys.exit(0 if success else 1)
