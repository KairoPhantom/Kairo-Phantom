use anyhow::Result;
use rusqlite::{params, Connection};
use std::path::PathBuf;
use std::sync::Mutex;
use chrono::Utc;
use tracing::{info, warn};

/// MemMachine is the enterprise-grade evolution of Kairo's memory system.
/// It supports vector embeddings for semantic retrieval and cross-session knowledge graphs.
///
/// The `Connection` is wrapped in a `Mutex` to make `MemMachine` `Send + Sync`,
/// enabling use across `tokio::spawn` task boundaries. SQLite write serialization
/// is correct because rusqlite's `Connection` is single-writer by design.
pub struct MemMachine {
    conn: Mutex<Connection>,
    #[allow(dead_code)]
    vault_dir: PathBuf,
}

impl MemMachine {
    pub fn new(vault_dir: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(&vault_dir)?;
        let db_path = vault_dir.join("mem_machine.db");
        let conn = Connection::open(db_path)?;

        // Schema evolution: Added 'embedding' BLOB and 'context_graph' table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS semantic_memory (
                id TEXT PRIMARY KEY,
                timestamp INTEGER,
                content TEXT,
                full_episode TEXT,
                embedding BLOB,
                app_context TEXT,
                context_key TEXT,
                is_ground_truth INTEGER DEFAULT 0,
                storage_strength REAL DEFAULT 1.0,
                retrieval_strength REAL DEFAULT 1.0,
                tags TEXT
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS context_graph (
                source_id TEXT,
                target_id TEXT,
                relation_type TEXT,
                weight REAL,
                PRIMARY KEY(source_id, target_id, relation_type)
            )",
            [],
        )?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS feedback_signals (
                id TEXT PRIMARY KEY,
                timestamp INTEGER,
                app_name TEXT,
                channel TEXT,
                orig_value TEXT,
                new_value TEXT,
                confidence REAL
            )",
            [],
        )?;

        Ok(Self { conn: Mutex::new(conn), vault_dir })
    }

    /// Stores a new memory fragment with its semantic embedding and ground-truth episode.
    pub async fn remember(
        &self,
        content: &str,
        full_episode: Option<&str>,
        app_context: &str,
        context_key: Option<&str>,
        is_ground_truth: bool,
        tags: Vec<&str>
    ) -> Result<()> {
        let id = uuid::Uuid::new_v4().to_string();
        let timestamp = Utc::now().timestamp();
        let tags_str = tags.join(",");

        // Mock embedding generation (production would call an embedding API)
        let mock_embedding = vec![0.0f32; 1536];
        let embedding_blob = bincode::serialize(&mock_embedding)?;

        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO semantic_memory (id, timestamp, content, full_episode, embedding, app_context, context_key, is_ground_truth, tags)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                id,
                timestamp,
                content,
                full_episode.unwrap_or(""),
                embedding_blob,
                app_context,
                context_key.unwrap_or(""),
                if is_ground_truth { 1 } else { 0 },
                tags_str
            ],
        )?;

        Ok(())
    }

    /// Retrieves relevant memories using context-first retrieval with entropy-based routing.
    ///
    /// Priority order (Upgrade 4 — Entropy-Based Routing Fallback):
    ///   1. Section-level: exact `context_key` match (highest precision)
    ///   2. App-level: `app_context` match (broader)
    ///   3. Global: `app_context = 'global'` (broadest fallback)
    ///
    /// Within each stage, results are ranked by storage_strength (a proxy for
    /// how strongly the preference has been reinforced by user feedback).
    /// A LIKE clause on the query provides an optional relevance boost but is
    /// NOT required — context matching is the primary retrieval axis.
    pub async fn recall_contextualized(&self, query: &str, granularities: Vec<String>, limit: usize) -> Result<Vec<String>> {
        let mut results = Vec::new();
        let mut seen_ids: Vec<String> = Vec::new();
        let query_pattern = format!("%{}%", query);

        // ── Stage 1: Section-level (context_key) matches ─────────────────────
        for gran in &granularities {
            if results.len() >= limit { break; }
            let batch: Vec<(String, String, i64, String, String, String)> = {
                let conn = self.conn.lock().unwrap();
                let mut stmt = conn.prepare(
                    "SELECT id, content, timestamp, full_episode, app_context, context_key
                     FROM semantic_memory
                     WHERE context_key = ?1
                     ORDER BY
                       CASE WHEN (content LIKE ?2 OR full_episode LIKE ?2) THEN 0 ELSE 1 END,
                       storage_strength DESC,
                       timestamp DESC
                     LIMIT ?3"
                )?;
                let rows = stmt.query_map(params![gran, query_pattern, limit], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, i64>(2)?,
                        row.get::<_, String>(3)?, row.get::<_, String>(4)?, row.get::<_, String>(5)?))
                })?;
                rows.filter_map(|r| r.ok()).collect()
            }; // conn + stmt dropped here
            for (id, content, ts, episode, app, ctx) in batch {
                if !seen_ids.contains(&id) {
                    seen_ids.push(id.clone());
                    results.push(self.format_memory(id, content, ts, episode, app, ctx, 2.0)?);
                }
            }
        }

        // ── Stage 2: App-level (app_context) matches ─────────────────────────
        for gran in &granularities {
            if results.len() >= limit { break; }
            let remaining = limit - results.len();
            let batch: Vec<(String, String, i64, String, String, String)> = {
                let conn = self.conn.lock().unwrap();
                let mut stmt = conn.prepare(
                    "SELECT id, content, timestamp, full_episode, app_context, context_key
                     FROM semantic_memory
                     WHERE app_context = ?1
                     ORDER BY
                       CASE WHEN (content LIKE ?2 OR full_episode LIKE ?2) THEN 0 ELSE 1 END,
                       storage_strength DESC,
                       timestamp DESC
                     LIMIT ?3"
                )?;
                let rows = stmt.query_map(params![gran, query_pattern, remaining], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, i64>(2)?,
                        row.get::<_, String>(3)?, row.get::<_, String>(4)?, row.get::<_, String>(5)?))
                })?;
                rows.filter_map(|r| r.ok()).collect()
            }; // conn + stmt dropped here
            for (id, content, ts, episode, app, ctx) in batch {
                if !seen_ids.contains(&id) {
                    seen_ids.push(id.clone());
                    results.push(self.format_memory(id, content, ts, episode, app, ctx, 1.2)?);
                }
            }
        }

        // ── Stage 3: Global preference fallback ──────────────────────────────
        if results.len() < limit {
            let remaining = limit - results.len();
            let batch: Vec<(String, String, i64, String, String, String)> = {
                let conn = self.conn.lock().unwrap();
                let mut stmt = conn.prepare(
                    "SELECT id, content, timestamp, full_episode, app_context, context_key
                     FROM semantic_memory
                     WHERE app_context = 'global'
                     ORDER BY storage_strength DESC, timestamp DESC
                     LIMIT ?1"
                )?;
                let rows = stmt.query_map(params![remaining], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, i64>(2)?,
                        row.get::<_, String>(3)?, row.get::<_, String>(4)?, row.get::<_, String>(5)?))
                })?;
                rows.filter_map(|r| r.ok()).collect()
            }; // conn + stmt dropped here
            for (id, content, ts, episode, app, ctx) in batch {
                if !seen_ids.contains(&id) {
                    seen_ids.push(id.clone());
                    results.push(self.format_memory(id, content, ts, episode, app, ctx, 1.0)?);
                }
            }
        }

        Ok(results)
    }


    #[allow(clippy::too_many_arguments)]
    fn format_memory(&self, id: String, content: String, ts: i64, episode: String, app: String, ctx: String, score: f64) -> Result<String> {
        let _ = self.update_strengths(&id, 0.05, 0.2);
        let neighbors = self.get_neighbors(&id, ts)?;
        let mut full_context = format!("--- Episode (ID: {}, RoutingWeight: {:.2}, Context: {}/{}) ---\n", id, score, app, ctx);
        if !episode.is_empty() {
            full_context.push_str(&format!("RAW EPISODE: {}\n", episode));
        }
        full_context.push_str(&format!("SUMMARY: {}\n", content));
        if !neighbors.is_empty() {
            full_context.push_str("\nNEARBY EVENTS:\n");
            for n in neighbors {
                full_context.push_str(&format!("- {}\n", n));
            }
        }
        Ok(full_context)
    }

    fn get_neighbors(&self, _id: &str, timestamp: i64) -> Result<Vec<String>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT content FROM semantic_memory
             WHERE timestamp > ?1 - 3600 AND timestamp < ?1 + 3600
             AND id != ?2
             ORDER BY timestamp ASC LIMIT 3"
        )?;
        let rows = stmt.query_map(params![timestamp, _id], |row| row.get(0))?;
        let mut neighbors = Vec::new();
        for c in rows.flatten() { neighbors.push(c); }
        Ok(neighbors)
    }

    pub fn update_strengths(&self, id: &str, storage_inc: f64, retrieval_inc: f64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE semantic_memory
             SET storage_strength = MIN(2.0, storage_strength + ?1),
                 retrieval_strength = MIN(2.0, retrieval_strength + ?2),
                 timestamp = ?3
             WHERE id = ?4",
            params![storage_inc, retrieval_inc, Utc::now().timestamp(), id],
        )?;
        Ok(())
    }

    /// Runs the Alaya maintenance cycle (cognitive decay + semantic consolidation).
    pub async fn run_maintenance_cycle(&self) -> Result<()> {
        info!("🧠 MemMachine: Starting maintenance cycle...");

        {
            let conn = self.conn.lock().unwrap();
            // 1. Decay retrieval strength (forgetting curve)
            conn.execute(
                "UPDATE semantic_memory
                 SET retrieval_strength = retrieval_strength * 0.9
                 WHERE is_ground_truth = 0",
                [],
            )?;

            // 2. Remove "forgotten" memories
            let deleted = conn.execute(
                "DELETE FROM semantic_memory WHERE retrieval_strength < 0.1 AND is_ground_truth = 0",
                []
            )?;
            if deleted > 0 {
                warn!("♻️  MemMachine: Decayed and forgot {} irrelevant memories.", deleted);
            }
        }

        // 3. PRIME Meta-Operations: Merge/Split/Generalize
        self.run_meta_operations().await?;

        info!("🧠 MemMachine: Maintenance cycle complete.");
        Ok(())
    }

    async fn run_meta_operations(&self) -> Result<()> {
        // A. Generalize: If a preference is consistent across multiple apps, promote it.
        let consistent_prefs: Vec<(String, String)> = {
            let conn = self.conn.lock().unwrap();
            let mut stmt = conn.prepare(
                "SELECT content, context_key FROM semantic_memory
                 WHERE storage_strength > 0.8 AND context_key != '' AND app_context != 'global'
                 GROUP BY content, context_key HAVING COUNT(DISTINCT app_context) > 1"
            )?;
            let rows = stmt.query_map([], |row| Ok((row.get(0)?, row.get(1)?)))?;
            let mut collected = Vec::new();
            for val in rows.flatten() { collected.push(val); }
            collected
        };

        for (content, ctx) in consistent_prefs {
            info!("🧠 PRIME: Generalizing preference to global: {}", ctx);
            let _ = self.remember(&content, None, "global", Some(&ctx), false, vec!["generalized"]).await;
        }

        // B. Split: If a preference has high retrieval but low storage (contradicted), isolate it.
        {
            let conn = self.conn.lock().unwrap();
            conn.execute(
                "UPDATE semantic_memory SET tags = tags || ',split_isolated'
                 WHERE storage_strength < 0.3 AND retrieval_strength > 0.5",
                []
            )?;
        }

        Ok(())
    }

    /// Forms a relationship between two memory entities (Context Graphing).
    pub fn graph_relate(&self, source: &str, target: &str, relation: &str, weight: f64) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO context_graph (source_id, target_id, relation_type, weight)
             VALUES (?1, ?2, ?3, ?4)
             ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET weight = excluded.weight",
            params![source, target, relation, weight],
        )?;
        Ok(())
    }

    /// Stores a list of feedback signals detected from user correction.
    pub fn store_feedback(&self, app_name: &str, signals: Vec<crate::memory::feedback::FeedbackSignal>) -> Result<()> {
        let timestamp = Utc::now().timestamp();
        let conn = self.conn.lock().unwrap();
        for s in signals {
            let id = uuid::Uuid::new_v4().to_string();
            conn.execute(
                "INSERT INTO feedback_signals (id, timestamp, app_name, channel, orig_value, new_value, confidence)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![id, timestamp, app_name, s.channel, s.from, s.to, s.confidence],
            )?;
        }
        Ok(())
    }

    /// Retrieves the feedback history for an app.
    pub fn get_feedback_history(&self, app_name: &str) -> Result<Vec<crate::memory::feedback::FeedbackSignal>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT channel, orig_value, new_value, confidence FROM feedback_signals
             WHERE app_name = ?1 ORDER BY timestamp DESC LIMIT 20"
        )?;
        let rows = stmt.query_map(params![app_name], |row| {
            Ok(crate::memory::feedback::FeedbackSignal {
                channel: row.get(0)?,
                from: row.get(1)?,
                to: row.get(2)?,
                confidence: row.get(3)?,
            })
        })?;
        let mut results = Vec::new();
        for s in rows.flatten() { results.push(s); }
        Ok(results)
    }
}
