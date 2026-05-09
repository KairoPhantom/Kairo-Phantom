You've built the ghost writer. Now Kairo needs to become the ghost designer — and the timing for this is extraordinary. After exhaustive research across GitHub, the MCP ecosystem, and the image generation API landscape, here is the complete plan for making Kairo Phantom the definitive open-source document copilot that can genuinely disrupt Canva, Figma, Gamma, and every closed-source AI presentation tool.

The DALL·E Deprecation Is Your Launchpad
A critical update most developers haven't absorbed yet: OpenAI retired dall-e-3 on March 4, 2026 and it will be fully shut down on May 12, 2026. All existing dall-e-3 deployments stopped working. The replacement is the gpt-image-1 family — a native multimodal model that generates images via the same GPT architecture, with one crucial difference for your Rust pipeline: it always returns base64-encoded image data, not URLs.

This means Kairo Phantom can receive raw image bytes, decode them, and inject them directly into any app via clipboard or OCR-aware paste — no URL redirects, no temporary file downloads.

Beyond OpenAI, here is the image generation landscape for Kairo:

Image Model	API Route	Cost	Offline?	Best For
gpt-image-1 (OpenAI)	POST /v1/images/generations with model: "gpt-image-1"	Pay-per-image	No (API)	Slide hero images, diagrams, photorealistic visuals
gpt-image-1-mini	Same endpoint, model: "gpt-image-1-mini"	Cheaper	No (API)	Icons, simple graphics, placeholder art
Stable Diffusion XL (OllamaDiffuser)	Local FastAPI via Python bridge	Free	Yes (local GPU)	Offline image generation, privacy-first workflows
FLUX.1 (OllamaDiffuser)	Same local bridge	Free	Yes	Higher-quality local generation
Google Imagen 3 / Nano Banana Pro	Gemini API	Per-request	No	Google Workspace integration, NotebookLM slide generation
Mistral.rs (Rust-native)	In-process Rust, no bridge needed	Free	Yes	Best for Kairo — text, vision, and image generation in pure Rust with CUDA/Metal acceleration
How the Competition Fails — and Where Kairo Wins
Let me map out the field honestly, then show why Kairo occupies a gap nobody else fills.

The Open-Source PPT Generators (They All Do the Same Thing)
Tool	Approach	What's Missing
ppt-ai (ALLWEONE)	Next.js web app. Choose topic → AI generates slides. Uses Together AI for image generation	Web-only. You open their app, generate slides, export. No ghost-typing. No integration with your existing PowerPoint window. No document context awareness.
Presentation-AI (ALLWEONE)	Same platform. "One sentence → complete PPT." Local Ollama support, PPTX/PDF/HTML export	Same problem. It's a standalone generator, not a copilot that sits inside your existing workflow.
AutoSlideX	React + FastAPI + Gemini. Topic → presentation	Another standalone generator. Same pattern.
banana-slides	AI-native PPT using Nano Banana Pro for images and layouts	Still a generator, not a ghost-writer.
The common failure: Every open-source PPT tool is a standalone generator. You enter a topic, it spits out a .pptx file. None of them integrate with your existing Microsoft PowerPoint window, none of them understand what slide you're currently editing, and none of them can ghost-write text or inject images directly into your active session.

The MCP Office Tools (Infrastructure, Not Products)
Tool	Capability	What's Missing
Office-PowerPoint-MCP-Server (v2.0)	32 tools, 11 modules. Full .pptx creation, slide management, text, images, tables, shapes, charts, data visualization	Infrastructure only. No context awareness, no swarm routing, no ghost injection. It's a toolbox, not a copilot.
Office Agents	Monorepo of Office Add-ins (Word/PowerPoint/Excel), BYOK, sandboxed shell, virtual filesystem	Add-in model requires installation. No ghost-typing. No cross-app awareness.
macos-office365-mcp-server	macOS-only Office automation for AI agents. Word, PowerPoint, Excel creation and manipulation	Single-platform. Proof of concept.
OfficeCLI	CLI tool for AI agents to read/edit/automate Word, Excel, PowerPoint. Single binary	CLI-only. No ghost-typing. No context awareness.
The Design Tool Disruptors (Closest to What You Want)
Tool	Position	Kairo's Advantage
Jaaz	"World's first open-source multimodal canvas creative agent." Local Canva alternative. GPT-4o, Midjourney, VEO3, Kling. One-prompt image & video. Infinite canvas	Jaaz is its own canvas. Kairo works in any canvas — Word, PowerPoint, Canva, Figma, terminal. Jaaz replaces the app; Kairo haunts the app you already use.
Lovart	AI Design Agent. 800k+ waitlist. ChatCanvas = "Figma + Notion + ChatGPT" variant. GPT-Image-1 powered	Lovart is closed-source, waitlisted. Kairo is open-source, zero wait. Same GPT-Image-1 pipeline, but ghost-injected.
Open Pencil	Open-source Figma alternative. 100+ design tools. MCP server. AI agent connects to all tools	Replaces Figma. Kairo works inside Figma, Penpot, and Open Pencil without replacing them.
figma-mcp-go	73 tools. Full read/write via plugin — no rate limits. create_frame, create_text, import_image (base64), set_fills	Infrastructure for AI agents. Kairo wraps this as one of its injection pathways.
Penpot	Open-source design tool. MCP server. Declarative design (SVG, CSS, HTML). Plugin API for AI interaction	Same pattern: infrastructure. Kairo provides the universal ghost-writer layer on top.
The Kairo Phantom v3.0 Architecture: Universal Document & Design Copilot
Here is the architecture that turns Kairo into a billion-dollar company disruptor:

