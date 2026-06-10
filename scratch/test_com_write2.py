import win32com.client
import os
import time

try:
    # Try to get active Word instance, or start it if not running
    try:
        word = win32com.client.GetActiveObject("Word.Application")
    except Exception:
        word = win32com.client.Dispatch("Word.Application")
        
    word.Visible = True
    
    # Create a new document
    doc = word.Documents.Add()
    print("Document created.")
    
    # Write some initial paragraphs
    p1 = doc.Paragraphs(1)
    p1.Range.Text = "Initial Paragraph 1\n"
    
    # Now let's try to insert a Heading 1 after Paragraph 1
    # Method: Paragraphs.Add before the next paragraph (p1.Next())
    print("Inserting styled paragraph after p1...")
    p1 = doc.Paragraphs(1)
    next_p = p1.Next()
    if next_p:
        new_p = doc.Paragraphs.Add(Range=next_p.Range)
    else:
        # Fallback if no next paragraph
        rng = p1.Range
        rng.Collapse(0)
        rng.InsertParagraphAfter()
        new_p = doc.Paragraphs(doc.Paragraphs.Count)
        
    # Set text and style without trailing \r
    new_p.Range.Text = "This is Heading 1"
    new_p.Style = doc.Styles("Heading 1")
    
    # Insert another paragraph after Heading 1
    print("Inserting Normal paragraph after Heading 1...")
    h1_p = doc.Paragraphs(2)
    next_p = h1_p.Next()
    if next_p:
        new_p2 = doc.Paragraphs.Add(Range=next_p.Range)
    else:
        rng = h1_p.Range
        rng.Collapse(0)
        rng.InsertParagraphAfter()
        new_p2 = doc.Paragraphs(doc.Paragraphs.Count)
        
    new_p2.Range.Text = "This is normal body text under Heading 1."
    new_p2.Style = doc.Styles("Normal")
    
    print("\nPARAGRAPH STYLES IN WORD APPLICATION:")
    for idx in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs(idx)
        print(f"Paragraph {idx-1}: Style={p.Style.NameLocal!r} Text={repr(p.Range.Text)}")
        
    # Clean up
    doc.Close(SaveChanges=False)
    word.Quit()
except Exception as e:
    print("COM Error:", e)
