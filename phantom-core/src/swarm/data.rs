// phantom-core/src/swarm/data.rs
use crate::document_context::{DocumentContext, DocKind};
use crate::plugin::SwarmAgent;

pub struct DataAnalystAgent;
impl SwarmAgent for DataAnalystAgent {
    fn id(&self) -> &str { "data" }
    fn name(&self) -> &str { "Data & Spreadsheet Analyst" }
    fn build_system_prompt(&self, doc_ctx: &DocumentContext) -> String {
        let base = crate::ai::KAIRO_SYSTEM_PROMPT;
        let doc_fragment = doc_ctx.to_system_prompt_fragment();
        format!(
            "{}\n\n[DOCUMENT CONTEXT]\n{}\n\n<SWARM_ROLE>\n\
            ROLE: Data & Spreadsheet Analyst\n\
            OBJECTIVE: Excel formulas, pivot tables, and data summaries.\n\
            CONSTRAINTS: Correct formula syntax (=VLOOKUP, etc.). Explain patterns clearly. Use bullet points for summaries. Describe best chart types.\n\
            </SWARM_ROLE>\n\n\
            COMMAND: Execute the user request within the defined context. START with [REPLACE] if applicable. OUTPUT ONLY THE CONTENT.",
            base, doc_fragment
        )
    }
    fn match_score(&self, doc_ctx: &DocumentContext) -> u8 {
        if matches!(doc_ctx.doc_kind, DocKind::ExcelSpreadsheet | DocKind::OpenDocumentSpreadsheet) { return 100; }
        let p = doc_ctx.prompt_text.to_lowercase();
        if p.contains("formula") || p.contains("excel") || p.contains("spreadsheet")
            || p.contains("pivot") || p.contains("vlookup") || p.contains("chart") { 75 }
        else { 0 }
    }
}
