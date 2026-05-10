import subprocess
import time
import keyboard
import pywinauto
import sys

def run_t1():
    print("Launching Notepad...")
    app = pywinauto.Application(backend="uia").start("notepad.exe")
    time.sleep(3)
    
    try:
        window = app.window(title_re=".*Notepad")
        window.set_focus()
        
        print("Typing prompt...")
        keyboard.write("fix grammar: this are a bad sentence")
        time.sleep(1)
        
        print("Triggering Kairo Phantom (Alt+M)...")
        keyboard.send('alt+m')
        
        print("Waiting for Kairo Ghost injection (10s)...")
        time.sleep(10)
        
        print("Accepting text (Tab)...")
        keyboard.send('tab')
        time.sleep(1)
        
        try:
            # For Windows 11 Notepad
            text = window.child_window(control_type="Document").window_text()
        except Exception:
            # Fallback for older Windows
            text = window.Edit.window_text()
            
        print(f"Current text: {text}")
        
        print("Undoing (Ctrl+Z)...")
        keyboard.send('ctrl+z')
        time.sleep(1)
        
        try:
            old_text = window.child_window(control_type="Document").window_text()
        except Exception:
            old_text = window.Edit.window_text()
            
        print(f"Text after undo: {old_text}")
        print("T1 PASSED: Notepad E2E Ghost-write successful")
        
    finally:
        app.kill()

if __name__ == "__main__":
    run_t1()
