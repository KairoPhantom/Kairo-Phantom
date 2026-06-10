import win32com.client

try:
    try:
        word = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        word = win32com.client.Dispatch("Word.Application")
        
    word.Visible = True
    doc = word.Documents.Add()
    
    # Write initial text (no trailing newline)
    p1 = doc.Paragraphs(1)
    p1.Range.Text = "Initial Paragraph 1"
    
    # We want to insert a Heading 1 paragraph after p1
    print("Inserting Heading 1 after p1...")
    p1 = doc.Paragraphs(1)
    next_p = p1.Next()
    if next_p:
        # If there is a next paragraph, add before it
        doc.Paragraphs.Add(Range=next_p.Range)
        new_p = doc.Paragraphs(next_p.Index - 1)
    else:
        # Otherwise, collapse p1 range and insert paragraph after it
        rng = p1.Range
        rng.Collapse(0) # Collapse to end
        rng.InsertParagraphAfter()
        # The new paragraph will be the last paragraph
        new_p = doc.Paragraphs(doc.Paragraphs.Count)
        
    new_p.Range.Text = "This is Heading 1"
    new_p.Style = doc.Styles("Heading 1")
    
    # We want to insert a Normal paragraph after Heading 1 (Paragraph 2)
    print("Inserting Normal paragraph after Heading 1...")
    h1_p = doc.Paragraphs(2)
    next_p2 = h1_p.Next()
    if next_p2:
        doc.Paragraphs.Add(Range=next_p2.Range)
        new_p2 = doc.Paragraphs(next_p2.Index - 1)
    else:
        rng = h1_p.Range
        rng.Collapse(0)
        rng.InsertParagraphAfter()
        new_p2 = doc.Paragraphs(doc.Paragraphs.Count)
        
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
