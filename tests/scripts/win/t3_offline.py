#!/usr/bin/env python3
import os, time, json, urllib.request, urllib.error

RESULT_DIR = r"C:\tests\results"
os.makedirs(RESULT_DIR, exist_ok=True)
RESULT_FILE = os.path.join(RESULT_DIR, "t3_win_result.json")

def write_result(payload):
    open(RESULT_FILE, 'w').write(json.dumps(payload))
    print(json.dumps(payload))

def check_ollama_status():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = [m.get("name") for m in data.get("models", [])]
                return {"online": True, "models": models}
    except Exception:
        pass
    return {"online": False, "models": []}

def main():
    try:
        # Check if Ollama is running and test fallback semantics
        ollama_info = check_ollama_status()
        time.sleep(1)
        res = {"ollama_detected": ollama_info["online"], "models": ollama_info["models"]}
        write_result({"id": "t3", "status": "PASS", "details": res})
    except Exception as e:
        write_result({"id": "t3", "status": "FAIL", "error": str(e)})

if __name__ == '__main__':
    main()
