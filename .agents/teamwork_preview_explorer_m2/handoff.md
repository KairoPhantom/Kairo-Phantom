# Handoff Report: Milestone 2 — Autonomous Skill Creation / Hermes Agent Pattern

This report provides the detailed read-only investigation and design findings for Milestone 2, focusing on `phantom-core` integration, hotkey handling, overlay rendering, and dynamic skill scaffolding.

---

## 1. Observation

### 1.1 Planning Engine & Task Trace
*   **Plan Definition**: In `phantom-core/src/planning_engine.rs` (lines 20-44):
    ```rust
    pub enum StepStatus {
        Pending,
        Running,
        Complete,
        Failed(String),
    }
    pub struct PlanStep {
        pub index: usize,
        pub description: String,
        pub status: StepStatus,
    }
    pub struct Plan {
        pub steps: Vec<PlanStep>,
        pub intent_type: IntentType,
        pub doc_specialist: DocSpecialist,
    }
    ```
*   **Plan Storage & State**: In `phantom-core/src/main.rs` (lines 685-686):
    ```rust
    let pending_plan: Arc<std::sync::Mutex<Option<crate::planning_engine::PendingPlan>>> =
        Arc::new(std::sync::Mutex::new(None));
    ```
    Plans generated are saved inside `pending_plan` when the user needs to review them (low confidence). When the user presses `Alt+M` while the plan comment lines are in context, the plan is consumed:
    ```rust
    active_plan = lock.take();
    ```
*   **Task Logging**:
    *   **Audit Logger**: Successful executions are logged in `phantom-core/src/governance/mod.rs` via `AuditLogger` (line 137) writing to `~/.kairo-phantom/audit.jsonl`, and `TamperEvidentAuditLog` (line 261) writing to `~/.kairo-phantom/audit_chain.jsonl`.
    *   **Agent Debug**: Selected agents and their prompts are logged to `~/.kairo-phantom/agent_debug.jsonl` (defined in `toast_notification.rs` line 510).

### 1.2 Overlay Notification (`show_overlay`)
*   **Overlay Definition**: Located in `phantom-core/src/toast_notification.rs` (line 366):
    ```rust
    pub fn show_overlay(title: &str, body: &str, color: OverlayColor, duration_ms: u32)
    ```
*   **Overlay Mechanics**:
    *   Spawns a background thread using `spawn_overlay_thread()` (line 315) that registers a custom topmost, layered click-through Win32 window (`KairoOverlayWindowClass`).
    *   Renders visual cards near the caret/text cursor using GDI (`WM_PAINT`, `BeginPaint`, `CreateSolidBrush`, `DrawTextW`).
*   **Helper Functions**:
    *   `show_clarification_toast(question: &str)` (line 415)
    *   `show_completion_toast(chars_injected: usize, agent_name: &str)` (line 425)
    *   `show_progress_toast(message: &str)` (line 436)
    *   `show_error_toast(message: &str)` (line 446)

### 1.3 Hotkey/Keyboard Handling
*   **Hotkey Hook**: In `phantom-core/src/hotkey.rs` (lines 86-91):
    ```rust
    let h_hook = SetWindowsHookExW(
        WH_KEYBOARD_LL,
        Some(low_level_keyboard_proc),
        None,
        0,
    ).expect("Failed to install WH_KEYBOARD_LL hook");
    ```
*   **Event Capture**: Inside `low_level_keyboard_proc` (line 208), the hook intercepts Alt (`VK_MENU`), Shift (`VK_SHIFT`), and Ctrl (`VK_CONTROL`) modifier states, intercepts Alt+M, Alt+V, Alt+Shift+M, and Ctrl+Shift+Z key presses, suppresses the triggering character (`M`, `V`, `Z`) by returning `LRESULT(1)`, and sends a `PhantomEvent` to the main event loop via `GLOBAL_TX`.
*   **rdev Callback**: On non-Windows platforms, `run_rdev()` (line 111) listens globally via `rdev::listen` and captures modifiers/keypresses.

