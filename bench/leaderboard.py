"""
Kairo Phantom — HTML Leaderboard Generator (SPEC §S8, §S9)
"""
from __future__ import annotations

import json
import pathlib
import sys


def main():
    report_file = pathlib.Path("bench/REPORT.json")
    if not report_file.exists():
        print(f"Error: {report_file} does not exist. Run bench.harness first.", file=sys.stderr)
        sys.exit(1)

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp", "N/A")
    packs = data.get("packs", {})

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kairo Phantom — Grounding Leaderboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(20, 26, 46, 0.45);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --gradient-1: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            --glow-color: rgba(139, 92, 246, 0.2);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%);
        }}

        header {{
            text-align: center;
            margin-bottom: 3rem;
            max-width: 800px;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 3rem;
            font-weight: 800;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 300;
            margin-bottom: 1rem;
        }}

        .meta {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.03);
            padding: 0.4rem 1rem;
            border-radius: 50px;
            border: 1px solid var(--card-border);
            display: inline-block;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
            width: 100%;
            max-width: 1200px;
            margin-bottom: 3rem;
        }}

        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid var(--card-border);
            padding: 2rem;
            position: relative;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s;
            overflow: hidden;
        }}

        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px var(--glow-color);
            border-color: rgba(139, 92, 246, 0.3);
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--gradient-1);
        }}

        .card-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
            text-transform: capitalize;
            margin-bottom: 1.5rem;
        }}

        .metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .metric-label {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}

        .metric-value {{
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            font-size: 1.2rem;
        }}

        .val-green {{ color: var(--accent-green); }}
        .val-blue {{ color: var(--accent-blue); }}
        .val-purple {{ color: var(--accent-purple); }}

        .accuracy-section {{
            margin-top: 1.5rem;
        }}

        .accuracy-title {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.8rem;
        }}

        .accuracy-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            font-size: 0.85rem;
        }}

        .acc-item {{
            background: rgba(255, 255, 255, 0.02);
            padding: 0.5rem;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            border: 1px solid rgba(255, 255, 255, 0.02);
        }}

        .acc-name {{
            color: var(--text-secondary);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 90px;
        }}

        .acc-val {{
            font-weight: 600;
        }}

        footer {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: auto;
            text-align: center;
            border-top: 1px solid var(--card-border);
            padding-top: 1.5rem;
            width: 100%;
            max-width: 1200px;
        }}
    </style>
</head>
<body>
    <header>
        <h1>KAIRO PHANTOM</h1>
        <p class="subtitle">Public Grounding Benchmark Leaderboard — FACTUM Citation Audit</p>
        <div class="meta">Generated: {timestamp} (SYNTHETIC / self-graded — unvalidated)</div>
    </header>

    <div class="grid">
    """

    for pack_name, metrics in packs.items():
        html_content += f"""
        <div class="card">
            <div class="card-title">{pack_name} pack</div>
            <div class="metric-row">
                <span class="metric-label">Grounded-Answer Rate</span>
                <span class="metric-value val-green">{metrics['grounded_answer_rate']}%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Citation-Hallucination Rate</span>
                <span class="metric-value val-blue">{metrics['citation_hallucination_rate']}%</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Refusal-Correctness</span>
                <span class="metric-value val-purple">{metrics['refusal_correctness']}%</span>
            </div>

            <div class="accuracy-section">
                <div class="accuracy-title">Per-Field Accuracy</div>
                <div class="accuracy-grid">
        """

        for field, acc in sorted(metrics.get("per_field_accuracy", {}).items()):
            html_content += f"""
                    <div class="acc-item">
                        <span class="acc-name" title="{field}">{field}</span>
                        <span class="acc-val">{(acc * 100.0):.1f}%</span>
                    </div>
            """

        html_content += """
                </div>
            </div>
        </div>
        """

    html_content += """
    </div>

    <footer>
        <p>© 2026 Kairo Phantom. All benchmark results are local-first, reproducible, and verifiable.</p>
    </footer>
</body>
</html>
"""

    output_path = pathlib.Path("bench/leaderboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML leaderboard written to {output_path}")


if __name__ == "__main__":
    main()
