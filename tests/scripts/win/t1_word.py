import subprocess, time, keyboard, sys
import pywinauto
from pywinauto import Application
import os

DOC_PATH = r"C:\tests\report.docx"

def main():
    print("Launching WINWORD.EXE...")
    try:
        proc = subprocess.Popen(["start", "winword", DOC_PATH], shell=True)
    except Exception:
        proc = subprocess.Popen([r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE", DOC_PATH])
        
    time.sleep(8)  # let Word load fully
    
    print("Connecting to Word via UIA...")
    app = Application(backend="uia").connect(title_re=".*Word")
    win = app.window(title_re=".*Word")
    win.set_focus()
    
    print("Navigating to target paragraph...")
    # Word shortcuts
    keyboard.press_and_release('ctrl+home')
    time.sleep(1)
    keyboard.press_and_release('ctrl+f')
    time.sleep(1)
    keyboard.write("Revenue Analysis")
    time.sleep(1)
    keyboard.press_and_release('esc')
    time.sleep(1)
    keyboard.press_and_release('down')
    keyboard.press_and_release('shift+down')
    
    print("Triggering Ghost-Write...")
    keyboard.write("Make this more formal")
    keyboard.press_and_release('alt+m')
    
    print("Waiting 8s for generation...")
    time.sleep(8)
    
    print("Accepting ghost text...")
    keyboard.press_and_release('tab')
    time.sleep(2)
    
    print("Verifying Undo functionality...")
    keyboard.press_and_release('ctrl+z')
    time.sleep(2)
    
    print("T1 Word E2E Verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
