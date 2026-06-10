import win32com.client

def _com_apply_runs(rng, runs_data):
    start = rng.Start
    for r in runs_data:
        text = r.get("text", "")
        length = len(text)
        if length == 0:
            continue
        run_rng = rng.Document.Range(start, start + length)
        if r.get("bold"):
            run_rng.Bold = True
        if r.get("italic"):
            run_rng.Italic = True
        start += length

try:
    try:
        word = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        word = win32com.client.Dispatch("Word.Application")
        
    word.Visible = True
    doc = word.Documents.Add()
    
    p1 = doc.Paragraphs(1)
    p1.Range.Text = "Initial text\n"
    
    # We want to insert a paragraph with bold and italic runs
    runs_data = [
        {"text": "This is bold, ", "bold": True},
        {"text": "this is italic, ", "italic": True},
        {"text": "and this is normal."}
    ]
    
    text = "".join(r.get("text", "") for r in runs_data)
    
    next_p = p1.Next()
    if next_p:
        new_p = doc.Paragraphs.Add(Range=next_p.Range)
    else:
        rng = p1.Range
        rng.Collapse(0)
        rng.InsertParagraphAfter()
        new_p = doc.Paragraphs(doc.Paragraphs.Count)
        
    new_p.Range.Text = text
    _com_apply_runs(new_p.Range, runs_data)
    new_p.Style = doc.Styles("Normal")
    
    print("\nPARAGRAPH STYLES & RUNS IN WORD:")
    for idx in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs(idx)
        print(f"Paragraph {idx-1}: Style={p.Style.NameLocal!r} Text={repr(p.Range.Text)}")
        for r_idx, run in enumerate(p.Range.Words):
            print(f"  Word {r_idx}: Text={repr(run.Text)} Bold={run.Bold} Italic={run.Italic}")
            
    doc.Close(SaveChanges=False)
    word.Quit()
except Exception as e:
    print("COM Error:", e)
