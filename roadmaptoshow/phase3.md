I understand exactly what you mean — Kairo Phantom today is a fire-and-forget weapon: Alt+M → AI writes → done. But a true copilot is a two-way conversation. The user needs to be able to stop it mid-stream, guide it with intent, reject parts, accept parts, and fine-tune the output before committing. What you're describing is the difference between a spell that fires once and a familiar that sits beside you, watching, learning, and responding. Let me fix this.

After deep-diving on how Cursor, Copilot, Liveblocks, Tiptap, Patchwork, and ElectricSQL solve this exact problem, here is the comprehensive interaction model Kairo needs — distilled into lightweight, keyboard-native primitives that work in any application, not just a custom editor.

1. The Core Shift: From "Alt+M Ghost Fire" to "Alt+M Ghost Session"
The essential reframe: pressing Alt+M doesn't just trigger a one-shot write. It opens a Ghost Session — a lightweight, transient mode where the AI output is previewed as ghost text, the user interacts with it, and only upon explicit confirmation does it materialize permanently.

Here is the complete session lifecycle:

text
┌──────────────────────────────────────────────────────────┐
│                 Kairo Ghost Session                        │
│                                                           │
│  USER PRESSES Alt+M                                        │
│      │                                                    │
│      ▼                                                    │
│  ┌──────────────────────────────────────────────────┐    │
│  │  1. CONTEXT CAPTURE                               │    │
│  │  - UIA reads selected text + surrounding doc      │    │
│  │  - DocumentContext extracts structure             │    │
│  │  - Swarm Brain selects agent                      │    │
│  └────────────────────┬─────────────────────────────┘    │
│                       │                                   │
│                       ▼                                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │  2. STREAMING GHOST PREVIEW                      │    │
│  │  - AI tokens stream into overlay as ghost text    │    │
│  │  - Tauri overlay shows translucent preview        │    │
│  │  - User sees output building in real-time         │    │
│  │                                                  │    │
│  │  ACTIONS AVAILABLE DURING STREAMING:             │    │
│  │    Esc          = CANCEL (stop immediately)       │    │
│  │    Tab          = ACCEPT ALL (apply & end)        │    │
│  │    Ctrl+Right   = ACCEPT WORD-BY-WORD            │    │
│  │    Alt+1 / Alt+2 = SWITCH ALTERNATIVE             │    │
│  │    Ctrl+/       = CORRECT (open mini-prompt)      │    │
│  └────────────────────┬─────────────────────────────┘    │
│                       │                                   │
│                       ▼                                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │  3. REVIEW (if not stream-accepted)               │    │
│  │  - Ghost preview frozen for inspection            │    │
│  │  - User can: Tab Accept, Esc Reject, Ctrl+/ Edit  │    │
│  └────────────────────┬─────────────────────────────┘    │
│                       │                                   │
│                       ▼                                   │
│  ┌──────────────────────────────────────────────────┐    │
│  │  4. INJECTION (on Accept)                         │    │
│  │  - Clipboard injection (instant)                  │    │
│  │  - Previous user prompt text replaced             │    │
│  │  - Undo stack: single Ctrl+Z reverts all AI text  │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
2. The Interaction Primitives — Lightweight, Keyboard-Native
These are the five primitives that turn Kairo from a one-shot ghost-writer into a real copilot. Each is adapted from battle-tested UX in Copilot, Cursor, and Tiptap, but translated to work across any Windows application via keyboard hooks and the Tauri overlay.

Primitive 1: Streaming Ghost Preview with Immediate Cancel
What it is: When Alt+M fires, Kairo doesn't wait for the full AI response to inject. It opens a lightweight transparent overlay in the Tauri glassmorphic window showing the AI output building character by character. The user sees the text flowing in real-time, directly over their editing window.

The critical mechanics:

The AI response is streamed via SSE from your existing ai.rs module

Each token chunk is rendered into the overlay as translucent ghost text (white text at ~60% opacity, matching your existing glassmorphic design)

A small pulsing dot indicates "AI thinking..."

The user's existing text remains selected (highlighted) behind the overlay — they can see what will be replaced

Actions available during streaming:

