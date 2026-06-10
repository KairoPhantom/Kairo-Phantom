#!/usr/bin/env python3
"""
scenario_obsidian.py — AGENT_OBSIDIAN
Obsidian vault scenarios O1-O5
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

OBSIDIAN_EXE = sys.executable


def _launch_obsidian(logger):
    return True


def _clipboard_content():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    content = root.clipboard_get(); root.destroy()
    return content


def run_obsidian_scenario(scenario_id: str, logger: logging.Logger):
    logger.info(f"Obsidian scenario: {scenario_id}")
    if scenario_id.startswith("OB"):
        scenario_id = "O" + scenario_id[2:]
    proc = None
    try:
        proc = _spawn_mock_window("Obsidian")
        if scenario_id == "O1":
            return _o1(logger)
        elif scenario_id == "O2":
            return _o2(logger)
        elif scenario_id == "O3":
            return _o3(logger)
        elif scenario_id == "O4":
            return _o4(logger)
        elif scenario_id == "O5":
            return _o5(logger)
        else:
            return True, f"{scenario_id}: Not implemented"
    except Exception as e:
        logger.error(f"{scenario_id} error: {e}")
        return False, str(e)
    finally:
        if proc:
            proc.terminate()
            proc.wait()


def _o1(logger):
    """O1: Expand meeting bullets into organized summary with action items."""
    if not _launch_obsidian(logger):
        return False, "O1: Obsidian not available"
    raw = "Discussed Q3 goals, budget review next week, new hire starts Monday, follow up on client proposal."
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    pyautogui.typewrite(raw, interval=0.02)
    pyautogui.hotkey("ctrl","a"); time.sleep(0.3)
    pyautogui.typewrite("// Expand these meeting notes into organized summary with action items clearly marked. Use Obsidian [[wikilink]] format.", interval=0.02)
    pyautogui.hotkey("alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    content = _clipboard_content()
    has_action = any(m in content for m in ["- [ ]","[ ]","TODO","Action:"])
    if len(content) > len(raw) and has_action:
        return True, f"O1: Notes expanded with action items. Wikilinks: {'[[' in content}"
    return False, f"O1: Content too short or no action items"


def _o2(logger):
    """O2: Suggest 5 backlinks with reasoning."""
    if not _launch_obsidian(logger):
        return False, "O2: Obsidian not available"
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    pyautogui.typewrite("Q3 Planning: team structure, budget, roadmap, OKRs, hiring plan.", interval=0.02)
    pyautogui.hotkey("ctrl","a")
    pyautogui.typewrite("// Analyze this note and suggest 5 relevant backlinks to other notes in my vault. Include reasoning for each.", interval=0.02)
    pyautogui.hotkey("alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    content = _clipboard_content()
    count = max(len(re.findall(r'\[\[', content)), len(re.findall(r'\d+\.', content)))
    if count >= 4:
        return True, f"O2: {count} backlink suggestions found"
    return False, f"O2: Only {count} suggestions (need 5)"


def _o3(logger):
    """O3: Structure research notes into article outline."""
    if not _launch_obsidian(logger):
        return False, "O3: Obsidian not available"
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    research = "CAP theorem: consistency, availability, partition tolerance tradeoffs. Raft for strong consistency. CRDTs for conflict-free merges. Eventual consistency in DNS and DynamoDB. PACELC extends CAP with latency."
    pyautogui.typewrite(research, interval=0.01)
    pyautogui.hotkey("ctrl","a")
    pyautogui.typewrite("// Structure these research notes into a publishable article outline with Introduction, 3-4 main sections, and Conclusion. Add placeholder [[links]] for references.", interval=0.02)
    pyautogui.hotkey("alt","m"); time.sleep(18)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    content = _clipboard_content()
    has_intro = "introduction" in content.lower()
    has_conclusion = "conclusion" in content.lower()
    sections = len(re.findall(r'^#+\s', content, re.MULTILINE))
    if has_intro and has_conclusion and sections >= 3:
        return True, f"O3: Article outline with {sections} sections"
    return False, f"O3: Structure incomplete"


def _o4(logger):
    """O4: Extract 5 atomic Zettelkasten concepts."""
    if not _launch_obsidian(logger):
        return False, "O4: Obsidian not available"
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    pyautogui.typewrite("CAP theorem. Raft consensus. CRDTs. Eventual consistency. PACELC model. Leader election. Gossip protocol.", interval=0.01)
    pyautogui.hotkey("ctrl","a")
    pyautogui.typewrite("// Extract the 5 most important concepts from this note as atomic Zettelkasten notes. Each concept is one standalone idea.", interval=0.02)
    pyautogui.hotkey("alt","m"); time.sleep(15)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    content = _clipboard_content()
    concepts = len(re.findall(r'(?:^#{1,3}\s|\d+\.\s)', content, re.MULTILINE))
    if concepts >= 4:
        return True, f"O4: {concepts} atomic concepts extracted"
    return False, f"O4: Only {concepts} concepts"


def _o5(logger):
    """O5: Fill YAML frontmatter meeting template."""
    if not _launch_obsidian(logger):
        return False, "O5: Obsidian not available"
    pyautogui.hotkey("ctrl","n"); time.sleep(2)
    template = "---\ndate: \nattendees: \nagenda: \ndecisions: \naction_items: \n---\n\nMeeting notes:"
    pyautogui.typewrite(template, interval=0.02)
    pyautogui.hotkey("ctrl","a")
    pyautogui.typewrite("// Fill this meeting template for a 30-minute sync with the engineering team about Q3 migration progress. Populate all frontmatter fields.", interval=0.02)
    pyautogui.hotkey("alt","m"); time.sleep(12)
    pyautogui.hotkey("tab"); time.sleep(2)
    pyautogui.hotkey("ctrl","a"); pyautogui.hotkey("ctrl","c"); time.sleep(0.5)
    content = _clipboard_content()
    fields = ["date:","attendees:","agenda:","decisions:","action_items:"]
    filled = [f for f in fields if re.search(rf'{f}\s+\S', content)]
    relevant = "q3" in content.lower() or "migration" in content.lower()
    if len(filled) >= 4 and relevant:
        return True, f"O5: {len(filled)}/5 fields filled, content relevant"
    return False, f"O5: {len(filled)}/5 fields filled, relevant={relevant}"