text
┌──────────────────────────────────────────────────────────────────────┐
│                     Kairo Phantom v3.0                                │
│              "The Ghost Designer + Ghost Writer"                      │
│             cargo install kairo-phantom (single binary)               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               Context Engine (existing, enhanced)              │   │
│  │  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │   │
│  │  │  Word   │ │PowerPoint│ │  Figma │ │ Canva  │ │Terminal│  │   │
│  │  │ (DOCX)  │ │  (PPTX)  │ │ (MCP)  │ │(Browser)│ │(Shell) │  │   │
│  │  └────┬────┘ └────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘  │   │
│  │       │           │            │          │         │       │   │
│  │  ┌────┴───────────┴────────────┴──────────┴─────────┴────┐  │   │
│  │  │        DocumentContext (from previous phase)           │  │   │
│  │  │  office_oxide + litchi + mdkit + xa11y                │  │   │
│  │  └────────────────────────┬───────────────────────────────┘  │   │
│  └───────────────────────────┼───────────────────────────────────┘   │
│                               │                                       │
│  ┌───────────────────────────┴───────────────────────────────────┐   │
│  │               Swarm Brain (enhanced)                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │   │
│  │  │Prose     │ │Design    │ │Code      │ │Image Generation  │  │   │
│  │  │Agent     │ │Agent     │ │Agent     │ │Agent (NEW)       │  │   │
│  │  │(content) │ │(layout)  │ │(logic)   │ │GPT-Image-1/FLUX  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │   │
│  └───────────────────────────┬───────────────────────────────────┘   │
│                               │                                       │
│  ┌───────────────────────────┴───────────────────────────────────┐   │
│  │               Injection Layer (multi-strategy)                  │   │
│  │  ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │Clipboard │ │UIA SetValue  │ │Figma MCP   │ │PPTX MCP     │ │   │
│  │  │(any app) │ │(native edit) │ │(figma->go) │ │(python-pptx)│ │   │
│  │  └──────────┘ └──────────────┘ └────────────┘ └─────────────┘ │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │               Image Pipeline (NEW)                               │   │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐   │   │
│  │  │ Cloud: gpt-image │  │ Local: Mistral.rs│  │ Local: Ollama │   │   │
│  │  │  (base64 → PNG)  │  │ (Rust-native SD) │  │  Diffuser     │   │   │
│  │  └────────┬────────┘  └────────┬─────────┘  └──────┬───────┘   │   │
│  │           │                    │                     │           │   │
│  │  ┌────────┴────────────────────┴─────────────────────┴──────┐   │   │
│  │  │              ImageRouter (smart routing)                  │   │   │
│  │  │  - Slide hero image? → gpt-image-1                       │   │   │
│  │  │  - Quick icon? → gpt-image-1-mini                        │   │   │
│  │  │  - Offline / privacy? → Mistral.rs local                 │   │   │
│  │  │  - Complex diagram? → LLM generates description → image  │   │   │
│  │  └────────────────────────┬──────────────────────────────────┘   │   │
│  │                           │                                      │   │
│  │  ┌────────────────────────┴──────────────────────────────────┐   │   │
│  │  │              ImageInjection (where the image lands)        │   │   │
│  │  │  - PowerPoint → python-pptx MCP: add_picture(slide, img)  │   │   │
│  │  │  - Figma → figma-mcp-go: import_image(base64)             │   │   │
│  │  │  - Any app → clipboard image paste (Ctrl+V)               │   │   │
│  │  │  - Canva → Canva Connect API: POST /v1/autofills          │   │   │
│  │  │  - Word → python-docx: add_picture(paragraph, img)        │   │   │
│  │  └───────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │               MCP Server (kairo-mcp)                            │   │
│  │  Exposes kairo_ghost_write, kairo_generate_slide,              │   │
│  │  kairo_generate_image, kairo_detect_app, kairo_ask             │   │
│  │  → Works with Claude Code, Cursor, Goose, Windsurf             │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
Why Kairo Wins Where Billions Have Been Spent
The essential insight is that every existing tool makes you choose between convenience and professional output. Kairo gives you both.