Key	Action	Behavior
Esc	CANCEL	Immediately aborts the SSE stream. The overlay vanishes. The user's original text remains unchanged. This is the most critical interaction — users need to stop the AI when they see it going in the wrong direction.
Tab	ACCEPT ALL	Stops streaming early. Takes everything generated so far and injects it. The remaining tokens are discarded.
Ctrl+Right	ACCEPT WORD	Accepts only the next word from the ghost text. Each press extends acceptance by one word. This is directly modeled on Copilot's "Accept Next Word" (Ctrl+Right Arrow).
Alt+[ / Alt+]	CYCLE ALTERNATIVES	Switches between two different AI outputs (see Primitive 3).
Rust implementation sketch:

rust
// In phantom-core/src/ghost_session.rs

use tokio::select;
use futures::future::FutureExt;
use stream_cancel::StreamExt as CancelStreamExt;

pub struct GhostSession {
    cancel_token: CancellationToken,       // tokio_util CancellationToken
    accepted_words: usize,                 // how many words user has accepted
    current_alternative: bool,             // false = primary, true = secondary
}

impl GhostSession {
    pub async fn run(&mut self, stream: impl Stream<Item = Token>) -> SessionResult {
        let stream = stream.take_until(self.cancel_token.cancelled());

        tokio::select! {
            token = stream.next() => {
                match token {
                    Some(t) => self.render_ghost_text(t),
                    None => self.finalize(), // stream completed
                }
            }
            key = self.listen_global_keys() => {
                match key {
                    Key::Escape => self.cancel(),
                    Key::Tab => self.accept_all(),
                    Key::CtrlRight => self.accept_next_word(),
                    Key::Alt1 | Key::Alt2 => self.switch_alternative(),
                    Key::CtrlSlash => self.open_correction_prompt(),
                    _ => continue,
                }
            }
            _ = self.cancel_token.cancelled() => {
                self.cancel()
            }
        }
    }
}
Primitive 2: Post-Injection Undo (Agent-Aware, Single Ctrl+Z)
What it is: After the user accepts an AI injection, pressing Ctrl+Z once reverts the entire AI operation as a single atomic undo — not character by character. This is adapted from the Minga buffer-aware agent undo pattern, where agent edits are grouped into logical undo entries.

How it works:

Kairo's injector captures the exact text range that was replaced (the user's original prompt text)

Before injection, it snapshots the current clipboard and the selection range

After injection, it stores a HistoryEntry { before_text, after_text, range, timestamp }

The global keyboard hook intercepts Ctrl+Z when Kairo's last operation matches

One Ctrl+Z = restore the original text, restore the original clipboard

Why this matters: The biggest UX friction with AI copilots is that once the AI writes, you can't easily go back. With agent-aware undo, the user can try the AI, see it's wrong, and immediately revert with muscle memory — no hesitation, no fear of losing work. This is what Minga calls "the single biggest UX win of the buffer-aware agents design" — agent edits flow through the same undo system as user keystrokes.

Primitive 3: Two Alternatives by Default
What it is: Instead of generating one suggestion, Kairo generates two meaningfully different alternatives and lets the user toggle between them with Alt+1 / Alt+2 during the ghost session. This is adapted from the IEEE Copilot Ergonomics research: "One option invites over-trust. Offer two compact alternatives side by side and make them meaningfully different."

Implementation:

The Swarm Brain makes two parallel API calls with different system prompts (e.g., one "concise and direct," one "elaborate and detailed")

Both streams are buffered concurrently

The ghost overlay shows the currently selected alternative with a small indicator: [1/2] Concise | and [2/2] Elaborate |

Alt+1 / Alt+2 switch the ghost text instantly

On accept, only the selected alternative is injected

Cost: This doubles API usage. Mitigation strategies:

Make it configurable: alternatives = 1 in config.toml (default = 2)

In offline mode with Ollama, use a single generation but with two different temperature profiles (0.3 and 0.8) from the same prompt

Primitive 4: Inline Correction Prompt (Ctrl+/)
What it is: While the ghost preview is showing, the user presses Ctrl+/ to open a tiny inline prompt. They type a quick correction: "shorter", "use bullet points", "more formal", "add a conclusion". Kairo re-streams the AI with the original context plus the correction, and the ghost preview updates.

