import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Enforce clean package imports
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from sidecar.ipc import start_named_pipe_server
from sidecar.parsers.docx_parser import parse_docx
from sidecar.parsers.xlsx_parser import parse_xlsx
from sidecar.parsers.pptx_parser import parse_pptx
from sidecar.parsers.context_extractor import extract_context
from sidecar.writers.docx_writer import write_docx
from sidecar.writers.xlsx_writer import write_xlsx
from sidecar.writers.pptx_writer import write_pptx
from sidecar.embeddings import embed_text, embed_texts
from sidecar.schemas.docx_schema import DocxResponse
from sidecar.schemas.prompt_builder import build_docx_prompt
from sidecar.llm_caller import call_with_schema
from sidecar.exporters.quarkdown_compiler import compile_quarkdown
from sidecar.exporters.kami_handlers import KamiCommandHandler

# ─── Domain 1: Word / DOCX Native Track Changes ───────────────────────────────
from sidecar.parsers.adeu_bridge import (
    adeu_read_document,
    adeu_apply_edits,
    adeu_read_live_document,
    adeu_sanitize,
)
from sidecar.parsers.safedocx_bridge import (
    safedocx_read_file,
    safedocx_grep_and_replace,
    safedocx_batch_edits,
)
from sidecar.parsers.legal_redline import (
    analyze_contract,
    detect_cuad_clauses,
    generate_redlines_for_clause,
    generate_contract_summary,
)

# ─── Domain 2: Excel / Spreadsheet ───────────────────────────────────────────
from sidecar.parsers.excelmcp_bridge import (
    get_workbook_blueprint as bridge_get_workbook_blueprint,
    excelmcp_read_range,
    excelmcp_write_range,
    excelmcp_write_cell,
    excelmcp_fill_formula,
    excelmcp_create_chart,
    excelmcp_create_pivot_table,
    excelmcp_screenshot_range,
)
from sidecar.parsers.forge_bridge import (
    validate_formula,
    explain_formula,
    validate_formula_batch,
)
from sidecar.parsers.excel_context import (
    ExcelContextCapture,
    get_workbook_overview,
    get_active_cell_context,
    format_excel_context_for_prompt,
)
from sidecar.parsers.xlsx_parser import write_xlsx_with_formatting

# ─── Domain 3: PowerPoint / Presentations ─────────────────────────────────────
from sidecar.parsers.pptx_mcp_bridge import PptxMcpBridge
from sidecar.parsers.pptx_context import PptxContextCapture
from sidecar.parsers.deeppresenter_bridge import DeepPresenterBridge
from sidecar.parsers.slide_image_gen import SlideImageGenerator, ImageBackend

# ─── Domain 4: PDF Extraction & AI-Ready Data ─────────────────────────────────
from sidecar.parsers.pdf_extraction_engine import PdfExtractionEngine
from sidecar.exporters.kami_pdf_exporter import KamiPdfExporter


# ─── Logging ─────────────────────────────────────────────────────────────────
log_path = Path.home() / ".kairo-phantom" / "sidecar.log"
log_path.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIDECAR] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("kairo-sidecar.main")

