import win32com.client
import os

try:
    word = win32com.client.GetActiveObject("Word.Application")
    doc = word.ActiveDocument
    print("Document title:", doc.Name)
    print("Paragraphs count before:", doc.Paragraphs.Count)
    
    # Let's insert a paragraph at the end
    rng = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
    new_p = doc.Paragraphs.Add(Range=rng)
    new_p.Range.Text = "This is a styled H1 paragraph"
    try:
        new_p.Style = doc.Styles("Heading 1")
    except Exception as e:
        print("Failed to set Heading 1:", e)
        
    print("Paragraphs count after:", doc.Paragraphs.Count)
    print("Last paragraph style:", doc.Paragraphs(doc.Paragraphs.Count - 1).Style.NameLocal)
    print("Last paragraph text:", repr(doc.Paragraphs(doc.Paragraphs.Count - 1).Range.Text))
except Exception as e:
    print("COM Error:", e)
