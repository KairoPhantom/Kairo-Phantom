use crate::quality_gate::{SentinelHashDetector, IntegrityGateChecklist};
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
        let sentinel = SentinelHashDetector::new();
        
        // Stage 1: Plan — use ONLY the user prompt + document context, NOT the full system_prompt
        // (system_prompt contains internal directives and security markers that confuse the model)
        info!("Pipeline Stage 1: Plan - Analyzing context and generating outline");
        let plan_prompt = if context.len() > 50 {
            format!(
                "Document context (first 500 chars):\n{}\n\nTask: {}",
                &context[..context.len().min(500)],
                user_prompt
            )
        } else {
            format!("Task: {}", user_prompt)
        };
        let plan = generate_fn(plan_prompt).await;
        info!("Plan: {}", if plan.len() > 100 { &plan[..100] } else { &plan });

        while retries < 3 {
            // Stage 2: Write — build a clean prompt combining plan + user request
            info!("Pipeline Stage 2: Write - Attempt {}", retries + 1);
            
            // Build a clean user-facing prompt without exposing internal system_prompt
            let full_prompt = if plan.is_empty() || plan.len() < 10 {
                // Plan generation failed, just use the user prompt directly
                format!(
                    "Document context:\n{}\n\nRequest: {}\n\nProvide a complete, well-written response. Do not add meta-commentary.",
                    &context[..context.len().min(800)],
                    user_prompt
                )
            } else {
                format!(
                    "Plan:\n{}\n\nDocument context:\n{}\n\nRequest: {}\n\nNow write the complete response based on the plan above.",
                    &plan[..plan.len().min(400)],
                    &context[..context.len().min(500)],
                    user_prompt
                )
            };
            
            let raw_output = generate_fn(full_prompt).await;
            
            // Extract from <output> tags if present (optional — model may or may not include them)
            let clean_output = if let (Some(start), Some(end)) = (raw_output.find("<output>"), raw_output.find("</output>")) {
                if start < end {
                    raw_output[start + 8..end].trim().to_string()
                } else {
                    raw_output.trim().to_string()
                }
            } else {
                // No <output> tags — use the raw response directly (normal for most LLMs)
                raw_output.trim().to_string()
            };
            
            if clean_output.is_empty() {
                warn!("Pipeline Stage 2: Empty response from LLM. Retrying...");
                retries += 1;
                continue;
            }
            
            // Stage 3: Sentinel leak check only (removed overly aggressive style checks)
            info!("Pipeline Stage 3: Review - Checking for leakage");
            if let Err(e) = sentinel.scan_output(&clean_output) {
                warn!("Sentinel leak detected: {}. Retrying...", e);
                retries += 1;
                continue;
            }

            // Light integrity check — only block obvious problems
            if let Err(e) = IntegrityGateChecklist::check(&clean_output, context) {
                warn!("Integrity check: {}. Retrying...", e);
                retries += 1;
                continue;
            }

            info!("Pipeline Stage 4: Finalize - {} chars ready for injection", clean_output.len());
            return Ok(clean_output);
        }
        
        Err("Pipeline failed after 3 retries.".to_string())
    }
}
