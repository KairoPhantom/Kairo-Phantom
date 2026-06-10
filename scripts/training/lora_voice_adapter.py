#!/usr/bin/env python3
"""
scripts/training/lora_voice_adapter.py

Overnight LoRA voice adapter training from user session logs.
Compares accepted/rejected documents in MemMachine to update the voice adapter.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root / "scripts" / "training"))

from personal_finetune import PersonalFinetuner


def main():
    parser = argparse.ArgumentParser(description="Kairo LoRA Voice Adapter overnight trainer.")
    parser.add_argument("--user-id", default="local", help="User ID to train adapter for")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct", help="Base model to apply LoRA on")
    parser.add_argument("--now", action="store_true", help="Run fine-tuning immediately instead of scheduling for overnight")
    
    args = parser.parse_args()
    
    tuner = PersonalFinetuner(base_model=args.base_model)
    
    if args.now:
        print(f"Running overnight SFT training immediately for user: {args.user_id}...")
        try:
            adapter_path = tuner.prepare_lora_adapter(args.base_model, args.user_id)
            print(f"SFT Training complete! Adapter saved at: {adapter_path}")
            
            print("Swapping adapter in Ollama kairo-fast...")
            success = tuner.swap_model_adapter(adapter_path)
            if success:
                print("Model adapter successfully swapped and active in Ollama!")
            else:
                print("Failed to swap adapter in Ollama.")
                sys.exit(1)
        except Exception as e:
            print(f"Fine-tuning failed: {e}")
            sys.exit(1)
    else:
        print(f"Scheduling overnight SFT training for user: {args.user_id} at 2:00 AM.")
        tuner.trigger_overnight_finetune(args.user_id)
        print("Scheduler running in background thread.")


if __name__ == "__main__":
    main()
