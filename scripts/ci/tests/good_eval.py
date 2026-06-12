import urllib.request, json

def call_model(prompt, system, model, timeout=60.0):
    endpoint = "http://localhost:4000/v1/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]
