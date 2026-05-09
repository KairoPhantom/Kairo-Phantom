#!/usr/bin/env python3
"""
kairo_memory_graph.py — Graphify Memory Graph for Kairo Phantom Phases 1-4

Generates a structured knowledge graph representing:
- The 4 roadmap phases and their relationships
- Key components, agents, and bridges
- Integration surfaces and data flows
- Tech stack nodes and connections

Run: python kairo_memory_graph.py
Output: kairo_phases_graph.html (interactive) + kairo_phases_graph.json (data)
"""

import json
import os
from datetime import datetime

# ─── Graph Data Model ──────────────────────────────────────────────────────────

NODES = [
    # === PHASES (Top-level) ===
    {"id": "phase1", "label": "Phase 1: Image Generation Layer", "group": "phase", "level": 0,
     "description": "gpt-image-1 + Ollama Diffuser + ImageRouter. Weeks 1-2.",
     "status": "COMPLETE"},
    {"id": "phase2", "label": "Phase 2: PPT MCP Bridge", "group": "phase", "level": 0,
     "description": "Office-PowerPoint-MCP-Server + python-pptx. Weeks 3-4.",
     "status": "COMPLETE"},
    {"id": "phase3", "label": "Phase 3: Ghost Session UX", "group": "phase", "level": 0,
     "description": "Streaming cancel, ghost preview, undo, alternatives, Yjs CRDT. Weeks 5-6.",
     "status": "COMPLETE"},
    {"id": "phase4", "label": "Phase 4: Launch & Distribution", "group": "phase", "level": 0,
     "description": "kairo-mcp server, one-liner install, demo video, VC readiness.",
     "status": "COMPLETE"},

    # === CORE ENGINE ===
    {"id": "phantom_core", "label": "phantom-core (Rust)", "group": "core", "level": 1,
     "description": "Single binary. cargo install kairo-phantom."},
    {"id": "swarm_brain", "label": "Swarm Brain", "group": "core", "level": 2,
     "description": "Multi-agent orchestrator. Routes to Design/Prose/Code/Image agent."},
    {"id": "context_engine", "label": "Context Engine", "group": "core", "level": 2,
     "description": "AppFingerprinter + DocumentContext extraction."},
    {"id": "injector", "label": "Injector", "group": "core", "level": 2,
     "description": "Clipboard + UIA SetValue + MCP routes (Adeu/Notion/Figma)."},
    {"id": "crdt", "label": "CRDT Session (Yrs)", "group": "core", "level": 2,
     "description": "Yjs-compatible CRDT for collaborative AI peer mode."},
    {"id": "hotkey", "label": "Hotkey Listener (Alt+M)", "group": "core", "level": 2,
     "description": "Global hotkey via rdev. Triggers Ghost Session."},

    # === PHASE 1 COMPONENTS ===
    {"id": "image_pipeline", "label": "image_pipeline.rs", "group": "phase1", "level": 3,
     "description": "ImageRouter with cloud/local backends."},
    {"id": "openai_image", "label": "OpenAI gpt-image-1", "group": "phase1", "level": 4,
     "description": "Cloud: returns base64 PNG. Title slides, hero images."},
    {"id": "openai_mini", "label": "gpt-image-1-mini", "group": "phase1", "level": 4,
     "description": "Cloud: faster/cheaper. Icons, thumbnails."},
    {"id": "ollama_sd", "label": "Ollama Stable Diffusion", "group": "phase1", "level": 4,
     "description": "Local: Stable Diffusion / FLUX via Ollama API."},
    {"id": "image_router", "label": "ImageRouter", "group": "phase1", "level": 3,
     "description": "Smart routing: offline? → local. Title slide? → cloud HQ. Icon? → mini."},
    {"id": "image_inject", "label": "Image Clipboard Inject", "group": "phase1", "level": 3,
     "description": "write_image_to_clipboard() → Ctrl+V into Word/PPT/Figma."},

    # === PHASE 2 COMPONENTS ===
    {"id": "office_pptx_bridge", "label": "office-pptx-bridge (Python)", "group": "phase2", "level": 3,
     "description": "MCP stdio server. Wraps python-pptx for full PPTX manipulation."},
    {"id": "python_pptx", "label": "python-pptx", "group": "phase2", "level": 4,
     "description": "create_presentation, add_slide, add_picture, read_slide_text."},
    {"id": "figma_bridge", "label": "figma-mcp-go Bridge", "group": "phase2", "level": 4,
     "description": "73 tools. import_image(base64), create_text, set_fills."},
    {"id": "canva_api", "label": "Canva Connect API", "group": "phase2", "level": 4,
     "description": "POST /v1/autofills. Image placeholder injection."},
    {"id": "notion_mcp", "label": "easy-notion-mcp", "group": "phase2", "level": 4,
     "description": "25 block types. Append, update, round-trip fidelity."},
    {"id": "adeu_mcp", "label": "Adeu MCP (DOCX Track Changes)", "group": "phase2", "level": 4,
     "description": "Native DOCX redlining without breaking formatting."},

    # === PHASE 3 COMPONENTS ===
    {"id": "ghost_session", "label": "ghost_session.rs", "group": "phase3", "level": 3,
     "description": "Full Ghost Session lifecycle: stream → review → accept/cancel."},
    {"id": "cancel_token", "label": "CancellationToken (Esc)", "group": "phase3", "level": 4,
     "description": "tokio_util CancellationToken. Esc immediately aborts stream."},
    {"id": "ghost_buffer", "label": "GhostBuffer (Alt A/B)", "group": "phase3", "level": 4,
     "description": "Two alternatives. word-by-word accept (Ctrl+Right)."},
    {"id": "undo_manager", "label": "UndoManager (Ctrl+Z)", "group": "phase3", "level": 4,
     "description": "Agent-aware undo. One Ctrl+Z reverts entire AI operation."},
    {"id": "confidence_band", "label": "Confidence Bands", "group": "phase3", "level": 4,
     "description": "High/Medium/Low. Changes available actions. Trust calibration."},
    {"id": "yjs_peer", "label": "Yjs CRDT Peer", "group": "phase3", "level": 4,
     "description": "AI joins as WebSocket peer with clientID. Real-time collab."},
    {"id": "inline_correction", "label": "Inline Correction (Ctrl+/)", "group": "phase3", "level": 4,
     "description": "Mini-prompt overlay. Re-streams with correction."},

    # === PHASE 4 COMPONENTS ===
    {"id": "kairo_mcp", "label": "kairo-mcp Server", "group": "phase4", "level": 3,
     "description": "MCP stdio server exposing 5 tools for Claude Code/Cursor/Goose."},
    {"id": "mcp_tools", "label": "MCP Tools (5)", "group": "phase4", "level": 4,
     "description": "kairo_read_context, kairo_ghost_write, kairo_ask, kairo_detect_app, kairo_generate_image."},
    {"id": "install_script", "label": "install.py (One-liner)", "group": "phase4", "level": 4,
     "description": "Cross-platform installer. Checks Rust, Ollama, builds binary."},
    {"id": "demo_video", "label": "90s Demo Video", "group": "phase4", "level": 4,
     "description": "Word → PPT → Figma → Terminal. Single continuous take. Launch asset."},
    {"id": "vc_readiness", "label": "Enterprise / VC Readiness", "group": "phase4", "level": 4,
     "description": "SSO, audit logging, plugin governance, private registries."},

    # === TARGET APPS ===
    {"id": "word", "label": "Microsoft Word", "group": "target", "level": 5},
    {"id": "ppt", "label": "Microsoft PowerPoint", "group": "target", "level": 5},
    {"id": "figma", "label": "Figma", "group": "target", "level": 5},
    {"id": "notion", "label": "Notion", "group": "target", "level": 5},
    {"id": "vscode", "label": "VS Code", "group": "target", "level": 5},
    {"id": "terminal", "label": "Terminal", "group": "target", "level": 5},
    {"id": "canva", "label": "Canva", "group": "target", "level": 5},
    {"id": "google_docs", "label": "Google Docs (Yjs)", "group": "target", "level": 5},
    {"id": "any_app", "label": "Any Text Field", "group": "target", "level": 5},
]

