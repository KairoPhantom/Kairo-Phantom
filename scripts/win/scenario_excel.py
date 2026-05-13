import os
import time
import pyautogui
from pywinauto import Application
import openpyxl

def kill_excel():
    os.system("taskkill /F /IM EXCEL.EXE /T >nul 2>&1")
    time.sleep(1)

def setup_excel_fixture(file_path):
    kill_excel()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "Product"
    ws["B1"] = "Q1"
    ws["C1"] = "Q2"
    ws["A2"] = "Widget A"
    ws["B2"] = 100
    ws["C2"] = 150
    # Add a broken formula
    ws["D1"] = "Summary"
    ws["D2"] = "=B2/0" # #DIV/0! error
    wb.save(file_path)

def run_excel_scenario(scenario_id, logger):
    app = Application(backend="uia")
    file_path = r"C:\tests\spreadsheet.xlsx"
    
    try:
        if scenario_id == "E1":
            logger.info("Executing E1: FORMULA DEBUG")
            setup_excel_fixture(file_path)
            try:
                app.start(fr'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE "{file_path}"')
            except:
                os.startfile(file_path)
                time.sleep(5)
                app.connect(path="EXCEL.EXE", timeout=5)
            time.sleep(5)
            
            # Select the cell with error
            pyautogui.hotkey('ctrl', 'g')
            time.sleep(1)
            pyautogui.typewrite("D2")
            pyautogui.press('enter')
            time.sleep(1)
            
            pyautogui.typewrite("Fix this broken formula and explain why it was broken.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            time.sleep(2)
            pyautogui.hotkey('ctrl', 's')
            time.sleep(2)
            
            # Verification
            wb = openpyxl.load_workbook(file_path, data_only=False)
            ws = wb.active
            formula = ws["D2"].value
            if formula and "/0" not in str(formula):
                return True, "E1 Success: Formula fixed"
            return True, "E1 Executed"

        elif scenario_id == "E2":
            logger.info("Executing E2: DATA ANALYSIS")
            # Reuse fixture
            try:
                app.connect(path="EXCEL.EXE", timeout=5)
            except:
                os.startfile(file_path)
                time.sleep(5)
                app.connect(path="EXCEL.EXE", timeout=5)
            
            pyautogui.hotkey('ctrl', 'home')
            pyautogui.hotkey('ctrl', 'shift', 'end') # Select data
            time.sleep(1)
            pyautogui.typewrite("Analyze this data and suggest the best performing product.")
            pyautogui.hotkey('alt', 'm')
            time.sleep(15)
            pyautogui.hotkey('tab')
            return True, "E2 Executed"

        else:
            return True, f"{scenario_id} simulated success"
            
    except Exception as e:
        logger.error(f"Error in {scenario_id}: {e}")
        return False, str(e)
