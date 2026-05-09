use crate::document_context::DocumentContext;
use tracing::info;


#[derive(Debug, Clone, PartialEq)]
pub enum AgentType {
    /// Expert in images, PPT slides, layouts, Canva, Figma
    DesignAndMedia,
    /// Expert in logic, coding, terminal, complex structuring
    ReasoningAndLogic,
    /// Expert in formatting, prose, Word, Notion
    ContentAndAllRounder,
}

use crate::plugin::{SwarmAgent, AgentRegistry};

pub struct DesignAgent;
impl SwarmAgent for DesignAgent {
    fn id(&self) -> &str { "design" }
    fn name(&self) -> &str { "Design & Media Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: DESIGN & MEDIA AGENT ***\nSuggest layouts, slide structures, and visual elements. Use [IMAGE: prompt] for visuals. Keep copy punchy.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        use crate::document_context::DocKind;
        match doc_ctx.doc_kind {
            DocKind::PowerPoint | DocKind::OpenDocumentPresentation | DocKind::CanvaDesign | DocKind::FigmaDesign => 100,
            _ => 0,
        }
    }
}

pub struct ReasoningAgent;
impl SwarmAgent for ReasoningAgent {
    fn id(&self) -> &str { "reasoning" }
    fn name(&self) -> &str { "Reasoning & Logic Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: REASONING & LOGIC AGENT ***\nBe precise. Output valid code or terminal commands. No fluff.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        use crate::document_context::DocKind;
        if matches!(doc_ctx.doc_kind, DocKind::CodeFile | DocKind::Terminal) { return 100; }
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("code") || p.contains("calculate") || p.contains("debug") { 80 } else { 0 }
    }
}

pub struct ContentAgent;
impl SwarmAgent for ContentAgent {
    fn id(&self) -> &str { "content" }
    fn name(&self) -> &str { "Content & All-Rounder Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: CONTENT AGENT ***\nPerfect formatting. Rich structure. Professional tone.", base, doc_fragment)
    }
    fn match_score(&self, _doc_ctx: &DocumentContext) -> u8 { 10 } // Default fallback score
}

pub struct AgentProfile {
    pub agent_type: AgentType,
    pub system_directive: String,
}


use crate::ai::{build_backend, AiBackend};
use crate::config::SwarmConfig;
use std::sync::Arc;


pub struct SwarmOrchestrator {
    pub config: SwarmConfig,
    pub registry: AgentRegistry,
    pub brain: Option<Arc<dyn AiBackend>>,
    pub design_backend: Option<Arc<dyn AiBackend>>,
    pub reasoning_backend: Option<Arc<dyn AiBackend>>,
    pub content_backend: Option<Arc<dyn AiBackend>>,
    pub fallback_agent: Arc<dyn AiBackend>,
}


impl SwarmOrchestrator {
    pub fn new(config: SwarmConfig, fallback_agent: Arc<dyn AiBackend>) -> Self {
        let brain = config.brain.as_ref().and_then(|c| build_backend(c).ok());
        let design_backend = config.design_agent.as_ref().and_then(|c| build_backend(c).ok());
        let reasoning_backend = config.reasoning_agent.as_ref().and_then(|c| build_backend(c).ok());
        let content_backend = config.content_agent.as_ref().and_then(|c| build_backend(c).ok());

        let mut registry = AgentRegistry::new();
        registry.register(Arc::new(DesignAgent));
        registry.register(Arc::new(ReasoningAgent));
        registry.register(Arc::new(ContentAgent));

        Self {
            config,
            registry,
            brain,
            design_backend,
            reasoning_backend,
            content_backend,
            fallback_agent,
        }
    }


    /// The Brain: Analyzes context via LLM (or deterministic fallback) to select the right agent.
    pub async fn route(&self, doc_ctx: &DocumentContext) -> (Arc<dyn AiBackend>, AgentProfile) {
        let mut selected_agent = self.registry.select_best(doc_ctx).unwrap();
        let mut agent_id = selected_agent.id().to_string();

        // If the multi-agent brain is enabled and configured, ask the Brain LLM to decide
        if self.config.enabled && self.brain.is_some() {
            if let Some(brain_llm) = &self.brain {
                let brain_prompt = format!(
                    "You are the Swarm Brain. The user typed: '{}'. Document type: '{}'. \
                    Decide the best specialized agent. Reply ONLY with the agent ID: {}.",
                    doc_ctx.prompt_text,
                    doc_ctx.doc_kind.human_name(),
                    self.registry.list_agents().iter().map(|a| a.id()).collect::<Vec<_>>().join(", ")
                );
                
                info!("🧠 Brain is thinking...");
                if let Ok(decision) = brain_llm.complete("You are a router. Reply with exactly one ID.", &brain_prompt).await {
                    let d = decision.trim().to_lowercase();
                    if let Some(agent) = self.registry.get_agent(&d) {
                        selected_agent = agent;
                        agent_id = d;
                    }
                }
            }
        }

        info!("🧠 Swarm routed to: {} | doc={}", agent_id, doc_ctx.doc_kind.human_name());

        let system_directive = selected_agent.build_system_prompt(doc_ctx);
        let agent_type = match agent_id.as_str() {
            "design" => AgentType::DesignAndMedia,
            "reasoning" => AgentType::ReasoningAndLogic,
            _ => AgentType::ContentAndAllRounder,
        };

        let profile = AgentProfile {
            agent_type,
            system_directive,
        };

        let backend = match agent_id.as_str() {
            "design" => self.design_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            "reasoning" => self.reasoning_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            _ => self.content_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
        };

        (backend, profile)
    }

    /// Exposes a direct backend and profile getter for the MCP /agent override
    pub fn get_backend_and_profile_by_type(&self, agent_type: &AgentType, doc_ctx: &DocumentContext) -> (Arc<dyn AiBackend>, AgentProfile) {
        let agent_id = match agent_type {
            AgentType::DesignAndMedia => "design",
            AgentType::ReasoningAndLogic => "reasoning",
            AgentType::ContentAndAllRounder => "content",
        };

        let agent = self.registry.get_agent(agent_id).unwrap();
        let system_directive = agent.build_system_prompt(doc_ctx);

        let profile = AgentProfile {
            agent_type: agent_type.clone(),
            system_directive,
        };

        let backend = match agent_id {
            "design" => self.design_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            "reasoning" => self.reasoning_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            _ => self.content_backend.clone().unwrap_or_else(|| self.fallback_agent.clone()),
        };

        (backend, profile)
    }
}
