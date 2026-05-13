use std::fs;
use std::process::Command;

pub struct FactsVerifier;

impl FactsVerifier {
    pub fn verify_all() -> Result<bool, String> {
        let facts_path = if std::path::Path::new("../Kairo.facts").exists() {
            "../Kairo.facts"
        } else {
            "Kairo.facts"
        };
        let content = fs::read_to_string(facts_path).map_err(|e| format!("Failed to read {}: {}", facts_path, e))?;
        
        let mut implemented = 0;
        let mut specs = 0;
        let mut drafts = 0;
        let mut passed = 0;
        let mut failed = 0;
        
        let mut current_fact_type = "";
        
        for line in content.lines() {
            let line = line.trim();
            if line.starts_with("@implemented:") {
                implemented += 1;
                current_fact_type = "implemented";
            } else if line.starts_with("@spec:") {
                specs += 1;
                current_fact_type = "spec";
            } else if line.starts_with("@draft:") {
                drafts += 1;
                current_fact_type = "draft";
            } else if line.starts_with("command:") {
                if current_fact_type == "implemented" {
                    let cmd_str = line.trim_start_matches("command:").trim();
                    let parts: Vec<&str> = cmd_str.split_whitespace().collect();
                    if !parts.is_empty() {
                        let mut cmd = Command::new(parts[0]);
                        cmd.args(&parts[1..]);
                        match cmd.status() {
                            Ok(status) if status.success() => passed += 1,
                            _ => failed += 1,
                        }
                    }
                }
            }
        }
        
        let total_valid = implemented + specs + drafts;
        let readiness = if total_valid > 0 { (implemented as f64 / total_valid as f64) * 100.0 } else { 0.0 };
        
        println!("Kairo Phantom v4.0: {}/{} facts implemented, {} specs in progress, {} drafts. Production readiness: {:.1}%.",
            implemented, total_valid, specs, drafts, readiness);
            
        if failed > 0 {
            println!("Verification FAILED: {} commands failed.", failed);
            Ok(false)
        } else {
            println!("Verification PASSED.");
            Ok(true)
        }
    }
}
