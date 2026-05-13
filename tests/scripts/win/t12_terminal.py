import os
import time
import json
import pyautogui
import keyboard
import subprocess
import pyperclip
from pywinauto import Application

RESULT_DIR = r"C:\tests\results"
LOG_DIR = r"C:\tests\logs"
SCREENSHOT_DIR = r"C:\tests\screenshots"

for d in [RESULT_DIR, LOG_DIR, SCREENSHOT_DIR]:
    os.makedirs(d, exist_ok=True)

RESULT_FILE = os.path.join(RESULT_DIR, "t12_terminal_result.json")
LOG_FILE = os.path.join(LOG_DIR, "agent_terminal.log")

def write_log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass

def write_result(payload):
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload))
    print(json.dumps(payload))

def take_screenshot(scenario_id):
    path = os.path.join(SCREENSHOT_DIR, f"{scenario_id}_fail.png")
    pyautogui.screenshot(path)
    return path

def verify_t1(text):
    t = text.lower()
    if "get-childitem" not in t and "ls" not in t and "find" not in t:
        return False, "Not a valid lookup command."
    if ".ts" not in t:
        return False, "Does not target TS files."
    if "length" not in t and "size" not in t:
        return False, "Does not reference size."
    return True, "Valid powershell command."

def verify_t2(text):
    t = text.lower()
    if "npm" not in t and "install" not in t:
        return False, "Missing install step."
    if "test" not in t and "build" not in t:
        return False, "Missing test or build."
    if "try" not in t and "error" not in t:
        return False, "Missing error handling."
    return True, "Valid deployment script."

def verify_t3(text):
    t = text.lower()
    if "eresolve" not in t and "dependency" not in t:
        return False, "Did not explain ERESOLVE properly."
    if "legacy-peer-deps" not in t and "force" not in t:
        return False, "No fix command provided."
    return True, "Valid error explanation."

def verify_t4(text):
    t = text.lower()
    if "migration" not in t or "redis" not in t or "restart" not in t:
        return False, "Missing workflow steps."
    if "read-host" not in t and "confirm" not in t:
        return False, "Missing safety prompts."
    return True, "Valid orchestration generated."

def run_scenario(scenario_id, setup_command, user_action_text, verify_func, target_time):
    write_log(f"Starting {scenario_id}")
    try:
        # Start Windows Terminal
        subprocess.Popen("wt.exe")
        time.sleep(3)
        
        if setup_command:
            pyautogui.write(setup_command, interval=0.01)
            pyautogui.press('enter')
            time.sleep(1)
        
        pyautogui.write(user_action_text, interval=0.01)
        time.sleep(1)
        
        # Trigger Kairo Phantom
        pyautogui.hotkey('alt', 'm')
        time.sleep(target_time)
        
        # Accept
        pyautogui.press('tab')
        time.sleep(1)
        
        # To grab the text from terminal we can copy everything
        pyautogui.hotkey('ctrl', 'shift', 'a')
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'shift', 'c')
        time.sleep(0.5)
        
        result_text = pyperclip.paste()
        passed, msg = verify_func(result_text)
        
        if not passed:
            write_log(f"{scenario_id} Assertion Failed: {msg}")
            take_screenshot(scenario_id)
            return False, msg
            
        write_log(f"{scenario_id} Passed: {msg}")
        return True, "PASS"
    except Exception as e:
        write_log(f"{scenario_id} Error: {str(e)}")
        take_screenshot(scenario_id)
        return False, str(e)
    finally:
        # kill wt.exe
        subprocess.call(["taskkill", "/F", "/IM", "WindowsTerminal.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.call(["taskkill", "/F", "/IM", "wt.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

def main():
    results = {}
    
    # T1
    t1_setup = ""
    t1_prompt = "Show me the command to find all TypeScript files modified in the last 7 days, recursively, and list them with their sizes sorted by size descending."
    p1, m1 = run_scenario("T1", t1_setup, t1_prompt, verify_t1, 10)
    results["T1"] = {"status": "PASS" if p1 else "FAIL", "msg": m1}
    
    # T2
    t2_setup = ""
    t2_prompt = "Write a complete deployment script for this Node.js project. Include: installing dependencies, running tests, building the project, and deploying to a server. Use PowerShell syntax."
    p2, m2 = run_scenario("T2", t2_setup, t2_prompt, verify_t2, 18)
    results["T2"] = {"status": "PASS" if p2 else "FAIL", "msg": m2}
    
    # T3
    t3_setup = "echo 'npm ERR! code ERESOLVE, npm ERR! ERESOLVE unable to resolve dependency tree'"
    t3_prompt = "Explain what caused this error and show me the exact command to fix it."
    p3, m3 = run_scenario("T3", t3_setup, t3_prompt, verify_t3, 12)
    results["T3"] = {"status": "PASS" if p3 else "FAIL", "msg": m3}
    
    # T4
    t4_setup = ""
    t4_prompt = "Create a script that: (1) backs up the database to ./backups/, (2) runs pending migrations, (3) clears the Redis cache, and (4) restarts the application service. Include confirmation prompts before each destructive action."
    p4, m4 = run_scenario("T4", t4_setup, t4_prompt, verify_t4, 20)
    results["T4"] = {"status": "PASS" if p4 else "FAIL", "msg": m4}
    
    all_pass = all(r["status"] == "PASS" for r in results.values())
    
    write_result({
        "id": "agent_terminal",
        "status": "PASS" if all_pass else "FAIL",
        "scenarios": results
    })

if __name__ == '__main__':
    main()
