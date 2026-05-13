use crate::agent_registry::AgentRegistry;
use crate::AgentManifest;

pub struct AgentRouter;

impl AgentRouter {
    pub fn route(
        registry: &AgentRegistry,
        prompt: &str,
        app_context: &str,
        historical_acceptance: f32, // Passed from Memory Vault (VaultV2)
    ) -> Option<AgentManifest> {
        let agents = registry.get_agents();
        let prompt_lower = prompt.to_lowercase();
        let mut best_score = 0.0;
        let mut best_agent = None;

        for (_, manifest) in agents {
            let mut score = 0.0;

            // 1. Keyword matching
            for keyword in &manifest.triggers.keywords {
                if prompt_lower.contains(&keyword.to_lowercase()) {
                    score += 0.4;
                }
            }

            // 2. App context match
            for ctx in &manifest.triggers.app_contexts {
                if app_context.contains(ctx) {
                    score += 0.3;
                }
            }

            // 3. Boost
            score += manifest.triggers.confidence_boost;

            // 4. Historical acceptance rate
            score += historical_acceptance * 0.3;

            if score > best_score {
                best_score = score;
                best_agent = Some(manifest);
            }
        }

        best_agent
    }
}
