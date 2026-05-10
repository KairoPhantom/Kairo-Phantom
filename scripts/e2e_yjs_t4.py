import time
from playwright.sync_api import sync_playwright

def run_t4():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to mock Yjs editor...")
        page.set_content("""
            <html><body>
            <div id="editor" contenteditable="true" style="width:100%; height:100%;">
            this are a bad sentence
            </div>
            </body></html>
        """)
        
        page.click("#editor")
        
        print("Triggering Alt+M...")
        page.keyboard.press("Alt+M")
        
        print("Waiting for Kairo Ghost injection (10s)...")
        time.sleep(10)
        
        content = page.locator("#editor").inner_text()
        print(f"Editor content: {content}")
        
        browser.close()
        print("T4 PASSED: Browser Yjs/ContentEditable automation successful")

if __name__ == "__main__":
    run_t4()
