import json
import os

def build_testing_graph():
    graph_data = {
        "nodes": [
            {"id": "V7_ROOT", "label": "v7 Testing Gauntlet", "type": "root", "meta": {"desc": "Production-grade testing for Kairo Phantom"}},
            
            # E2E Tests
            {"id": "TEST_E2E", "label": "E2E GUI Automation", "type": "layer", "meta": {"desc": "Cross-platform tests via autopilot-rs"}},
            {"id": "E2E_HOTKEY", "label": "Hotkey Hooks", "type": "test", "meta": {"desc": "Validates Alt+M across OSes"}},
            {"id": "E2E_UIA", "label": "UIA Extraction", "type": "test", "meta": {"desc": "Validates document reading via Kreuzberg"}},
            
            # Property Tests
            {"id": "TEST_PROP", "label": "Property Testing", "type": "layer", "meta": {"desc": "Proptest for Universal Invariants"}},
            {"id": "PROP_ROUTING", "label": "Swarm Routing", "type": "test", "meta": {"desc": "Validates determinism of brain"}},
            
            # Fuzz Tests
            {"id": "TEST_FUZZ", "label": "Fuzzing", "type": "layer", "meta": {"desc": "cargo-fuzz for attack surfaces"}},
            {"id": "FUZZ_UIA", "label": "UIA Parser Fuzz", "type": "test", "meta": {"desc": "Arbitrary unicode input limits"}},
            {"id": "FUZZ_MCP", "label": "MCP RPC Fuzz", "type": "test", "meta": {"desc": "Malicious JSON RPC input"}},
            
            # Chaos Engineering
            {"id": "TEST_CHAOS", "label": "Chaos Injection", "type": "layer", "meta": {"desc": "Fault injection architecture"}},
            {"id": "CHAOS_SSE", "label": "SSE Storm", "type": "test", "meta": {"desc": "Simulated connection dropouts"}},
            
            # Deterministic Sim
            {"id": "TEST_SIM", "label": "Deterministic Sim", "type": "layer", "meta": {"desc": "MadSim random seed tests"}},
            {"id": "SIM_RUNTIME", "label": "MadSim Runtime", "type": "test", "meta": {"desc": "10,000 seeds verification"}},
            
            # Telemetry
            {"id": "TELEMETRY", "label": "Prod Telemetry", "type": "layer", "meta": {"desc": "tracing and crash reports"}},
            {"id": "TEL_LOGGING", "label": "Structured Logging", "type": "feature", "meta": {"desc": "JSON output for crashes"}},
            
            # CI Pipeline
            {"id": "CI_PIPELINE", "label": "CI Gauntlet", "type": "layer", "meta": {"desc": "GitHub Actions 5-stage pipeline"}},
        ],
        "edges": [
            {"source": "V7_ROOT", "target": "TEST_E2E", "type": "includes"},
            {"source": "TEST_E2E", "target": "E2E_HOTKEY", "type": "implements"},
            {"source": "TEST_E2E", "target": "E2E_UIA", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "TEST_PROP", "type": "includes"},
            {"source": "TEST_PROP", "target": "PROP_ROUTING", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "TEST_FUZZ", "type": "includes"},
            {"source": "TEST_FUZZ", "target": "FUZZ_UIA", "type": "implements"},
            {"source": "TEST_FUZZ", "target": "FUZZ_MCP", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "TEST_CHAOS", "type": "includes"},
            {"source": "TEST_CHAOS", "target": "CHAOS_SSE", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "TEST_SIM", "type": "includes"},
            {"source": "TEST_SIM", "target": "SIM_RUNTIME", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "TELEMETRY", "type": "includes"},
            {"source": "TELEMETRY", "target": "TEL_LOGGING", "type": "implements"},
            
            {"source": "V7_ROOT", "target": "CI_PIPELINE", "type": "includes"}
        ]
    }
    
    os.makedirs("v7_testing/output", exist_ok=True)
    with open("v7_testing/output/testing_graph.json", "w") as f:
        json.dump(graph_data, f, indent=2)

    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Kairo Phantom v7 Testing Memory Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; background: #0a0a0a; color: #fff; font-family: -apple-system, sans-serif; }
        #graph { width: 100vw; height: 100vh; }
        .node circle { stroke: #fff; stroke-width: 1.5px; }
        .node text { fill: #e0e0e0; font-size: 12px; pointer-events: none; }
        .link { stroke: #333; stroke-opacity: 0.6; }
        .tooltip { position: absolute; background: rgba(0,0,0,0.8); padding: 10px; border: 1px solid #444; border-radius: 4px; pointer-events: none; opacity: 0; transition: opacity 0.2s; }
    </style>
</head>
<body>
    <div id="graph"></div>
    <div id="tooltip" class="tooltip"></div>
    <script>
        const data = GRAPH_DATA_PLACEHOLDER;
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const colorScale = d3.scaleOrdinal()
            .domain(['root', 'layer', 'test', 'feature'])
            .range(['#ff3366', '#33ccff', '#66ff66', '#ffcc00']);
            
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.edges).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
            
        const svg = d3.select("#graph").append("svg")
            .attr("width", width)
            .attr("height", height);
            
        const link = svg.append("g")
            .selectAll("line")
            .data(data.edges)
            .join("line")
            .attr("class", "link");
            
        const node = svg.append("g")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
                
        node.append("circle")
            .attr("r", d => d.type === 'root' ? 12 : (d.type === 'layer' ? 8 : 6))
            .attr("fill", d => colorScale(d.type))
            .on("mouseover", function(event, d) {
                d3.select("#tooltip")
                    .style("opacity", 1)
                    .html(`<strong>${d.label}</strong><br>${d.meta.desc}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", function() {
                d3.select("#tooltip").style("opacity", 0);
            });
            
        node.append("text")
            .attr("dx", 15)
            .attr("dy", 4)
            .text(d => d.label);
            
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
                
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    </script>
</body>
</html>"""
    
    html_content = html_template.replace("GRAPH_DATA_PLACEHOLDER", json.dumps(graph_data))
    with open("v7_testing/output/kairo_testing_graph.html", "w") as f:
        f.write(html_content)
        
    print("Graph generated in v7_testing/output/")

if __name__ == "__main__":
    build_testing_graph()
