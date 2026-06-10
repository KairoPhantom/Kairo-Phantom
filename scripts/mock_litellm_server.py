#!/usr/bin/env python3
"""
scripts/mock_litellm_server.py
=============================================================================
A standalone HTTP mock server mimicking LiteLLM proxy on port 4000.
Used for headless test environments to supply valid JSON schema operations.
"""

import http.server
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MOCK_LITELLM] %(levelname)s: %(message)s")
log = logging.getLogger("mock_litellm")

PORT = 4000

class MockLiteLLMHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default request logging to keep stdout clean
        pass

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                req = json.loads(post_data.decode("utf-8"))

                # Extract messages
                messages = req.get("messages", [])
                system_prompt = ""
                user_prompt = ""
                for m in messages:
                    role = m.get("role")
                    content = m.get("content", "")
                    if role == "system":
                        system_prompt = content
                    elif role == "user":
                        user_prompt = content

                model = req.get("model", "kairo-standard")
                log.info(f"Received request for model {model!r} with user prompt: {user_prompt[:50]!r}")

                # Determine and generate mock JSON payload
                response_content = self.generate_mock_payload(system_prompt, user_prompt)

                # Wrap in OpenAI / LiteLLM chat completions format
                response_data = {
                    "id": "chatcmpl-mock-4000",
                    "object": "chat.completion",
                    "created": 1677648600,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_content
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 25,
                        "total_tokens": 40
                    }
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode("utf-8"))
            except Exception as e:
                log.error(f"Error handling request: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def generate_mock_payload(self, system: str, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # Group 1: Docx Operation Mocking
        if "KairoDocWriter" in system:
            if "heading" in prompt_lower or "style" in prompt_lower:
                op = {"type": "insert_paragraph", "after_paragraph_index": 2, "style": "Heading 2", "runs": [{"text": "Q3 Results", "bold": False, "italic": False}]}
            elif "replace" in prompt_lower:
                op = {"type": "replace_paragraph", "paragraph_index": 5, "runs": [{"text": "Revenue exceeded targets by 12%.", "bold": False, "italic": False}]}
            elif "bullet" in prompt_lower:
                op = {"type": "append", "runs": [{"text": "Improved customer retention", "bold": False, "italic": False}]}
            elif "table" in prompt_lower:
                op = {"type": "insert_table", "after_paragraph_index": 1, "headers": ["Product", "Revenue", "Cost"], "rows": [["Widget A", "100", "80"]]}
            elif "delete" in prompt_lower:
                op = {"type": "delete_paragraph", "paragraph_index": 4}
            else:
                op = {"type": "insert_paragraph", "after_paragraph_index": 0, "runs": [{"text": "Mock Docx content"}]}
            return json.dumps({"operations": [op]})

        # Group 2: Excel Operation Mocking
        elif "KairoExcelWriter" in system:
            if "vlookup" in prompt_lower:
                op = {"type": "write_cell", "sheet": "Sheet1", "cell": "E2", "formula": "=VLOOKUP(A2, A:B, 2, FALSE)"}
            elif "sum" in prompt_lower or "revenue" in prompt_lower:
                op = {"type": "write_cell", "sheet": "Sheet1", "cell": "D10", "formula": "=SUM(D2:D9)"}
            elif "iferror" in prompt_lower:
                op = {"type": "fill_formula", "sheet": "Sheet1", "range": "C5", "formula": "=IFERROR(C5, 0)"}
            elif "if" in prompt_lower:
                op = {"type": "fill_formula", "sheet": "Sheet1", "range": "G3", "formula": "=IF(F3>1000, \"High\", \"Normal\")"}
            elif "average" in prompt_lower:
                op = {"type": "write_cell", "sheet": "Sheet1", "cell": "C20", "formula": "=AVERAGE(C2:C19)"}
            else:
                op = {"type": "write_cell", "sheet": "Sheet1", "cell": "A1", "formula": "=TODAY()"}
            return json.dumps({"operations": [op]})

        # Group 3: Slide/PowerPoint Operation Mocking
        elif "KairoPptxWriter" in system:
            if "title" in prompt_lower and "update" in prompt_lower:
                op = {"type": "update_title", "slide_index": 3, "title": "Q3 Performance Overview"}
            elif "bullet" in prompt_lower and "replace" in prompt_lower:
                op = {"type": "replace_bullet", "slide_index": 5, "bullet_index": 2, "text": "Revenue up 15% YoY"}
            elif "add" in prompt_lower:
                op = {"type": "add_slide", "after_slide_index": 4, "title": "Key Risks"}
            elif "delete" in prompt_lower:
                op = {"type": "delete_slide", "slide_index": 7}
            elif "notes" in prompt_lower:
                op = {"type": "add_speaker_notes", "slide_index": 3, "notes": "Emphasize the growth trajectory"}
            else:
                op = {"type": "update_title", "slide_index": 0, "title": "Mock Presentation"}
            return json.dumps({"operations": [op]})

        # Fallback empty operations
        return json.dumps({"operations": []})

def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), MockLiteLLMHandler)
    log.info(f"Mock LiteLLM Proxy started at http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Mock server shutting down.")
        server.server_close()

if __name__ == "__main__":
    main()
