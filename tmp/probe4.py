"""Isolate: does a name-only copy, or a Step-only addition, break the model?"""
import re, xmlrpc.client
from pathlib import Path
import numpy as np

ROOT = Path(r'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch')
BASE = ROOT / 'Hartmann_DeltaSwitch.plecs'
p = xmlrpc.client.ServerProxy('http://localhost:1080')


def make(tag, mutator):
    txt = BASE.read_text(encoding='utf-8')
    txt = txt.replace('Name          "Hartmann_DeltaSwitch"',
                      'Name          "P4_%s"' % tag, 1)
    txt = mutator(txt)
    f = ROOT / ('P4_%s.plecs' % tag)
    f.write_text(txt, encoding='utf-8')
    return f


def run(tag, f, tstop=0.004):
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate('P4_' + tag, {'ModelVars': {'Tstop': tstop, 'Pnom': 3000,
                                                         'Rload': 400.0**2/3000,
                                                         'Ginit': 3000/(3*115**2)},
                                          'SolverOpts': {'MaxStep': 1/(72000*10)}})
        print('OK  ', tag, 'points', len(r['Time']))
    except xmlrpc.client.Fault as e:
        print('FAIL', tag, '::', str(e).splitlines()[0][:110])


# 1) name-only copy
f = make('copy', lambda t: t)
run('copy', f)

# 2) + t_loss in the initialization commands
f = make('withvar', lambda t: t.replace('Tstop=0.12;\\n"', 'Tstop=0.12;\\nt_loss=0.06;\\n"'))
run('withvar', f)

# 3) + a Step component (unconnected)
STEP = '''    Component {
      Type          Step
      Name          "LossStep"
      Show          on
      Position      [60, 60]
      Direction     right
      Flipped       off
      LabelPosition south
      Parameter {
        Variable      "Time"
        Value         "0.06"
        Show          off
      }
      Parameter {
        Variable      "Before"
        Value         "1"
        Show          off
      }
      Parameter {
        Variable      "After"
        Value         "0"
        Show          off
      }
      Parameter {
        Variable      "DataType"
        Value         "10"
        Show          off
      }
    }
'''
def add_step(t):
    m = '\n  }\n}'
    assert t.count(m) == 1
    return t.replace(m, '\n' + STEP + '  }\n}')
run('step', make('step', add_step))
