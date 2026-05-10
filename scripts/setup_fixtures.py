import os
try:
    from docx import Document
except ImportError:
    import subprocess
    subprocess.check_call(["python", "-m", "pip", "install", "python-docx"])
    from docx import Document

def create_word_fixture():
    doc = Document()
    doc.add_heading('Q3 Financial Report', 0)
    doc.add_heading('Executive Summary', level=1)
    doc.add_paragraph('This quarter saw moderate growth across all sectors. We expect continued momentum into Q4.')
    doc.add_heading('Revenue Analysis', level=2)
    doc.add_paragraph('Revenue increased by 12% year-over-year, driven primarily by cloud services...')
    
    os.makedirs(r"C:\tests", exist_ok=True)
    doc.save(r"C:\tests\report.docx")
    print("Created C:\\tests\\report.docx")

if __name__ == "__main__":
    create_word_fixture()
