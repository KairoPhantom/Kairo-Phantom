import win32com.client

try:
    try:
        word = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        word = win32com.client.Dispatch("Word.Application")
        
    word.Visible = True
    doc = word.Documents.Add()
    
    p1 = doc.Paragraphs(1)
    p1.Range.Text = "Initial Paragraph 1"
    
    # Insert after p1
    rng = p1.Range
    rng.Collapse(0) # Collapse to end
    rng.InsertParagraphAfter()
    
    new_p = p1.Next()
    if new_p:
        new_p.Range.Text = "This is Heading 1"
        new_p.Style = doc.Styles("Heading 1")
        
    # Insert after Heading 1
    h1_p = doc.Paragraphs(2)
    rng2 = h1_p.Range
    rng2.Collapse(0)
    rng2.InsertParagraphAfter()
    
    new_p2 = h1_p.Next()
    if new_p2:
        new_p2.Range.Text = "This is normal body text under Heading 1."
        new_p2.Style = doc.Styles("Normal")
        
    print("\nPARAGRAPH STYLES IN WORD:")
    for idx in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs(idx)
        print(f"Paragraph {idx-1}: Style={p.Style.NameLocal!r} Text={repr(p.Range.Text)}")
        
    doc.Close(SaveChanges=False)
    word.Quit()
except Exception as e:
    print("COM Error:", e)
