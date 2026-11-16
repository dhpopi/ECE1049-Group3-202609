"""Bisect the phase-loss variant: which added part leaves terminals unconnected."""
import re, xmlrpc.client
from pathlib import Path
import numpy as np

ROOT = Path(r'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch')
SRC = ROOT / 'Hartmann_DeltaSwitch_PhaseLoss.plecs'
p = xmlrpc.client.ServerProxy('http://localhost:1080')


def blocks(lines, kind):
    out, i, head = [], 0, '    %s {' % kind
    while i < len(lines):
        if lines[i].startswith(head):
            d = lines[i].count('{') - lines[i].count('}')
            j = i
            while d > 0:
                j += 1
                d += lines[j].count('{') - lines[j].count('}')
            name = ''
            for k in range(i, j + 1):
                m = re.search(r'Name\s+"([^"]+)"', lines[k])
                if m:
                    name = m.group(1)
                    break
            out.append((i, j, name))
            i = j + 1
        else:
            i += 1
    return out


def make(tag, drop_comps=(), drop_kw=()):
    lines = SRC.read_text(encoding='utf-8').split('\n')
    drop = set()
    for s, e, name in blocks(lines, 'Component'):
        if name in drop_comps:
            drop.update(range(s, e + 1))
    for s, e, name in blocks(lines, 'Connection'):
        body = '\n'.join(lines[s:e + 1])
        if any(k in body for k in drop_kw):
            drop.update(range(s, e + 1))
    txt = '\n'.join(l for i, l in enumerate(lines) if i not in drop)
    txt = txt.replace('Name "Hartmann_DeltaSwitch_PhaseLoss"', 'Name "%s"' % tag, 1)
    f = ROOT / (tag + '.plecs')
    f.write_text(txt, encoding='utf-8')
    return f


def run(f):
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate(f.stem, {'ModelVars': {'Tstop': 0.005, 'Pnom': 5000,
                                                    'Rload': 32.0,
                                                    'Ginit': 5000 / (3 * 115**2),
                                                    't_loss': 1.0},
                                     'SolverOpts': {'MaxStep': 1/(72000*10)}})
        print('OK  ', f.stem, len(r['Time']))
    except xmlrpc.client.Fault as e:
        print('FAIL', f.stem, '::', str(e.faultString).splitlines()[0][:120])


run(make('Q_k1step', drop_comps=('C_loss', 'R_loss'), drop_kw=('C_loss', 'R_loss')))
run(make('Q_full'))