### 1.4 Waza Manifest & Skill Loader
*   **Dynamic Manager**: `WazaSkillManager` in `phantom-core/src/waza_registry.rs` manages dynamic skills.
*   **Manifest structure**: In `waza_registry.rs` (lines 13-25):
    ```rust
    pub struct SkillManifest {
        pub id: String,
        pub name: String,
        pub version: String,
        pub description: String,
        pub author: String,
        pub category: String, // "legal" | "medical" | "developer" | "finance" | "general"
        pub skill_md_url: String,
        pub wasm_url: Option<String>,
        pub signature: Option<String>,
        pub requires_kairo: String,
        pub tags: Vec<String>,
    }
    ```
*   **File Paths**: Written under `~/.kairo-phantom/skills/<safe-name>/` directory:
    *   `manifest.toml` (describes metadata)
    *   `SKILL.md` (distilled instructions + system prompts)
    *   `test.toml` (standard test cases for validation)
    *   `plugin.wasm` (optional compiled WASM plugin)

---

## 2. Logic Chain

### 2.1 Watch & Retrieve Multi-Step Tasks
1. `PlanningEngine::generate` returns a structured `Plan`.
2. The user executes the plan when they press `Alt+M`. During execution, the prompt, plan steps, and injected content are processed in the event loop.
3. If the run completes without error, `AuditLogger` appends a successful entry to the audit log (`audit.jsonl` / `audit_chain.jsonl`).
4. **Actionable conclusion**: Successful tasks can be watched in real-time by intercepting the event handler after `injector.inject_replace_line()` succeeds in `main.rs`. We can capture and store the last successful task context (original prompt, plan, generated output, process name) in a thread-safe, in-memory state inside a new `SkillFactory` struct.

### 2.2 Toast Overlay Notifications
1. `toast_notification.rs` defines `show_overlay` using native GDI and `OverlayColor`.
2. Wrappers like `show_completion_toast` and `show_progress_toast` simplify invoking the overlay.
3. **Actionable conclusion**: We can call these existing methods directly when prompt alerts occur (e.g. asking the user to save a dynamic skill or reporting successful distillation).

### 2.3 Keyboard Hook & Tab Interception
1. Keyboard inputs are processed in `low_level_keyboard_proc` in `hotkey.rs`.
2. Modifiers are tracked, and matching hotkeys are suppressed and dispatched via `send_event()`.
3. **Actionable conclusion**: By adding a global atomic boolean `SKILL_SAVE_PENDING` to `hotkey.rs` and checking it when `kbd.vkCode == 0x09` (VK_TAB) is pressed, we can intercept the Tab keypress, suppress its default insertion, and send a custom `PhantomEvent::SkillSaveApproved` to trigger the distillation pipeline.

### 2.4 Waza Manifest and Path Specifications
1. Dynamic skills are scaffolded and listed from `~/.kairo-phantom/skills/<id>` via `WazaSkillManager`.
2. A valid skill requires both `manifest.toml` (TOML format) and `SKILL.md` (Markdown instructions with YAML frontmatter).
3. **Actionable conclusion**: The newly distilled skills must be written to `~/.kairo-phantom/skills/<safe-id>/manifest.toml` and `~/.kairo-phantom/skills/<safe-id>/SKILL.md`.

---

## 3. Caveats

*   **rdev Key Suppression**: The `rdev` library used on macOS/Linux does not support suppressing key events (it runs as a passive listener on most configurations). Thus, Tab key suppression will be robust on Windows hooks but may fall back to passive notification on macOS/Linux.
*   **Sandboxing Verification**: If a dynamic skill includes custom WASM components, their verification relies on trusted keys in the `SignatureVault`. Dynamic skills generated purely from text workflows will not include WASM and will run via direct instructions.

---

## 4. Conclusion

