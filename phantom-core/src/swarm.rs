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
    /// Student/beginner-friendly explanations and guided writing
    StudentTutor,
    /// Developer/engineer-grade technical depth
    Engineer,
    /// Excel, spreadsheets, formulas, data analysis
    DataAnalyst,
}

use crate::plugin::{SwarmAgent, AgentRegistry};

pub struct DesignAgent;
impl SwarmAgent for DesignAgent {
    fn id(&self) -> &str { "design" }
    fn name(&self) -> &str { "Design & Media Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: DESIGN & MEDIA AGENT ***\nSuggest layouts, slide structures, and visual elements. Use [IMAGE: prompt] for visuals. Keep copy punchy. Prioritize visual storytelling over text density.", base, doc_fragment)
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
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: REASONING & LOGIC AGENT ***\nBe precise. Output valid code or terminal commands. No fluff. Include error handling and edge cases.", base, doc_fragment)
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
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: CONTENT AGENT ***\nPerfect formatting. Rich structure. Professional tone. Adapt voice to the document context. If writing or continuing a list, ensure numbering is strictly sequential (1, 2, 3). DO NOT repeat characters, duplicate list numbers, or hallucinate text. Keep output crisp, concise, and logically justified.", base, doc_fragment)
    }
    fn match_score(&self, _doc_ctx: &DocumentContext) -> u8 { 10 } // Default fallback score
}

/// Student & Beginner Tutor Agent — writes accessibly, explains concepts, adapts to learners.
pub struct StudentTutorAgent;
impl SwarmAgent for StudentTutorAgent {
    fn id(&self) -> &str { "student" }
    fn name(&self) -> &str { "Student & Beginner Tutor" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: STUDENT TUTOR AGENT ***\n\
            You are a patient, encouraging tutor. Write clearly for beginners. \
            Define jargon when you use it. Use analogies and examples. \
            If writing an essay or assignment, structure it with a clear intro, body, and conclusion. \
            Never be condescending — assume the student is smart but new to this topic.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("explain") || p.contains("what is") || p.contains("how does")
            || p.contains("essay") || p.contains("assignment") || p.contains("homework")
            || p.contains("study") || p.contains("understand") { 85 }
        else { 5 }
    }
}

/// Engineer & Developer Agent — writes technical docs, READMEs, commit messages, API docs.
pub struct EngineerAgent;
impl SwarmAgent for EngineerAgent {
    fn id(&self) -> &str { "engineer" }
    fn name(&self) -> &str { "Engineer & Developer Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: ENGINEER AGENT ***\n\
            You are a senior engineer writing for a technical audience. \
            Prefer precise language, exact types, and real examples. \
            For documentation: use markdown headings, code fences, and callouts. \
            For commit messages: follow Conventional Commits. \
            For README: include badges, setup steps, and usage examples.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        use crate::document_context::DocKind;
        if matches!(doc_ctx.doc_kind, DocKind::CodeFile | DocKind::Markdown | DocKind::Terminal) {
            let p = doc_ctx.prompt_text.to_lowercase();
            if p.contains("readme") || p.contains("doc") || p.contains("api") 
                || p.contains("commit") || p.contains("changelog") { return 95; }
            return 70;
        }
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("function") || p.contains("implement") || p.contains("refactor")
            || p.contains("architecture") || p.contains("deploy") { 60 } else { 0 }
    }
}

/// Data Analyst Agent — Excel formulas, pivot tables, data summaries.
pub struct DataAnalystAgent;
impl SwarmAgent for DataAnalystAgent {
    fn id(&self) -> &str { "data" }
    fn name(&self) -> &str { "Data & Spreadsheet Analyst" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: DATA ANALYST AGENT ***\n\
            You are a spreadsheet and data expert. Write Excel formulas correctly (=VLOOKUP, =SUMIF, etc.). \
            Explain data patterns clearly. For summaries, use bullet points with key numbers. \
            For charts: describe what chart type would best visualize the data. \
            Always double-check formula syntax before outputting.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        use crate::document_context::DocKind;
        if matches!(doc_ctx.doc_kind, DocKind::ExcelSpreadsheet | DocKind::OpenDocumentSpreadsheet) { return 100; }
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("formula") || p.contains("excel") || p.contains("spreadsheet")
            || p.contains("pivot") || p.contains("vlookup") || p.contains("chart") { 75 }
        else { 0 }
    }
}

/// Image Generation Agent — specialized in [IMAGE: prompt] generation for the image pipeline.
pub struct ImageAgent;
impl SwarmAgent for ImageAgent {
    fn id(&self) -> &str { "image" }
    fn name(&self) -> &str { "Image Generation Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: IMAGE GENERATION AGENT ***\n\
            You generate and optimize prompts for AI image generation.\n\
            When asked to add/create/generate an image:\n\
            1. Output exactly: [IMAGE: <detailed photorealistic prompt>] on its own line\n\
            2. For presentations (16:9): wide cinematic hero images with strong composition\n\
            3. For icons: 'flat vector icon, minimal, single color, white background'\n\
            4. For diagrams: 'clean technical diagram, labeled arrows, white background'\n\
            5. For infographics: 'modern data visualization, brand colors, clean layout'\n\
            6. For portraits/headshots: 'professional headshot, studio lighting, sharp focus'\n\
            Always follow [IMAGE: ...] with one brief caption sentence.", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("[image") || p.contains("generate image") || p.contains("create image") {
            return 100;
        }
        if p.contains("image") || p.contains("picture") || p.contains("photo")
            || p.contains("icon") || p.contains("illustration") || p.contains("diagram")
            || p.contains("visual") || p.contains("infographic") || p.contains("chart image")
            || p.contains("banner") || p.contains("thumbnail") { 90 } else { 0 }
    }
}