EDGES = [
    # Phase → Core
    {"from": "phase1", "to": "image_pipeline", "label": "implements"},
    {"from": "phase2", "to": "office_pptx_bridge", "label": "implements"},
    {"from": "phase3", "to": "ghost_session", "label": "implements"},
    {"from": "phase4", "to": "kairo_mcp", "label": "implements"},

    # Core engine relationships
    {"from": "phantom_core", "to": "swarm_brain", "label": "orchestrates"},
    {"from": "phantom_core", "to": "context_engine", "label": "uses"},
    {"from": "phantom_core", "to": "injector", "label": "uses"},
    {"from": "phantom_core", "to": "crdt", "label": "uses"},
    {"from": "phantom_core", "to": "hotkey", "label": "triggered by"},
    {"from": "hotkey", "to": "ghost_session", "label": "starts"},

    # Image Pipeline
    {"from": "image_pipeline", "to": "image_router", "label": "contains"},
    {"from": "image_router", "to": "openai_image", "label": "routes to"},
    {"from": "image_router", "to": "openai_mini", "label": "routes to"},
    {"from": "image_router", "to": "ollama_sd", "label": "routes to"},
    {"from": "image_pipeline", "to": "image_inject", "label": "outputs to"},
    {"from": "swarm_brain", "to": "image_pipeline", "label": "delegates"},

    # PPT/MCP bridges
    {"from": "office_pptx_bridge", "to": "python_pptx", "label": "wraps"},
    {"from": "injector", "to": "figma_bridge", "label": "MCP route"},
    {"from": "injector", "to": "notion_mcp", "label": "MCP route"},
    {"from": "injector", "to": "adeu_mcp", "label": "MCP route"},
    {"from": "injector", "to": "office_pptx_bridge", "label": "subprocess bridge"},
    {"from": "injector", "to": "canva_api", "label": "REST call"},

    # Ghost Session
    {"from": "ghost_session", "to": "cancel_token", "label": "Esc"},
    {"from": "ghost_session", "to": "ghost_buffer", "label": "buffers"},
    {"from": "ghost_session", "to": "undo_manager", "label": "Ctrl+Z"},
    {"from": "ghost_session", "to": "confidence_band", "label": "computes"},
    {"from": "ghost_session", "to": "yjs_peer", "label": "Yjs mode"},
    {"from": "ghost_session", "to": "inline_correction", "label": "Ctrl+/"},
    {"from": "ghost_session", "to": "injector", "label": "Tab accept"},

    # MCP Server
    {"from": "kairo_mcp", "to": "mcp_tools", "label": "exposes"},
    {"from": "kairo_mcp", "to": "phantom_core", "label": "proxies to"},

    # Target app integrations
    {"from": "image_inject", "to": "word", "label": "paste image"},
    {"from": "image_inject", "to": "ppt", "label": "paste image"},
    {"from": "python_pptx", "to": "ppt", "label": "native write"},
    {"from": "figma_bridge", "to": "figma", "label": "73 tools"},
    {"from": "notion_mcp", "to": "notion", "label": "25 block types"},
    {"from": "adeu_mcp", "to": "word", "label": "track changes"},
    {"from": "injector", "to": "vscode", "label": "clipboard"},
    {"from": "injector", "to": "terminal", "label": "clipboard"},
    {"from": "canva_api", "to": "canva", "label": "autofills"},
    {"from": "yjs_peer", "to": "google_docs", "label": "CRDT peer"},
    {"from": "injector", "to": "any_app", "label": "Ctrl+V"},

    # Install/Demo
    {"from": "install_script", "to": "phantom_core", "label": "builds"},
    {"from": "install_script", "to": "kairo_mcp", "label": "builds"},
    {"from": "demo_video", "to": "word", "label": "demonstrates"},
    {"from": "demo_video", "to": "ppt", "label": "demonstrates"},
    {"from": "demo_video", "to": "figma", "label": "demonstrates"},
    {"from": "demo_video", "to": "terminal", "label": "demonstrates"},
]

