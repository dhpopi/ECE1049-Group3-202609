from pathlib import Path
import re,json
base=Path(r'C:\Users\Yipeng Guo\Documents\Plexim\PLECS 4.9 (64 bit)')
s=(base/'components.plecs').read_text()
def block(s,start):
 depth=0; quote=False; esc=False
 for i in range(start,len(s)):
  c=s[i]
  if quote:
   if esc: esc=False
   elif c=='\\': esc=True
   elif c=='"': quote=False
  elif c=='"':quote=True
  elif c=='{':depth+=1
  elif c=='}':
   depth-=1
   if depth==0:return s[start:i+1]
types=['CScript','Mosfet','MOSFET','MOSFETWithDiode','Capacitor','Resistor','ACVoltageSource','ThreePhaseVoltageSource','TriangleGenerator','Comparator','Output','Ammeter','Voltmeter','SignalMux','SignalDemux','Ground','ElectricalLabel','Label']
for typ in types:
 m=re.search(r'Component \{\s+Type\s+'+typ+r'\s',s)
 if m:
  b=block(s,m.start()); Path('tmp/plecs/'+typ+'.txt').write_text(b); print(typ+'\n'+(b[:6000] if typ!='CScript' else '\n'.join(re.findall(r'Variable\s+"([^"]+)"',b))))