async def handle_request(req: dict) -> dict:
    req_id = req.get("id", "unknown")
    action = req.get("action", "")
    path = req.get("path", "")
    payload = req.get("payload", {})

    log.info(f"Request [{req_id}] action={action} path={path}")

    try:
        if action == "ping":
            return {"id": req_id, "ok": True, "data": {"pong": True, "version": "1.2.0"}}

        elif action == "read_docx":
            data = parse_docx(path)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "write_docx":
            ops = payload.get("operations", [])
            data = write_docx(path, ops)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "read_xlsx":
            active_cell = payload.get("active_cell")
            data = parse_xlsx(path, active_cell)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "write_xlsx":
            ops = payload.get("operations", [])
            data = write_xlsx(path, ops)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "read_pptx":
            data = parse_pptx(path)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "write_pptx":
            ops = payload.get("operations", [])
            data = write_pptx(path, ops)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "extract_context":
            active_cell = payload.get("active_cell")
            data = extract_context(path, active_cell)
            return {"id": req_id, "ok": "error" not in data, "data": data}

        elif action == "embed_text":
            text = payload.get("text", "")
            vector = embed_text(text)
            return {"id": req_id, "ok": True, "data": {"vector": vector}}

        elif action == "embed_texts":
            texts = payload.get("texts", [])
            vectors = embed_texts(texts)
            return {"id": req_id, "ok": True, "data": {"vectors": vectors}}

        elif action == "llm_structured_docx":
            user_instruction = payload.get("user_instruction", "")
            mem_context = payload.get("mem_context", "")
            document_context = payload.get("document_context")
            if not document_context and path:
                document_context = parse_docx(path)
            
            prompt = build_docx_prompt(user_instruction, document_context, mem_context)
            model_name = payload.get("model", "ollama/qwen2.5:7b")
            
            # Execute LLM Structured Output with validation & self-correcting retries
            validated_response = call_with_schema(prompt, DocxResponse, model=model_name)
            
            return {
                "id": req_id,
                "ok": True,
                "data": validated_response.model_dump()
            }

        elif action == "compile_quarkdown":
            content = payload.get("content", "")
            output_format = payload.get("format", "revealjs")
            output_path = payload.get("output_path", "")
            success = compile_quarkdown(content, output_format, output_path)
            return {"id": req_id, "ok": success, "data": {"success": success, "output_path": output_path}}

        # ─── Domain 1: Word / DOCX Native Track Changes ───────────────────────

        elif action == "adeu_read":
            # Read DOCX via Adeu → returns CriticMarkup markdown + paragraph index
            result = adeu_read_document(path)
            return {"id": req_id, **result}

        elif action == "adeu_apply_edits":
            # Apply Track Changes edits via Adeu (live COM or file-based)
            edits = payload.get("edits", [])
            output_path_out = payload.get("output_path") or None
            author = payload.get("author", "Kairo AI")
            result = adeu_apply_edits(path, edits, output_path=output_path_out, author=author)
            return {"id": req_id, **result}

        elif action == "adeu_read_live":
            # Read whatever DOCX is currently open in Word (no path needed)
            result = adeu_read_live_document()
            return {"id": req_id, **result}

        elif action == "adeu_sanitize":
            # Strip metadata from DOCX (author names, revision history)
            output_path_out = payload.get("output_path") or None
            result = adeu_sanitize(path, output_path=output_path_out)
            return {"id": req_id, **result}

        elif action == "safedocx_read":
            # Read DOCX via safe-docx (returns stable _bk_NNN paragraph IDs)
            result = safedocx_read_file(path)
            return {"id": req_id, **result}

        elif action == "safedocx_edit":
            # Surgical paragraph replacement via safe-docx
            edits = payload.get("edits", [])
            clean_out = payload.get("clean_output_path") or None
            tracked_out = payload.get("tracked_output_path") or None
            result = safedocx_batch_edits(path, edits, clean_out, tracked_out)
            return {"id": req_id, **result}

        elif action == "analyze_contract":
            # Full contract review: CUAD detection + redlines + summary
            # Accepts file path OR raw text via payload
            document_text = payload.get("document_text", "")
            if not document_text and path:
                doc_data = parse_docx(path)
                document_text = doc_data.get("full_text", "")
                if not document_text:
                    # Reconstruct from paragraphs
                    paragraphs = doc_data.get("paragraphs", [])
                    document_text = "\n\n".join(p.get("text", "") for p in paragraphs)
            else:
                paragraphs = None
            result = analyze_contract(document_text, paragraphs=paragraphs)
            return {"id": req_id, **result}

        elif action == "detect_clauses":
            # CUAD-only clause detection (lightweight, no redlines)
            document_text = payload.get("document_text", "")
            if not document_text and path:
                doc_data = parse_docx(path)
                paragraphs = doc_data.get("paragraphs", [])
                document_text = "\n\n".join(p.get("text", "") for p in paragraphs)
            else:
                paragraphs = None
            result = detect_cuad_clauses(document_text, paragraphs)
            return {"id": req_id, **result}

        elif action == "generate_redline":
            # Generate AI redline for a single clause text
            clause_text = payload.get("clause_text", "")
            clause_id = payload.get("clause_id", "")
            stance = payload.get("negotiation_stance", "balanced")
            party = payload.get("party", "client")
            result = generate_redlines_for_clause(clause_text, clause_id, stance, party)
            return {"id": req_id, **result}

        # ─── Domain 2: Excel / Spreadsheet Actions ───────────────────────────

        elif action == "get_workbook_blueprint":
            res = bridge_get_workbook_blueprint(path)
            return {"id": req_id, **res}

        elif action == "validate_formula":
            formula = payload.get("formula", "")
            context = payload.get("context")
            res = validate_formula(formula, context)
            return {"id": req_id, "ok": True, "data": res}

        elif action == "explain_formula":
            formula = payload.get("formula", "")
            explanation = explain_formula(formula)
            return {"id": req_id, "ok": True, "data": {"explanation": explanation}}

        elif action == "write_xlsx_formatted":
            ops = payload.get("operations", [])
            res = write_xlsx_with_formatting(path, ops)
            return {"id": req_id, **res}

        elif action == "excelmcp_create_chart":
            source_range = payload.get("source_range", "")
            chart_type = payload.get("chart_type", "column")
            title = payload.get("title", "Chart")
            target_sheet = payload.get("target_sheet") or None
            res = excelmcp_create_chart(path, source_range, chart_type, title, target_sheet)
            return {"id": req_id, **res}

        elif action == "excelmcp_create_pivot":
            source_range = payload.get("source_range", "")
            rows = payload.get("rows", [])
            columns = payload.get("columns", [])
            values = payload.get("values", [])
            target_sheet = payload.get("target_sheet") or None
            res = excelmcp_create_pivot_table(path, source_range, rows, columns, values, target_sheet)
            return {"id": req_id, **res}

        elif action == "excel_smart_context":
            active_cell = payload.get("active_cell")
            capture = ExcelContextCapture()
            ctx = capture.capture(path, active_cell)
            return {"id": req_id, "ok": True, "data": ctx}

        elif action == "excelmcp_fill_formula":
            formula = payload.get("formula", "")
            fill_range = payload.get("fill_range", "")
            res = excelmcp_fill_formula(path, formula, fill_range)
            return {"id": req_id, **res}

        # ─── Domain 3: PowerPoint / Presentations Actions ─────────────────────

        elif action == "pptx_context_capture":
            pres_id = payload.get("presentation_id", path)
            slide_idx = payload.get("slide_index")
            capture = PptxContextCapture()
            ctx = capture.capture(pres_id, slide_idx)
            system_fragment = capture.to_system_prompt_fragment(ctx)
            return {"id": req_id, "ok": True, "data": {"context": ctx, "system_prompt_fragment": system_fragment}}

        elif action == "deeppresenter_generate":
            topic = payload.get("topic", "")
            slide_count = payload.get("slide_count", 5)
            style = payload.get("style", "professional")
            audience = payload.get("audience", "general")
            output_dir = payload.get("output_dir") or None
            outline = payload.get("outline") or None
            
            bridge = DeepPresenterBridge()
            if outline:
                res = bridge.generate_from_outline(outline, style=style, output_dir=output_dir)
            else:
                res = bridge.generate_presentation(topic, slide_count=slide_count, style=style, audience=audience, output_dir=output_dir)
            return {"id": req_id, "ok": "pptx_path" in res, "data": res}

        elif action == "slide_image_generate":
            slide_content = payload.get("slide_content")
            slide_contents = payload.get("slide_contents")
            backend_str = payload.get("backend")
            style = payload.get("style", "professional")
            
            backend = None
            if backend_str:
                try:
                    backend = ImageBackend(backend_str.lower())
                except ValueError:
                    pass
            
            generator = SlideImageGenerator()
            if slide_contents:
                paths = generator.generate_deck_images(slide_contents, backend=backend, style=style)
                return {"id": req_id, "ok": True, "data": {"image_paths": paths}}
            elif slide_content:
                path_out = generator.generate_slide_image(slide_content, backend=backend, style=style)
                return {"id": req_id, "ok": True, "data": {"image_path": path_out}}
            else:
                return {"id": req_id, "ok": False, "error": "Missing slide_content or slide_contents"}

        # ─── Domain 4: PDF Extraction & AI-Ready Data ───────────────────────

        elif action == "pdf_extract":
            # Multi-tier PDF extraction: PyMuPDF → OpenDataLoader → olmOCR → Surya
            engine = PdfExtractionEngine(offline_mode=True)
            result = engine.extract(path)
            return {
                "id": req_id,
                "ok": True,
                "data": {
                    "text": result.text,
                    "markdown": result.markdown,
                    "tables": result.tables,
                    "images": result.images,
                    "headings": result.headings,
                    "metadata": result.metadata,
                    "tier_used": result.tier_used.name if result.tier_used else None,
                    "extraction_time_ms": result.extraction_time_ms,
                    "confidence": result.confidence,
                    "language": result.language,
                }
            }

        elif action == "pdf_kami_export":
            # Export Markdown content to a professionally typeset PDF
            content = payload.get("content", "")
            theme = payload.get("theme", "github-light")
            title = payload.get("title", "Kairo Export")
            author = payload.get("author", "Kairo Phantom")
            subtitle = payload.get("subtitle", "")
            output_path = payload.get("output_path", "")
            if not output_path:
                import datetime, os
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(
                    os.path.expanduser("~"), "Documents", "Kairo Exports",
                    f"kairo-export-{ts}.pdf"
                )
            exporter = KamiPdfExporter()
            try:
                written_path = exporter.export(
                    markdown_content=content,
                    output_path=output_path,
                    theme=theme,
                    title=title,
                    author=author,
                    subtitle=subtitle,
                )
                return {
                    "id": req_id,
                    "ok": True,
                    "data": {"success": True, "output_path": written_path, "theme_used": theme}
                }
            except Exception as e:
                return {
                    "id": req_id,
                    "ok": True,
                    "data": {"success": False, "output_path": "", "theme_used": theme, "error": str(e)}
                }

        elif action == "kami_export":
            command = payload.get("command", "")
            args = payload.get("args", {})
            content = payload.get("content", "")
            metadata = payload.get("metadata", {})
            
            arg_str = ""
            for k, v in args.items():
                if v == "true" or v is True:
                    arg_str += f" --{k}"
                else:
                    arg_str += f" --{k} {v}"
            
            full_command = f"// kami {command}{arg_str}"
            handler = KamiCommandHandler()
            res = handler.handle(full_command, content, metadata)
            return {"id": req_id, "ok": res.get("ok", True), "data": res}

        elif action == "pdf_extract_table":
            # Extract a specific table from a PDF page
            engine = PdfExtractionEngine(offline_mode=True)
            result = engine.extract(path)
            page_num = payload.get("page", 1)
            table_index = payload.get("table_index", 0)
            page_tables = [t for t in result.tables if t.get("page") == page_num]
            if table_index < len(page_tables):
                table = page_tables[table_index]
            elif result.tables:
                table = result.tables[0]
            else:
                table = {"headers": [], "rows": [], "page": page_num, "caption": ""}
            return {"id": req_id, "ok": True, "data": table}

        elif action == "pdf_summarize":
            # Extract text from PDF and return a concise summary payload for LLM
            engine = PdfExtractionEngine(offline_mode=True)
            result = engine.extract(path)
            # Return text + headings outline for LLM prompt building
            outline = "\n".join(
                f"{'  ' * (h.get('level', 1) - 1)}{h.get('text', '')} (p.{h.get('page', 0)})"
                for h in result.headings[:20]
            )
            return {
                "id": req_id,
                "ok": True,
                "data": {
                    "text": result.text[:8000],  # first 8k chars for LLM
                    "markdown": result.markdown[:8000],
                    "outline": outline,
                    "table_count": len(result.tables),
                    "page_count": result.metadata.get("pages", 0),
                    "language": result.language,
                    "confidence": result.confidence,
                }
            }

        # ─── Domain 5: Design & Figma Actions ───────────────────────────────
        elif action == "figma_create":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            node_type = payload.get("node_type", "FRAME").upper()
            name = payload.get("name", "Unnamed Node")
            x = payload.get("x", 0)
            y = payload.get("y", 0)
            width = payload.get("width", 100)
            height = payload.get("height", 100)
            parent_id = payload.get("parent_id", "canvas-root")
            characters = payload.get("characters", "")
            fontSize = payload.get("fontSize", 14)
            color_hex = payload.get("color_hex")
            layout_mode = payload.get("layout_mode")
            spacing = payload.get("spacing", 10)
            padding_tb = payload.get("padding_tb", 0)
            padding_lr = payload.get("padding_lr", 0)

            res = {}
            if node_type == "FRAME":
                res = bridge.figma.create_frame(name, x, y, width, height, parent_id)
            elif node_type == "TEXT":
                res = bridge.figma.create_text_node(name, characters, fontSize, parent_id)
            elif node_type == "RECTANGLE":
                res = bridge.figma.create_rectangle(name, x, y, width, height, parent_id)
            elif node_type == "COMPONENT":
                res = bridge.figma.create_component(name, parent_id)
            elif node_type == "SECTION":
                res = bridge.figma.create_section(name, parent_id)
            else:
                res = {"ok": False, "error": f"Unsupported node type: {node_type}"}

            if res.get("ok") and color_hex:
                bridge.figma.set_fills(res["node_id"], color_hex)
            if res.get("ok") and layout_mode and node_type in ("FRAME", "COMPONENT"):
                bridge.figma.set_auto_layout(res["node_id"], layout_mode, spacing, padding_tb, padding_lr)

            return {"id": req_id, "ok": res.get("ok", False), "data": res}

        elif action == "design_ghost_write":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            window_title = payload.get("window_title", "")
            tool = bridge.detect_active_design_tool(window_title)
            
            res = {"tool_detected": tool}
            if tool == "figma":
                # Create a sample text node to represent ghost design action
                node = bridge.figma.create_text_node("Ghost Written Element", "Generated via Kairo Swarm", 16)
                res.update(node)
            elif tool == "penpot":
                svg = payload.get("svg", "<svg><rect width='100' height='100' fill='#6140f0'/></svg>")
                penpot_res = bridge.penpot.draw_svg(svg)
                res.update(penpot_res)
            elif tool == "tldraw":
                shapes = payload.get("shapes", [{"type": "geo", "x": 100, "y": 100, "props": {"w": 100, "h": 50, "text": "Ghost"}}])
                created = []
                for s in shapes:
                    s_type = s.get("type", "geo")
                    s_x = s.get("x", 0.0)
                    s_y = s.get("y", 0.0)
                    s_props = s.get("props", {})
                    created.append(bridge.tldraw.create_shape(s_type, s_x, s_y, s_props))
                res["created_shapes"] = created
            elif tool == "openpencil":
                stroke = payload.get("stroke", {"points": [(0,0), (10,10)]})
                op_res = bridge.openpencil.record_stroke(stroke)
                res.update(op_res)
            elif tool == "frameground":
                filename = payload.get("filename", "frameground_canvas.html")
                html = payload.get("html", "<div>Frameground</div>")
                path_out = bridge.frameground.create_canvas(filename, html)
                res["canvas_path"] = path_out
            else:
                res["error"] = "No active design tool matched window title."
                res["ok"] = False
                return {"id": req_id, "ok": False, "data": res}
            
            res["ok"] = True
            return {"id": req_id, "ok": True, "data": res}

        elif action == "generate_design_asset":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            prompt = payload.get("prompt", "")
            style = payload.get("style", "default")
            output_path = payload.get("output_path")
            res = bridge.comfyui.generate_asset(prompt, style, output_path)
            return {"id": req_id, "ok": res.get("ok", False), "data": res}

        elif action == "tldraw_canvas":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            operation = payload.get("operation", "get_shapes")
            
            if operation == "create_shape":
                shape_type = payload.get("shape_type", "geo")
                x = payload.get("x", 0.0)
                y = payload.get("y", 0.0)
                props = payload.get("props", {})
                res = bridge.tldraw.create_shape(shape_type, x, y, props)
            elif operation == "update_shape":
                shape_id = payload.get("shape_id", "")
                x = payload.get("x")
                y = payload.get("y")
                props = payload.get("props")
                res = bridge.tldraw.update_shape(shape_id, x, y, props)
            elif operation == "delete_shape":
                shape_id = payload.get("shape_id", "")
                res = bridge.tldraw.delete_shape(shape_id)
            elif operation == "draw_flowchart":
                nodes = payload.get("nodes", [])
                edges = payload.get("edges", [])
                res = bridge.tldraw.draw_flowchart(nodes, edges)
            else:
                res = {"shapes": bridge.tldraw.get_canvas_shapes(), "ok": True}
                
            return {"id": req_id, "ok": res.get("ok", True), "data": res}

        elif action == "extract_design_code":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            root_id = payload.get("root_id", "canvas-root")
            html = bridge.transpile_figma_to_tailwind(root_id)
            return {"id": req_id, "ok": True, "data": {"html": html}}

        elif action == "learn_design_preference":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            tool = payload.get("tool", "default")
            key = payload.get("key", "")
            value = payload.get("value")
            bridge.memory.learn_preference(tool, key, value)
            return {"id": req_id, "ok": True}

        elif action == "get_design_preference":
            from sidecar.parsers.design_bridge import UnifiedDesignBridge
            bridge = UnifiedDesignBridge(offline_mode=True)
            tool = payload.get("tool", "default")
            key = payload.get("key", "")
            fallback = payload.get("fallback")
            val = bridge.memory.get_preference(tool, key, fallback)
            return {"id": req_id, "ok": True, "data": val}

        # ─── Domain 8: Multimodal Input (Voice + Screen Context) ─────────────
        elif action == "voice_process":
            # Post-process voice transcription from whisper.cpp
            from sidecar.voice_bridge import VoiceBridge
            bridge = VoiceBridge()
            transcription = payload.get("transcription", "")
            app_context = payload.get("app_context", {})
            result = await bridge.post_process_transcription(transcription, app_context)
            return {"id": req_id, "ok": True, "data": result}

        elif action == "voice_format":
            # Format voice transcription as a Kairo prompt
            from sidecar.voice_bridge import VoiceBridge
            bridge = VoiceBridge()
            transcription = payload.get("transcription", "")
            mode = payload.get("mode", "ghost_write")
            result = await bridge.format_voice_prompt(transcription, mode)
            return {"id": req_id, "ok": True, "data": result}

        elif action == "screen_extract":
            # Extract structured context from a screenshot
            from sidecar.screen_context_bridge import ScreenContextBridge
            bridge = ScreenContextBridge()
            image_path = payload.get("image_path", "")
            app_context = payload.get("app_context", {})
            result = await bridge.extract_context(image_path, app_context)
            return {"id": req_id, "ok": result.get("success", False), "data": result}

        # ─── Domain 8 Extended: Moonshine Voice Actions ─────────────────────

        elif action == "moonshine_transcribe":
            # Transcribe WAV file via Moonshine Voice (primary ASR)
            # Falls back automatically to whisper.cpp on failure/low-confidence
            wav_path = payload.get("wav_path", "")
            moonshine_url = payload.get("moonshine_url", "http://localhost:7439")
            confidence_threshold = float(payload.get("confidence_threshold", 0.6))
            whisper_model = payload.get("whisper_model", "base.en")
            whisper_language = payload.get("whisper_language", "en")

            from sidecar.voice_bridge import transcribe_with_moonshine_or_fallback
            result = await transcribe_with_moonshine_or_fallback(
                wav_path,
                confidence_threshold=confidence_threshold,
                moonshine_url=moonshine_url,
                whisper_model=whisper_model,
                whisper_language=whisper_language,
            )
            return {"id": req_id, "ok": True, "data": result}

        elif action == "moonshine_health":
            # Check Moonshine Voice service health
            moonshine_url = payload.get("moonshine_url", "http://localhost:7439")
            from sidecar.voice_bridge import MoonshineClient
            client = MoonshineClient(moonshine_url)
            available = client.is_available()
            languages = client.get_supported_languages() if available else ["en"]
            return {
                "id": req_id,
                "ok": True,
                "data": {
                    "available": available,
                    "url": moonshine_url,
                    "supported_languages": languages,
                },
            }

        elif action == "tts_speak":
            # Speak text via sherpa-onnx TTS (with SAPI/espeak fallback)
            text = payload.get("text", "")
            voice = payload.get("voice", "en_US-amy-medium")
            if not text.strip():
                return {"id": req_id, "ok": True, "data": {"skipped": True, "reason": "empty_text"}}

            from sidecar.speech.tts_service import TtsService
            svc = TtsService()
            success = svc.speak(text, voice=voice)
            return {"id": req_id, "ok": success, "data": {"spoken": text, "engine": svc.active_engine}}

        else:
            return {"id": req_id, "ok": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        log.error(f"Handler error for [{req_id}]: {e}\n{traceback.format_exc()}")
        return {"id": req_id, "ok": False, "error": str(e), "traceback": traceback.format_exc()}


async def main():
    pipe_name = r"\\.\pipe\kairo_sidecar"
    log.info("Kairo Phantom Named Pipe Sidecar booting up...")
    
    # Proactively start background LiteLLM proxy gateway
    try:
        from sidecar.start_litellm import main as start_litellm_main
        start_litellm_main()
    except Exception as e:
        log.warning(f"Could not start LiteLLM gateway automatically: {e}")
        
    try:
        server = await start_named_pipe_server(pipe_name, handle_request)
        log.info(f"✅ Named Pipe server successfully bound and listening at: {pipe_name}")
        
        while True:
            await asyncio.sleep(3600)
    except OSError as e:
        log.error(f"❌ Failed to bind Named Pipe: {e}. Check if another instance is already running.")
        sys.exit(1)
    except Exception as e:
        log.error(f"❌ Unhandled sidecar crash: {e}\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        # Explicitly set Proactor event loop for Windows Named Pipe support
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
