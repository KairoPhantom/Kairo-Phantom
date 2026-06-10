"""
Wrapper to expose DspyPromptOptimizer from scripts.training.dspy_prompt_optimizer.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from scripts.training.dspy_prompt_optimizer import DspyPromptOptimizer

if __name__ == "__main__":
    optimizer = DspyPromptOptimizer()
    optimizer.run_optimization()
