# tests/test_oracles.py
import os
import pytest
from PIL import Image

import docx
import openpyxl
import pptx
import fitz

from sidecar.oracles import (
    verify_docx,
    verify_xlsx,
    verify_pptx,
    verify_pdf,
    excel_libreoffice_recompute,
    NetworkSnifferOracle,
    verify_screenshot_diff
)

@pytest.fixture
def temp_dir(tmpdir):
    return str(tmpdir)

def test_verify_docx(temp_dir):
    docx_path = os.path.join(temp_dir, "test.docx")
    doc = docx.Document()
    doc.add_heading("Performance Metrics", level=2)
    doc.add_paragraph("Kairo CUA latency is under 2ms.")
    doc.save(docx_path)
    
    # Verification should pass
    assert verify_docx(docx_path, ["Performance Metrics", "latency is under 2ms"])
    
    # Verification should raise AssertionError for missing text
    with pytest.raises(AssertionError) as excinfo:
        verify_docx(docx_path, ["Nonexistent Text"])
    assert "not found" in str(excinfo.value)

def test_verify_xlsx(temp_dir):
    xlsx_path = os.path.join(temp_dir, "test.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = 10
    ws["A2"] = 20
    ws["A3"] = "=SUM(A1:A2)"
    wb.save(xlsx_path)
    
    # Verification should pass for formula match
    assert verify_xlsx(xlsx_path, cell_formulas={"A3": "=SUM(A1:A2)"})
    
    # Verification should fail for wrong formula
    with pytest.raises(AssertionError):
        verify_xlsx(xlsx_path, cell_formulas={"A3": "=SUM(A1:A3)"})
        
    # Verification should match evaluated values (openpyxl load fallback writes values)
    assert verify_xlsx(xlsx_path, cell_values={"A1": 10, "A2": 20})

def test_verify_pptx(temp_dir):
    pptx_path = os.path.join(temp_dir, "test.pptx")
    prs = pptx.Presentation()
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Add textbox with content
    txBox = slide.shapes.add_textbox(0, 0, 100, 100)
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "- Run E2E harness on Windows Sandbox."
    prs.save(pptx_path)
    
    # Verification should pass
    assert verify_pptx(pptx_path, expected_slide_count=1, bullet_word_limit=12)
    
    # Verification should fail for wrong slide count
    with pytest.raises(AssertionError):
        verify_pptx(pptx_path, expected_slide_count=2)

def test_verify_pdf(temp_dir):
    pdf_path = os.path.join(temp_dir, "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "PDF Oracle Verification Test.")
    doc.save(pdf_path)
    doc.close()
    
    # Verification should pass
    assert verify_pdf(pdf_path, ["PDF Oracle", "Verification"])
    
    # Verification should fail for missing text
    with pytest.raises(AssertionError):
        verify_pdf(pdf_path, ["Outbound connection blocked"])

def test_libreoffice_recompute_not_found(temp_dir):
    xlsx_path = os.path.join(temp_dir, "test.xlsx")
    wb = openpyxl.Workbook()
    wb.save(xlsx_path)
    
    # If LibreOffice is not installed, it should raise FileNotFoundError
    # (Since we know LibreOffice is absent on this machine, this test must raise FileNotFoundError)
    with pytest.raises(FileNotFoundError) as excinfo:
        excel_libreoffice_recompute(xlsx_path, temp_dir)
    assert "LibreOffice" in str(excinfo.value)

def test_network_sniffer_oracle():
    sniffer = NetworkSnifferOracle()
    sniffer.start()
    
    # Check that starting doesn't crash and destinations is a set
    assert isinstance(sniffer.external_destinations, set)
    
    sniffer.stop()

def test_verify_screenshot_diff(temp_dir):
    path_a = os.path.join(temp_dir, "a.png")
    path_b = os.path.join(temp_dir, "b.png")
    path_c = os.path.join(temp_dir, "c.png")
    
    img_a = Image.new("RGB", (100, 100), color="white")
    img_a.save(path_a)
    
    img_b = Image.new("RGB", (100, 100), color="white")
    img_b.save(path_b)
    
    img_c = Image.new("RGB", (100, 100), color="black")
    img_c.save(path_c)
    
    # A and B match
    assert verify_screenshot_diff(path_a, path_b)
    
    # A and C do not match
    with pytest.raises(AssertionError):
        verify_screenshot_diff(path_a, path_c)
