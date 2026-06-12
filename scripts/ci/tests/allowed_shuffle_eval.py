import urllib.request, json
import random

CASES = list(range(50))

def pick():
    return random.sample(CASES, k=5)   # ci-guard:allow-random reason=seeded prompt selection, not scoring

def call_model(prompt, system, model, timeout=60.0):
    endpoint = "http://localhost:4000/v1/chat/completions"
    req = urllib.request.Request(endpoint, data=json.dumps({"model": model}).encode())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"]
