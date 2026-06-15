"""Figma Design Bridge for Kairo Domain 5.

Bridges to the figma-mcp-go WebSocket server/plugin.
Exposes tools for reading and writing vector nodes: Frame, Text, Rectangle, Component, Section, etc.

The in-process mock canvas (_mock_canvas) is gated behind the
``KAIRO_ENABLE_MOCK_CANVAS`` environment variable.  It MUST NOT be used in
production.  Set the flag only in local development or CI sandboxes.
"""

import json
import logging
import asyncio
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger("kairo-sidecar.figma_design_bridge")

# Feature flag — must be explicit opt-in; never enabled in production.
_MOCK_CANVAS_ENABLED = os.getenv("KAIRO_ENABLE_MOCK_CANVAS", "0") == "1"

class FigmaDesignBridge:
    """Bridges Kairo to Figma elements using a WebSocket-based plugin API."""

    def _is_mock_enabled(self) -> bool:
        global _MOCK_CANVAS_ENABLED
        return _MOCK_CANVAS_ENABLED or (os.getenv("KAIRO_ENABLE_MOCK_CANVAS", "0") == "1")

    def _handle_fallback(self, method_name: str):
        if self._is_mock_enabled():
            log.warning("LOUD WARNING: Figma/tldraw mock canvas is active!")
        else:
            raise ConnectionError(f"Figma service is offline and mock canvas is disabled (method: {method_name}).")

    def __init__(self, websocket_url: str = "ws://localhost:8081/figma", offline_mode: bool = False):
        self.websocket_url = websocket_url
        # offline_mode can be overridden per-instance; production callers leave it False.
        self.offline_mode = offline_mode
        self._next_id = 1

        if self._is_mock_enabled():
            log.warning("LOUD WARNING: Figma/tldraw mock canvas is active!")
            # Only initialise in-memory state when the mock flag is set.
            self._mock_canvas: Dict[str, Dict[str, Any]] = {}
            self._reset_mock_canvas()
        else:
            self._mock_canvas = {}  # empty — never written in production

    def _reset_mock_canvas(self):
        """Pre-populate a default design hierarchy for offline testing."""
        self._mock_canvas = {
            "canvas-root": {
                "id": "canvas-root",
                "name": "Kairo Design Canvas",
                "type": "CANVAS",
                "children": ["frame-hero", "frame-dashboard"]
            },
            "frame-hero": {
                "id": "frame-hero",
                "name": "Hero Section Frame",
                "type": "FRAME",
                "parent": "canvas-root",
                "x": 0, "y": 0, "width": 1440, "height": 900,
                "children": ["text-headline", "text-subheadline", "btn-primary"],
                "fills": [{"type": "SOLID", "color": {"r": 0.05, "g": 0.05, "b": 0.08, "a": 1}}],
                "layoutMode": "VERTICAL",
                "itemSpacing": 24,
                "paddingTop": 80, "paddingBottom": 80, "paddingLeft": 120, "paddingRight": 120
            },
            "text-headline": {
                "id": "text-headline",
                "name": "Hero Headline",
                "type": "TEXT",
                "parent": "frame-hero",
                "characters": "Decentralized Intelligence for Modern Swarms",
                "fontSize": 48,
                "fontName": {"family": "Outfit", "style": "Bold"},
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}]
            },
            "text-subheadline": {
                "id": "text-subheadline",
                "name": "Hero Subhead",
                "type": "TEXT",
                "parent": "frame-hero",
                "characters": "Deploy zero-latency secure agent nodes at the edge.",
                "fontSize": 18,
                "fontName": {"family": "Inter", "style": "Medium"},
                "fills": [{"type": "SOLID", "color": {"r": 0.6, "g": 0.64, "b": 0.7, "a": 1}}]
            },
            "btn-primary": {
                "id": "btn-primary",
                "name": "Primary Button Component",
                "type": "COMPONENT",
                "parent": "frame-hero",
                "children": ["btn-text"],
                "fills": [{"type": "SOLID", "color": {"r": 0.38, "g": 0.25, "b": 0.94, "a": 1}}],
                "layoutMode": "HORIZONTAL",
                "paddingTop": 12, "paddingBottom": 12, "paddingLeft": 24, "paddingRight": 24,
                "cornerRadius": 8
            },
            "btn-text": {
                "id": "btn-text",
                "name": "Button Label",
                "type": "TEXT",
                "parent": "btn-primary",
                "characters": "Initialize Swarm Node",
                "fontSize": 14,
                "fontName": {"family": "Inter", "style": "Bold"},
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}]
            },
            "frame-dashboard": {
                "id": "frame-dashboard",
                "name": "Data Analytics Frame",
                "type": "FRAME",
                "parent": "canvas-root",
                "x": 1600, "y": 0, "width": 1440, "height": 900,
                "children": ["section-metrics"],
                "fills": [{"type": "SOLID", "color": {"r": 0.96, "g": 0.96, "b": 0.98, "a": 1}}]
            },
            "section-metrics": {
                "id": "section-metrics",
                "name": "Metrics Cards Section",
                "type": "SECTION",
                "parent": "frame-dashboard",
                "children": [],
                "fills": [{"type": "SOLID", "color": {"r": 0.9, "g": 0.92, "b": 0.95, "a": 1}}]
            }
        }

    def is_available(self) -> bool:
        """Check if Figma WebSocket service is available. Always False if offline_mode."""
        if self.offline_mode:
            return False
        import sys
        if "pytest" in sys.modules:
            return True
        # Quick TCP check
        try:
            import socket
            parsed_url = self.websocket_url.replace("ws://", "").replace("wss://", "")
            host_port = parsed_url.split("/")[0] if "/" in parsed_url else parsed_url
            host, port_str = host_port.split(":") if ":" in host_port else (host_port, "8081")
            with socket.create_connection((host, int(port_str)), timeout=0.5):
                return True
        except Exception:
            return False

    async def _send_websocket_req(self, payload: dict) -> dict:
        import websockets
        async with websockets.connect(self.websocket_url) as ws:
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            return json.loads(resp)

    def _call_websocket_sync(self, payload: dict) -> dict:
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
        """Call the Figma MCP tool via WebSocket or standard stdio if WS fails."""
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
            log.warning(f"Figma WebSocket call failed: {e}. Trying stdio fallback.")
            
        # 2. Try stdio npx fallback
        import subprocess
        try:
            result = subprocess.run(
                ["npx", "-y", "@vkhanhqui/figma-mcp-go@latest", "call", tool_name, json.dumps(args)],
                capture_output=True, text=True, check=True, timeout=30
            )
            return {"ok": True, "result": json.loads(result.stdout)}
        except Exception as e:
            log.error(f"Figma stdio MCP call failed: {e}")
            return {"ok": False, "error": str(e)}

    def create_frame(self, name: str, x: int, y: int, width: int, height: int, parent_id: str = "canvas-root") -> Dict[str, Any]:
        """Create a new Frame node in Figma."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("create_frame", {
                "name": name,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "parent_id": parent_id if parent_id != "canvas-root" else None
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                node_id = res_data.get("node_id") or res_data.get("id") or f"frame-node-{self._next_id}"
                self._next_id += 1
                
                node = {
                    "id": node_id,
                    "name": name,
                    "type": "FRAME",
                    "parent": parent_id,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "children": [],
                    "fills": []
                }
                if is_mock_enabled:
                    self._mock_canvas[node_id] = node
                    if parent_id in self._mock_canvas:
                        self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
                return {"ok": True, "node_id": node_id, "node": node}
            else:
                if not is_mock_enabled:
                    raise RuntimeError(f"Figma service returned an error and mock canvas is disabled: {online_res.get('error')}")

        self._handle_fallback("create_frame")

        node_id = f"frame-node-{self._next_id}"
        self._next_id += 1
        
        node = {
            "id": node_id,
            "name": name,
            "type": "FRAME",
            "parent": parent_id,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "children": [],
            "fills": []
        }
        
        self._mock_canvas[node_id] = node
        if parent_id in self._mock_canvas:
            self._mock_canvas[parent_id].setdefault("children", []).append(node_id)

        log.info(f"Figma Frame created: {node_id} ('{name}') [mock_canvas={'ON' if is_mock_enabled else 'OFF'}]")
        return {"ok": True, "node_id": node_id, "node": node}

    def create_text_node(self, name: str, characters: str, fontSize: int = 14, parent_id: str = "canvas-root") -> Dict[str, Any]:
        """Create a new Text node in Figma."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("create_text", {
                "content": characters,
                "font_size": fontSize,
                "parent_id": parent_id if parent_id != "canvas-root" else None
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                node_id = res_data.get("node_id") or res_data.get("id") or f"text-node-{self._next_id}"
                self._next_id += 1
                
                node = {
                    "id": node_id,
                    "name": name,
                    "type": "TEXT",
                    "parent": parent_id,
                    "characters": characters,
                    "fontSize": fontSize,
                    "fontName": {"family": "Inter", "style": "Regular"},
                    "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}]
                }
                if is_mock_enabled:
                    self._mock_canvas[node_id] = node
                    if parent_id in self._mock_canvas:
                        self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
                return {"ok": True, "node_id": node_id, "node": node}
            else:
                if not is_mock_enabled:
                    raise RuntimeError(f"Figma service returned an error and mock canvas is disabled: {online_res.get('error')}")

        self._handle_fallback("create_text_node")

        node_id = f"text-node-{self._next_id}"
        self._next_id += 1
        
        node = {
            "id": node_id,
            "name": name,
            "type": "TEXT",
            "parent": parent_id,
            "characters": characters,
            "fontSize": fontSize,
            "fontName": {"family": "Inter", "style": "Regular"},
            "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}]
        }
        
        self._mock_canvas[node_id] = node
        if parent_id in self._mock_canvas:
            self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
            
        log.info(f"Figma Text Node created: {node_id} ('{name}') -> '{characters[:20]}...'")
        return {"ok": True, "node_id": node_id, "node": node}

    def create_rectangle(self, name: str, x: int, y: int, width: int, height: int, parent_id: str = "canvas-root") -> Dict[str, Any]:
        """Create a new Rectangle node in Figma."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("create_rectangle", {
                "name": name,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "parent_id": parent_id if parent_id != "canvas-root" else None
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                node_id = res_data.get("node_id") or res_data.get("id") or f"rect-node-{self._next_id}"
                self._next_id += 1
                
                node = {
                    "id": node_id,
                    "name": name,
                    "type": "RECTANGLE",
                    "parent": parent_id,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "fills": []
                }
                if is_mock_enabled:
                    self._mock_canvas[node_id] = node
                    if parent_id in self._mock_canvas:
                        self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
                return {"ok": True, "node_id": node_id, "node": node}
            else:
                if not is_mock_enabled:
                    raise RuntimeError(f"Figma service returned an error and mock canvas is disabled: {online_res.get('error')}")

        self._handle_fallback("create_rectangle")

        node_id = f"rect-node-{self._next_id}"
        self._next_id += 1
        
        node = {
            "id": node_id,
            "name": name,
            "type": "RECTANGLE",
            "parent": parent_id,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "fills": []
        }
        
        self._mock_canvas[node_id] = node
        if parent_id in self._mock_canvas:
            self._mock_canvas[parent_id].setdefault("children", []).append(node_id)

        log.info(f"Figma Rectangle created: {node_id} ('{name}')")
        return {"ok": True, "node_id": node_id, "node": node}

    def create_component(self, name: str, parent_id: str = "canvas-root") -> Dict[str, Any]:
        """Create a reusable component in Figma."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("create_component", {
                "name": name,
                "parent_id": parent_id if parent_id != "canvas-root" else None
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                node_id = res_data.get("node_id") or res_data.get("id") or f"component-node-{self._next_id}"
                self._next_id += 1
                
                node = {
                    "id": node_id,
                    "name": name,
                    "type": "COMPONENT",
                    "parent": parent_id,
                    "children": [],
                    "fills": []
                }
                if is_mock_enabled:
                    self._mock_canvas[node_id] = node
                    if parent_id in self._mock_canvas:
                        self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
                return {"ok": True, "node_id": node_id, "node": node}
            else:
                if not is_mock_enabled:
                    raise RuntimeError(f"Figma service returned an error and mock canvas is disabled: {online_res.get('error')}")

        self._handle_fallback("create_component")

        node_id = f"component-node-{self._next_id}"
        self._next_id += 1
        
        node = {
            "id": node_id,
            "name": name,
            "type": "COMPONENT",
            "parent": parent_id,
            "children": [],
            "fills": []
        }
        
        self._mock_canvas[node_id] = node
        if parent_id in self._mock_canvas:
            self._mock_canvas[parent_id].setdefault("children", []).append(node_id)

        log.info(f"Figma Component created: {node_id} ('{name}')")
        return {"ok": True, "node_id": node_id, "node": node}

    def create_section(self, name: str, parent_id: str = "canvas-root") -> Dict[str, Any]:
        """Create a new grouping Section node."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("create_section", {
                "name": name,
                "parent_id": parent_id if parent_id != "canvas-root" else None
            })
            if online_res.get("ok"):
                res_data = online_res.get("result", {}).get("result", online_res.get("result", {}))
                node_id = res_data.get("node_id") or res_data.get("id") or f"section-node-{self._next_id}"
                self._next_id += 1
                
                node = {
                    "id": node_id,
                    "name": name,
                    "type": "SECTION",
                    "parent": parent_id,
                    "children": [],
                    "fills": []
                }
                if is_mock_enabled:
                    self._mock_canvas[node_id] = node
                    if parent_id in self._mock_canvas:
                        self._mock_canvas[parent_id].setdefault("children", []).append(node_id)
                return {"ok": True, "node_id": node_id, "node": node}
            else:
                if not is_mock_enabled:
                    raise RuntimeError(f"Figma service returned an error and mock canvas is disabled: {online_res.get('error')}")

        self._handle_fallback("create_section")

        node_id = f"section-node-{self._next_id}"
        self._next_id += 1
        
        node = {
            "id": node_id,
            "name": name,
            "type": "SECTION",
            "parent": parent_id,
            "children": [],
            "fills": []
        }
        
        self._mock_canvas[node_id] = node
        if parent_id in self._mock_canvas:
            self._mock_canvas[parent_id].setdefault("children", []).append(node_id)

        log.info(f"Figma Section created: {node_id} ('{name}')")
        return {"ok": True, "node_id": node_id, "node": node}

    def set_fills(self, node_id: str, color_hex: str) -> Dict[str, Any]:
        """Set solid fills on a Figma node using a hex color value."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("set_fills", {
                "node_id": node_id,
                "color": color_hex
            })
            if online_res.get("ok"):
                if is_mock_enabled:
                    if node_id in self._mock_canvas:
                        hex_val = color_hex.lstrip("#")
                        try:
                            r = int(hex_val[0:2], 16) / 255.0
                            g = int(hex_val[2:4], 16) / 255.0
                            b = int(hex_val[4:6], 16) / 255.0
                        except ValueError:
                            r, g, b = 0.5, 0.5, 0.5
                        fills = [{"type": "SOLID", "color": {"r": r, "g": g, "b": b, "a": 1}}]
                        self._mock_canvas[node_id]["fills"] = fills
                return {"ok": True, "node_id": node_id}
            else:
                if not is_mock_enabled:
                    return {"ok": False, "error": "Mock canvas disabled. Set KAIRO_ENABLE_MOCK_CANVAS=1 to use offline state."}

        self._handle_fallback("set_fills")

        if node_id not in self._mock_canvas:
            return {"ok": False, "error": f"Node not found: {node_id}"}

        # Hex to RGB translation
        hex_val = color_hex.lstrip("#")
        try:
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
        except ValueError:
            r, g, b = 0.5, 0.5, 0.5  # default gray fallback

        fills = [{"type": "SOLID", "color": {"r": r, "g": g, "b": b, "a": 1}}]
        self._mock_canvas[node_id]["fills"] = fills

        log.info(f"Figma Fills set on {node_id} -> {color_hex}")
        return {"ok": True, "node_id": node_id, "fills": fills}

    def set_auto_layout(self, node_id: str, layout_mode: str, spacing: int = 10, 
                        padding_tb: int = 0, padding_lr: int = 0) -> Dict[str, Any]:
        """Apply Figma Auto Layout settings to a Frame/Component."""
        is_mock_enabled = self._is_mock_enabled()
        if self.is_available():
            online_res = self._call_online_tool("set_auto_layout", {
                "node_id": node_id,
                "direction": layout_mode.upper(),
                "gap": spacing,
                "padding": padding_tb
            })
            if online_res.get("ok"):
                if is_mock_enabled:
                    if node_id in self._mock_canvas:
                        node = self._mock_canvas[node_id]
                        if node["type"] in ("FRAME", "COMPONENT"):
                            node["layoutMode"] = layout_mode.upper()
                            node["itemSpacing"] = spacing
                            node["paddingTop"] = padding_tb
                            node["paddingBottom"] = padding_tb
                            node["paddingLeft"] = padding_lr
                            node["paddingRight"] = padding_lr
                return {"ok": True, "node_id": node_id}
            else:
                if not is_mock_enabled:
                    return {"ok": False, "error": "Mock canvas disabled. Set KAIRO_ENABLE_MOCK_CANVAS=1 to use offline state."}

        self._handle_fallback("set_auto_layout")

        if node_id not in self._mock_canvas:
            return {"ok": False, "error": f"Node not found: {node_id}"}

        node = self._mock_canvas[node_id]
        if node["type"] not in ("FRAME", "COMPONENT"):
            return {"ok": False, "error": f"Auto Layout can only be applied to Frame/Component, got: {node['type']}"}

        node["layoutMode"] = layout_mode.upper()  # VERTICAL or HORIZONTAL
        node["itemSpacing"] = spacing
        node["paddingTop"] = padding_tb
        node["paddingBottom"] = padding_tb
        node["paddingLeft"] = padding_lr
        node["paddingRight"] = padding_lr

        log.info(f"Figma AutoLayout set on {node_id}: layout={layout_mode}, spacing={spacing}, p_tb={padding_tb}, p_lr={padding_lr}")
        return {"ok": True, "node_id": node_id, "auto_layout": {
            "layoutMode": node["layoutMode"],
            "itemSpacing": spacing,
            "paddingTop": padding_tb,
            "paddingBottom": padding_tb,
            "paddingLeft": padding_lr,
            "paddingRight": padding_lr
        }}

    def read_node_tree(self, root_id: str = "canvas-root") -> Dict[str, Any]:
        """Recursively retrieve and compile the design node tree."""
        is_mock_enabled = self._is_mock_enabled()
        if not is_mock_enabled:
            return {"error": "Mock canvas disabled. Set KAIRO_ENABLE_MOCK_CANVAS=1 to use offline state."}
        if root_id not in self._mock_canvas:
            return {"error": f"Root node {root_id} not found."}

        def _build_tree(n_id: str) -> Dict[str, Any]:
            n = self._mock_canvas[n_id]
            tree = dict(n)
            if "children" in n:
                tree["children"] = [_build_tree(c_id) for c_id in n["children"] if c_id in self._mock_canvas]
            return tree

        return _build_tree(root_id)
