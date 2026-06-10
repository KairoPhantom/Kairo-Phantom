import win32com.client

try:
    try:
        word = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        word = win32com.client.Dispatch("Word.Application")
        
    word.Visible = True
    doc = word.Documents.Add()
    
    # 3 paragraphs
    p1 = doc.Paragraphs(1)
    p1.Range.Text = "Para 1\n"
    p2 = doc.Paragraphs(2)
    p2.Range.Text = "Para 2\n"
    p3 = doc.Paragraphs(3)
    p3.Range.Text = "Para 3"
    
    # Replace Paragraph 2 (index 2)
    p_rep = doc.Paragraphs(2)
    
    # Sub-range excluding the paragraph mark
    rng = doc.Range(Start=p_rep.Range.Start, End=p_rep.Range.End - 1)
    rng.Text = "Replaced Para 2 Content"
    p_rep.Style = doc.Styles("Heading 2")
    
    print("\nAfter replace with sub-range:")
    for idx in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs(idx)
        print(f"Paragraph {idx-1}: Style={p.Style.NameLocal!r} Text={repr(p.Range.Text)}")
        
    doc.Close(SaveChanges=False)
    word.Quit()
except Exception as e:
    print("COM Error:", e)