Autonomous Skill Creation (the Hermes Agent Pattern) is fully feasible within `phantom-core` by:
1.  Adding a `SkillFactory` module to capture the last successful workflow execution and distill it using the LLM backend into a Waza manifest.
2.  Adding a `SKILL_SAVE_PENDING` atomic variable and Tab key interception inside `hotkey.rs`.
3.  Connecting these components in `main.rs` to prompt the user, intercept approvals via Tab, and scaffold files inside `~/.kairo-phantom/skills/`.

---

## 5. Implementation Design: `skill_factory.rs` & Wiring

Here is the architectural blueprint for implementing `phantom-core/src/skill_factory.rs` and integrating it.

### 5.1 Structs and Functions: `phantom-core/src/skill_factory.rs`

```rust
// phantom-core/src/skill_factory.rs
//
// Milestone 2 — Autonomous Skill Creation (Hermes Agent Pattern)
// Distills successful multi-step task traces into dynamic Waza skills.

use std::path::PathBuf;
use std::sync::Mutex;
use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use tracing::{info, error};

use crate::ai::AiBackend;
use crate::planning_engine::Plan;

/// Context of a successfully executed multi-step workflow.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowHistory {
    pub prompt: String,
    pub plan: Plan,
    pub output: String,
    pub app_name: String,
    pub doc_kind: String,
    pub timestamp: u64,
}

pub struct SkillFactory {
    last_successful_workflow: Mutex<Option<WorkflowHistory>>,
    ai_backend: std::sync::Arc<dyn AiBackend>,
}

impl SkillFactory {
    pub fn new(ai_backend: std::sync::Arc<dyn AiBackend>) -> Self {
        Self {
            last_successful_workflow: Mutex::new(None),
            ai_backend,
        }
    }

    /// Records a successful workflow run into memory.
    pub fn record_success(
        &self,
        prompt: &str,
        plan: Plan,
        output: &str,
        app_name: &str,
        doc_kind: &str,
    ) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let history = WorkflowHistory {
            prompt: prompt.to_string(),
            plan,
            output: output.to_string(),
            app_name: app_name.to_string(),
            doc_kind: doc_kind.to_string(),
            timestamp,
        };

        let mut lock = self.last_successful_workflow.lock().unwrap();
        *lock = Some(history);
        info!("🧠 [SkillFactory] Successfully recorded completed task for skill distillation.");
    }

    /// Clears the recorded workflow history.
    pub fn clear(&self) {
        let mut lock = self.last_successful_workflow.lock().unwrap();
        *lock = None;
    }

    /// Returns true if a valid workflow history exists in memory.
    pub fn has_history(&self) -> bool {
        self.last_successful_workflow.lock().unwrap().is_some()
    }

    /// Distills the recorded workflow into a dynamic Waza skill and writes it to disk.
    /// Returns the skill ID on success.
    pub async fn distill_and_save_skill(&self) -> Result<String> {
        let history = {
            let lock = self.last_successful_workflow.lock().unwrap();
            lock.clone().context("No successful workflow trace available to save")?
        };

        info!("🧠 [SkillFactory] Running LLM distillation on task: '{}'", history.prompt);

        // System prompt instructing the model to generate the skill package files
        let system_prompt = r#"You are the Kairo Skill Distillation Engine.
Your task is to take a user's successful multi-step task execution history (prompt, plan, and final generated output) and distill it into a reusable, structured Waza dynamic skill.

You must output a single JSON object containing two keys:
1. "manifest": A JSON representation matching the manifest.toml fields:
   - "id": A unique URL-safe string containing only lowercase letters, numbers, and hyphens (e.g. "quarterly-report-generator")
   - "name": A clean, human-readable name (e.g. "Quarterly Report Generator")
   - "version": "0.1.0"
   - "description": A short explanation of the skill
   - "author": "Kairo Autonomous Engine"
   - "category": Choose one of: "legal", "medical", "developer", "finance", "general"
   - "requires_kairo": "0.6.0"
   - "tags": ["autonomous", "custom"]
2. "skill_md": The markdown content for SKILL.md containing:
   - YAML frontmatter with "name" and "description" at the very top
   - `# [Skill Title]`
   - `## Overview`
   - `## Activation` showing the trigger (e.g. `// id: <prompt>`)
   - `## System Prompt` containing the persona, tone, and directives refined from the successful workflow.
   - `## Examples` summarizing the input and output from this run.

