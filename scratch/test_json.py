raw_json = r"""[
  {"cell":"F1","value":""},
  {"cell":"F2","value":"Analysis:\",n1. Best Product: Widget A ($28,100)\",n2. Top Region: North ($23,700)\",n3. SUMIF formula added in F3"},
  {"cell":"F3","formula":"=SUMIF(B2:B6,\\"Widget A\\",D2:D6)"}
]"""

print("Length of raw_json:", len(raw_json))
print("Char at 214:", repr(raw_json[214]))
print("Context around 214:", repr(raw_json[200:230]))
