"""Narrow down the K1-induced chatter: time, s_init, component type."""
import re, xmlrpc.client
from pathlib import Path
import numpy as np

ROOT = Path(r'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch')
p = xmlrpc.client.ServerProxy('http://localhost:1080')


def variant(tag, s_init='1', tstop=0.004):
    src = (ROOT / 'Probe_norc.plecs').read_text(encoding='utf-8')
    if s_init != '1':
        src = src.replace('''        Variable      "s_init"
        Value         "1"''', '''        Variable      "s_init"
        Value         "%s"''' % s_init, 1)
    src = re.sub(r'Name\s+"Probe_norc"', 'Name          "P3_%s"' % tag, src, count=1)
    f = ROOT / ('P3_%s.plecs' % tag)
    f.write_text(src, encoding='utf-8')
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate('P3_' + tag, {'ModelVars': {'Tstop': tstop, 'Pnom': 3000,
                                                         'Rload': 400.0**2/3000,
                                                         'Ginit': 3000/(3*115**2),
                                                         't_loss': 1.0},
                                          'SolverOpts': {'MaxStep': 1/(72000*10)}})
        print('OK  ', tag, tstop, 'points', len(r['Time']))
    except xmlrpc.client.Fault as e:
        print('FAIL', tag, tstop, '::', str(e).splitlines()[0][:100])


for ts in (0.0002, 0.0006, 0.001, 0.002):
    variant('t%dus' % round(ts*1e6), '1', ts)
variant('sinit0', '0', 0.004)