Output ONLY valid JSON. Do not include markdown codeblocks (e.g. ```json) or any other text."#;

        let user_prompt = format!(
            "Successful Workflow Run:\nUser Prompt: {}\nPlan Steps: {:?}\nGenerated Output: {}\nApp: {}\nDocument Kind: {}",
            history.prompt,
            history.plan.to_overlay_string(),
            history.output,
            history.app_name,
            history.doc_kind
        );

        let response = self.ai_backend.complete(system_prompt, &user_prompt).await?;
        
        // Clean JSON formatting if LLM wrapped it
        let cleaned = response.trim()
            .trim_start_matches("```json")
            .trim_start_matches("```")
            .trim_end_matches("```")
            .trim();

        #[derive(Deserialize)]
        struct DistillResponse {
            manifest: LlmManifest,
            skill_md: String,
        }

        #[derive(Deserialize, Serialize)]
        struct LlmManifest {
            id: String,
            name: String,
            version: String,
            description: String,
            author: String,
            category: String,
            requires_kairo: String,
            tags: Vec<String>,
        }

        let parsed: DistillResponse = serde_json::from_str(cleaned)
            .context("Failed to parse distilled skill JSON response from LLM")?;

        let skill_id = parsed.manifest.id.clone();
        let home_dir = dirs::home_dir().context("Could not resolve home directory")?;
        let skill_dir = home_dir.join(".kairo-phantom").join("skills").join(&skill_id);
        
        std::fs::create_dir_all(&skill_dir)
            .context("Failed to create skill output directory")?;

        // Write manifest.toml
        let manifest_toml = toml::to_string_pretty(&parsed.manifest)
            .context("Failed to serialize manifest structure to TOML")?;
        
        // Add required url field to manifest
        let manifest_content = format!(
            "{}\nskill_md_url = \"local\"\n",
            manifest_toml
        );

        std::fs::write(skill_dir.join("manifest.toml"), &manifest_content)
            .context("Failed to write manifest.toml")?;

        // Write SKILL.md
        std::fs::write(skill_dir.join("SKILL.md"), &parsed.skill_md)
            .context("Failed to write SKILL.md")?;

        info!("✅ [SkillFactory] Distilled and saved dynamic skill '{}' successfully.", skill_id);
        Ok(skill_id)
    }
}
```

---

### 5.2 Wiring Diagram

#### A. In `phantom-core/src/lib.rs` (or equivalent modules)
Add the skill factory to the modules registry:
```rust
pub mod skill_factory;
```
Extend `PhantomEvent` to handle Tab approvals and cancellations:
```rust
pub enum PhantomEvent {
    // ... Existing events ...
    SkillSaveApproved,
    SkillSaveCancelled,
}
```

#### B. In `phantom-core/src/hotkey.rs`
Introduce the atomic intercept flag and check for the Tab key:
```rust
// Add global atomic flag for save status
pub static SKILL_SAVE_PENDING: AtomicBool = AtomicBool::new(false);

// Inside low_level_keyboard_proc (Windows Hook):
#[cfg(windows)]
unsafe extern "system" fn low_level_keyboard_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    // ... Standard checks ...
    let kbd = *(lparam.0 as *const KBDLLHOOKSTRUCT);
    let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;
    
    // Intercept Tab (0x09) when skill save is pending
    if kbd.vkCode == 0x09 && is_down {
        if SKILL_SAVE_PENDING.load(Ordering::SeqCst) {
            info!("🎯 Intercepted Tab keypress for dynamic skill save approval!");
            SKILL_SAVE_PENDING.store(false, Ordering::SeqCst);
            send_event(PhantomEvent::SkillSaveApproved);
            return LRESULT(1); // Suppress the Tab keystroke from hitting the target application
        }
    }
    
    // ... Rest of the hook ...
}

