#!/usr/bin/env python3
"""
scripts/generate_dataset_supplement.py — Supplemental dataset generator to reach 3,500 examples
"""

import os
import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INPUT_FILE = REPO_ROOT / "training_data" / "kairo_docops_2k.jsonl"
OUTPUT_FILE = REPO_ROOT / "training_data" / "kairo_docops_3500.jsonl"

def generate_excel_supplement(count):
    examples = []
    topics = ["Total Revenue", "Average Cost", "Sales Tax", "Net Profit", "Growth Rate", "Max Value", "Count Entries"]
    formulas = ["=SUM(A1:A10)", "=AVERAGE(B1:B20)", "=C1*0.08", "=D1-E1", "=(F2-F1)/F1", "=MAX(G1:G100)", "=COUNT(H1:H50)"]
    for i in range(count):
        idx = random.randint(0, len(topics) - 1)
        topic = topics[idx]
        formula = formulas[idx]
        cell = f"{random.choice(['A','B','C','D','E','F'])}{random.randint(1, 100)}"
        instruction = f"Calculate the {topic.lower()} in cell {cell} using an Excel formula."
        
        input_data = {
            "document_context": {
                "active_sheet": "Sheet1",
                "cell_range": f"{cell}:{cell}"
            },
            "mem_context": "User prefers uppercase formula names."
        }
        output_data = {
            "operations": [{
                "type": "write_cell",
                "cell": cell,
                "value": formula
            }],
            "confidence": 0.95,
            "reasoning": f"Calculated {topic.lower()} with standard formula."
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_slide_supplement(count):
    examples = []
    titles = ["Project Timeline", "Market Overview", "Q3 Performance", "Risk Factors", "Next Steps"]
    for i in range(count):
        title = random.choice(titles)
        slide_idx = random.randint(0, 10)
        instruction = f"Create a slide titled '{title}' with bullet points summarizing key achievements."
        input_data = {
            "document_context": {
                "slide_count": slide_idx + 1,
                "current_slide_index": slide_idx
            },
            "mem_context": "User prefers concise slide points."
        }
        output_data = {
            "operations": [
                {
                    "type": "insert_slide",
                    "index": slide_idx + 1,
                    "layout": "Title and Content"
                },
                {
                    "type": "set_slide_title",
                    "index": slide_idx + 1,
                    "title": title
                },
                {
                    "type": "set_slide_bullets",
                    "index": slide_idx + 1,
                    "bullets": ["Completed phase 1 on time", "Exceeded Q3 goals by 15%", "Identified cost saving options"]
                }
            ],
            "confidence": 0.9,
            "reasoning": "Added new slide and populated standard title/bullets structure."
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_code_supplement(count):
    examples = []
    funcs = ["calculate_primes", "parse_json_file", "connect_to_database", "validate_email_address", "sort_array_descending"]
    languages = ["Python", "Rust", "JavaScript", "Go", "C++"]
    for i in range(count):
        func = random.choice(funcs)
        lang = random.choice(languages)
        instruction = f"Add a comprehensive docstring to the {lang} function '{func}' explaining inputs and return types."
        input_data = {
            "document_context": {
                "language": lang,
                "code_snippet": f"def {func}(data):\n    pass"
            },
            "mem_context": "User prefers Google-style docstrings."
        }
        output_data = {
            "operations": [{
                "type": "insert_docstring",
                "function_name": func,
                "docstring": f'"""\nBrief description of {func}.\n\nArgs:\n    data: The input data.\n\nReturns:\n    The processed result.\n"""'
            }],
            "confidence": 0.92,
            "reasoning": "Generated Google-style docstring explaining parameters."
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_negative_supplement(count):
    examples = []
    queries = [
        "What is the capital of France?",
        "Tell me a programming joke.",
        "How do I cook pasta?",
        "Explain quantum computing in simple terms.",
        "Why is the sky blue?",
        "How far is the moon from Earth?",
        "Recommend a good sci-fi movie."
    ]
    for i in range(count):
        query = random.choice(queries)
        instruction = f"Answer this general query: {query}"
        input_data = {
            "document_context": {},
            "mem_context": ""
        }
        output_data = {
            "operations": [],
            "confidence": 1.0,
            "reasoning": "This is a general query that does not require any document editing operations. Returning empty operations."
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_routing_supplement(count):
    examples = []
    tiers = ["kairo-fast", "kairo-standard", "kairo-think", "kairo-cloud"]
    for i in range(count):
        tier = random.choice(tiers)
        instruction = f"Route this prompt to the correct model tier: Force routing to {tier}."
        input_data = {
            "document_context": {},
            "mem_context": f"Force model tier to {tier}."
        }
        output_data = {
            "operations": [],
            "confidence": 1.0,
            "reasoning": f"Routed to {tier} per force directive."
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def main():
    print("Reading base dataset...")
    if not INPUT_FILE.exists():
        print(f"Base dataset {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f]

    print(f"Loaded {len(dataset)} base examples.")

    # Generate supplement to reach 3,500 total
    # Breakdown of new additions to reach 3,500 (need 1,500 more):
    # - Excel: 300
    # - Slide: 200
    # - Code: 400
    # - Negative: 400
    # - Routing: 200
    # Total supplement: 1500
    excel_supp = generate_excel_supplement(300)
    slide_supp = generate_slide_supplement(200)
    code_supp = generate_code_supplement(400)
    negative_supp = generate_negative_supplement(400)
    routing_supp = generate_routing_supplement(200)

    dataset.extend(excel_supp)
    dataset.extend(slide_supp)
    dataset.extend(code_supp)
    dataset.extend(negative_supp)
    dataset.extend(routing_supp)

    print(f"Total dataset size after supplement: {len(dataset)} examples.")
    random.shuffle(dataset)

    # Make sure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")

    print(f"Successfully generated {len(dataset)} examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
