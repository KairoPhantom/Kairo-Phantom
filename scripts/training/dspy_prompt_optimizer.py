"""
Waza Agent Prompt Optimizer — Offline prompt optimization using DSPy.
Evaluates candidates using the cargo-based KMB-1 Memory Benchmark (`cargo test --test kmb1_benchmark`).
"""

import os
import sys
import json
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("dspy_prompt_optimizer")

# Try importing DSPy
try:
    import dspy
    _DSPY_AVAILABLE = True
except ImportError:
    log.warning("DSPy package is not available. Using simulated prompt optimization fallback.")
    _DSPY_AVAILABLE = False


def run_kmb1_benchmark() -> float:
    """
    Executes the Rust integration test suite (kmb1_benchmark) and parses the KMB-1 memory recall score.
    """
    log.info("Running kmb1_benchmark integration tests...")
    try:
        project_root = Path(__file__).parent.parent.parent.resolve()
        res = subprocess.run(
            ["cargo", "test", "--test", "kmb1_benchmark", "--", "--nocapture"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False
        )
        output = res.stdout + res.stderr
        
        # Look for kmb1_score in the JSON leaderboard printed by the benchmark
        match = re.search(r'"kmb1_score":\s*([0-9.]+)', output)
        if match:
            score = float(match.group(1))
            log.info(f"Parsed KMB-1 Score from leaderboard: {score:.4f}")
            return score
            
        # Fallback to KMB-1 Score text pattern
        score_match = re.search(r'KMB-1 Score:\s*([0-9.]+)', output)
        if score_match:
            score = float(score_match.group(1))
            log.info(f"Parsed KMB-1 Score from stdout: {score:.4f}")
            return score
            
        if "✅ PASS" in output:
            log.info("Benchmark PASSED (estimated score: 1.0)")
            return 1.0
            
    except Exception as e:
        log.error(f"Failed to execute kmb1_benchmark: {e}")
    
    log.warning("Could not parse kmb1_benchmark score. Returning default 0.0")
    return 0.0


class DspyPromptOptimizer:
    """
    Offline Waza Agent prompt optimizer.
    Uses DSPy to optimize prompt instructions against kmb1_benchmark.
    """
    def __init__(self, skill_id: str = "feynman-verifier"):
        self.project_root = Path(__file__).parent.parent.parent.resolve()
        self.skill_id = skill_id
        self.skill_dir = self.project_root / "skills" / skill_id
        self.skill_md_path = self.skill_dir / "SKILL.md"

    def load_current_prompt(self) -> str:
        """Loads the prompt from the target SKILL.md file."""
        if not self.skill_md_path.exists():
            log.warning(f"SKILL.md not found for {self.skill_id}. Returning default.")
            return "Default system prompt contents."
        return self.skill_md_path.read_text(encoding="utf-8")

    def save_optimized_prompt(self, optimized_content: str):
        """Saves the optimized prompt back to the target SKILL.md file."""
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        self.skill_md_path.write_text(optimized_content, encoding="utf-8")
        log.info(f"Successfully saved optimized prompt to {self.skill_md_path}")

    def run_optimization(self) -> str:
        """
        Runs the prompt optimization loop.
        Uses DSPy if available, otherwise runs a simulated optimization heuristics pass.
        """
        current_prompt = self.load_current_prompt()
        initial_score = run_kmb1_benchmark()
        log.info(f"Initial kmb1_benchmark baseline score: {initial_score:.4f}")

        if _DSPY_AVAILABLE:
            # 1. Setup local Ollama or fallback NIM client in DSPy
            lm = dspy.LM('ollama/qwen2.5-coder:14b', api_base='http://localhost:11434')
            dspy.settings.configure(lm=lm)

            # 2. Define the DSPy Signature
            class PromptOptimizerSignature(dspy.Signature):
                """Optimize Waza agent system prompts to maximize MemMachine KMB-1 recall quality."""
                task_description = dspy.InputCol(desc="Target task descriptor or benchmark objective")
                current_prompt = dspy.InputCol(desc="Current system prompt / instructions to optimize")
                score_metric = dspy.InputCol(desc="KMB-1 memory score from the test run")
                optimized_prompt = dspy.OutputCol(desc="Optimized system prompt contents maximizing KMB-1 recall")

            # 3. Define the DSPy Module/Program
            class PromptOptimizerModule(dspy.Module):
                def __init__(self):
                    super().__init__()
                    self.optimizer = dspy.Predict(PromptOptimizerSignature)

                def forward(self, task_description, current_prompt, score_metric):
                    return self.optimizer(
                        task_description=task_description,
                        current_prompt=current_prompt,
                        score_metric=str(score_metric)
                    )

            # 4. Run DSPy Predict / Optimizer
            log.info("Executing DSPy optimizer program...")
            program = PromptOptimizerModule()
            result = program(
                task_description="Enhance the system prompt instructions to guarantee that users' format, tone, and length preferences are recalled precisely.",
                current_prompt=current_prompt,
                score_metric=initial_score
            )
            optimized_prompt = result.optimized_prompt
        else:
            # Simulated Optimization Fallback: Add precise instruction heuristics to the prompt
            log.info("Running simulated prompt optimization pass...")
            # We append high-impact prompt directives to guide the LLM to respect preferences
            heuristics = (
                "\n\n## OPTIMIZATION DIRECTIVES (DSPy / KMB-1 Precision):\n"
                "- Pay extreme attention to the format preferences (such as lists vs. paragraphs).\n"
                "- Pay extreme attention to tone preferences (such as strictly formal vs. casual).\n"
                "- Respect length bounds and concise preferences (limit descriptions to requested word count/length)."
            )
            
            if "OPTIMIZATION DIRECTIVES" not in current_prompt:
                optimized_prompt = current_prompt + heuristics
            else:
                optimized_prompt = current_prompt

        # Evaluate the optimized candidate
        self.save_optimized_prompt(optimized_prompt)
        final_score = run_kmb1_benchmark()
        log.info(f"Final optimized kmb1_benchmark score: {final_score:.4f}")
        
        if final_score < initial_score:
            log.warning("Optimized prompt scored lower. Reverting to original baseline prompt.")
            self.save_optimized_prompt(current_prompt)
            return current_prompt

        log.info("Optimization successful.")
        return optimized_prompt


if __name__ == "__main__":
    optimizer = DspyPromptOptimizer()
    optimizer.run_optimization()
