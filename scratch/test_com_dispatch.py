import os
import time
import win32com.client
import pythoncom
import subprocess

def is_process_running(proc_name):
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {proc_name}"], capture_output=True, text=True)
        return proc_name.lower() in out.stdout.lower()
    except Exception:
        return False

def get_active_app(app_name, proc_name):
    if not is_process_running(proc_name):
        print(f"{proc_name} is not running. Skipping Dispatch.")
        return None
    try:
        # Try GetActiveObject first
        return win32com.client.GetActiveObject(app_name)
    except Exception as e:
        print(f"GetActiveObject failed ({e}), trying Dispatch...")
        try:
            return win32com.client.Dispatch(app_name)
        except Exception as e2:
            print(f"Dispatch failed: {e2}")
            return None

file_path = r"C:\tests\spreadsheet.xlsx"

# 1. Kill any existing Excel instances
os.system("taskkill /F /IM EXCEL.EXE /T >nul 2>&1")
time.sleep(1)

# 2. Test when Excel is not running
print("Excel is not running. Testing...")
xl = get_active_app("Excel.Application", "excel.exe")
print(f"Result (should be None): {xl}")

# 3. Start Excel with the file
print("\nStarting Excel with the spreadsheet...")
os.startfile(file_path)
time.sleep(5)

# 4. Test when Excel is running
print("Excel is running. Testing...")
xl = get_active_app("Excel.Application", "excel.exe")
print(f"Result (should be COM object): {xl}")
if xl:
    print(f"Visible: {xl.Visible}")
    print(f"Workbooks count: {xl.Workbooks.Count}")
    for wb in xl.Workbooks:
         print(f" - Workbook Name: {wb.Name}")

# Clean up
os.system("taskkill /F /IM EXCEL.EXE /T >nul 2>&1")