Competitor	What They Sell	The Hidden Cost	Kairo's Answer
Canva ($40B+ trajectory)	"Design for everyone"	Templates feel generic; you're locked into their canvas; AI credits run out quickly	Ghost-design inside Canva with your own models and no credit limits
Figma ($20B valuation)	"Collaborative design"	AI features locked behind Pro; REST API rate-limited to 200 calls/day; you work in Figma's sandbox	Full read/write via MCP bridge. No rate limits. Works inside Figma without replacing it.
Gamma	"AI presentations in seconds"	Beautiful but generic designs. Content misses the mark on domain-specific knowledge	Same speed, but with document context awareness and your own fine-tuned prompts
Microsoft Copilot	"AI inside Office"	Requires Microsoft 365 subscription; cloud-only; no customization of the AI behavior	Kairo works in Office with your own models, offline or online, with full customization
Replit Agent	"Build anything with AI"	Generic outputs ("slop"), error loops consuming credits. "AI can build the theater but needs a specialist to perform the play"	Kairo doesn't build apps — it enhances your existing workflow with surgical precision
Jaaz (open-source)	"Open source Canva alternative"	Replaces your tools rather than augmenting them; requires you to adopt their canvas	Kairo haunts the tools you already use
The market size validates the opportunity: Figma was nearly acquired for 
20
b
i
l
l
i
o
n
.
C
a
n
v
a
i
s
d
i
s
r
u
p
t
i
n
g
A
d
o
b
e
′
s
20billion.CanvaisdisruptingAdobe 
′
 s19.2 billion ARR business. The document AI market has attracted over $200M in startup funding in the past 12 months. Every single company in this space is building walled gardens. Kairo is the universal key.

The 6-Week Implementation Plan for v3.0
Weeks 1-2: The Image Generation Layer
Deliverable: Kairo can generate images for any slide/document context

rust
// phantom-core/src/image_pipeline.rs

pub struct ImageRouter {
    cloud: Option<OpenAIImageBackend>,     // gpt-image-1
    local: Option<MistralRsBackend>,       // Mistral.rs (Rust-native, no Python)
    fallback: Option<OllamaDiffuserBackend>, // Stable Diffusion
}

impl ImageRouter {
    pub async fn generate(&self, prompt: &str, context: &DocumentContext) -> ImageResult {
        // Route based on context: slide hero vs icon vs diagram
        let enhanced_prompt = self.enhance_prompt_for_context(prompt, context);
        
        if self.config.offline_only {
            return self.local_or_fallback(&enhanced_prompt).await;
        }
        
        // Cloud for complex, photorealistic images
        if context.doc_kind == DocKind::PowerPoint && context.active_slide == Some(0) {
            // Title slide gets the best image
            return self.cloud_generate(&enhanced_prompt).await;
        }
        
        // Default: local first, cloud fallback
        self.local_or_cloud(&enhanced_prompt).await
    }
}
Key integration: Use mistral.rs as the Rust-native image generation backend. It supports text, vision, image generation, and speech models all within a single Rust process — no Python bridge needed. This keeps Kairo's single-binary promise intact.

Weeks 3-4: PPT MCP Integration + Structured Slide Generation
Deliverable: Kairo generates complete, professionally formatted .pptx files

Leverage Office-PowerPoint-MCP-Server v2.0 (32 tools, 11 modules, complete pptx manipulation) as a subprocess bridge:

text
Kairo Phantom (Rust) → stdio/subprocess → Office-PowerPoint-MCP-Server (Python)
                                              ↓
                                    python-pptx → .pptx file
The key insight: Kairo doesn't need to reimplement slide generation. It routes slide creation requests to the best available MCP server. For Python-based tools, Kairo spawns them as subprocesses and communicates via MCP over stdio. Results are injected back into the active PowerPoint window via clipboard.