# ─── HTML Graph Generator ──────────────────────────────────────────────────────

GROUP_COLORS = {
    "phase": "#6366f1",    # indigo
    "core": "#0ea5e9",     # sky blue
    "phase1": "#f59e0b",   # amber
    "phase2": "#10b981",   # emerald
    "phase3": "#ec4899",   # pink
    "phase4": "#8b5cf6",   # violet
    "target": "#64748b",   # slate
}

def build_html(nodes, edges):
    nodes_js = json.dumps([{
        "id": n["id"],
        "label": n["label"],
        "group": n["group"],
        "level": n.get("level", 0),
        "title": n.get("description", ""),
        "color": GROUP_COLORS.get(n["group"], "#94a3b8"),
        "font": {"color": "#fff", "size": 12},
        "shape": "box",
        "status": n.get("status", ""),
    } for n in nodes], indent=2)

    edges_js = json.dumps([{
        "from": e["from"],
        "to": e["to"],
        "label": e.get("label", ""),
        "arrows": "to",
        "color": {"color": "#475569"},
        "font": {"color": "#94a3b8", "size": 10},
    } for e in edges], indent=2)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kairo Phantom — Phase Memory Graph</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0f172a;
    font-family: 'Inter', system-ui, sans-serif;
    color: #e2e8f0;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }}
  header {{
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-bottom: 1px solid #1e3a5f;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  header h1 {{
    font-size: 1.25rem;
    font-weight: 700;
    background: linear-gradient(90deg, #60a5fa, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  header p {{
    font-size: 0.75rem;
    color: #64748b;
  }}
  .badge {{
    background: #1e3a5f;
    color: #60a5fa;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
    border: 1px solid #2563eb44;
  }}
  #legend {{
    display: flex;
    gap: 12px;
    padding: 8px 24px;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    flex-wrap: wrap;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    color: #94a3b8;
  }}
  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }}
  #graph {{
    flex: 1;
    background: #0a0f1e;
  }}
  #info-panel {{
    position: fixed;
    right: 16px;
    top: 100px;
    width: 260px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
    display: none;
    box-shadow: 0 20px 60px #00000080;
  }}
  #info-panel h3 {{
    font-size: 0.9rem;
    color: #e2e8f0;
    margin-bottom: 8px;
  }}
  #info-panel p {{
    font-size: 0.75rem;
    color: #94a3b8;
    line-height: 1.5;
  }}
  #info-panel .status {{
    margin-top: 8px;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    display: inline-block;
    background: #16a34a22;
    color: #4ade80;
    border: 1px solid #16a34a44;
  }}
