// phantom-core/src/waza_sdk.rs
// Waza Agent SDK - Public Interface for Community Extensions
// Allows loading third-party agents like "Tax Advisor Agent" or "Medical Scribe Agent".

use async_trait::async_trait;
use std::collections::HashMap;

/// Public interface for developing a Waza-compliant agent.
#[async_trait]
pub trait WazaAgent: Send + Sync {
    /// Unique identifier for this agent (e.g., "tax_advisor", "medical_scribe").
    fn id(&self) -> &str;

    /// Human-readable name (e.g., "Tax Advisor Agent").
    fn name(&self) -> &str;

    /// The base system prompt that defines the agent's persona and rules.
    fn system_prompt(&self) -> &str;

    /// Process the context and user prompt, potentially returning a modified prompt or injected context.
    async fn preprocess(&self, context: &str, prompt: &str) -> Result<String, String>;

    /// Hook to process the LLM output before it is injected via Ghost Write.
    async fn postprocess(&self, output: &str) -> Result<String, String>;
}

/// Registry to hold both internal and dynamically loaded external Waza Agents.
pub struct WazaAgentRegistry {
    agents: HashMap<String, Box<dyn WazaAgent>>,
}

impl Default for WazaAgentRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl WazaAgentRegistry {
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    /// Register a new external agent.
    pub fn register(&mut self, agent: Box<dyn WazaAgent>) {
        self.agents.insert(agent.id().to_string(), agent);
    }

    /// Retrieve an agent by ID.
    pub fn get_agent(&self, id: &str) -> Option<&dyn WazaAgent> {
        self.agents.get(id).map(|a| a.as_ref())
    }

    /// List all registered agents.
    pub fn list_agents(&self) -> Vec<&str> {
        self.agents.keys().map(|k| k.as_str()).collect()
    }
}
