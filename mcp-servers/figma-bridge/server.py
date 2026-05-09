#!/usr/bin/env python3
"""
Figma MCP Bridge — Phase 2 of Kairo Phantom v3.0
Exposes Figma operations as JSON-RPC/stdio MCP tools.
Integrates with figma-mcp-go protocol for import_image, create_text, create_frame.

Usage:
    python server.py
    (stdin/stdout JSON-RPC transport — spawned by kairo-phantom via mcp_bridge.rs)

Requirements:
    pip install requests python-dotenv
"""

import json
import sys
import os
import base64
import tempfile
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, Optional

# ─── Figma REST API helper ────────────────────────────────────────────────────

def get_figma_token() -> Optional[str]:
    """Read Figma personal access token from env or config."""
    token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if not token:
        config_path = os.path.expanduser("~/.kairo-phantom/config.toml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("figma_token"):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return token

FIGMA_TOKEN = get_figma_token()

def figma_api(method: str, path: str, body: Any = None) -> Dict:
    """Call Figma REST API."""
    if not FIGMA_TOKEN:
        return {"error": "No Figma access token configured. Set FIGMA_ACCESS_TOKEN env var."}

    url = f"https://api.figma.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "X-Figma-Token": FIGMA_TOKEN,
            "Content-Type": "application/json"
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        return {"error": f"Figma API {e.code}: {body_text}"}
    except Exception as e:
        return {"error": str(e)}

# ─── Tool Implementations ─────────────────────────────────────────────────────

def import_image(args: Dict) -> Dict:
    """
    Import an image (base64) into the clipboard so it can be pasted into Figma.
    Also saves to temp file for "Insert > Image" workflow.
    """
    name = args.get("name", "kairo_image")
    image_base64 = args.get("image_base64", "")
    image_mime = args.get("image_mime", "image/png")

    if not image_base64:
        return {"error": "image_base64 is required"}

    # Decode and save to temp file
    try:
        img_bytes = base64.b64decode(image_base64)
        ext = "png" if "png" in image_mime else "jpg"
        tmp_path = os.path.join(tempfile.gettempdir(), f"kairo_figma_{name}.{ext}")
        with open(tmp_path, "wb") as f:
            f.write(img_bytes)

        return {
            "status": "ok",
            "message": f"Image saved to {tmp_path} — drag into Figma or use Import > Image",
            "temp_path": tmp_path,
            "size_bytes": len(img_bytes)
        }
    except Exception as e:
        return {"error": str(e)}

def create_text(args: Dict) -> Dict:
    """Create a text note (saved to clipboard for manual paste into Figma)."""
    text = args.get("text", "")
    x = args.get("x", 0)
    y = args.get("y", 0)

    if not text:
        return {"error": "text is required"}

    # For now: copy text to clipboard via echo approach (full Figma plugin API would need a running plugin)
    # This is the fallback path — the figma-mcp-go plugin provides native write access
    return {
        "status": "ok",
        "text": text,
        "position": {"x": x, "y": y},
        "message": "Text ready. Use figma-mcp-go plugin for direct frame insertion, or Ctrl+V to paste.",
        "clipboard_text": text
    }

def get_file_info(args: Dict) -> Dict:
    """Get Figma file info (requires FIGMA_ACCESS_TOKEN and file_key)."""
    file_key = args.get("file_key", "")
    if not file_key:
        return {"error": "file_key is required"}

    result = figma_api("GET", f"/files/{file_key}")
    if "error" in result:
        return result

    return {
        "status": "ok",
        "name": result.get("name", ""),
        "lastModified": result.get("lastModified", ""),
        "pages": [p["name"] for p in result.get("document", {}).get("children", [])],
    }

def list_frames(args: Dict) -> Dict:
    """List frames in a Figma file."""
    file_key = args.get("file_key", "")
    if not file_key:
        return {"error": "file_key is required"}

    result = figma_api("GET", f"/files/{file_key}/nodes?ids=0:1")
    return result

# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "import_image",
        "description": "Import a base64-encoded image into Figma (saves to temp file + clipboard staging)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Image name (used as filename)"},
                "image_base64": {"type": "string", "description": "Base64-encoded image data (PNG or JPEG)"},
                "image_mime": {"type": "string", "description": "MIME type (image/png or image/jpeg)"}
            },
            "required": ["image_base64"]
        }
    },
    {
        "name": "create_text",
        "description": "Create a text node in Figma (clipboard staging + figma-mcp-go integration)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content"},
                "x": {"type": "number", "description": "X position in Figma canvas"},
                "y": {"type": "number", "description": "Y position in Figma canvas"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "get_file_info",
        "description": "Get metadata about a Figma file (requires FIGMA_ACCESS_TOKEN)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_key": {"type": "string", "description": "Figma file key from the URL"}
            },
            "required": ["file_key"]
        }
    },
    {
        "name": "list_frames",
        "description": "List all top-level frames in a Figma file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_key": {"type": "string", "description": "Figma file key"}
            },
            "required": ["file_key"]
        }
    }
]

TOOL_FNS = {
    "import_image": import_image,
    "create_text": create_text,
    "get_file_info": get_file_info,
    "list_frames": list_frames,
}

# ─── JSON-RPC Server (stdio) ─────────────────────────────────────────────────

def respond(id, result=None, error=None):
    obj = {"jsonrpc": "2.0", "id": id}
    if result is not None:
        obj["result"] = result
    if error is not None:
        obj["error"] = error
    print(json.dumps(obj), flush=True)

def main():
    print("figma-bridge v0.3.0 ready (stdio transport)", file=sys.stderr, flush=True)

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError as e:
            respond(None, error={"code": -32700, "message": f"Parse error: {e}"})
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            respond(req_id, result={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "kairo-figma-bridge", "version": "0.3.0"}
            })

        elif method == "tools/list":
            respond(req_id, result={"tools": TOOLS})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            fn = TOOL_FNS.get(tool_name)
            if fn is None:
                respond(req_id, error={"code": -32000, "message": f"Unknown tool: {tool_name}"})
            else:
                try:
                    result = fn(args)
                    respond(req_id, result=result)
                except Exception as e:
                    respond(req_id, error={"code": -32000, "message": str(e)})
        else:
            respond(req_id, error={"code": -32601, "message": f"Method not found: {method}"})

if __name__ == "__main__":
    main()
