#!/usr/bin/env python3
"""
kairo_gauntlet_graph.py  —  Graphify the 76-scenario memory graph
=================================================================
Reads roadmaptoshow/output/kairo_gauntlet_graph.json and generates
an interactive D3.js force-directed HTML graph at:
  roadmaptoshow/output/kairo_gauntlet_graph.html

Nodes:
  ● Blue  = Agent (12 nodes)
  ● Green = Scenario (76 nodes)
  ● Red   = Global rule / prerequisite node

Edges:
  Agent → Scenario (owns)
  Scenario → Fixture (requires)

Run:
    python roadmaptoshow/kairo_gauntlet_graph.py
"""

import json, pathlib, textwrap, html

ROOT = pathlib.Path(__file__).parent
GRAPH_JSON  = ROOT / "output" / "kairo_gauntlet_graph.json"
OUTPUT_HTML = ROOT / "output" / "kairo_gauntlet_graph.html"


def build_graph(data: dict):
    nodes, links = [], []
    nid = {}   # name → index

    def add(name, group, meta=""):
        if name not in nid:
            nid[name] = len(nodes)
            nodes.append({"id": name, "group": group, "meta": meta})
        return nid[name]

    # Central hub
    hub = add("Kairo Phantom\n76-Scenario Gauntlet", 0)

    for agent in data["agents"]:
        aid  = agent["agentId"]
        aapp = agent.get("app","")
        ram  = agent.get("local_ram_mb", 0)
        a_node = add(aid, 1, f"{aapp} | RAM ~{ram} MB")
        links.append({"source": hub, "target": a_node, "type": "owns"})

        for scenario in agent.get("scenarios", []):
            sid = scenario["id"]
            label = f"{sid}\n{scenario['name'][:40]}"
            timeout = scenario.get("timeout", 0)
            s_node = add(label, 2, f"Timeout: {timeout}s")
            links.append({"source": a_node, "target": s_node, "type": "contains"})

            # Fixture edge
            if "fixture" in scenario:
                fix_label = f"📄 {scenario['fixture']}"
                f_node = add(fix_label, 3)
                links.append({"source": s_node, "target": f_node, "type": "requires"})

    return nodes, links


