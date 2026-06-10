import win32gui
import sys

# Set standard output encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

def win_enum_handler(hwnd, ctx):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        if title:
            print(f"HWND: {hwnd} | Class: {class_name} | Title: {title}")

win32gui.EnumWindows(win_enum_handler, None)
