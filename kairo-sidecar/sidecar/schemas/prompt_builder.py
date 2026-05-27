import json
from typing import Dict

def build_docx_prompt(user_instruction: str, document_context: dict, mem_context: str) -> str:
    """
    Builds a highly structured system + user prompt for document editing.
    Instructs the LLM to output a JSON object conforming exactly to the DocxResponse schema.
    """
    
    # DocxResponse Pydantic representation for LLM awareness
    schema_description = """
{
  "operations": [
    # A list of operations of the following types:
    
    # 1. Insert Paragraph:
    # {
    #   "type": "insert_paragraph",
    #   "after_paragraph_index": int,    # The index of the paragraph to insert AFTER. Use -1 to append to end of document.
    #   "style": "Normal" | "Heading1" | "Heading2" | "Heading3" | "Heading4" | "Heading5" | "Heading6" | "ListBullet" | "ListNumber" | "Quote",
    #   "runs": [
    #     {
    #       "text": str,
    #       "bold": bool,
    #       "italic": bool
    #     }
    #   ]
    # }
    
    # 2. Replace Paragraph:
    # {
    #   "type": "replace_paragraph",
    #   "paragraph_index": int,
    #   "style": "Normal" | "Heading1" | "Heading2" | "Heading3" | "Heading4" | "Heading5" | "Heading6" | "ListBullet" | "ListNumber" | "Quote",
    #   "runs": [
    #     {
    #       "text": str,
    #       "bold": bool,
    #       "italic": bool
    #     }
    #   ]
    # }
    
    # 3. Insert Table:
    # {
    #   "type": "insert_table",
    #   "after_paragraph_index": int,
    #   "headers": [str],
    #   "rows": [[str]]
    # }
    
    # 4. Delete Paragraph:
    # {
    #   "type": "delete_paragraph",
    #   "paragraph_index": int
    # }
  ],
  "confidence": float,  # Float between 0.0 and 1.0 representing confidence in change matching user intent
  "reasoning": str      # Max 200 characters explanation of chosen operations (not visible to user)
}
"""

    few_shot_1_input = {
        "instruction": "Write a short summary paragraph at the end of the document",
        "document_context": {
            "paragraphs": [
                {"index": 0, "text": "Kairo Phantom Project Plan", "style": "Heading1"},
                {"index": 1, "text": "This project aims to automate office document generation using locally hosted LLMs and native sidecars.", "style": "Normal"}
            ]
        }
    }
    
    few_shot_1_output = {
        "operations": [
            {
                "type": "insert_paragraph",
                "after_paragraph_index": 1,
                "style": "Normal",
                "runs": [
                    {"text": "Summary: Kairo Phantom delivers sub-2ms local vector search and 100% offline-first secure document manipulation.", "bold": True, "italic": False}
                ]
            }
        ],
        "confidence": 0.95,
        "reasoning": "Inserted summary paragraph at the end of the document as requested."
    }

    few_shot_2_input = {
        "instruction": "Update the title of the document to Kairo Phantom Production Design",
        "document_context": {
            "paragraphs": [
                {"index": 0, "text": "Old Kairo Document Title", "style": "Heading1"},
                {"index": 1, "text": "Intro text.", "style": "Normal"}
            ]
        }
    }
    
    few_shot_2_output = {
        "operations": [
            {
                "type": "replace_paragraph",
                "paragraph_index": 0,
                "style": "Heading1",
                "runs": [
                    {"text": "Kairo Phantom Production Design", "bold": False, "italic": False}
                ]
            }
        ],
        "confidence": 0.98,
        "reasoning": "Replaced the document title with the requested title while keeping the Heading1 style."
    }

    system_prompt = f"""You are a professional, specialized Document AI system operating on a local user workstation.
Your task is to take a user instruction, current document context, and optional user preference memory, and generate a sequence of structured document operations to perfectly fulfill the request.

You MUST respond with a single valid JSON object matching the schema below.
DO NOT include any markdown formatting blocks (like ```json), no preamble text, and no explanations outside of the JSON structure itself.

JSON Response Schema to conform to:
{schema_description}

---
FEW-SHOT EXAMPLES FOR CLARITY:

Example 1 Input:
Instruction: {few_shot_1_input['instruction']}
Document Context: {json.dumps(few_shot_1_input['document_context'])}

Example 1 Output:
{json.dumps(few_shot_1_output, indent=2)}

Example 2 Input:
Instruction: {few_shot_2_input['instruction']}
Document Context: {json.dumps(few_shot_2_input['document_context'])}

Example 2 Output:
{json.dumps(few_shot_2_output, indent=2)}
"""

    user_prompt = f"""User Instruction: {user_instruction}

Document Context:
{json.dumps(document_context, indent=2)}

User Preference Memory (MemMachine context):
{mem_context or "No specific style preferences stored."}

Generate the JSON response conforming to the DocxResponse schema. Remember: ONLY the raw JSON output is allowed. No markdown fences.
"""

    return f"{system_prompt}\n\n{user_prompt}"
