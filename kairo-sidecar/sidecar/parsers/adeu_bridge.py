"""
Adeu Bridge — Native Track Changes for Kairo Phantom Word Specialist.
=====================================================================
Provides zero-clipboard, format-preserving edit injection into DOCX files
via the Adeu Virtual DOM (https://github.com/dealfluence/adeu).

Injection ladder (tried in order):
  1. process_active_word_batch  — live Word COM injection (Track Changes, no clipboard)
  2. process_document_batch     — file-based Track Changes via Adeu Python SDK
  3. Fallback to caller         — safe-docx or clipboard (managed by injector.rs)

All functions return dicts matching Kairo's sidecar JSON envelope:
  {"ok": bool, "data": {...}, "error": str | None}
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import traceback
from io import BytesIO
from pathlib import Path
from typing import Any

log = logging.getLogger("kairo-sidecar.adeu_bridge")


# ---------------------------------------------------------------------------
# Capability detection (safe — never raises)
# ---------------------------------------------------------------------------

def _adeu_installed() -> bool:
    """True if the `adeu` CLI is available in PATH."""
    return shutil.which("adeu") is not None


def _adeu_sdk_available() -> bool:
    """True if the adeu Python package is importable."""
    try:
        import adeu  # noqa: F401
        return True
    except ImportError:
        return False


def _word_is_open_with_file(file_path: str) -> bool:
    """
    Windows-only: check if WINWORD.EXE has the file open.
    Returns False on non-Windows or any error — fail-safe.
    """
    try:
        import sys
        if sys.platform != "win32":
            return False
        import win32com.client  # type: ignore
        word = win32com.client.GetActiveObject("Word.Application")
        for doc in word.Documents:
            if Path(doc.FullName).resolve() == Path(file_path).resolve():
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def adeu_read_document(file_path: str) -> dict:
    """
    Extract document text + paragraph structure via `adeu extract`.

    Returns:
        {
            "ok": True,
            "data": {
                "full_text": str,          # CriticMarkup markdown
                "paragraphs": [...],       # indexed paragraph list
                "format": "criticmarkup",
            }
        }
    """
    if not _adeu_installed():
        return _unavailable("adeu CLI not installed — run: pip install adeu")

    file_path = str(Path(file_path).resolve())
    if not Path(file_path).exists():
        return _error(f"File not found: {file_path}")

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".md")
    os.close(tmp_fd)
    try:
        result = subprocess.run(
            ["adeu", "extract", file_path, "-o", tmp_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        with open(tmp_path, "r", encoding="utf-8") as f:
            markdown = f.read()

        paragraphs = _parse_markdown_to_paragraphs(markdown)
        log.info(
            "adeu_read_document OK: %d chars, %d paragraphs from %s",
            len(markdown), len(paragraphs), file_path,
        )
        return {
            "ok": True,
            "data": {
                "full_text": markdown,
                "paragraphs": paragraphs,
                "format": "criticmarkup",
                "file_path": file_path,
            },
        }
    except subprocess.TimeoutExpired:
        return _error("adeu extract timed out after 30 s")
    except subprocess.CalledProcessError as e:
        return _error(f"adeu extract failed (exit {e.returncode}): {e.stderr[:500]}")
    except Exception:
        return _error(traceback.format_exc())
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def adeu_apply_edits(
    file_path: str,
    edits: list[dict],
    output_path: str | None = None,
    author: str = "Kairo AI",
) -> dict:
    """
    Apply a list of text edits as native DOCX Track Changes (w:ins/w:del).

    `edits` is a list of dicts with keys:
        target_text  (str, required) — exact text to find and replace
        new_text     (str, required) — replacement text
        comment      (str, optional) — comment/rationale for the change

    Returns the path of the saved redlined file.
    """
    file_path = str(Path(file_path).resolve())
    if not Path(file_path).exists():
        return _error(f"File not found: {file_path}")
    if not edits:
        return _error("edits list is empty — nothing to apply")

    # --- Strategy 1: Live Word COM injection (best quality)
    if _word_is_open_with_file(file_path):
        live_result = _adeu_live_apply(file_path, edits, author)
        if live_result["ok"]:
            return live_result
        log.warning("Live COM injection failed, falling back to SDK: %s", live_result.get("error"))

    # --- Strategy 2: Python SDK file-based injection
    if _adeu_sdk_available():
        return _adeu_sdk_apply(file_path, edits, output_path, author)

    # --- Strategy 3: CLI-based fallback (adeu apply)
    if _adeu_installed():
        return _adeu_cli_apply(file_path, edits, output_path, author)

    return _unavailable(
        "Adeu is not installed. Run: pip install adeu\n"
        "Then restart the Kairo sidecar."
    )


def adeu_read_live_document() -> dict:
    """
    Read the currently active Word document via Adeu's COM bridge.
    Windows only; requires `adeu read-active` CLI command.
    """
    if not _adeu_installed():
        return _unavailable("adeu CLI not installed")
    try:
        result = subprocess.run(
            ["adeu", "read-active"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return _error(f"adeu read-active failed: {result.stderr[:400]}")
        data = json.loads(result.stdout)
        return {"ok": True, "data": data}
    except subprocess.TimeoutExpired:
        return _error("adeu read-active timed out")
    except json.JSONDecodeError:
        return _error("adeu read-active returned invalid JSON")
    except Exception:
        return _error(traceback.format_exc())


def adeu_sanitize(file_path: str, output_path: str | None = None) -> dict:
    """
    Strip dangerous metadata from DOCX before sharing (adeu sanitize).
    Removes author names, comments history, revision tracking metadata.
    """
    file_path = str(Path(file_path).resolve())
    if not Path(file_path).exists():
        return _error(f"File not found: {file_path}")
    if not _adeu_installed():
        return _unavailable("adeu CLI not installed")

    if output_path is None:
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_sanitized{ext}"

    try:
        subprocess.run(
            ["adeu", "sanitize", file_path, "-o", output_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        log.info("adeu_sanitize OK: %s → %s", file_path, output_path)
        return {"ok": True, "data": {"output_path": output_path}}
    except subprocess.CalledProcessError as e:
        return _error(f"adeu sanitize failed: {e.stderr[:400]}")
    except subprocess.TimeoutExpired:
        return _error("adeu sanitize timed out")
    except Exception:
        return _error(traceback.format_exc())


# ---------------------------------------------------------------------------
# Internal strategies
# ---------------------------------------------------------------------------

def _adeu_sdk_apply(
    file_path: str,
    edits: list[dict],
    output_path: str | None,
    author: str,
) -> dict:
    """File-based Track Changes via adeu Python SDK (no COM, works headless)."""
    try:
        from adeu import RedlineEngine, ModifyText  # type: ignore

        if output_path is None:
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_redlined{ext}"

        with open(file_path, "rb") as f:
            stream = BytesIO(f.read())

        engine = RedlineEngine(stream, author=author)

        modify_ops = []
        for edit in edits:
            target = edit.get("target_text", "").strip()
            new = edit.get("new_text", "").strip()
            comment = edit.get("comment", "") or ""
            if not target or not new:
                log.warning("Skipping edit with empty target_text or new_text: %r", edit)
                continue
            modify_ops.append(
                ModifyText(target_text=target, new_text=new, comment=comment or None)
            )

        if not modify_ops:
            return _error("All edits were invalid (empty target_text or new_text)")

        # Pre-validate to surface missing-text errors before applying
        validation_errors = engine.validate_edits(modify_ops)
        if validation_errors:
            log.warning(
                "adeu validate_edits found %d issues: %s",
                len(validation_errors), validation_errors[:3]
            )
            # Non-fatal: apply anyway (engine skips unresolvable edits gracefully)

        # apply_edits returns (applied_count, skipped_count)
        applied_count, skipped_count = engine.apply_edits(modify_ops)

        with open(output_path, "wb") as f:
            f.write(engine.save_to_stream().getvalue())

        log.info(
            "adeu_sdk_apply OK: %d applied, %d skipped → %s",
            applied_count, skipped_count, output_path
        )
        return {
            "ok": True,
            "data": {
                "output_path": output_path,
                "applied_count": applied_count,
                "skipped_count": skipped_count,
                "validation_warnings": validation_errors[:5] if validation_errors else [],
                "backend": "adeu_sdk",
            },
        }
    except ImportError:
        return _unavailable("adeu Python SDK import failed (pip install adeu)")
    except Exception:
        return _error(traceback.format_exc())


def _adeu_cli_apply(
    file_path: str,
    edits: list[dict],
    output_path: str | None,
    author: str,
) -> dict:
    """CLI-based fallback using `adeu apply` subcommand."""
    if output_path is None:
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_redlined{ext}"

    # Write edits to a temp JSON file
    tmp_fd, tmp_json = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    try:
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(edits, f)

        subprocess.run(
            [
                "adeu", "apply", file_path,
                "--edits", tmp_json,
                "--author", author,
                "-o", output_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        log.info("adeu_cli_apply OK: %d edits → %s", len(edits), output_path)
        return {
            "ok": True,
            "data": {
                "output_path": output_path,
                "applied_count": len(edits),
                "backend": "adeu_cli",
            },
        }
    except subprocess.CalledProcessError as e:
        return _error(f"adeu apply failed: {e.stderr[:500]}")
    except subprocess.TimeoutExpired:
        return _error("adeu apply CLI timed out after 30 s")
    except Exception:
        return _error(traceback.format_exc())
    finally:
        try:
            os.unlink(tmp_json)
        except OSError:
            pass


def _adeu_live_apply(
    file_path: str,
    edits: list[dict],
    author: str,
) -> dict:
    """
    Live COM-macro injection via `adeu process-active`.
    Only called when Word has the file open.
    """
    tmp_fd, tmp_json = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    try:
        with open(tmp_json, "w", encoding="utf-8") as f:
            json.dump(edits, f)

        result = subprocess.run(
            [
                "adeu", "process-active",
                "--edits", tmp_json,
                "--author", author,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            return _error(f"adeu process-active failed: {result.stderr[:400]}")

        log.info("adeu_live_apply OK: %d edits injected via COM", len(edits))
        return {
            "ok": True,
            "data": {
                "applied_count": len(edits),
                "backend": "adeu_live_com",
            },
        }
    except subprocess.TimeoutExpired:
        return _error("adeu process-active timed out")
    except Exception:
        return _error(traceback.format_exc())
    finally:
        try:
            os.unlink(tmp_json)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_markdown_to_paragraphs(markdown: str) -> list[dict]:
    """
    Split CriticMarkup-flavoured markdown into indexed paragraph blocks.
    Each block gets an `is_heading` flag, `level`, and `is_table` flag.
    """
    paragraphs: list[dict] = []
    for i, block in enumerate(markdown.split("\n\n")):
        stripped = block.strip()
        if not stripped:
            continue
        level = 0
        if stripped.startswith("# "):
            level = 1
        elif stripped.startswith("## "):
            level = 2
        elif stripped.startswith("### "):
            level = 3
        elif stripped.startswith("#### "):
            level = 4
        paragraphs.append(
            {
                "index": i,
                "text": stripped,
                "level": level,
                "is_heading": level > 0,
                "is_table": ("|" in stripped and stripped.startswith("|")),
            }
        )
    return paragraphs


def _error(msg: str) -> dict:
    log.error("AdeuBridge error: %s", msg)
    return {"ok": False, "data": None, "error": msg}


def _unavailable(msg: str) -> dict:
    log.warning("AdeuBridge unavailable: %s", msg)
    return {"ok": False, "data": None, "error": msg, "unavailable": True}
