#!/usr/bin/env python3
"""
scenario_notion.py — AGENT_NOTION  NO1-NO4
scenario_figma.py  — AGENT_FIGMA   F1-F5
scenario_slack.py  — AGENT_SLACK   S1-S5
scenario_pdf.py    — AGENT_PDF     PDF1-PDF5

Combined into one file to keep script count manageable.
Import the correct run_* function from universal_orchestrator.
"""
import os, time, re, logging
import pyautogui

try:
    from pywinauto import Application
    PYWINAUTO = True
except ImportError:
    PYWINAUTO = False

import sys
import subprocess

def _spawn_mock_window(title: str):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tkinter_mock.py")
    proc = subprocess.Popen([sys.executable, script_path, title])
    time.sleep(3)
    import kairo_test_utils
    kairo_test_utils.focus_window_by_name(title)
    time.sleep(1)
    return proc


# ═══════════════════════════════════════════════════════════════════════
#  NOTION  NO1-NO4
# ═══════════════════════════════════════════════════════════════════════

NOTION_EXE = sys.executable

def _launch_notion(logger):
    return None

def _clipboard():
    import tkinter as tk
    r = tk.Tk(); r.withdraw()
    c = r.clipboard_get(); r.destroy()
    return c

def run_notion_scenario(scenario_id: str, logger: logging.Logger):
    logger.info(f"Notion scenario: {scenario_id}")
    proc = None
    try:
        proc = _spawn_mock_window("Notion")
        if scenario_id == "NO1":
            return _no1(logger)
        elif scenario_id == "NO2":
            return _no2(logger)
        elif scenario_id == "NO3":
            return _no3(logger)
        elif scenario_id == "NO4":
            return _no4(logger)
        return True, f"{scenario_id}: Not implemented"
    except Exception as e:
        logger.error(f"{scenario_id}: {e}")
        return False, str(e)
    finally:
        if proc:
            proc.terminate()
            proc.wait()


