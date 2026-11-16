"""Clean-layout bisect: series resistor at an empty spot, then MOSFET pair."""
import re, xmlrpc.client
from pathlib import Path
import numpy as np

ROOT = Path(r'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch')
BASE = ROOT / 'Hartmann_DeltaSwitch.plecs'
p = xmlrpc.client.ServerProxy('http://localhost:1080')
OLD = ('      SrcComponent  "Grid_115Vrms"\n'
       '      SrcTerminal   1\n'
       '      Points        [95, 140; 150, 140]\n')

RES = '''    Component {
      Type          Resistor
      Name          "Rk"
      Show          on
      Position      [130, 80]
      Direction     right
      Flipped       off
      LabelPosition south
      Parameter {
        Variable      "R"
        Value         "0.001"
        Show          off
      }
    }
    Connection {
      Type          Wire
      SrcComponent  "Grid_115Vrms"
      SrcTerminal   1
      DstComponent  "Rk"
      DstTerminal   1
    }
'''


def build(tag, new_src, extra):
    txt = BASE.read_text(encoding='utf-8')
    txt = txt.replace('Name          "Hartmann_DeltaSwitch"', 'Name          "P7_%s"' % tag, 1)
    assert txt.count(OLD) == 1
    txt = txt.replace(OLD, new_src)
    m = '\n  }\n}'
    txt = txt.replace(m, '\n' + extra + '  }\n}')
    f = ROOT / ('P7_%s.plecs' % tag)
    f.write_text(txt, encoding='utf-8')
    return f


def run(tag, f, tstop=0.01):
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate('P7_' + tag, {'ModelVars': {'Tstop': tstop, 'Pnom': 5000,
                                                         'Rload': 32.0,
                                                         'Ginit': 5000/(3*115**2)},
                                          'SolverOpts': {'MaxStep': 1/(72000*10)}})
        y = np.asarray(r['Values'])
        print('OK  ', tag, 'points', len(r['Time']), 'Vdc_end', round(float(y[6, -1]), 3))
    except xmlrpc.client.Fault as e:
        print('FAIL', tag, '::', str(e).splitlines()[0][:110])


run('res', build('res', '      SrcComponent  "Rk"\n      SrcTerminal   2\n', RES))

# MOSFET pair at the same clean spot, gates tied to a Step that stays at 1
MOS = (ROOT / 'Hartmann_DeltaSwitch_PhaseLoss.plecs').read_text(encoding='utf-8')
comp = re.search(r'    Component \{\n      Type          MosfetWithDiode\n      Name          "K1a".*?Name          "K1b".*?\n    \}\n', MOS, re.S).group(0)
comp = comp.replace('[110, 140]', '[115, 90]').replace('[140, 140]', '[150, 90]')
step = re.search(r'    Component \{\n      Type          Step\n      Name          "LossStep".*?\n    \}\n', MOS, re.S).group(0)
step = step.replace('[60, 60]', '[60, 45]')
conn = '''    Connection {
      Type          Wire
      SrcComponent  "Grid_115Vrms"
      SrcTerminal   1
      DstComponent  "K1a"
      DstTerminal   1
    }
    Connection {
      Type          Wire
      SrcComponent  "K1a"
      SrcTerminal   2
      DstComponent  "K1b"
      DstTerminal   2
    }
    Connection {
      Type          Signal
      SrcComponent  "LossStep"
      SrcTerminal   1
      Branch {
        DstComponent  "K1a"
        DstTerminal   3
      }
      Branch {
        DstComponent  "K1b"
        DstTerminal   3
      }
    }
'''
run('mos', build('mos', '      SrcComponent  "K1b"\n      SrcTerminal   1\n', comp + step + conn))
