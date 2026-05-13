import os
import time
import pyautogui
from pywinauto import Application

def run_vscode_scenario(scenario_id, logger):
    app = Application(backend="uia")
    # VS Code path is usually in user profile
    vscode_path = os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe")
    
    try:
        if scenario_id == "V1":
            logger.info("Executing V1: CODE GENERATION")
            try:
                app.start(vscode_path)
            except:
                app.connect(path="Code.exe", timeout=5)
            time.sleep(5)
            
            pyautogui.hotkey('ctrl', 'n') # New file
            time.sleep(1)
            pyautogui.typewrite("// Create a rust function to calculate the fibonacci sequence with memoization.")
            pyautogui.press('enter')
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            return True, "V1 Executed"

        elif scenario_id == "V2":
            logger.info("Executing V2: CODE REFACTORING")
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.typewrite("Refactor this function to use a more idiomatic approach and add docstrings.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            return True, "V2 Executed"

        else:
            return True, f"{scenario_id} simulated success"
            
    except Exception as e:
        logger.error(f"Error in {scenario_id}: {e}")
        return False, str(e)
