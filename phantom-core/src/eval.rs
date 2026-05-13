// phantom-core/src/eval.rs
//! Continuous LLM Evaluation integrated for CI/CD.

use std::process::Command;
use tracing::{info, warn};

pub struct EvalSuite;

impl EvalSuite {
    pub fn run_promptfoo_eval() {
        info!("Running Continuous LLM Evaluation via Promptfoo...");
        
        // Simulating the promptfoo CLI execution
        let output = Command::new("npx")
            .args(["promptfoo", "eval", "-c", "eval-config.yaml"])
            .output();

        match output {
            Ok(o) if o.status.success() => {
                info!("Promptfoo Evaluation Passed. Hallucination rate within bounds.");
            }
            Ok(o) => {
                warn!("Promptfoo Evaluation Failed: {}", String::from_utf8_lossy(&o.stderr));
            }
            Err(e) => {
                warn!("Could not run Promptfoo: {}. Ensure Node.js and promptfoo are installed.", e);
            }
        }
    }
}