/// Sales & Marketing Agent — persuasive copy, CRM, proposals.
pub struct SalesAgent;
impl SwarmAgent for SalesAgent {
    fn id(&self) -> &str { "sales" }
    fn name(&self) -> &str { "Sales & Marketing Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: SALES AGENT ***\n\
            You are a senior sales and marketing copywriter. Your guidelines:\n\
            - Write with conviction and urgency, not desperation\n\
            - Lead with value, not features: 'you get X' not 'we have Y'\n\
            - Use AIDA (Attention, Interest, Desire, Action) for cold outreach\n\
            - Subject lines: under 50 chars, curiosity-driven, no spam triggers\n\
            - CTAs: one clear action, time-boxed if possible ('schedule a 15-min call this week')\n\
            - Social proof: weave in results ('saved $2M', 'cut onboarding by 40%') naturally\n\
            - Remove corporate jargon; replace with plain, powerful English", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("sales") || p.contains("proposal") || p.contains("pitch")
            || p.contains("outreach") || p.contains("email") && p.contains("cold")
            || p.contains("crm") || p.contains("marketing") || p.contains("campaign")
            || p.contains("copy") || p.contains("cta") || p.contains("funnel") { 85 } else { 0 }
    }
}

/// Medical Documentation Agent — clinical notes, patient summaries, SOAP format.
pub struct MedicalAgent;
impl SwarmAgent for MedicalAgent {
    fn id(&self) -> &str { "medical" }
    fn name(&self) -> &str { "Medical Documentation Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: MEDICAL AGENT ***\n\
            You assist with medical documentation (NOT diagnosis). Your guidelines:\n\
            - Use standard clinical terminology (ICD-10 codes where appropriate)\n\
            - SOAP format for clinical notes: Subjective, Objective, Assessment, Plan\n\
            - Medication documentation: drug name (brand/generic), dose, route, frequency\n\
            - Always flag: 'This is documentation assistance only — verify with licensed professional'\n\
            - Patient summaries: concise, chronological, include chief complaint first\n\
            - Use standard abbreviations: c/o (complains of), h/o (history of), PMH, HPI, ROS\n\
            - Lab values: include units and reference ranges", base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("patient") || p.contains("diagnosis") || p.contains("clinical")
            || p.contains("soap") || p.contains("medication") || p.contains("prescription")
            || p.contains("medical") || p.contains("doctor") || p.contains("hospital")
            || p.contains("symptom") || p.contains("treatment") { 90 } else { 0 }
    }
}

/// Legal+ Agent — contracts, legal analysis, precise language.
pub struct LegalPlusAgent;
impl SwarmAgent for LegalPlusAgent {
    fn id(&self) -> &str { "legal" }
    fn name(&self) -> &str { "Legal Document Specialist" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!("{}\n\n[DOCUMENT INTELLIGENCE]\n{}\n\n*** SWARM ROLE: LEGAL AGENT ***\n\
            You assist with legal document drafting (NOT legal advice). Guidelines:\n\
            - Use precise, unambiguous language — avoid 'may', prefer 'shall' or 'must'\n\
            - Define terms on first use: 'the Service Provider (hereinafter \"Provider\")'\n\
            - Structure: Recitals → Definitions → Obligations → Representations → Remedies → Governing Law\n\
            - Indemnification clauses: specify scope, exclusions, caps clearly\n\
            - Jurisdiction: always specify governing law and dispute resolution\n\
            - NDA/Confidentiality: define what IS confidential, not just what isn't\n\
            - Always append: 'This draft is for reference only — review with qualified legal counsel'\n\
            - Common patterns: 'notwithstanding', 'in perpetuity', 'licensee', 'licensor', 'assignable'",
            base, doc_fragment)
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("contract") || p.contains("agreement") || p.contains("legal")
            || p.contains("nda") || p.contains("clause") || p.contains("indemnif")
            || p.contains("license") || p.contains("liability") || p.contains("terms of service")
            || p.contains("privacy policy") { 92 } else { 0 }
    }
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
        }
    }


    /// The Brain: Analyzes context via LLM (or deterministic fallback) to select the right agent.
    pub async fn route(&self, doc_ctx: &DocumentContext) -> (Arc<dyn AiBackend>, AgentProfile) {
        // select_best returns None on empty registry — fall back to ContentAgent behavior
        let mut selected_agent: Arc<dyn SwarmAgent> = match self.registry.select_best(doc_ctx) {
            Some(agent) => agent,
            None => {
                // Registry is empty — use direct fallback (no panic)
                info!("⚠️  No agents in registry, using raw fallback backend");
                let profile = AgentProfile {
                    agent_type: AgentType::ContentAndAllRounder,
                    system_directive: format!("{}", crate::ai::KAIRO_SYSTEM_PROMPT),
                };
                return (self.fallback_agent.clone(), profile);
            }
        };
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

        let agent_score = selected_agent.match_score(doc_ctx);
        info!("🧠 Swarm routed to: {} (score={}) | doc={}", agent_id, agent_score, doc_ctx.doc_kind.human_name());


        let system_directive = selected_agent.build_system_prompt(doc_ctx);
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

        // All new specialized agents share the fallback backend (same model, different system prompts)
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
            AgentType::StudentTutor => "student",
            AgentType::Engineer => "engineer",
            AgentType::DataAnalyst => "data",
            AgentType::ContentAndAllRounder => "content",
        };

        // Use get_agent with graceful fallback — no panic on missing agent
        let system_directive = self.registry.get_agent(agent_id)
            .map(|a| a.build_system_prompt(doc_ctx))
            .unwrap_or_else(|| crate::ai::KAIRO_SYSTEM_PROMPT.to_string());

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
