import win32com.client
try:
    word = win32com.client.GetActiveObject("Word.Application")
    doc = word.ActiveDocument
    print("SUCCESS")
    print(repr(doc.Content.Text))
except Exception as e:
    print("FAILED:", str(e))