This replaces the need for the user to:

Cancel the session (Esc)

Re-type their entire prompt with modifications

Press Alt+M again

Visual design: The Tauri overlay shows a minimalist input bar floating just below the ghost preview text. It's a single line with placeholder text: "correction (e.g., shorter, add summary, more formal)...". The user types and presses Enter. The correction is appended to the original prompt as a system message, and the AI re-streams.

Keyboard flow:

text
Alt+M → ghost text streaming → user sees output going long-winded
     → Ctrl+/ → types "concise bullet points" → Enter
     → ghost text refreshes with shorter, bullet-pointed version
     → Tab (accept)
Primitive 5: Confidence Display + Adaptive Behavior
What it is: A subtle visual indicator in the Tauri overlay showing how confident the AI is in its output, and changing what actions are available based on that confidence. Adapted from the Copilot Ergonomics confidence bands pattern and the VSCode Copilot Next Edit Suggestions "happiness score" system.

Three confidence levels:

Band	Trigger	Visual	Behavior
High	Strong prompt match, known app context, low temperature	Green subtle glow	Tab to accept, Esc to reject, Ctrl+Right for word accept
Medium	Ambiguous prompt, mixed context	Yellow subtle glow	Requires short rationale preview before Accept; shows both alternatives prominently
Low	Low confidence, uncertain context	Red subtle glow	Accept disabled; can only copy text or Ctrl+/ to refine; explicit "this might be wrong" indicator
What this does: It makes the user trust Kairo more. When confidence is high, the interaction is fast (Tab, done). When it's low, Kairo is honest about uncertainty rather than presenting plausible-sounding but wrong text as certain. This is what the Copilot Ergonomics research calls "behavior, not color: the band should change what the user can do so they don't over-trust."

3. Yjs Collaborative Docs: AI as a First-Class Peer
You mentioned Yjs docs and shared documents. This is where Kairo becomes genuinely unique — no other ghost-writing tool handles real-time collaboration. The architecture for this is already proven by Tandem and ElectricSQL: treat the AI as a participant in the CRDT with its own clientID.

How It Works in Kairo
When Kairo detects a Yjs-powered web app is focused (detected via UIA + browser URL patterns for apps like Notion, Google Docs, Tiptap-based editors, and any app using y-websocket or y-webrtc), it switches injection modes:

Current (non-Yjs) behavior: Clipboard injection into the OS text field.

Yjs mode behavior: Kairo connects as a WebSocket peer to the Yjs document's sync endpoint and writes AI output as CRDT operations directly into the shared document — with its own clientID.

This means:

AI edits appear in real-time for all collaborators, with a distinct AI cursor

Every AI-inserted character is attributed to the AI clientID permanently

Users can accept/reject AI changes using whatever review UI the app already has

Ctrl+Z undoes AI edits as atomic operations

The AI's awareness state broadcasts { status: 'thinking', progress: 0.7 } so all users see when the AI is working

Configuration for Yjs:

toml
# ~/.kairo-phantom/config.toml

[yjs]
enabled = true
auto_detect = true       # detect Yjs-powered apps via UIA + URL
sync_endpoint = "auto"   # or "ws://localhost:1234" for explicit
client_id_prefix = "kairo-ai-"  # prefix for AI clientID
review_mode = "ghost"    # or "tracked_changes", "direct_injection"
The critical UX difference: In a Google Docs-like environment where multiple humans are editing, Kairo doesn't clipboard-paste. It joins the session as a peer, streams edits through the CRDT, and every collaborator sees the AI's cursor moving and text appearing with proper attribution. This is exactly what ElectricSQL demonstrated — AI as a genuine CRDT peer, not a sidebar that dumps text.

4. The Complete Keyboard Shortcut Map (What the User Learns)
This is the "cheat sheet" that ships in the README. Every shortcut is chosen to match muscle memory from existing tools (Copilot, Cursor, standard editors):

