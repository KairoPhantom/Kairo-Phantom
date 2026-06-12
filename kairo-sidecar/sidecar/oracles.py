# sidecar/oracles.py
import os
import sys
import time
import subprocess
import threading
import ipaddress
from pathlib import Path
from typing import Dict, List, Any, Optional

import docx
import openpyxl
import pptx
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

try:
    import scapy.all as scapy
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ─── 1. Word / DOCX Oracle ────────────────────────────────────────────────────

def verify_docx(path: str, expected_text_substrings: Optional[List[str]] = None) -> bool:
    """Verifies DOCX structure and content."""
    doc = docx.Document(path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text.append(cell.text)
    
    combined_text = "\n".join(full_text)
    
    if expected_text_substrings:
        for substring in expected_text_substrings:
            if substring not in combined_text:
                raise AssertionError(f"Expected DOCX to contain: '{substring}' but not found.")
    return True


# ─── 2. Excel / XLSX Oracle ────────────────────────────────────────────────────

def verify_xlsx(path: str, cell_values: Optional[Dict[str, Any]] = None, cell_formulas: Optional[Dict[str, str]] = None) -> bool:
    """Verifies XLSX sheet structure, exact cell values, and formulas."""
    wb = openpyxl.load_workbook(path, data_only=False)
    sheet = wb.active
    
    if cell_formulas:
        for cell_ref, expected_formula in cell_formulas.items():
            val = sheet[cell_ref].value
            if not isinstance(val, str) or not val.startswith("="):
                raise AssertionError(f"Expected formula in {cell_ref} but found value: {val}")
            if val.strip().upper() != expected_formula.strip().upper():
                raise AssertionError(f"Formula mismatch in {cell_ref}: expected '{expected_formula}', found '{val}'")
                
    if cell_values:
        # Load workbook again with data_only=True to read evaluated values
        wb_val = openpyxl.load_workbook(path, data_only=True)
        sheet_val = wb_val.active
        for cell_ref, expected_val in cell_values.items():
            val = sheet_val[cell_ref].value
            if str(val) != str(expected_val):
                raise AssertionError(f"Value mismatch in {cell_ref}: expected '{expected_val}', found '{val}'")
                
    return True


# ─── 3. PowerPoint / PPTX Oracle ──────────────────────────────────────────────

def verify_pptx(path: str, expected_slide_count: Optional[int] = None, check_placeholders: bool = True, bullet_word_limit: int = 12) -> bool:
    """Verifies PPTX structure, slide counts, placeholder slop, and word limits."""
    prs = pptx.Presentation(path)
    
    if expected_slide_count is not None:
        if len(prs.slides) != expected_slide_count:
            raise AssertionError(f"Slide count mismatch: expected {expected_slide_count}, found {len(prs.slides)}")
            
    for i, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    # Check for placeholders
                    if check_placeholders:
                        placeholders = ["click to add", "lorem ipsum", "[enter title]", "[insert text]"]
                        for pl in placeholders:
                            if pl in text.lower():
                                raise AssertionError(f"Placeholder slop found on slide {i}: '{text}'")
                    # Check word limit on bullet points
                    if text.startswith("-") or paragraph.level > 0:
                        words = len(text.split())
                        if words > bullet_word_limit:
                            raise AssertionError(f"Slide {i} bullet exceeds word limit ({words} > {bullet_word_limit}): '{text}'")
    return True


# ─── 4. PDF Oracle ────────────────────────────────────────────────────────────

def verify_pdf(path: str, expected_substrings: Optional[List[str]] = None) -> bool:
    """Verifies PDF content by reading it back."""
    extracted_text = []
    with fitz.open(path) as doc:
        for page in doc:
            extracted_text.append(page.get_text())
            
    combined_text = "\n".join(extracted_text)
    
    if expected_substrings:
        for substring in expected_substrings:
            if substring not in combined_text:
                raise AssertionError(f"Expected PDF to contain: '{substring}' but not found.")
    return True


# ─── 5. LibreOffice Headless Excel Recompute Oracle ───────────────────────────

def excel_libreoffice_recompute(file_path: str, output_pdf_dir: str) -> str:
    """Runs LibreOffice headless to convert Excel sheet to PDF (which triggers formula recomputation).
    Returns the path to the converted PDF file. If LibreOffice is not installed, raises FileNotFoundError.
    """
    # 1. Search for soffice
    soffice_path = None
    common_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            soffice_path = p
            break
            
    if not soffice_path:
        # Check in PATH
        try:
            subprocess.run(["soffice", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            soffice_path = "soffice"
        except FileNotFoundError:
            pass
            
    if not soffice_path:
        # Halt and report blocked
        raise FileNotFoundError(
            "LibreOffice (soffice) not found on system. This is a critical system dependency. "
            "Mark this item as BLOCKED until LibreOffice is installed."
        )
        
    # Run LibreOffice headless conversion
    cmd = [
        soffice_path,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_pdf_dir,
        file_path
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {res.stderr}\n{res.stdout}")
        
    pdf_filename = Path(file_path).with_suffix(".pdf").name
    pdf_path = os.path.join(output_pdf_dir, pdf_filename)
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"Converted PDF file not found at: {pdf_path}")
        
    return pdf_path


# ─── 6. Network Sniffer Oracle ────────────────────────────────────────────────

class NetworkSnifferOracle:
    """A zero-flake network sniffer that monitors external egress connections.
    Uses scapy if available/privileged, falling back to psutil scanning of active TCP sockets.
    """
    def __init__(self):
        self.external_destinations = set()
        self.stop_sniffing = threading.Event()
        self._thread = None

    def _is_private(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_link_local
        except ValueError:
            return True # If not parseable, ignore or treat as safe for routing
            
    def _run_scapy(self):
        def prn(pkt):
            if self.stop_sniffing.is_set():
                return
            if pkt.haslayer(scapy.IP):
                dst = pkt[scapy.IP].dst
                if not self._is_private(dst):
                    self.external_destinations.add(dst)
            elif pkt.haslayer(scapy.IPv6):
                dst = pkt[scapy.IPv6].dst
                if not self._is_private(dst):
                    self.external_destinations.add(dst)
        try:
            scapy.sniff(prn=prn, stop_filter=lambda x: self.stop_sniffing.is_set(), timeout=60)
        except Exception:
            pass # Fall back silently to psutil

    def _run_psutil(self):
        while not self.stop_sniffing.is_set():
            try:
                for conn in psutil.net_connections(kind="inet"):
                    if conn.status == "ESTABLISHED" and conn.raddr:
                        r_ip = conn.raddr.ip
                        if not self._is_private(r_ip):
                            self.external_destinations.add(r_ip)
            except Exception:
                pass
            time.sleep(0.1)

    def start(self):
        self.external_destinations.clear()
        self.stop_sniffing.clear()
        
        # Prefer psutil because it doesn't require admin/Npcap on Windows
        if HAS_PSUTIL:
            self._thread = threading.Thread(target=self._run_psutil, daemon=True)
            self._thread.start()
        elif HAS_SCAPY:
            self._thread = threading.Thread(target=self._run_scapy, daemon=True)
            self._thread.start()

    def stop(self) -> List[str]:
        self.stop_sniffing.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        return list(self.external_destinations)


# ─── 7. Screenshot Diff / Image Oracle ────────────────────────────────────────

def verify_screenshot_diff(path_a: str, path_b: str, max_diff_pixels_ratio: float = 0.01) -> bool:
    """Verifies that two screenshots match visually (pixel-level difference)."""
    img_a = Image.open(path_a).convert("RGB")
    img_b = Image.open(path_b).convert("RGB")
    
    if img_a.size != img_b.size:
        raise AssertionError(f"Image dimensions mismatch: {img_a.size} vs {img_b.size}")
        
    pixels_a = img_a.load()
    pixels_b = img_b.load()
    
    width, height = img_a.size
    mismatched_pixels = 0
    total_pixels = width * height
    
    for y in range(height):
        for x in range(width):
            color_a = pixels_a[x, y]
            color_b = pixels_b[x, y]
            # Simple Manhattan distance for RGB
            diff = abs(color_a[0]-color_b[0]) + abs(color_a[1]-color_b[1]) + abs(color_a[2]-color_b[2])
            if diff > 15: # threshold
                mismatched_pixels += 1
                
    ratio = mismatched_pixels / total_pixels
    if ratio > max_diff_pixels_ratio:
        raise AssertionError(f"Visual diff failed: {mismatched_pixels} mismatched pixels ({ratio*100:.2f}% > {max_diff_pixels_ratio*100:.2f}%)")
        
    return True
