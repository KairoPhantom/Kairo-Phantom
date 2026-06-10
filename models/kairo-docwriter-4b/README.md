# KairoDocWriter-4B Model

This directory contains the Ollama Modelfile for the fine-tuned `kairo-docwriter-4b` model.

## Model Overview

`kairo-docwriter-4b` is a QLoRA fine-tuned Qwen3-4B model trained on 3,500 document operation examples to produce valid JSON schema output for Kairo Phantom's document operations.

**Key specs:**
- Base model: `unsloth/Qwen3-4B`
- Fine-tuned on: 3,500 DocxOperation / ExcelOperation / SlideOperation examples
- Target schema failure rate: <3% (down from ~25% with qwen2.5:7b)
- Quantization: Q4_K_M (GGUF)
- Context: 2048 tokens
- Temperature: 0.1 (deterministic JSON output)

## Training

```bash
# Generate training data
python scripts/generate_dataset.py --output models/kairo-docwriter-4b/training_data.jsonl

# Run QLoRA fine-tuning (requires CUDA GPU)
python scripts/training/personal_finetune.py

# Evaluate schema compliance (should be >=95%)
python scripts/eval_schema_compliance.py --model kairo-standard
```

## Installation

After training, register with Ollama:

```bash
cd models/kairo-docwriter-4b
ollama create kairo-docwriter-4b -f Modelfile
```

Then verify:
```bash
ollama run kairo-docwriter-4b "Insert a paragraph about Q3 results"
# Should output: {"operations": [...], "reasoning": "...", "confidence": 0.9}
```

## Fallback

Until `kairo-docwriter-4b` is fine-tuned, `kairo-fast` routes to `qwen2.5:7b` as a fallback (see `litellm_config.yaml`).
