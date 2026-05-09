#!/usr/bin/env python3
"""
Kairo Effects — MCP Server entry point
Wraps effects_engine.py as a proper MCP-compatible JSON-RPC server
"""

import sys
import json
import asyncio
import subprocess
import os
from pathlib import Path

EFFECTS_DIR = Path(__file__).parent

async def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id", 1)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "kairo-effects", "version": "1.0.0"}
            }
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "render_transition_video",
                        "description": "Render a cinematic transition video between two slides using physics/GLSL effects",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "effect": {"type": "string", "enum": [
                                    "cloth_tear", "glitch_reveal", "gl_wipe_left", "crosszoom",
                                    "gl_cube", "gl_ripple", "particle_disintegrate",
                                    "cinema_fade", "ascii_dissolve"
                                ]},
                                "from_image": {"type": "string", "description": "Path to from-slide screenshot"},
                                "to_image": {"type": "string", "description": "Path to to-slide screenshot"},
                                "output_path": {"type": "string", "description": "Output MP4 file path"},
                                "duration_ms": {"type": "integer", "default": 1200}
                            },
                            "required": ["effect", "output_path"]
                        }
                    },
                    {
                        "name": "list_effects",
                        "description": "List all available cinematic transition effects",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name == "list_effects":
            effects = [
                "cloth_tear", "glitch_reveal", "gl_wipe_left", "crosszoom",
                "gl_cube", "gl_ripple", "particle_disintegrate", "cinema_fade", "ascii_dissolve"
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": json.dumps({"effects": effects})}]
            }}

        if tool_name == "render_transition_video":
            effect = tool_args.get("effect", "cinema_fade")
            output_path = tool_args.get("output_path", "transition.mp4")
            from_image = tool_args.get("from_image", "")
            to_image = tool_args.get("to_image", "")
            duration_ms = tool_args.get("duration_ms", 1200)

            # Call effects_engine.py
            script = EFFECTS_DIR / "effects_engine.py"
            try:
                result = subprocess.run(
                    [sys.executable, str(script),
                     "--effect", effect,
                     "--output", output_path,
                     "--from", from_image,
                     "--to", to_image,
                     "--duration", str(duration_ms)],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return {"jsonrpc": "2.0", "id": req_id, "result": {
                        "content": [{"type": "text", "text": json.dumps({
                            "success": True, "output": output_path, "effect": effect
                        })}]
                    }}
                else:
                    return {"jsonrpc": "2.0", "id": req_id, "result": {
                        "content": [{"type": "text", "text": json.dumps({
                            "success": False, "error": result.stderr[:500]
                        })}]
                    }}
            except subprocess.TimeoutExpired:
                return {"jsonrpc": "2.0", "id": req_id, "result": {
                    "content": [{"type": "text", "text": json.dumps({"success": False, "error": "timeout"})}]
                }}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


async def main():
    """Stdio JSON-RPC server loop"""
    loop = asyncio.get_event_loop()

    def read_line():
        return sys.stdin.readline()

    while True:
        line = await loop.run_in_executor(None, read_line)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = await handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }), flush=True)
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
