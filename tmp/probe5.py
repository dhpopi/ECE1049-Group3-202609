"""Series-element bisect: plain resistor vs MOSFET pair vs pair+gate."""
import xmlrpc.client
from pathlib import Path

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
      Position      [120, 140]
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


def build(tag, src_conn, extra):
    txt = BASE.read_text(encoding='utf-8')
    txt = txt.replace('Name          "Hartmann_DeltaSwitch"', 'Name          "P5_%s"' % tag, 1)
    assert txt.count(OLD) == 1
    txt = txt.replace(OLD, src_conn)
    m = '\n  }\n}'
    txt = txt.replace(m, '\n' + extra + '  }\n}')
    f = ROOT / ('P5_%s.plecs' % tag)
    f.write_text(txt, encoding='utf-8')
    return f


def run(tag, f):
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate('P5_' + tag, {'ModelVars': {'Tstop': 0.004, 'Pnom': 3000,
                                                         'Rload': 400.0**2/3000,
                                                         'Ginit': 3000/(3*115**2)},
                                          'SolverOpts': {'MaxStep': 1/(72000*10)}})
        print('OK  ', tag, 'points', len(r['Time']))
    except xmlrpc.client.Fault as e:
        print('FAIL', tag, '::', str(e).splitlines()[0][:110])


# (a) series 1 mOhm resistor
f = build('res',
          '      SrcComponent  "Rk"\n      SrcTerminal   2\n',
          RES)
run('res', f)

# (b) MOSFET pair, same wiring as the PhaseLoss model, gate from a Step
MOS = open(ROOT / 'Hartmann_DeltaSwitch_PhaseLoss.plecs', encoding='utf-8').read()
import re
comp = re.search(r'    Component \{\n      Type          MosfetWithDiode\n      Name          "K1a".*?Name          "K1b".*?\n    \}\n', MOS, re.S).group(0)
step = re.search(r'    Component \{\n      Type          Step\n      Name          "LossStep".*?\n    \}\n', MOS, re.S).group(0)
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
f = build('mosfet',
          '      SrcComponent  "K1b"\n      SrcTerminal   1\n',
          comp + step + conn)
run('mosfet', f)
