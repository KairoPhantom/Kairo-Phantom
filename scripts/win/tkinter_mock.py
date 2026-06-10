#!/usr/bin/env python3
import sys
import tkinter as tk

def select_all(event):
    event.widget.tag_add("sel", "1.0", "end")
    return "break"

def main():
    if len(sys.argv) < 2:
        title = "Mock Application Window"
    else:
        title = sys.argv[1]

    root = tk.Tk()
    root.title(title)
    root.geometry("800x600")

    # Keep window on top so focus remains solid during GUI automation
    root.attributes("-topmost", True)

    text = tk.Text(root, font=("Consolas", 12), wrap="none")
    text.pack(expand=True, fill="both")
    text.focus_set()

    # Bind Ctrl+A to select all text
    text.bind("<Control-a>", select_all)
    text.bind("<Control-A>", select_all)

    root.mainloop()

if __name__ == "__main__":
    main()