</style>
</head>
<body>
<header>
  <div>
    <h1>👻 Kairo Phantom — Phase Memory Graph</h1>
    <p>Interactive knowledge graph of all 4 roadmap phases &amp; components</p>
  </div>
  <div class="badge">v4.0 · {datetime.now().strftime('%Y-%m-%d')}</div>
</header>
<div id="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#6366f1"></div>Phase</div>
  <div class="legend-item"><div class="legend-dot" style="background:#0ea5e9"></div>Core Engine</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div>Phase 1 (Image)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div>Phase 2 (PPT/MCP)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ec4899"></div>Phase 3 (Ghost UX)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6"></div>Phase 4 (Launch)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#64748b"></div>Target Apps</div>
</div>
<div id="graph"></div>
<div id="info-panel">
  <h3 id="info-title"></h3>
  <p id="info-desc"></p>
  <span class="status" id="info-status" style="display:none"></span>
</div>

<script>
const nodes = new vis.DataSet({nodes_js});
const edges = new vis.DataSet({edges_js});

const container = document.getElementById('graph');
const network = new vis.Network(container, {{ nodes, edges }}, {{
  layout: {{
    hierarchical: {{
      enabled: true,
      direction: 'LR',
      sortMethod: 'directed',
      levelSeparation: 200,
      nodeSpacing: 80,
    }}
  }},
  physics: {{
    hierarchicalRepulsion: {{
      nodeDistance: 120,
    }},
    stabilization: {{ iterations: 200 }}
  }},
  edges: {{
    smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal' }},
    width: 1.5,
  }},
  nodes: {{
    borderWidth: 1.5,
    borderColor: '#334155',
    margin: 8,
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 100,
  }}
}});

const nodeData = {json.dumps({n["id"]: {"label": n["label"], "description": n.get("description",""), "status": n.get("status","")} for n in NODES})};


network.on('click', function(params) {{
  const panel = document.getElementById('info-panel');
  if (params.nodes.length > 0) {{
    const id = params.nodes[0];
    const n = nodeData[id];
    if (n) {{
      document.getElementById('info-title').textContent = n.label;
      document.getElementById('info-desc').textContent = n.description || 'No description.';
      const statusEl = document.getElementById('info-status');
      if (n.status) {{
        statusEl.textContent = '✅ ' + n.status;
        statusEl.style.display = 'inline-block';
      }} else {{
        statusEl.style.display = 'none';
      }}
      panel.style.display = 'block';
    }}
  }} else {{
    panel.style.display = 'none';
  }}
}});
</script>
</body>
</html>
"""
    return html

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
    print("[*] Building Kairo Phantom Memory Graph (Graphify)...")

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Write JSON data
    graph_data = {"nodes": NODES, "edges": EDGES, "generated": datetime.now().isoformat()}
    json_path = os.path.join(output_dir, "kairo_phases_graph.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"  [OK] Graph data: {json_path}")

    # Write interactive HTML
    html = build_html(NODES, EDGES)
    html_path = os.path.join(output_dir, "kairo_phases_graph.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [OK] Interactive graph: {html_path}")

    print(f"\n[STATS] Graph Stats:")
    print(f"  Nodes: {len(NODES)}")
    print(f"  Edges: {len(EDGES)}")
    print(f"  Groups: phase, core, phase1, phase2, phase3, phase4, target")
    print(f"\n[OPEN] file://{html_path}")

if __name__ == "__main__":
    main()
