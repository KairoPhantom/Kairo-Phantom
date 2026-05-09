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

pub struct AgentProfile {
    pub agent_type: AgentType,
    pub system_directive: String,
}

use crate::ai::{build_backend, AiBackend};
use crate::config::SwarmConfig;
use anyhow::Result;
use std::sync::Arc;

pub struct SwarmOrchestrator {
    pub config: SwarmConfig,
    pub brain: Option<Arc<dyn AiBackend>>,
    pub design_agent: Option<Arc<dyn AiBackend>>,
    pub reasoning_agent: Option<Arc<dyn AiBackend>>,
    pub content_agent: Option<Arc<dyn AiBackend>>,
    pub fallback_agent: Arc<dyn AiBackend>,
}

impl SwarmOrchestrator {
    pub fn new(config: SwarmConfig, fallback_agent: Arc<dyn AiBackend>) -> Self {
        let brain = config.brain.as_ref().and_then(|c| build_backend(c).ok());
        let design_agent = config.design_agent.as_ref().and_then(|c| build_backend(c).ok());
        let reasoning_agent = config.reasoning_agent.as_ref().and_then(|c| build_backend(c).ok());
        let content_agent = config.content_agent.as_ref().and_then(|c| build_backend(c).ok());

        Self {
            config,
            brain,
            design_agent,
            reasoning_agent,
            content_agent,
            fallback_agent,
        }
    }

    /// The Brain: Analyzes context via LLM (or deterministic fallback) to select the right agent.
    pub async fn route(&self, doc_ctx: &DocumentContext) -> (Arc<dyn AiBackend>, AgentProfile) {
        let mut agent_type = self.deterministic_route(doc_ctx);

        // If the multi-agent brain is enabled and configured, ask the Brain LLM to decide
        if self.config.enabled && self.brain.is_some() {
            if let Some(brain_llm) = &self.brain {
                let brain_prompt = format!(
                    "You are the Swarm Brain. The user typed: '{}'. Document type: '{}'. Environment: '{}'. \
                    Decide the best specialized agent. Reply ONLY with one word: 'design', 'reasoning', or 'content'.",
                    doc_ctx.prompt_text,
                    doc_ctx.doc_kind.human_name(),
                    doc_ctx.file_path.as_ref()
                        .and_then(|p| p.file_name())
                        .and_then(|n| n.to_str())
                        .unwrap_or("unknown")
                );
                
                info!("🧠 Brain is thinking...");
                if let Ok(decision) = brain_llm.complete("You are a router. Reply with exactly one word.", &brain_prompt).await {
                    let d = decision.to_lowercase();
                    if d.contains("design") {
                        agent_type = AgentType::DesignAndMedia;
                    } else if d.contains("reasoning") {
                        agent_type = AgentType::ReasoningAndLogic;
                    } else if d.contains("content") {
                        agent_type = AgentType::ContentAndAllRounder;
                    }
                }
            }
        }

        info!("🧠 Swarm routed to: {:?} | doc={}", agent_type, doc_ctx.doc_kind.human_name());

        let system_directive = Self::build_agent_prompt(&agent_type, doc_ctx);
        let profile = AgentProfile {
            agent_type: agent_type.clone(),
            system_directive,
        };

        let backend = match agent_type {
            AgentType::DesignAndMedia => self.design_agent.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            AgentType::ReasoningAndLogic => self.reasoning_agent.clone().unwrap_or_else(|| self.fallback_agent.clone()),
            AgentType::ContentAndAllRounder => self.content_agent.clone().unwrap_or_else(|| self.fallback_agent.clone()),
        };

        (backend, profile)
    }

    fn deterministic_route(&self, doc_ctx: &DocumentContext) -> AgentType {
        use crate::document_context::DocKind;
        match &doc_ctx.doc_kind {
            DocKind::PowerPoint | DocKind::OpenDocumentPresentation
            | DocKind::CanvaDesign | DocKind::FigmaDesign => AgentType::DesignAndMedia,
            DocKind::CodeFile => AgentType::ReasoningAndLogic,
            DocKind::Terminal => AgentType::ReasoningAndLogic,
            _ => {
                let p = doc_ctx.prompt_text.to_lowercase();
                if p.contains("code") || p.contains("calculate") || p.contains("debug") {
                    AgentType::ReasoningAndLogic
                } else {
                    AgentType::ContentAndAllRounder
                }
            }
        }
    }

    fn build_agent_prompt(agent_type: &AgentType, doc_ctx: &DocumentContext) -> String {
        let base_persona = crate::ai::KAIRO_SYSTEM_PROMPT;

        // v3.0: Structured document context fragment (headings, tables, slide position)
        let doc_fragment = doc_ctx.to_system_prompt_fragment();

        let agent_specialty = match agent_type {
            AgentType::DesignAndMedia => {
                r#"
*** SWARM ROLE: DESIGN & MEDIA AGENT ***
You are the Design & Media Specialist. The user is in a visual tool (PowerPoint, Canva, Figma).
YOUR DIRECTIVES:
1. THINK VISUALLY: Suggest layouts, slide structures, and UI elements.
2. ADD IMAGES: Wherever a visual is required to make the document professional, insert an image prompt using the exact format: [IMAGE: highly detailed prompt for image generation]
3. KEEP COPY PUNCHY: Visual tools require short, impactful text. Do not write walls of text.
"#
            }
            AgentType::ReasoningAndLogic => {
                r#"
*** SWARM ROLE: REASONING & COMPLEX TASKS AGENT ***
You are the Reasoning & Logic Specialist. The user requires deep thought, coding, or complex logic.
YOUR DIRECTIVES:
1. BE PRECISE: Output perfectly valid code or terminal commands.
2. NO FLUFF: Do not explain unless asked. If writing code for an IDE, output ONLY the raw code.
3. LOGICAL STRUCTURE: If asked a complex question, break it down step-by-step.
"#
            }
            AgentType::ContentAndAllRounder => {
                r#"
*** SWARM ROLE: CONTENT & ALL-ROUNDER AGENT ***
You are the Content Specialist. The user is in a document tool (Word, Notion, etc).
YOUR DIRECTIVES:
1. PERFECT FORMATTING: Ensure the text is highly professional, perfectly justified, and aligned to the context.
2. RICH STRUCTURE: Use appropriate headings, bullet points, and paragraph breaks.
3. TONE MATCH: Match the exact professional standard expected for high-end corporate documents.
"#
            }
        };

        format!(
            "{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n{}",
            base_persona,
            doc_fragment,
            agent_specialty,
        )
    }
}