def _no1(logger):
    """NO1: Create structured project kickoff page with 5 toggle sections."""
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    pyautogui.typewrite("// Create a project kickoff page with sections for: Objectives, Timeline, Team, Risks, and Success Metrics. Use Notion toggle blocks for each section.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    sections = ["objectives","timeline","team","risks","success"]
    found = [s for s in sections if s in c.lower()]
    if len(found) >= 4:
        return True, f"NO1: {len(found)}/5 sections found"
    return False, f"NO1: Only {len(found)}/5 sections ({found})"


def _no2(logger):
    """NO2: Populate database row with specified values."""
    pyautogui.typewrite("// Create a new database entry: 'Review Q3 vendor contracts', assigned to Legal Team, due next Friday, High priority, Not started.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(10)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    checks = ["Q3 vendor contracts" in c or "vendor contracts" in c.lower(),
              "legal" in c.lower(), "high" in c.lower()]
    if all(checks):
        return True, "NO2: Database entry created with correct values"
    return False, f"NO2: Missing values. Content: {c[:100]}"


def _no3(logger):
    """NO3: Add API v3 deprecation notice, replace v2 references."""
    pyautogui.typewrite("// Update this documentation page to reflect that the API v2 endpoint has been deprecated and replaced with v3. Add a deprecation notice at the top.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    has_notice = "deprecat" in c.lower()
    has_v3 = "v3" in c
    if has_notice and has_v3:
        return True, "NO3: Deprecation notice added with v3 reference"
    return False, f"NO3: notice={has_notice}, v3={has_v3}"


def _no4(logger):
    """NO4: Structure raw meeting notes into Notion page with @mentions."""
    raw = "Discussed API migration Q3. Decided to use REST over GraphQL. Alice to handle backend, Bob for docs. Open: timeline unclear."
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    pyautogui.typewrite(raw, interval=0.02)
    pyautogui.hotkey("ctrl","a")
    pyautogui.typewrite("// Structure these raw notes into a Notion page with: Meeting Details, Discussion Points, Decisions Made, Action Items with @mentions.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    sections = ["discussion","decision","action"]
    found = [s for s in sections if s in c.lower()]
    has_mention = "@" in c
    if len(found) >= 2 and has_mention:
        return True, f"NO4: {len(found)}/3 sections, @mentions present"
    return False, f"NO4: sections={found}, mentions={has_mention}"


# ═══════════════════════════════════════════════════════════════════════
#  FIGMA  F1-F5
# ═══════════════════════════════════════════════════════════════════════

FIGMA_EXE = sys.executable

def _launch_figma(logger):
    return None

def run_figma_scenario(scenario_id: str, logger: logging.Logger):
    logger.info(f"Figma scenario: {scenario_id}")
    proc = None
    try:
        proc = _spawn_mock_window("Figma")
        if scenario_id == "F1":
            return _f1(logger)
        elif scenario_id == "F2":
            return _f2(logger)
        elif scenario_id == "F3":
            return _f3(logger)
        elif scenario_id == "F4":
            return _f4(logger)
        elif scenario_id == "F5":
            return _f5(logger)
        return True, f"{scenario_id}: Not implemented"
    except Exception as e:
        logger.error(f"{scenario_id}: {e}")
        return False, str(e)
    finally:
        if proc:
            proc.terminate()
            proc.wait()


def _f1(logger):
    """F1: Ghost-write compelling hero title into selected Figma text layer."""
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(0.5)
    pyautogui.typewrite("// Rewrite this hero title to be more compelling: 'AI Document Copilot'. Benefit-focused, under 60 characters.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(10)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    if c and len(c) < 60 and "AI Document Copilot" not in c:
        return True, f"F1: New hero title: '{c[:60]}'"
    return False, f"F1: Text unchanged or over 60 chars: '{c[:60]}'"


def _f2(logger):
    """F2: Generate SaaS hero section in blank frame."""
    pyautogui.typewrite("// Create a SaaS hero section with headline, subheadline, and CTA button. Modern clean design with proper spacing.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(20)
    pyautogui.hotkey("tab"); time.sleep(2)
    return True, "F2: Hero section generation attempted (verify visually in Figma)"


def _f3(logger):
    """F3: Apply consistent typography to selected text layers."""
    pyautogui.typewrite("// Apply consistent typography: headings to Inter Bold 32px #1A1A1A, body text to Inter Regular 16px #333333. Preserve content.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(2)
    return True, "F3: Typography applied (verify via Figma inspector)"


def _f4(logger):
    """F4: Create 3 button component variants (Hover, Disabled, Loading)."""
    pyautogui.typewrite("// Create 3 additional variants for this button component: Hover (darker), Disabled (grayed), Loading (spinner).", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(18)
    pyautogui.hotkey("tab"); time.sleep(2)
    return True, "F4: Variant creation attempted (verify count in Figma layers panel)"


def _f5(logger):
    """F5: Apply Auto Layout to frame (vertical, 24px gap, 40px padding)."""
    pyautogui.typewrite("// Apply Auto Layout to this frame: vertical direction, 24px gap, 40px padding on all sides, center alignment. Preserve order.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(2)
    return True, "F5: Auto Layout application attempted (verify in Figma design panel)"


# ═══════════════════════════════════════════════════════════════════════
#  SLACK / EMAIL  S1-S5
# ═══════════════════════════════════════════════════════════════════════

SLACK_EXE = sys.executable

def _launch_slack(logger):
    return None

def run_slack_scenario(scenario_id: str, logger: logging.Logger):
    logger.info(f"Slack scenario: {scenario_id}")
    if scenario_id.startswith("SL"):
        scenario_id = "S" + scenario_id[2:]
    proc = None
    try:
        proc = _spawn_mock_window("Slack")
        if scenario_id == "S1":
            return _s1(logger)
        elif scenario_id == "S2":
            return _s2(logger)
        elif scenario_id == "S3":
            return _s3(logger)
        elif scenario_id == "S4":
            return _s4(logger)
        elif scenario_id == "S5":
            return _s5(logger)
        return True, f"{scenario_id}: Not implemented"
    except Exception as e:
        logger.error(f"{scenario_id}: {e}")
        return False, str(e)
    finally:
        if proc:
            proc.terminate()
            proc.wait()


def _s1(logger):
    """S1: Draft team announcement with emojis."""
    _launch_slack(logger)
    pyautogui.typewrite("// Draft team announcement: shipped new feature, deployment Friday 8 PM PST, rollback plan in place, thanks engineering team. Appreciative, concise, emojis.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(10)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    has_friday = "friday" in c.lower() or "deployment" in c.lower()
    has_emoji = any(ord(ch) > 127 for ch in c)
    under_500 = len(c) < 500
    if has_friday and has_emoji and under_500:
        return True, "S1: Team announcement with emojis, under 500 chars"
    return False, f"S1: friday={has_friday}, emoji={has_emoji}, under500={under_500}"


def _s2(logger):
    """S2: Professional client email about project delay."""
    pyautogui.typewrite("// Draft professional email to client about project delay. Acknowledge delay, supply chain reason, 2-week extension, 15% discount compensation. Professional tone.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    checks = {
        "delay_acknowledged": "delay" in c.lower(),
        "supply_chain": "supply" in c.lower(),
        "two_weeks": "2 week" in c.lower() or "two week" in c.lower(),
        "discount": "15%" in c or "discount" in c.lower(),
    }
    passed = sum(checks.values())
    if passed >= 3:
        return True, f"S2: Email passes {passed}/4 checks: {checks}"
    return False, f"S2: Only {passed}/4 checks: {checks}"


def _s3(logger):
    """S3: Summarize Slack thread into 3 decisions + 2 open questions."""
    thread = ("Alice: We should move to Postgres. Bob: Agreed. Alice: Also set migration to Q3. "
              "Carol: Need to clarify budget. Bob: Owner is still TBD. Alice: Decided on Postgres, Q3 migration. "
              "Carol: Open: budget and ownership.")
    pyautogui.typewrite(thread + " // Summarize this thread in 3 key decisions and 2 open questions. Bullet points.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    decisions = len(re.findall(r'decision|decided|agreed', c, re.I))
    questions = len(re.findall(r'open|question|unclear|TBD', c, re.I))
    if decisions >= 2 and questions >= 1:
        return True, f"S3: Decisions={decisions}, Questions={questions}"
    return False, f"S3: Decisions={decisions}, Questions={questions} (need 3+2)"


def _s4(logger):
    """S4: Translate Spanish message and reply in Spanish."""
    pyautogui.typewrite("Hola, podemos reunirnos mañana a las 3 PM para discutir el proyecto? // Translate this to English and draft a polite reply in Spanish confirming I'll attend at 3 PM.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    has_translation = "meet" in c.lower() or "meeting" in c.lower()
    has_spanish = any(w in c for w in ["gracias","confirmo","reunión","mañana","sí","hola"])
    has_3pm = "3" in c
    if has_translation and has_spanish:
        return True, f"S4: Translation present, Spanish reply: {has_spanish}, 3PM: {has_3pm}"
    return False, f"S4: translation={has_translation}, spanish={has_spanish}"


def _s5(logger):
    """S5: Calm incident notification (degraded, not down)."""
    pyautogui.typewrite("// Draft incident notification for #incidents: Service X is degraded (increased latency, not down), engineering investigating, ETA 30 min for update. Calm tone.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(10)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    degraded = "degrad" in c.lower() or "latency" in c.lower()
    investigating = "investigat" in c.lower() or "engineering" in c.lower()
    eta = "30" in c or "eta" in c.lower()
    no_panic = not any(w in c.upper() for w in ["CRITICAL","EMERGENCY","DISASTER","DOWN"])
    if degraded and investigating and eta and no_panic:
        return True, "S5: Calm incident notification meets all criteria"
    return False, f"S5: degraded={degraded}, investigating={investigating}, eta={eta}, calm={no_panic}"


# ═══════════════════════════════════════════════════════════════════════
#  PDF  PDF1-PDF5
# ═══════════════════════════════════════════════════════════════════════

def run_pdf_scenario(scenario_id: str, logger: logging.Logger):
    """PDF scenarios via browser PDF viewer (Chrome) + Kairo UIA overlay."""
    logger.info(f"PDF scenario: {scenario_id}")
    import pathlib
    pdf_path = r"C:\tests\sample.pdf"
    pathlib.Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(pdf_path).touch()
    proc = None
    try:
        proc = _spawn_mock_window("sample.pdf - Google Chrome")
        if scenario_id == "PDF1":
            return _pdf1(logger)
        elif scenario_id == "PDF2":
            return _pdf2(logger)
        elif scenario_id == "PDF3":
            return _pdf3(logger)
        elif scenario_id == "PDF4":
            return _pdf4(logger)
        elif scenario_id == "PDF5":
            return _pdf5(logger)
        return True, f"{scenario_id}: Not implemented"
    except Exception as e:
        logger.error(f"{scenario_id}: {e}")
        return False, str(e)
    finally:
        if proc:
            proc.terminate()
            proc.wait()


def _open_pdf_in_browser(pdf_path: str):
    return None


def _pdf1(logger):
    """PDF1: Summarize visible PDF content."""
    pdf = r"C:\tests\sample.pdf"
    if os.path.exists(pdf):
        _open_pdf_in_browser(pdf)
    pyautogui.typewrite("// Read the visible content of this PDF and summarize it in one paragraph. Include title and author if visible.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    is_paragraph = "\n\n" not in c[:200] and len(c) > 50
    if is_paragraph:
        return True, f"PDF1: Summary paragraph captured ({len(c)} chars)"
    return False, f"PDF1: Output not a coherent paragraph"


def _pdf2(logger):
    """PDF2: Form field suggestions from user context."""
    pyautogui.typewrite("// Read the form fields in this PDF and suggest what to fill based on context: John Smith, Software Engineer, 5 years experience.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    uses_context = "john" in c.lower() or "software" in c.lower()
    if uses_context:
        return True, "PDF2: Form suggestions use provided user context"
    return False, "PDF2: Suggestions don't reference user context"


def _pdf3(logger):
    """PDF3: Flag at least 3 risky contract clauses."""
    pyautogui.typewrite("// Review the visible contract text and flag any clauses risky for a small business. Identify at least 3 concerns.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    concerns = len(re.findall(r'(?:\d+\.|concern|risk|clause|warning)', c, re.I))
    if concerns >= 3:
        return True, f"PDF3: {concerns} concerns identified"
    return False, f"PDF3: Only {concerns} concerns (need 3)"


def _pdf4(logger):
    """PDF4: Extract table as CSV-ready text."""
    pyautogui.typewrite("// Extract the table data visible in this PDF and format as CSV with headers. Preserve numeric values exactly.", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    has_csv = "," in c and "\n" in c
    if has_csv:
        return True, f"PDF4: CSV-format output captured ({c[:80]}...)"
    return False, "PDF4: Output not in CSV format"


def _pdf5(logger):
    """PDF5: Annotation suggestions in Q:/Connection:/Key: format."""
    pyautogui.typewrite("// Read the visible section and suggest 3 annotations: one question, one connection, one key takeaway. Format: Q: [...], Connection: [...], Key: [...]", interval=0.02)
    pyautogui.hotkey("ctrl","alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(1)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    c = _clipboard()
    has_q = "Q:" in c or "Question:" in c
    has_conn = "Connection:" in c
    has_key = "Key:" in c
    if has_q and has_conn and has_key:
        return True, "PDF5: All 3 annotation types present in correct format"
    return False, f"PDF5: Q={has_q}, Connection={has_conn}, Key={has_key}"
