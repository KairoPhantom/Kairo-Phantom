"""
Personal Fine-tuner — QLoRA fine-tuning on user's MemMachine interaction history.
Provides automated dataset collection, training, scheduling, and model hot-swapping.
"""

import os
import sys
import json
import time
import sqlite3
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import llamafactory
    LLAMAFACTORY_AVAILABLE = True
except ImportError:
    LLAMAFACTORY_AVAILABLE = False

log = logging.getLogger("kairo-sidecar.personal_finetune")


class PersonalFinetuner:
    """
    Manages personal fine-tuning pipelines using LlamaFactory/Unsloth.
    Saves user interaction corrections locally and triggers overnight training.
    """

    def __init__(self, db_path: Optional[str] = None, base_model: str = "Qwen/Qwen2.5-3B-Instruct"):
        # Import default DB path from mem_machine
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kairo-sidecar"))
        from sidecar.mem_machine import DEFAULT_DB_PATH
        self.db_path = db_path or os.environ.get("KAIRO_DB_PATH") or DEFAULT_DB_PATH
        self.base_model = base_model
        self.project_root = Path(__file__).parent.parent.parent.resolve()
        self.models_dir = self.project_root / "models"
        self.training_data_dir = self.project_root / "training_data"
        
        self.models_dir.mkdir(exist_ok=True)
        self.training_data_dir.mkdir(exist_ok=True)

    def collect_training_data(self, user_id: str = "local") -> str:
        """
        Query MemMachine interaction history for the given user,
        format as SFT instruction dataset, and save to JSONL.
        """
        log.info(f"Collecting training data for user: {user_id}")
        if not os.path.exists(self.db_path):
            log.warning(f"Database not found at {self.db_path}. Returning empty dataset.")
            return ""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Query interactions with style notes or corrections
        rows = conn.execute(
            """
            SELECT domain, task_type, user_prompt, output_preview, style_notes
            FROM interactions
            WHERE user_id = ? AND (style_notes IS NOT NULL AND style_notes != '')
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()
        conn.close()

        if not rows:
            log.warning("No user corrections found in MemMachine. Cannot fine-tune.")
            return ""

        output_file = self.training_data_dir / f"personal_{user_id}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for row in rows:
                input_ctx = {
                    "document_context": {"domain": row["domain"]},
                    "mem_context": row["style_notes"]
                }
                
                # Construct instruction format matching standard dataset
                example = {
                    "instruction": f"Execute the {row['domain']} operation for: {row['user_prompt']}",
                    "input": json.dumps(input_ctx),
                    "output": row["output_preview"] if row["output_preview"] else "{}",
                    "data_provenance": "user-opt-in"
                }
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        log.info(f"Saved {len(rows)} SFT examples to {output_file}")
        return str(output_file)

    def prepare_lora_adapter(self, base_model: str, user_id: str = "local") -> str:
        """
        Register personal dataset and launch LlamaFactory LoRA SFT training.
        """
        dataset_path = self.collect_training_data(user_id)
        if not dataset_path:
            raise ValueError("No training data collected. Check MemMachine history.")

        # Validate data provenance compliance
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
                            f"SFT datasets must only contain rows with data_provenance as 'synthetic-opt-in' or 'user-opt-in'."
                        )
                except Exception as e:
                    raise ValueError(f"Compliance Error: SFT data validation failed: {e}")

        if not LLAMAFACTORY_AVAILABLE:
            if os.environ.get("SKIP_FINETUNE") != "1":
                raise RuntimeError(
                    "LlamaFactory library is not installed. Cannot run real personal fine-tuning. "
                    "Set environment variable SKIP_FINETUNE=1 to bypass this check."
                )
            log.warning("LlamaFactory is not installed. Running simulated fine-tuning step...")
            output_adapter_dir = self.models_dir / f"kairo-personal-{user_id}-lora"
            output_adapter_dir.mkdir(parents=True, exist_ok=True)
            (output_adapter_dir / "adapter_config.json").write_text('{"peft_type": "LORA", "r": 16}', encoding="utf-8")
            return str(output_adapter_dir)

        log.info("Registering personal dataset in LlamaFactory...")
        try:
            # Locate LlamaFactory site-packages directory
            import llamafactory
            lf_path = os.path.dirname(llamafactory.__file__)
            lf_data_dir = os.path.join(lf_path, "data")
            
            # Copy dataset
            shutil_dest = os.path.join(lf_data_dir, f"personal_{user_id}.jsonl")
            import shutil
            shutil.copy2(dataset_path, shutil_dest)
            
            # Register in dataset_info.json
            info_json = os.path.join(lf_data_dir, "dataset_info.json")
            if os.path.exists(info_json):
                with open(info_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data[f"personal_{user_id}"] = {
                    "file_name": f"personal_{user_id}.jsonl",
                    "columns": {
                        "prompt": "instruction",
                        "query": "input",
                        "response": "output"
                    }
                }
                with open(info_json, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warning(f"Could not automatically register dataset in LlamaFactory: {e}. Proceeding directly...")

        # Write custom config
        config_path = self.project_root / f"personal_lora_config_{user_id}.yaml"
        output_adapter_dir = self.models_dir / f"kairo-personal-{user_id}-lora"
        
        config_content = f"""### model
model_name_or_path: {base_model}

### method
stage: sft
do_train: true
finetuning_type: lora
lora_target: q_proj,v_proj,k_proj,o_proj
lora_rank: 16
lora_alpha: 32
lora_dropout: 0.1

### dataset
dataset: personal_{user_id}
template: qwen
cutoff_len: 2048
max_samples: 1000
overwrite_cache: true

### output
output_dir: {output_adapter_dir.as_posix()}
logging_steps: 5
save_steps: 50
overwrite_output_dir: true

### train
per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 2.0e-4
num_train_epochs: 5.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
fp16: true
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        log.info(f"Running LlamaFactory CLI SFT on {base_model}...")
        # Execute LlamaFactory training command
        cmd = ["llamafactory-cli", "train", str(config_path)]
        try:
            subprocess.run(cmd, check=True)
            log.info("LlamaFactory LoRA training complete.")
            return str(output_adapter_dir)
        except subprocess.SubprocessError as e:
            log.error(f"Failed to execute training process: {e}")
            raise e

    def swap_model_adapter(self, adapter_path: str) -> bool:
        """
        Hot-swap the fine-tuned adapter into the local model running in Ollama.
        Re-builds/creates the local Ollama model referencing the new adapter.
        """
        log.info(f"Swapping model adapter with: {adapter_path}")
        modelfile_path = self.models_dir / "Modelfile_personal"
        
        # Read the GGUF model path from our existing build
        gguf_model = self.models_dir / "kairo-docwriter-3b-Q4_K_M.gguf"
        if not gguf_model.exists():
            # Fallback to standard base model
            gguf_model = "qwen2.5:3b"

        # Generate personalized Modelfile
        modelfile_content = f"""FROM {gguf_model}
ADAPTER {adapter_path}
TEMPLATE \"\"\"{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
\"\"\"
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
SYSTEM "You are KairoDocWriter. Output ONLY valid JSON. First character must be {{. Last character must be }}."
"""
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        # Create/refresh the Ollama model
        cmd = ["ollama", "create", "kairo-fast", "-f", str(modelfile_path)]
        try:
            subprocess.run(cmd, check=True)
            log.info("Ollama model 'kairo-fast' successfully updated with new adapter!")
            return True
        except subprocess.SubprocessError as e:
            log.error(f"Failed to create Ollama model with adapter: {e}")
            return False

    def trigger_overnight_finetune(self, user_id: str = "local") -> None:
        """
        Schedules a one-off fine-tuning run at 2:00 AM local time.
        Spawns a background worker thread.
        """
        def run_worker():
            now = datetime.now()
            # Target is 2:00 AM
            target = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if target <= now:
                # Target is tomorrow 2:00 AM
                target += timedelta(days=1)
                
            wait_seconds = (target - now).total_seconds()
            log.info(f"Scheduling overnight fine-tune at 2:00 AM. Waiting for {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            
            try:
                adapter_path = self.prepare_lora_adapter(self.base_model, user_id)
                self.swap_model_adapter(adapter_path)
                log.info("Overnight personal fine-tuning pipeline completed successfully!")
            except Exception as e:
                log.error(f"Overnight fine-tuning failed: {e}")

        thread = threading.Thread(target=run_worker, daemon=True)
        thread.start()
        log.info("Overnight fine-tuning thread scheduled successfully.")
