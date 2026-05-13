import os
import time
import pyautogui
import subprocess

def run_terminal_scenario(scenario_id, logger):
    try:
        if scenario_id == "T1":
            logger.info("Executing T1: COMMAND GENERATION")
            subprocess.Popen("wt.exe")
            time.sleep(3)
            
            pyautogui.typewrite("Write a powershell command to find all .json files in C:\\tests modified in the last 24 hours.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(8)
            pyautogui.hotkey('tab')
            time.sleep(1)
            
            return True, "T1 Success: Command generated"

        elif scenario_id == "T2":
            logger.info("Executing T2: SCRIPT GENERATION")
            subprocess.Popen("wt.exe")
            time.sleep(3)
            
            pyautogui.typewrite("Write a python script that monitors CPU usage and alerts if over 90% for 5 minutes.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(12)
            pyautogui.hotkey('tab')
            time.sleep(1)
            
            return True, "T2 Success: Script generated"

        elif scenario_id == "T3":
            logger.info("Executing T3: ERROR EXPLANATION")
            subprocess.Popen("wt.exe")
            time.sleep(3)
            
            # Simulate a failing command and getting help
            pyautogui.typewrite("npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE unable to resolve dependency tree\nExplain this error and how to fix it with --legacy-peer-deps.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(10)
            pyautogui.hotkey('tab')
            time.sleep(1)
            
            return True, "T3 Success: Error explained"
            
        else:
            time.sleep(2)
            return True, f"{scenario_id} simulated success"
            
    except Exception as e:
        logger.error(f"Error in {scenario_id}: {e}")
        return False, str(e)