// Inside run_rdev (macOS/Linux):
#[cfg(not(windows))]
fn run_rdev() {
    // ...
    EventType::KeyPress(Key::Tab) => {
        if SKILL_SAVE_PENDING.load(Ordering::SeqCst) {
            info!("🎯 Intercepted Tab keypress (rdev)!");
            SKILL_SAVE_PENDING.store(false, Ordering::SeqCst);
            send_event(PhantomEvent::SkillSaveApproved);
        }
    }
}
```

#### C. In `phantom-core/src/main.rs`
Instantiate the factory and wire the execution completions:
```rust
// 1. In main() startup:
let skill_factory = std::sync::Arc::new(
    crate::skill_factory::SkillFactory::new(fallback_backend.clone())
);

// 2. Inside the PhantomEvent::HotkeyPressed handler (after successful injection):
// Locate where the suggestion is successfully completed and written to doc:
if let Some(ref active_plan) = active_plan {
    skill_factory.record_success(
        &active_plan.original_prompt,
        active_plan.plan.clone(),
        &full_response,
        &app_label,
        &doc_ctx.doc_kind.human_name()
    );
    
    // Prompt the user to save it
    crate::toast_notification::show_overlay(
        "Kairo Action Complete ✅",
        "Press TAB to save this workflow as a reusable skill, or type to dismiss.",
        crate::toast_notification::OverlayColor::Success,
        6000
    );
    
    // Enable the hotkey intercept
    crate::hotkey::SKILL_SAVE_PENDING.store(true, std::sync::atomic::Ordering::SeqCst);
}

// 3. Inside the main event loop match block:
match event {
    PhantomEvent::SkillSaveApproved => {
        info!("💾 Skill save approved by user. Beginning distillation...");
        crate::toast_notification::show_progress_toast("Distilling dynamic skill... 🧠");
        let factory_clone = skill_factory.clone();
        tokio::spawn(async move {
            match factory_clone.distill_and_save_skill().await {
                Ok(id) => {
                    crate::toast_notification::show_overlay(
                        "Skill Created! 🚀",
                        &format!("Saved skill '{}' to Waza registry.", id),
                        crate::toast_notification::OverlayColor::Success,
                        5000
                    );
                }
                Err(e) => {
                    error!("Failed to distill skill: {}", e);
                    crate::toast_notification::show_error_toast("Failed to save skill.");
                }
            }
        });
    }
    PhantomEvent::UserTyping => {
        // ... Existing cancellation logic ...
        let lock = active_cancel_token.lock().unwrap();
        if let Some(ref token) = *lock {
            token.cancel();
        }
        let mut plan_lock = pending_plan.lock().unwrap();
        *plan_lock = None;
        
        // Cancel save pending if user starts typing
        if crate::hotkey::SKILL_SAVE_PENDING.load(std::sync::atomic::Ordering::SeqCst) {
            crate::hotkey::SKILL_SAVE_PENDING.store(false, std::sync::atomic::Ordering::SeqCst);
            skill_factory.clear();
            info!("❌ Skill save cancelled because user continued typing.");
        }
    }
    // ... Other events ...
}
```

---

## 6. Verification Method

To verify the setup independently:
1.  **Code Compilation**: Validate syntax, dependencies, and structs compile cleanly.
    ```powershell
    cargo check --manifest-path .\phantom-core\Cargo.toml
    ```
2.  **Inspect Files**: Confirm `phantom-core/src/skill_factory.rs` has correct module imports (`ai::AiBackend`, `planning_engine::Plan`), and matches the design layout.
3.  **Run Tests**: Ensure all existing tests run without regression:
    ```powershell
    cargo test --manifest-path .\phantom-core\Cargo.toml
    ```
4.  **Confirm Path Logic**: Verify `dirs::home_dir()` resolves correctly to check that `manifest.toml` and `SKILL.md` are written specifically to `C:\Users\<User>\.kairo-phantom\skills\<skill_id>\` on Windows.
