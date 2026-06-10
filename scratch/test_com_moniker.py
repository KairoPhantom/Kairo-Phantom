import os
import time
import win32com.client
import pythoncom
from pathlib import Path

file_path = r"C:\tests\spreadsheet.xlsx"

# 1. Kill Excel
os.system("taskkill /F /IM EXCEL.EXE /T >nul 2>&1")
time.sleep(1)

# 2. Start Excel with the file
print("Starting Excel...")
os.startfile(file_path)
time.sleep(5)

# 3. Connect via Moniker
try:
    pythoncom.CoInitialize()
    target_path = str(Path(file_path).resolve())
    print(f"Connecting to file moniker: {target_path}")
    
    wb = win32com.client.GetObject(target_path)
    print("Successfully got workbook COM object!")
    
    xl = wb.Application
    print(f"Excel Application found. Visible: {xl.Visible}")
    print(f"Active workbook: {xl.ActiveWorkbook.Name}")
    print(f"Active sheet: {xl.ActiveSheet.Name}")
    print(f"Active cell: {xl.ActiveCell.Address.replace('$', '')}")
    
except Exception as e:
    print(f"Moniker Connection Failed: {e}")

# Clean up
os.system("taskkill /F /IM EXCEL.EXE /T >nul 2>&1")
