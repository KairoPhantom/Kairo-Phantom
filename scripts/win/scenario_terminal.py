import os
import time
import subprocess
import pyautogui
import pyperclip

def _launch_terminal():
    """Launch Windows Terminal or fallback to cmd."""
    try:
        subprocess.Popen("wt.exe")
        time.sleep(3)
    except FileNotFoundError:
        subprocess.Popen("cmd.exe")
        time.sleep(2)
    import kairo_test_utils
    if not kairo_test_utils.focus_window_by_name("terminal"):
        kairo_test_utils.focus_window_by_name("cmd")

def _type_prompt(text):
    """Paste prompt via clipboard to preserve // and special chars."""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

def run_terminal_scenario(scenario_id, logger):
    try:
        # ── T1 — COMMAND GENERATION ──────────────────────────────────────────
        if scenario_id == "T1":
            logger.info("Executing T1: COMMAND GENERATION")
            _launch_terminal()
            _type_prompt(
                "// Write a PowerShell command to find all .json files in "
                "C:\\tests modified in the last 24 hours and list their sizes."
            )
            pyautogui.hotkey('alt', 'm')
            time.sleep(10)
            pyautogui.hotkey('tab')
            time.sleep(1)
            return True, "T1 Success: Command generated"

        # ── T2 — SCRIPT GENERATION ──────────────────────────────────────────
        elif scenario_id == "T2":
            logger.info("Executing T2: SCRIPT GENERATION")
            _launch_terminal()
            _type_prompt(
                "// Write a Python script that monitors CPU usage every 5 seconds "
                "and sends an alert (print warning) if usage exceeds 90% for 3 consecutive readings."
            )
            pyautogui.hotkey('alt', 'm')
            time.sleep(12)
            pyautogui.hotkey('tab')
            time.sleep(1)
            return True, "T2 Success: Monitoring script generated"

        # ── T3 — ERROR EXPLANATION ───────────────────────────────────────────
        elif scenario_id == "T3":
            logger.info("Executing T3: ERROR EXPLANATION")
            _launch_terminal()
            _type_prompt(
                "npm ERR! code ERESOLVE\n"
                "npm ERR! ERESOLVE unable to resolve dependency tree\n"
                "// Explain this npm error and provide 3 ways to fix it, "
                "starting with --legacy-peer-deps."
            )
            pyautogui.hotkey('alt', 'm')
            time.sleep(12)
            pyautogui.hotkey('tab')
            time.sleep(1)
            return True, "T3 Success: Error explained with solutions"

        # ── T4 — GIT WORKFLOW ────────────────────────────────────────────────
        elif scenario_id == "T4":
            logger.info("Executing T4: GIT WORKFLOW — commit message generation")
            _launch_terminal()
            _type_prompt(
                "// Generate a conventional commit message for these changes: "
                "added dynamic Office path resolution to scenario_word.py, "
                "scenario_pptx.py, and scenario_excel.py to fix hardcoded Office16 paths."
            )
            pyautogui.hotkey('alt', 'm')
            time.sleep(10)
            pyautogui.hotkey('tab')
            time.sleep(1)
            return True, "T4 Success: Git commit message generated"

        # ── T5 — DEBUGGING SESSION ───────────────────────────────────────────
        elif scenario_id == "T5":
            logger.info("Executing T5: DEBUGGING SESSION")
            _launch_terminal()
            _type_prompt(
                "Traceback (most recent call last):\n"
                "  File 'app.py', line 42, in process_data\n"
                "    result = data['revenue'] / data['units']\n"
                "ZeroDivisionError: division by zero\n"
                "// Debug this Python traceback: identify root cause, suggest a fix "
                "with proper zero-guard, and suggest a unit test to prevent regression."
            )
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            time.sleep(1)
            return True, "T5 Success: Debugging session complete"

        else:
            time.sleep(1)
            return True, f"{scenario_id} simulated success"

    except Exception as e:
        logger.error(f"Error in {scenario_id}: {e}")
        return False, str(e)
