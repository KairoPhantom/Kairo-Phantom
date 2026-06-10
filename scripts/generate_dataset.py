#!/usr/bin/env python3
"""
Kairo DocOps Dataset Generator (Sprint 7)
=========================================
Synthesizes a 3,500-line high-fidelity training dataset (kairo_docops_3500.jsonl)
matching the precise JSON output schemas of Kairo's specialist agents.
"""
import os
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "training_data"
OUTPUT_FILE_3500 = OUTPUT_DIR / "kairo_docops_3500.jsonl"
OUTPUT_FILE_2000 = OUTPUT_DIR / "kairo_docops_2k.jsonl"

def generate_docx_headings(count=200):
    examples = []
    topics = ["Project Plan", "Executive Summary", "Q4 Financials", "Marketing Plan", "Technical Specs", "Security Audit", "API Docs", "Release Notes", "HR Policy", "Legal Contract"]
    levels = [1, 2, 3]
    
    for i in range(count):
        topic = random.choice(topics)
        level = random.choice(levels)
        style = f"Heading{level}"
        index = random.randint(0, 10)
        
        instruction = f"Insert a {style.lower()} heading about {topic} at paragraph index {index}."
        input_data = {
            "document_context": {
                "paragraph_count": index + 5,
                "headings": [{"index": 0, "level": 1, "text": "Overview"}]
            },
            "mem_context": "User prefers structured outline levels."
        }
        
        output_data = {
            "operations": [
                {
                    "type": "insert_paragraph",
                    "after_paragraph_index": index,
                    "style": style,
                    "runs": [{"text": f"{topic} Overview", "bold": True, "italic": False}]
                }
            ],
            "confidence": round(random.uniform(0.85, 0.98), 2),
            "reasoning": f"Adding structural {style} layout node."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_docx_bullets(count=200):
    examples = []
    bullet_items = [
        ["Increase customer acquisition by 12%", "Lower standard server latencies", "Refactor core database indexes"],
        ["Streamline marketing budget operations", "Establish clear KPIs", "Align cross-functional leads"],
        ["Implement SOC2 security compliance rules", "Setup automated scanning pipelines", "Sign corporate audit log entries"],
        ["Deploy Model2Vec local embeddings", "Integrate air-gapped Named Pipes", "Test 50 E2E integration scenarios"]
    ]
    
    for i in range(count):
        items = random.choice(bullet_items)
        index = random.randint(1, 15)
        
        instruction = f"Add a bullet list with {len(items)} items at index {index} showing key goals."
        input_data = {
            "document_context": {"paragraph_count": index + 2},
            "mem_context": "User prefers concise list styles."
        }
        
        operations = []
        for idx, item in enumerate(items):
            operations.append({
                "type": "insert_paragraph",
                "after_paragraph_index": index + idx,
                "style": "ListBullet",
                "runs": [{"text": item, "bold": False, "italic": False}]
            })
            
        output_data = {
            "operations": operations,
            "confidence": round(random.uniform(0.8, 0.95), 2),
            "reasoning": "Inserting standard formatting ListBullet sequence."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_docx_rewrites(count=200):
    examples = []
    originals = [
        "This project has a lot of problems and we are running extremely late with our deliverables.",
        "The software runs slow because our database index structure is not good.",
        "We need to fix our security issues before the auditor comes next week."
    ]
    rewrites = [
        "The project is currently experiencing operational delays; mitigation strategies are underway to align with major roadmap deliverables.",
        "System latency is bound to sub-optimal index structures; optimization of SQLite indexing keys is in progress.",
        "Proactive remediation of outstanding security controls is scheduled ahead of the upcoming compliance audit."
    ]
    
    for i in range(count):
        idx = random.randint(0, len(originals)-1)
        orig = originals[idx]
        rew = rewrites[idx]
        p_index = random.randint(0, 10)
        
        instruction = f"Rewrite paragraph {p_index} to sound more professional and corporate."
        input_data = {
            "document_context": {
                "paragraphs": [{"index": p_index, "text": orig, "style": "Normal"}]
            },
            "mem_context": "User prefers formal, executive corporate terminology."
        }
        
        output_data = {
            "operations": [
                {
                    "type": "replace_paragraph",
                    "paragraph_index": p_index,
                    "style": "Normal",
                    "runs": [{"text": rew, "bold": False, "italic": False}]
                }
            ],
            "confidence": round(random.uniform(0.9, 0.99), 2),
            "reasoning": "Elevating paragraph vocabulary to executive register."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_docx_tables(count=100):
    examples = []
    
    for i in range(count):
        cols = random.randint(2, 4)
        rows_num = random.randint(3, 5)
        index = random.randint(1, 10)
        
        instruction = f"Insert a {cols}x{rows_num} matrix table showing key metric trends."
        input_data = {
            "document_context": {"paragraph_count": index + 2},
            "mem_context": "User prefers clean structured table formatting."
        }
        
        headers = [f"Col{c}" for c in range(cols)]
        rows = [[f"Val{r}_{c}" for c in range(cols)] for r in range(rows_num)]
        
        output_data = {
            "operations": [
                {
                    "type": "insert_table",
                    "after_paragraph_index": index,
                    "headers": headers,
                    "rows": rows
                }
            ],
            "confidence": round(random.uniform(0.85, 0.95), 2),
            "reasoning": "Deploying standard data comparison table."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_xlsx_formulas(count=200):
    examples = []
    formulas = [
        ("SUM(B2:B10)", "Calculate total quantities in column B"),
        ("AVERAGE(C2:C20)", "Find the average pricing of items in range C2 to C20"),
        ("VLOOKUP(E2, A2:C50, 3, FALSE)", "Fetch product price matching search key in cell E2"),
        ("IF(B2>100, 'Bulk', 'Standard')", "Apply discount label to cell depending on B2 volume")
    ]
    
    for i in range(count):
        f_val, desc = random.choice(formulas)
        target = f"{random.choice(['D','E','F'])}{random.randint(2,10)}"
        
        instruction = f"Write an Excel formula to: {desc} in target cell {target}."
        input_data = {
            "document_context": {"active_cell": target, "sheet_name": "Sales"},
            "mem_context": "User prefers uppercase formulas."
        }
        
        output_data = {
            "operations": [
                {
                    "cell": target,
                    "formula": f"={f_val}",
                    "value": ""
                }
            ],
            "confidence": round(random.uniform(0.9, 0.98), 2),
            "reasoning": f"Generating precise logical formula for cell {target}."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_xlsx_explanations(count=200):
    examples = []
    formulas = [
        ("=SUMIF(B2:B20, '>100', C2:C20)", "Calculates the sum of cells in range C2:C20 where the corresponding cell in B2:B20 exceeds 100."),
        ("=INDEX(A2:A10, MATCH(D2, B2:B10, 0))", "Finds the row index matching cell D2 in range B2:B10, then returns the corresponding value from range A2:A10."),
        ("=COUNTIF(D2:D50, 'Pending')", "Counts the number of cells in the range D2:D50 that match the string 'Pending'.")
    ]
    
    for i in range(count):
        f_val, exp = random.choice(formulas)
        cell = f"E{random.randint(2,10)}"
        
        instruction = f"Explain the complex Excel formula in cell {cell}."
        input_data = {
            "document_context": {"active_cell": cell, "grid": [[{"ref": cell, "value": "", "formula": f_val}]]},
            "mem_context": "User requests simple explanations."
        }
        
        output_data = {
            "explanation": exp,
            "confidence": round(random.uniform(0.9, 0.98), 2),
            "reasoning": "Decomposing nested formula logically."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_excel_supplement(count=200):
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

def generate_pptx_concision(count=200):
    examples = []
    paragraphs = [
        ("Our main roadmap goal for Q4 is to successfully implement the comprehensive Named Pipe local IPC architecture to boost performance and reduce latency to under 2ms.",
         ["Implement local Named Pipe IPC", "Reduce slide latency < 2ms"]),
        ("We should aggressively cut corporate costs across server infrastructure to save 40% annually.",
         ["Cut server costs 40% annually", "Optimize cloud resource usage"])
    ]
    
    for i in range(count):
        para, bullets = random.choice(paragraphs)
        slide = random.randint(0, 5)
        
        instruction = f"Reduce this long paragraph into slides bullet list on slide {slide} (strict <= 5 words constraint)."
        input_data = {
            "document_context": {"active_slide": slide},
            "mem_context": "Strict <= 5 words per bullet rule is active."
        }
        
        output_data = {
            "operations": [
                {
                    "slide_index": slide,
                    "bullets": bullets
                }
            ],
            "confidence": round(random.uniform(0.88, 0.96), 2),
            "reasoning": "Applying concision rules to match slides layout parameters."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_pptx_titles(count=200):
    examples = []
    titles = [
        ("A Detailed Analysis of the Q4 Infrastructure Cost Reductions", "Q4 Cost Analysis"),
        ("Overview of Kairo Phantom Local Memory Architecture Implementation Details", "Kairo Memory Architecture")
    ]
    
    for i in range(count):
        long_t, short_t = random.choice(titles)
        slide = random.randint(0, 5)
        
        instruction = f"Make this verbose title punchy for slide {slide}."
        input_data = {
            "document_context": {"active_slide": slide, "current_title": long_t},
            "mem_context": "Prefers succinct slide titles."
        }
        
        output_data = {
            "operations": [
                {
                    "slide_index": slide,
                    "bullets": [short_t]  # Update title mapped via bullets structure in slide mock
                }
            ],
            "confidence": round(random.uniform(0.9, 0.98), 2),
            "reasoning": "Updating verbose slide title."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_slide_supplement(count=100):
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

def generate_code_docstrings(count=200):
    examples = []
    methods = [
        ("def calculate_similarity(v1, v2):", "Python", '"""Calculates the cosine similarity between two 256-dim vectors."""'),
        ("fn get_db_connection() -> Result<Connection>", "Rust", "/// Establishes a connection to the local SQLite database.")
    ]
    
    for i in range(count):
        signature, lang, doc = random.choice(methods)
        
        instruction = f"Generate a high-quality, clear {lang} docstring for the method signature: {signature}."
        input_data = {
            "document_context": {"language": lang.lower(), "code_signature": signature},
            "mem_context": "Follows standard language doc specifications."
        }
        
        output_data = {
            "docstring": doc,
            "confidence": round(random.uniform(0.9, 0.99), 2),
            "reasoning": f"Adding idiomatic {lang} commentary node."
        }
        
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def generate_code_supplement(count=300):
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

def generate_negative_examples(count=500):
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

def generate_routing_examples(count=200):
    examples = []
    prompts = [
        ("Fix this Python syntax error", "vscode", "code", "debug", "simple"),
        ("Write a professional cover letter for a software engineer", "word", "word", "insert", "simple"),
        ("Explain this Excel formula", "excel", "excel", "explain", "simple"),
        ("Create a slide titled Project Timeline", "powerpoint", "slides", "insert", "simple"),
        ("Draft a reply email apologizing for the delay", "outlook", "email", "reply", "simple"),
        ("Optimize this SQL query for faster join execution", "vscode", "code", "optimize", "complex"),
        ("Refactor this long React component into subcomponents", "vscode", "code", "refactor", "complex"),
        ("Review this legal agreement for liability limits", "word", "word", "review", "complex")
    ]
    for i in range(count):
        prompt, app, domain, task_type, complexity = random.choice(prompts)
        instruction = f"Route this prompt to the correct model tier: {prompt}"
        input_data = {
            "prompt": prompt,
            "app": app,
            "document_context": {},
            "mem_context": ""
        }
        output_data = {
            "domain": domain,
            "task_type": task_type,
            "complexity": complexity,
            "confidence": round(random.uniform(0.9, 0.99), 2)
        }
        examples.append({
            "instruction": instruction,
            "input": json.dumps(input_data),
            "output": json.dumps(output_data)
        })
    return examples

def main():
    print("Synthesizing Kairo DocOps 3,500-line ML fine-tuning dataset...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    dataset = []
    dataset.extend(generate_docx_headings(300))
    dataset.extend(generate_docx_bullets(300))
    dataset.extend(generate_docx_rewrites(300))
    dataset.extend(generate_docx_tables(300))
    
    dataset.extend(generate_xlsx_formulas(200))
    dataset.extend(generate_xlsx_explanations(200))
    dataset.extend(generate_excel_supplement(200))
    
    dataset.extend(generate_pptx_concision(200))
    dataset.extend(generate_pptx_titles(200))
    dataset.extend(generate_slide_supplement(100))
    
    dataset.extend(generate_code_docstrings(200))
    dataset.extend(generate_code_supplement(300))
    
    dataset.extend(generate_negative_examples(500))
    dataset.extend(generate_routing_examples(200))
    
    random.shuffle(dataset)
    
    # Assert length is exactly 3,500 examples
    assert len(dataset) == 3500, f"Expected exactly 3500 examples, got {len(dataset)}"
    
    with open(OUTPUT_FILE_3500, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Successfully compiled 3,500 diverse, schema-compliant examples into:\n   -> {OUTPUT_FILE_3500}")
    
    # Write first 2000 shuffled examples to kairo_docops_2k.jsonl for backward compatibility
    with open(OUTPUT_FILE_2000, "w", encoding="utf-8") as f:
        for entry in dataset[:2000]:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Successfully compiled 2,000 subset examples into:\n   -> {OUTPUT_FILE_2000}")

if __name__ == "__main__":
    main()
