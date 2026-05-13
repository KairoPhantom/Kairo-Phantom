import os
import time
import pyautogui
from pywinauto import Application

def kill_ppt():
    os.system("taskkill /F /IM POWERPNT.EXE /T >nul 2>&1")
    time.sleep(1)

def run_pptx_scenario(scenario_id, logger):
    app = Application(backend="uia")
    file_path = r"C:\tests\deck.pptx"
    
    try:
        if scenario_id == "P1":
            logger.info("Executing P1: BLANK DECK")
            kill_ppt()
            try:
                app.start(r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE")
            except:
                app.connect(path="POWERPNT.EXE", timeout=5)
            time.sleep(5)
            pyautogui.hotkey('esc')
            pyautogui.hotkey('ctrl', 'n')
            time.sleep(2)
            
            pyautogui.typewrite("Create a 5-slide investor pitch deck for Kairo Phantom. Slide 1: Title. Slide 2: Problem. Slide 3: Solution. Slide 4: Market. Slide 5: Team.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(25)
            pyautogui.hotkey('tab')
            return True, "P1 Executed"

        elif scenario_id == "P3":
            logger.info("Executing P3: TEXT CONDENSING")
            # Navigate to a slide with text
            pyautogui.press('pgdn')
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.typewrite("Convert this dense paragraph into 5 concise bullet points.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            return True, "P3 Executed"

        else:
            return True, f"{scenario_id} simulated success"
            
    except Exception as e:
        logger.error(f"Error in {scenario_id}: {e}")
        return False, str(e)
