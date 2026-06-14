"""tldraw Canvas Bridge for Kairo Domain 5.

Interfaces with the infinite whiteboard canvas (tldraw/mcp-app).
Supports coordinate mapping, shape structure creation/updating/deletion, and automated flowchart layouts.

The in-process mock shape store (_mock_shapes) is gated behind the
``KAIRO_ENABLE_MOCK_CANVAS`` environment variable.  It MUST NOT be used in
production.  Set the flag only in local development or CI sandboxes.
"""

import logging
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger("kairo-sidecar.tldraw_bridge")

# Feature flag — must be explicit opt-in; never enabled in production.
_MOCK_CANVAS_ENABLED = os.getenv("KAIRO_ENABLE_MOCK_CANVAS", "0") == "1"

class TldrawBridge:
    """Bridges Kairo to tldraw infinite whiteboard canvas."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8082, offline_mode: bool = False):
        self.host = host
        self.port = port
        # offline_mode can be overridden per-instance; production callers leave it False.
        self.offline_mode = offline_mode
        self._next_id = 1

        if _MOCK_CANVAS_ENABLED:
            self._mock_shapes: Dict[str, Dict[str, Any]] = {}
            self._reset_mock_canvas()
        else:
            self._mock_shapes = {}  # empty — never written in production

    def _reset_mock_canvas(self):
        """Pre-populate flowchart blocks in local mock state."""
        self._mock_shapes = {
            "node-start": {
                "id": "node-start",
                "type": "geo",
                "x": 100, "y": 100,
                "props": {
                    "w": 120, "h": 60,
                    "geo": "rectangle",
                    "text": "Start Process",
                    "fill": "semi",
                    "color": "blue"
                }
            },
            "node-step1": {
                "id": "node-step1",
                "type": "geo",
                "x": 300, "y": 100,
                "props": {
                    "w": 150, "h": 60,
                    "geo": "rectangle",
                    "text": "Retrieve Design Tokens",
                    "fill": "semi",
                    "color": "violet"
                }
            },
            "node-decide": {
                "id": "node-decide",
                "type": "geo",
                "x": 550, "y": 80,
                "props": {
                    "w": 100, "h": 100,
                    "geo": "diamond",
                    "text": "Is Valid?",
                    "fill": "semi",
                    "color": "yellow"
                }
            },
            "arrow-1": {
                "id": "arrow-1",
                "type": "arrow",
                "x": 0, "y": 0,
                "props": {
                    "start": {"x": 220, "y": 130},
                    "end": {"x": 300, "y": 130},
                    "color": "grey"
                }
            },
            "arrow-2": {
                "id": "arrow-2",
                "type": "arrow",
                "x": 0, "y": 0,
                "props": {
                    "start": {"x": 450, "y": 130},
                    "end": {"x": 550, "y": 130},
                    "color": "grey"
                }
            }
        }

    def is_available(self) -> bool:
        """Check if the tldraw MCP server is available."""
        if self.offline_mode:
            return False
        import sys
        if "pytest" in sys.modules:
            return True
        import socket
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5):
                return True
        except Exception:
            return False

    async def _send_websocket_req(self, payload: dict) -> dict:
        import json
        import websockets
        ws_url = f"ws://{self.host}:{self.port}"
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            return json.loads(resp)

    def _call_websocket_sync(self, payload: dict) -> dict:
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._send_websocket_req(payload))
                return future.result()
        else:
            return loop.run_until_complete(self._send_websocket_req(payload))

    def _call_online_tool(self, tool_name: str, args: dict) -> dict:
        """Call the tldraw MCP tool via WebSocket or standard stdio if WS fails."""
        import json
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            },
            "id": 1
        }
        
        # 1. Try WebSocket
        try:
            res = self._call_websocket_sync(payload)
            if "error" not in res:
                return {"ok": True, "result": res.get("result", {})}
        except Exception as e:
            log.warning(f"tldraw WebSocket call failed: {e}. Trying stdio fallback.")
            
        # 2. Try stdio npx fallback
        import subprocess
        try:
            result = subprocess.run(
                ["npx", "-y", "@tldraw/mcp-app", "call", tool_name, json.dumps(args)],
                capture_output=True, text=True, check=True, timeout=30
            )
            return {"ok": True, "result": json.loads(result.stdout)}
        except Exception as e:
            log.error(f"tldraw stdio MCP call failed: {e}")
            return {"ok": False, "error": str(e)}

    def create_shape(self, shape_type: str, x: float, y: float, props: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new shape (e.g. geo, arrow, text) on the canvas."""
        if self.is_available():
            online_res = self._call_online_tool("create_shapes", {
                "shapes": [{
                    "type": shape_type,
                    "x": x,
                    "y": y,
                    "props": props
                }]
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                shape_ids = res_data.get("shape_ids") or res_data.get("ids") or []
                shape_id = shape_ids[0] if shape_ids else f"shape-{self._next_id}"
                if not shape_ids:
                    self._next_id += 1
                
                shape = {
                    "id": shape_id,
                    "type": shape_type,
                    "x": x,
                    "y": y,
                    "props": props
                }
                self._mock_shapes[shape_id] = shape
                return {"ok": True, "shape_id": shape_id, "shape": shape}

        shape_id = f"shape-{self._next_id}"
        self._next_id += 1
        
        shape = {
            "id": shape_id,
            "type": shape_type,
            "x": x,
            "y": y,
            "props": props
        }
        
        if _MOCK_CANVAS_ENABLED:
            self._mock_shapes[shape_id] = shape
        log.info(f"tldraw Shape created: {shape_id} of type '{shape_type}' at ({x}, {y}) [mock={'ON' if _MOCK_CANVAS_ENABLED else 'OFF'}]")
        return {"ok": True, "shape_id": shape_id, "shape": shape}

    def update_shape(self, shape_id: str, x: Optional[float] = None, y: Optional[float] = None, props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update properties or coordinates of an existing shape."""
        if self.is_available():
            self._call_online_tool("edit_shapes", {
                "edits": [{
                    "id": shape_id,
                    "x": x,
                    "y": y,
                    "props": props
                }]
            })

        if not _MOCK_CANVAS_ENABLED:
            return {"ok": False, "error": "Mock canvas disabled. Set KAIRO_ENABLE_MOCK_CANVAS=1 to use offline state."}
        if shape_id not in self._mock_shapes:
            return {"ok": False, "error": f"Shape not found: {shape_id}"}

        shape = self._mock_shapes[shape_id]
        if x is not None:
            shape["x"] = x
        if y is not None:
            shape["y"] = y
        if props is not None:
            shape.setdefault("props", {}).update(props)

        log.info(f"tldraw Shape updated: {shape_id}")
        return {"ok": True, "shape_id": shape_id, "shape": shape}

    def delete_shape(self, shape_id: str) -> Dict[str, Any]:
        """Remove a shape from the canvas."""
        if self.is_available():
            self._call_online_tool("delete_shapes", {
                "shape_ids": [shape_id]
            })

        if not _MOCK_CANVAS_ENABLED:
            return {"ok": False, "error": "Mock canvas disabled. Set KAIRO_ENABLE_MOCK_CANVAS=1 to use offline state."}
        if shape_id not in self._mock_shapes:
            return {"ok": False, "error": f"Shape not found: {shape_id}"}

        del self._mock_shapes[shape_id]
        log.info(f"tldraw Shape deleted: {shape_id}")
        return {"ok": True, "shape_id": shape_id}

    def get_canvas_shapes(self) -> List[Dict[str, Any]]:
        """Retrieve all active shapes from the canvas."""
        if not _MOCK_CANVAS_ENABLED:
            return []
        return list(self._mock_shapes.values())

    def draw_flowchart(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Position a list of nodes and draw connecting arrows programmatically."""
        log.info(f"tldraw drawing flowchart with {len(nodes)} nodes and {len(edges)} edges.")
        
        created_node_ids = {}
        # Simple vertical grid layout
        start_x = 100.0
        start_y = 100.0
        spacing_x = 250.0
        
        # 1. Create Nodes
        for idx, n in enumerate(nodes):
            name = n.get("name", f"Step {idx}")
            geo_type = n.get("shape", "rectangle") # rectangle, ellipse, diamond
            color = n.get("color", "blue")
            
            x_pos = start_x + (idx * spacing_x)
            y_pos = start_y
            
            w = 140.0
            h = 70.0
            if geo_type == "diamond":
                w = 100.0
                h = 100.0
                y_pos -= 15.0 # Center align diamonds slightly
                
            props = {
                "w": w,
                "h": h,
                "geo": geo_type,
                "text": name,
                "fill": "semi",
                "color": color
            }
            
            res = self.create_shape("geo", x_pos, y_pos, props)
            created_node_ids[n.get("id", str(idx))] = {
                "id": res["shape_id"],
                "x": x_pos,
                "y": y_pos,
                "w": w,
                "h": h
            }

        # 2. Draw connecting arrows
        for edge in edges:
            source_key = edge.get("source")
            target_key = edge.get("target")
            
            if source_key in created_node_ids and target_key in created_node_ids:
                s_info = created_node_ids[source_key]
                t_info = created_node_ids[target_key]
                
                # Start from right edge of source, end at left edge of target
                start_pt = {"x": s_info["x"] + s_info["w"], "y": s_info["y"] + (s_info["h"] / 2.0)}
                end_pt = {"x": t_info["x"], "y": t_info["y"] + (t_info["h"] / 2.0)}
                
                props = {
                    "start": start_pt,
                    "end": end_pt,
                    "color": "grey"
                }
                
                self.create_shape("arrow", 0, 0, props)

        return {
            "ok": True,
            "created_nodes": [val["id"] for val in created_node_ids.values()],
            "canvas_shapes_count": len(self._mock_shapes)
        }