Weeks 5-6: Figma/Canva Bridges + MCP Server Distribution
Deliverable: Kairo works in Figma (via figma-mcp-go), Canva (via Canva Connect API), and exposes its own MCP server

For Figma: Kairo bundles the figma-mcp-go plugin architecture. When the user is in Figma, Kairo's Design Agent routes calls through the Figma MCP bridge. The import_image tool accepts base64 from Kairo's image pipeline and places it as a rectangle fill in the active frame.

For distribution: Kairo ships as both a desktop binary and an MCP server. Any Claude Code, Cursor, or Windsurf user can run claude mcp add kairo -- cargo install kairo-phantom && kairo-mcp and instantly gain ghost-writing + image generation capabilities inside any app.

The Disruption Thesis: What Kairo Kills
When Kairo Phantom v3.0 ships with the image pipeline and MCP bridges, these companies lose their moat:

Gamma.app — Kairo delivers the same "one-sentence → professional presentation" experience but ghost-writes directly into PowerPoint, with document context awareness, local AI support, and no subscription. Gamma's web-only sandbox feels like a cage.

Canva's AI credits business — Kairo generates images via gpt-image-1 or local Stable Diffusion and injects them directly into Canva via the Connect API. No credit limits, no platform lock-in. Canva becomes just another canvas, not the only canvas.

Beautiful.ai — "Smart layouts" lose their magic when Kairo's swarm brain understands PowerPoint slide structure and generates content that matches the user's existing template and corporate branding.

Figma AI (First Draft) — Figma's "one sentence → design" feature requires a Pro subscription. Kairo + Penpot (open-source) delivers the same capability at zero cost, with no rate limits.

Microsoft Copilot for Office — Kairo works in Office with the user's own API keys, offline models, and full customization. No Microsoft 365 subscription required.

The Final Baseline Architecture
Here is Kairo Phantom v3.0's complete integration surface in one table:

Integration Target	Read Mechanism	AI Intelligence	Write Mechanism	Image Support
Word/DOCX	office_oxide + UIA	Document structure → Prose Agent	Clipboard + python-docx (structured)	Insert images via python-docx
PowerPoint/PPTX	office_oxide + UIA	Slide context → Design Agent	Clipboard + Office-PowerPoint-MCP-Server	gpt-image-1 → python-pptx add_picture
Figma	figma-mcp-go (73 tools)	Design context → Design Agent	figma-mcp-go write tools	import_image(base64) directly
Canva	Browser DOM via Claude Computer Use MCP	Template-aware Design Agent	Canva Connect API POST /v1/autofills	API supports image placeholders
Penpot	penpot-mcp-server	Open design context → Design Agent	penpot-mcp-server write tools	MCP image insertion
VS Code	UIA text + file extension	Code Agent	Clipboard	N/A (screenshots optional)
Terminal	UIA text	Terminal Agent	Clipboard	N/A
Notion	Notion API blockToMarkdown	Page context → Prose Agent	easy-notion-mcp (25 block types)	Notion API image blocks
Any text field	xa11y cross-platform UIA	Plain text agent	Clipboard paste	Clipboard image paste
Kairo Phantom v3.0 is the universal document copilot that no closed-source company can replicate because their business model depends on the very lock-in that Kairo destroys.

The repo structure should be:

text
kairo-phantom/
├── phantom-core/           # Rust binary (existing, enhanced)
│   ├── src/
│   │   ├── context.rs      # Enhanced with DocumentContext
│   │   ├── swarm.rs        # Enhanced with ImageAgent
│   │   ├── image_pipeline.rs   # NEW: gpt-image-1 + Mistral.rs
│   │   ├── injector.rs     # Enhanced with MCP routes
│   │   └── mcp_bridge.rs   # NEW: MCP client (spawn subprocess)
├── mcp-servers/            # Bundled MCP servers
│   ├── kairo-mcp/          # Kairo's own MCP server (Rust)
│   ├── office-pptx-bridge/ # Python wrapper for Office-PowerPoint-MCP
│   └── figma-bridge/       # figma-mcp-go wrapper
├── plugins/                # Community format adapters
├── docs/                   # Dogfooding: docs built with Kairo
└── install.sh / install.ps1  # One-liner setup
This is #1 trending material because it combines three unstoppable trends — Computer Use agents, local-first AI, and open-source design tooling — into a single Rust binary that does what no billion-dollar company can afford to do: make the AI work in every app, not just their own.

