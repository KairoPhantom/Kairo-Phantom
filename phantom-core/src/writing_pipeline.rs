use crate::quality_gate::{SentinelHashDetector, MultiReviewerPipeline, IntegrityGateChecklist};
use tracing::{info, warn};

use futures::Future;

pub struct WritingPipeline;

impl WritingPipeline {
    pub async fn execute<F, Fut>(
        system_prompt: &str,
        context: &str,
        user_prompt: &str,
        generate_fn: F
    ) -> Result<String, String> 
    where 
        F: Fn(String) -> Fut,
        Fut: Future<Output = String>
    {
        let mut retries = 0;
        let mut final_output = String::new();
        let sentinel = SentinelHashDetector::new();
        
        // Stage 1: Plan
        info!("Pipeline Stage 1: Plan - Analyzing context and generating outline");
        let plan_prompt = format!(
            "CONTEXT:\n{}\n\nTASK: Create a detailed 5-point execution plan for: {}\n\nOutput only the plan.",
            system_prompt, user_prompt
        );
        let plan = generate_fn(plan_prompt).await;
        info!("Plan: {}", plan);

        while retries < 3 {
            // Stage 2: Write
            info!("Pipeline Stage 2: Write - Attempt {}", retries + 1);
            let full_prompt = crate::quality_gate::anti_leakage_format(system_prompt, context, user_prompt, sentinel.get_hash());
            let mut raw_output = generate_fn(full_prompt).await;
            
            // Extract from <output> tags
            if let Some(start) = raw_output.find("<output>") {
                if let Some(end) = raw_output.find("</output>") {
                    if start < end {
                        raw_output = raw_output[start + 8..end].to_string();
                    }
                }
            } else if !raw_output.contains("<output>") {
                 warn!("No <output> tags found in LLM response. Searching for raw text...");
                 // Fallback to raw text if no tags but response seems okay
            }
            
            // Stage 3: Review
            info!("Pipeline Stage 3: Review - Scanning for leakage and quality");
            if let Err(e) = sentinel.scan_output(&raw_output) {
                warn!("Sentinel leak detected: {}. Retrying...", e);
                retries += 1;
                continue;
            }

            if let Err(e) = IntegrityGateChecklist::check(&raw_output, context) {
                warn!("Integrity check failed: {}. Retrying...", e);
                retries += 1;
                continue;
            }

            if let Err(e) = MultiReviewerPipeline::review(&raw_output) {
                // Stage 4: Revise
                info!("Pipeline Stage 4: Revise - Applying revision guidance for: {}", e);
                let revision_prompt = format!("Original: {}\nIssue: {}\nPlease revise to fix the issue.", raw_output, e);
                raw_output = generate_fn(revision_prompt).await;
                
                // Re-check after revision
                if MultiReviewerPipeline::review(&raw_output).is_err() {
                    warn!("Revision still failed review. Retrying from Write stage...");
                    retries += 1;
                    continue;
                }
            }
            
            // Stage 5: Finalize
            info!("Pipeline Stage 5: Finalize - Preparing for injection");
            final_output = raw_output;
            break;
        }
        
        if final_output.is_empty() {
            Err("Pipeline failed after 3 retries.".to_string())
        } else {
            Ok(final_output)
        }
    }
}
