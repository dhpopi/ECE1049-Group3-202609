from pathlib import Path
import re
base=Path(r'C:\Users\Yipeng Guo\Documents\Plexim\PLECS 4.9 (64 bit)')
for p in list((base/'demos').rglob('*.plecs'))+list((base/'examples').rglob('*.plecs')):
 s=p.read_text(errors='replace')
 # top-level output with 6-space indentation
 if re.search(r'^      Type +Output$',s,re.M):
  print(p)
  m=re.search(r'^    Component \{\n      Type +Output[\s\S]*?^    }',s,re.M)
  print(m.group() if m else '')
  print(s[:s.index('  Schematic')]);break
