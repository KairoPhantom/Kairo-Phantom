// phantom-core/src/swarm/mod.rs
pub mod design;
pub mod reasoning;
pub mod content;
pub mod engineer;
pub mod data;
pub mod image;
pub mod sales;
pub mod medical;
pub mod legal;
use crate::skills::SkillManager;

use crate::document_context::DocumentContext;
use tracing::info;
use std::sync::Arc;
use crate::ai::{build_backend, AiBackend};
use crate::config::SwarmConfig;
use crate::plugin::{SwarmAgent, AgentRegistry};
use crate::persona::{PersonaManager, PersonaAwareContext};
use crate::memory::KairoMemory;
use crate::context7::Context7;

pub use design::DesignAgent;
pub use reasoning::ReasoningAgent;
pub use content::{ContentAgent, StudentTutorAgent};
pub use engineer::EngineerAgent;
pub use data::DataAnalystAgent;
pub use image::ImageAgent;
pub use sales::SalesAgent;
pub use medical::MedicalAgent;
pub use legal::LegalPlusAgent;

#[derive(Debug, Clone, PartialEq)]
pub enum AgentType {
    DesignAndMedia,
    ReasoningAndLogic,
    ContentAndAllRounder,
    StudentTutor,
    Engineer,
    DataAnalyst,
}

pub struct AgentProfile {
    pub agent_type: AgentType,
    pub system_directive: String,
}

pub struct SwarmOrchestrator {
    pub config: SwarmConfig,
    pub registry: AgentRegistry,
    pub brain: Option<Arc<dyn AiBackend>>,
    pub design_backend: Option<Arc<dyn AiBackend>>,
    pub reasoning_backend: Option<Arc<dyn AiBackend>>,
    pub content_backend: Option<Arc<dyn AiBackend>>,
    pub fallback_agent: Arc<dyn AiBackend>,
    pub persona_manager: PersonaManager,
    pub memory: KairoMemory,
    pub context7: Context7,
    pub optimizer: crate::context_optimizer::ContextOptimizer,
    pub skill_manager: SkillManager,
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
        registry.register(Arc::new(StudentTutorAgent));
        registry.register(Arc::new(EngineerAgent));
        registry.register(Arc::new(DataAnalystAgent));
        registry.register(Arc::new(ImageAgent));
        registry.register(Arc::new(SalesAgent));
        registry.register(Arc::new(MedicalAgent));
        registry.register(Arc::new(LegalPlusAgent));

        Self {
            config,
            registry,
            brain,
            design_backend,
            reasoning_backend,
            content_backend,
            fallback_agent,
            persona_manager: PersonaManager::new(),
            memory: KairoMemory::new(),
            context7: Context7::new(),
            optimizer: crate::context_optimizer::ContextOptimizer::new(4096),
            skill_manager: SkillManager::new(),
        }
    }

    pub async fn route(&self, doc_ctx: &DocumentContext, command_mode: &crate::command_protocol::CommandMode) -> (Arc<dyn AiBackend>, AgentProfile) {
        let mut selected_agent: Arc<dyn SwarmAgent> = match self.registry.select_best(doc_ctx) {
            Some(agent) => agent,
            None => {
                info!("⚠️  No agents in registry, using raw fallback backend");
                let profile = AgentProfile {
                    agent_type: AgentType::ContentAndAllRounder,
                    system_directive: format!("{}", crate::ai::KAIRO_SYSTEM_PROMPT),
                };
                return (self.fallback_agent.clone(), profile);
            }
        };
        let mut agent_id = selected_agent.id().to_string();

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

        let agent_score = selected_agent.match_score(doc_ctx);
        info!("🧠 Swarm routed to: {} (score={}) | doc={}", agent_id, agent_score, doc_ctx.doc_kind.human_name());

        let base_directive = selected_agent.build_system_prompt(doc_ctx);
        let app_name = doc_ctx.app_name.clone().unwrap_or_default();
        let memory_fragment = self.optimizer.optimize_memory(&self.memory, &app_name);
        let ground_truth = self.context7.fetch_ground_truth(&doc_ctx.prompt_text).await;
        let ground_truth_fragment = ground_truth.map(|gt| format!("\n\n## GROUND TRUTH (Context7)\n{}", gt)).unwrap_or_default();

        let command_hint = command_mode.system_hint();
        let skill_directive = self.skill_manager.get_skill_directive(command_mode).unwrap_or_default();
        let persona_aware_ctx = PersonaAwareContext::new(doc_ctx.clone(), &self.persona_manager);
        let persona_fragment = persona_aware_ctx.persona.build_prompt_fragment();
        
        let system_directive = format!(
            "<system>\n{}\n\n{}\n\n{}\n\n{}\n\n{}\n\n## COMMAND PROTOCOL\n{}\n\nCRITICAL: Output ONLY within <output> tags. No conversational preamble.\n</system>",
            base_directive,
            persona_fragment,
            memory_fragment,
            ground_truth_fragment,
            skill_directive,
            command_hint
        );

        let agent_type = match agent_id.as_str() {
            "design" => AgentType::DesignAndMedia,
            "reasoning" => AgentType::ReasoningAndLogic,
            "student" => AgentType::StudentTutor,
            "engineer" => AgentType::Engineer,
            "data" => AgentType::DataAnalyst,
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

    pub fn get_backend_and_profile_by_type(&self, agent_type: &AgentType, doc_ctx: &DocumentContext) -> (Arc<dyn AiBackend>, AgentProfile) {
        let agent_id = match agent_type {
            AgentType::DesignAndMedia => "design",
            AgentType::ReasoningAndLogic => "reasoning",
            AgentType::StudentTutor => "student",
            AgentType::Engineer => "engineer",
            AgentType::DataAnalyst => "data",
            AgentType::ContentAndAllRounder => "content",
        };

        let base_directive = self.registry.get_agent(agent_id)
            .map(|a| a.build_system_prompt(doc_ctx))
            .unwrap_or_else(|| crate::ai::KAIRO_SYSTEM_PROMPT.to_string());

        let system_directive = format!("<system>\n{}\n\nCRITICAL: Output ONLY within <output> tags. No conversational preamble.\n</system>", base_directive);

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

pub struct TestFallbackBackend;
#[async_trait::async_trait]
impl AiBackend for TestFallbackBackend {
    async fn complete(&self, _system: &str, _prompt: &str) -> anyhow::Result<String> { Ok("test response".to_string()) }
    async fn stream_complete(&self, _system: &str, _prompt: &str, _tx: tokio::sync::mpsc::Sender<String>) -> anyhow::Result<()> { Ok(()) }
}

impl SwarmOrchestrator {
    pub fn new_for_test() -> Self {
        let fallback: Arc<dyn AiBackend> = Arc::new(TestFallbackBackend);
        Self::new(SwarmConfig::default(), fallback)
    }

    pub fn select_agent(&mut self, doc_ctx: &DocumentContext) -> String {
        self.registry.select_best(doc_ctx).map(|a| a.id().to_string()).unwrap_or_else(|| "content".to_string())
    }
}
