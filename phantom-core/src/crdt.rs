/// CRDT Session — Pure Rust Yjs session via yrs crate.
/// Maintains a shared document with the AI as a named peer (clientID 999).
/// Binary-protocol compatible with @docscode/core on the JS side.

use anyhow::Result;
use std::sync::Mutex;
use yrs::{Doc, GetString, Options, Text, Transact};

pub struct CrdtSession {
    /// The Yrs document (pure Rust Yjs)
    doc: Doc,
    /// AI client ID — used to track which changes came from AI
    pub ai_client_id: u64,
}

impl CrdtSession {
    /// Create a new session with the AI registered as a peer with the given clientID
    pub fn new(ai_client_id: u64) -> Self {
        let options = Options {
            client_id: ai_client_id,
            ..Default::default()
        };
        let doc = Doc::with_options(options);

        CrdtSession { doc, ai_client_id }
    }

    /// Insert human-typed text into the CRDT document.
    /// This represents the "human peer" state — used as AI context.
    pub fn insert_human_text(&self, text: &str) {
        let content = self.doc.get_or_insert_text("content");
        let mut txn = self.doc.transact_mut();

        // Replace entire human context with new snapshot
        // (In production this would be a delta, but for MVP we replace)
        let current_len = content.get_string(&txn).len() as u32;
        if current_len > 0 {
            content.remove_range(&mut txn, 0, current_len);
        }
        content.insert(&mut txn, 0, text);
    }

    /// Insert AI-generated suggestion text as the AI peer.
    pub fn insert_ai_text(&self, suggestion: &str) {
        let ai_response = self.doc.get_or_insert_text("ai_suggestion");
        let mut txn = self.doc.transact_mut();

        // Clear previous AI suggestion
        let current_len = ai_response.get_string(&txn).len() as u32;
        if current_len > 0 {
            ai_response.remove_range(&mut txn, 0, current_len);
        }
        ai_response.insert(&mut txn, 0, suggestion);
    }

    /// Get current human text content
    pub fn get_human_text(&self) -> String {
        let txn = self.doc.transact();
        self.doc.get_or_insert_text("content").get_string(&txn)
    }

    /// Get last AI suggestion from CRDT
    pub fn get_ai_suggestion(&self) -> String {
        let txn = self.doc.transact();
        self.doc.get_or_insert_text("ai_suggestion").get_string(&txn)
    }

    /// Build an AI prompt from the current CRDT state.
    /// This is what gets sent to Ollama/OpenAI/etc.
    pub fn build_prompt(&self) -> String {
        let human_text = self.get_human_text();

        format!(
            "You are a ghost writer AI. The user is currently writing the following text:\n\n\
            ---\n{}\n---\n\n\
            Continue this text naturally. Write only the continuation (no explanation, no preamble). \
            Keep it concise — 1-3 sentences maximum. Match the user's tone and style exactly.",
            human_text
        )
    }

    /// Get word count of current document
    pub fn word_count(&self) -> usize {
        self.get_human_text()
            .split_whitespace()
            .count()
    }

    /// Export CRDT state as binary (for syncing with @docscode/core)
    pub fn export_state(&self) -> Vec<u8> {
        let txn = self.doc.transact();
        txn.encode_state_as_update_v1(&Default::default())
    }
}
