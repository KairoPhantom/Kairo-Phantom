use rand::Rng;

pub struct SentinelHashDetector {
    current_hash: String,
}

impl Default for SentinelHashDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl SentinelHashDetector {
    pub fn new() -> Self {
        let hash: String = rand::thread_rng()
            .sample_iter(&rand::distributions::Alphanumeric)
            .take(32)
            .map(char::from)
            .collect();
        Self { current_hash: hash }
    }

    pub fn get_hash(&self) -> &str {
        &self.current_hash
    }

    pub fn scan_output(&self, output: &str) -> Result<(), String> {
        if output.contains(&self.current_hash) {
            return Err("Sentinel hash leak detected in output".to_string());
        }
        if output.to_lowercase().contains("swarm role") || output.to_lowercase().contains("swarm brain") {
            return Err("System prompt role leak detected in output".to_string());
        }
        Ok(())
    }
}

pub struct IntegrityGateChecklist;
impl IntegrityGateChecklist {
    pub fn check(output: &str, context: &str) -> Result<(), String> {
        let lower_output = output.to_lowercase();
        let lower_context = context.to_lowercase();

        // 1. Implementation bugs (plausible but wrong)
        if lower_output.contains("[placeholder]") || lower_output.contains("insert text here") || lower_output.contains("todo:") {
            return Err("Integrity check failed: Placeholder or TODO text detected.".to_string());
        }

        // 2. Hallucinated results (not grounded in context)
        if lower_output.contains("my knowledge cutoff") || lower_output.contains("as of my last update") {
            return Err("Integrity check failed: AI model metadata leakage.".to_string());
        }

        // 3. Shortcut reliance
        if output.len() < 15 && !context.is_empty() && output.chars().filter(|c| c.is_alphanumeric()).count() < 10 {
             return Err("Integrity check failed: Response too short, likely a shortcut.".to_string());
        }

        // 4. Citation hallucinations
        if (lower_output.contains("http://") || lower_output.contains("https://"))
            && !lower_context.contains("http") && !lower_output.contains("google.com") && !lower_output.contains("github.com") {
                return Err("Integrity check failed: Potentially hallucinated URL.".to_string());
            }

        // 5. Bug-as-insight reframing (Detecting "clever" ways to hide failure)
        let red_flags = ["this is intentional", "by design, this is missing", "left as an exercise"];
        for flag in red_flags {
            if lower_output.contains(flag) && !lower_context.contains(flag) {
                return Err(format!("Integrity check failed: Detected potential bug-as-insight reframing ('{}').", flag));
            }
        }

        // 6. Methodology fabrication
        let methods = ["using our proprietary algorithm", "according to the kairo standard", "following internal protocols"];
        for m in methods {
            if lower_output.contains(m) && !lower_context.contains(m) {
                return Err(format!("Integrity check failed: Detected methodology fabrication ('{}').", m));
            }
        }

        // 7. Frame-lock (LLM stuck in a specific mental frame)
        if lower_output.contains("as an ai assistant") || lower_output.contains("i am a language model") {
             return Err("Integrity check failed: Frame-lock detected (AI persona leakage).".to_string());
        }

        Ok(())
    }
}

pub struct MultiReviewerPipeline;
impl MultiReviewerPipeline {
    pub fn review(output: &str) -> Result<(), String> {
        let lower_output = output.to_lowercase();

        // Devil's Advocate: Look for contradictions or excessive hedging
        if (output.contains("however") && output.contains("but") && output.len() < 100) || lower_output.contains("it is possible that") {
            return Err("Devil's Advocate rejected: Possible internal contradiction or excessive hedging.".to_string());
        }

        // Style Reviewer: Check for "stiff" or "AI-like" phrasing
        let stiff_phrases = [
            "it is important to note", "delve into", "tapestry of", "in conclusion", "to summarize", 
            "not only but also", "furthermore", "moreover", "in summary", "essentially", "crucially"
        ];
        for phrase in stiff_phrases {
            if lower_output.contains(phrase) {
                return Err(format!("Style Reviewer rejected: Detected overused AI phrasing ('{}').", phrase));
            }
        }

        // Check for informalities as requested in kairo-intel.md
        let informal = ["gotta", "cuz", "theyre", "lol", "alright", "wanna", "gonna"];
        for word in informal {
            if lower_output.contains(word) {
                return Err(format!("Style Reviewer rejected: Informal language or slang detected ('{}').", word));
            }
        }

        // Check for "Assistant" persona
        if lower_output.contains("how can i help") || lower_output.contains("happy to assist") {
            return Err("Style Reviewer rejected: Assistant persona detected.".to_string());
        }

        Ok(())
    }
}

pub fn anti_leakage_format(system: &str, context: &str, user_prompt: &str, sentinel: &str) -> String {
    format!(
        "<system>\n{}\nSentinel: {}\n</system>\n<document_context>\n{}\n</document_context>\n<user_prompt>\n{}\n</user_prompt>\nOutput your response between <output> and </output> tags.",
        system, sentinel, context, user_prompt
    )
}
