#!/usr/bin/env python3
"""
scripts/training/finetune_docwriter.py

Unsloth LoRA fine-tuning SFT pipeline stub for KairoDocWriter-4B.

This script implements the neural-inspired fine-tuning task formulation:
  "Write a [n]-word [document type] about [content] emulating the style of [Persona]"
using Unsloth for fast parameter-efficient fine-tuning on consumer GPUs.
"""

import os
import sys
from pathlib import Path

# Try to import Unsloth
try:
    from unsloth import FastLanguageModel
    import torch
    from trl import SFTTrainer
    from transformers import TrainingArguments
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False


def run_sft_pipeline(
    dataset_path: str,
    base_model_name: str = "unsloth/Qwen2.5-Coder-7B-Instruct",
    output_dir: str = "./models/kairo-docwriter-4b-lora",
    max_steps: int = 100,
) -> bool:
    """Runs the SFT training pipeline on the dataset."""
    print(f"Loading SFT dataset from: {dataset_path}")
    
    if not Path(dataset_path).exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return False

    # Enforce data provenance safety gate
    import json
    with open(dataset_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                provenance = item.get("data_provenance")
                if provenance not in ["synthetic-opt-in", "user-opt-in"]:
                    raise ValueError(
                        f"Compliance Error: Row {idx} in SFT dataset has invalid data_provenance: {provenance}. "
                        f"Kairo SFT pipeline requires either 'synthetic-opt-in' or 'user-opt-in' provenance."
                    )
            except Exception as e:
                raise ValueError(f"Compliance Error: SFT data validation failed: {e}")
        
    if not UNSLOTH_AVAILABLE:
        if os.environ.get("SKIP_FINETUNE") != "1":
            raise RuntimeError(
                "Unsloth library is not installed. Cannot run real fine-tuning pipeline. "
                "Set environment variable SKIP_FINETUNE=1 to bypass this check."
            )
        print("Unsloth is not installed. Running simulated fine-tuning SFT pipeline pass...")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        # Write dummy adapter info
        (Path(output_dir) / "adapter_config.json").write_text('{"peft_type": "LORA", "r": 16}', encoding="utf-8")
        print("Simulated fine-tuning complete. Saved adapter stub.")
        return True

    print(f"Initializing base model: {base_model_name}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model_name,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    # Apply PEFT (LoRA)
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0, # optimized
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # Load SFT dataset
    from datasets import load_dataset
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    def format_prompts(examples):
        texts = []
        for inst, inp, out in zip(examples["instruction"], examples["input"], examples["output"]):
            # Format according to template
            text = f"<|im_start|>system\nYou are KairoDocWriter.<|im_end|>\n<|im_start|>user\n{inst}\nContext: {inp}<|im_end|>\n<|im_start|>assistant\n{out}<|im_end|>"
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(format_prompts, batched=True)

    # Trainer configuration
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            max_steps=max_steps,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=output_dir,
        ),
    )

    print("Starting fine-tuning...")
    trainer.train()
    print(f"Training complete. Saving adapter to {output_dir}")
    model.save_pretrained_lora(output_dir)
    tokenizer.save_pretrained(output_dir)
    return True


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.resolve()
    default_dataset = project_root / "training_data" / "kairo_writing_dataset_5k.jsonl"
    run_sft_pipeline(str(default_dataset))