def render_html(nodes, links) -> str:
    nodes_js = json.dumps(nodes)
    links_js = json.dumps(links)

    return textwrap.dedent(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Kairo Phantom — 76-Scenario Agent Memory Graph</title>
      <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#0d1117; color:#e6edf3; font-family:Inter,system-ui,sans-serif; overflow:hidden; }}
        #header {{
          position:fixed; top:0; left:0; right:0; z-index:10;
          padding:14px 24px;
          background:rgba(13,17,23,0.92);
          border-bottom:1px solid #30363d;
          display:flex; align-items:center; gap:16px;
        }}
        #header h1 {{ font-size:15px; font-weight:600; color:#f0f6fc; }}
        #header .badge {{
          padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600;
        }}
        .b-agents {{ background:#1f4e8c; color:#79c0ff; }}
        .b-scenarios {{ background:#1a4428; color:#56d364; }}
        .b-fixtures {{ background:#3d2200; color:#ffa657; }}
        #tooltip {{
          position:fixed; background:#161b22; border:1px solid #30363d;
          border-radius:8px; padding:10px 14px; font-size:13px;
          pointer-events:none; opacity:0; transition:opacity .15s;
          max-width:280px; line-height:1.5;
        }}
        svg {{ width:100vw; height:100vh; }}
        .link {{ stroke-opacity:0.35; }}
        .link-owns      {{ stroke:#1f4e8c; }}
        .link-contains  {{ stroke:#1a4428; }}
        .link-requires  {{ stroke:#3d2200; }}
        .node circle {{ stroke-width:1.5; cursor:pointer; }}
        .node text {{
          font-size:9px; fill:#c9d1d9; pointer-events:none;
          text-anchor:middle; dominant-baseline:central;
        }}
        /* Legend */
        #legend {{
          position:fixed; bottom:20px; left:20px;
          background:rgba(13,17,23,0.9); border:1px solid #30363d;
          border-radius:8px; padding:12px 16px; font-size:12px;
        }}
        .leg-row {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
        .leg-dot {{ width:12px; height:12px; border-radius:50%; flex-shrink:0; }}
      </style>
      <script src="https://d3js.org/d3.v7.min.js"></script>
    </head>
    <body>
    <div id="header">
      <h1>🧠 Kairo Phantom — Agent Memory Graph</h1>
      <span class="badge b-agents">12 Agents</span>
      <span class="badge b-scenarios">76 Scenarios</span>
      <span class="badge b-fixtures">Fixtures</span>
    </div>
    <div id="tooltip"></div>
    <div id="legend">
      <div class="leg-row"><div class="leg-dot" style="background:#f78166"></div>Hub</div>
      <div class="leg-row"><div class="leg-dot" style="background:#79c0ff"></div>Agent (12)</div>
      <div class="leg-row"><div class="leg-dot" style="background:#56d364"></div>Scenario (76)</div>
      <div class="leg-row"><div class="leg-dot" style="background:#ffa657"></div>Fixture</div>
    </div>
    <svg id="graph"></svg>
    <script>
    const nodes = {nodes_js};
    const links = {links_js};

    const colorMap = ["#f78166","#79c0ff","#56d364","#ffa657","#d2a8ff"];

    const svg   = d3.select("#graph");
    const W     = window.innerWidth;
    const H     = window.innerHeight;
    const tooltip = document.getElementById("tooltip");

    const sim = d3.forceSimulation(nodes)
      .force("link",   d3.forceLink(links).id(d=>d.id).distance(d=>d.type==="contains"?90:160).strength(0.6))
      .force("charge", d3.forceManyBody().strength(-220))
      .force("center", d3.forceCenter(W/2, H/2))
      .force("collide", d3.forceCollide(20));

    const g = svg.append("g");

    // Zoom
    svg.call(d3.zoom().scaleExtent([0.15,4]).on("zoom", e => g.attr("transform", e.transform)));

    // Links
    const link = g.append("g").selectAll("line")
      .data(links).join("line")
      .attr("class", d=>"link link-"+d.type)
      .attr("stroke-width", d=>d.type==="owns"?2:1);

    // Nodes
    const node = g.append("g").selectAll("g")
      .data(nodes).join("g")
      .attr("class","node")
      .call(d3.drag()
        .on("start", (e,d)=>{{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
        .on("drag",  (e,d)=>{{ d.fx=e.x; d.fy=e.y; }})
        .on("end",   (e,d)=>{{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}));

    node.append("circle")
      .attr("r", d=>d.group===0?22:d.group===1?16:d.group===2?10:8)
      .attr("fill", d=>colorMap[d.group]||"#888")
      .attr("fill-opacity", d=>d.group===0?1:0.85)
      .attr("stroke", d=>d3.color(colorMap[d.group]||"#888").brighter(1))
      .on("mouseover", (e,d)=>{{
        tooltip.style.opacity=1;
        tooltip.style.left=(e.clientX+16)+"px";
        tooltip.style.top=(e.clientY-10)+"px";
        tooltip.innerHTML="<strong>"+d.id.replace(/\n/,"<br>")+"</strong>"+(d.meta?"<br><span style='color:#8b949e'>"+d.meta+"</span>":"");
      }})
      .on("mousemove", e=>{{tooltip.style.left=(e.clientX+16)+"px"; tooltip.style.top=(e.clientY-10)+"px";}})
      .on("mouseout",  ()=>{{tooltip.style.opacity=0;}});

    node.append("text")
      .text(d=>d.id.split("\\n")[0].replace("agent_","").toUpperCase())
      .attr("font-weight", d=>d.group<=1?"600":"400");

    sim.on("tick",()=>{{
      link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
          .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
      node.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
    }});

    window.addEventListener("resize",()=>{{
      sim.force("center",d3.forceCenter(window.innerWidth/2,window.innerHeight/2)).alpha(0.3).restart();
    }});
    </script>
    </body></html>
    """).strip()


def main():
    data = json.loads(GRAPH_JSON.read_text())
    nodes, links = build_graph(data)
    html_content = render_html(nodes, links)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"[OK] Graph written: {OUTPUT_HTML}")
    print(f"     Nodes: {len(nodes)} | Links: {len(links)}")
    print(f"     Open:  file:///{OUTPUT_HTML.as_posix()}")


if __name__ == "__main__":
    main()