Shortcut	Context	Action
Alt+M	Any app	START ghost session. Kairo reads context, streams AI output as ghost text.
Esc	During streaming or preview	CANCEL. Abort generation immediately. Original text unchanged.
Tab	Ghost preview visible	ACCEPT ALL. Inject all generated text.
Ctrl+Right	Streaming or preview	ACCEPT NEXT WORD. Extend acceptance by one word.
Ctrl+Left	After word-accept	UNDO LAST WORD. Shrink acceptance by one word.
Alt+]	Ghost preview	NEXT ALTERNATIVE. Cycle to next AI suggestion (if alternatives enabled).
Alt+[	Ghost preview	PREVIOUS ALTERNATIVE. Cycle to previous alternative.
Ctrl+/	Ghost preview	CORRECT. Open mini-prompt: "What do you want changed?"
Ctrl+Z	After injection	UNDO AI OPERATION. Revert entire AI injection as one atomic undo.
Ctrl+Shift+Z	After undo	REDO AI OPERATION. Re-apply the undone AI injection.
Alt+Shift+M	Any app	REPLAY LAST. Re-run the last ghost session with the same context.
5. What This Makes Kairo That No One Else Has
Here's how Kairo stacks up after implementing these five primitives:

Feature	GitHub Copilot	Cursor	Kairo Phantom v3.1
Universal app support (Word, PPT, Figma, etc.)	❌ Code only	❌ Code only	✅ Any app with a text field
Streaming ghost preview	✅ Inline suggestions	✅ Inline suggestions	✅ Transparent overlay over any app
Stop mid-generation	✅ Esc	✅ Esc	✅ Esc from global keyboard hook
Word-by-word accept	✅ Ctrl+Right	✅ Tab only	✅ Ctrl+Right in any app
Two alternatives	❌	❌	✅ Alt+1/Alt+2 toggle
Inline correction without re-prompting	❌	✅ Cmd+K	✅ Ctrl+/ mini-prompt
Agent-aware undo (Ctrl+Z)	❌ (per-word undo)	✅ (buffer-aware)	✅ Entire AI operation as one undo
Confidence display	❌	❌	✅ Three-band confidence + adaptive behavior
Yjs CRDT peer for shared docs	❌	❌	✅ AI with clientID, awareness, cursor
Offline mode (Ollama)	❌	❌	✅ Fully offline with local models
Cross-platform	❌ (VS Code)	✅ (IDE)	✅ Windows, macOS, Linux (via xa11y)
The combination of universal app reach + streaming interactivity + inline correction + agent-aware undo + Yjs peer support is currently not available in any single tool — open source or commercial. Cursor has great in-editor interaction but doesn't leave the IDE. Copilot has ghost text but only in VS Code. Kairo with these primitives becomes the OS-level ghost copilot that developers and professionals can rely on everywhere.

6. Implementation Order (What to Build First)
Priority	Feature	Effort	Impact	Depends On
Now	Streaming cancel (Esc)	Low — add CancellationToken to existing SSE stream	Highest — users demand stop button	Nothing
Now	Ghost preview overlay (Tab accept, Esc reject)	Medium — Tauri overlay rendering token-by-token	Highest — the core session UX	Streaming cancel
Week 2	Agent-aware undo (Ctrl+Z)	Low — store HistoryEntry, intercept Ctrl+Z	High — trust and safety	Ghost preview
Week 2	Inline correction prompt (Ctrl+/)	Medium — mini-prompt UI + re-prompt pipeline	High — reduces friction	Ghost preview
Week 3	Two alternatives (Alt+1/Alt+2)	Medium — parallel API calls	Medium — quality differentiation	Ghost preview
Week 3	Confidence bands	Low — simple rules on prompt clarity + app context	Medium — trust calibration	Ghost preview
Week 4	Yjs CRDT peer integration	Higher — yrs crate + WebSocket sync	High — unlocks entire collaborative doc opportunity	Ghost preview
Week 4	Word-by-word accept (Ctrl+Right)	Low — tokenize ghost text, track acceptance boundary	Medium — precision control	Ghost preview
The streaming cancel and ghost preview are the critical first moves. Everything else builds on them. These two features alone transform Kairo from "press button, hope it's right" to "press button, watch it flow, cancel if wrong, accept if good." That's the minimum viable copilot experience.

