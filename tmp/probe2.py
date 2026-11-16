"""Bisect which added part causes the zero-crossing chatter."""
import re, sys, xmlrpc.client
from pathlib import Path
import numpy as np

ROOT = Path(r'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch')
p = xmlrpc.client.ServerProxy('http://localhost:1080')


def split_blocks(txt, kind):
    """Yield (start_line, end_line, name) for blocks '    <kind> {' ... matching '    }'."""
    lines = txt.split('\n')
    out = []
    i = 0
    head = '    %s {' % kind
    while i < len(lines):
        if lines[i].startswith(head):
            depth = lines[i].count('{') - lines[i].count('}')
            j = i
            while depth > 0:
                j += 1
                depth += lines[j].count('{') - lines[j].count('}')
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


def strip(txt, comp_names=(), conn_keywords=()):
    lines = txt.split('\n')
    drop = set()
    for kind in ('Component', 'Connection'):
        for s, e, name in split_blocks(txt, kind):
            if kind == 'Component' and name in comp_names:
                drop.update(range(s, e + 1))
            if kind == 'Connection':
                body = '\n'.join(lines[s:e + 1])
                if any(k in body for k in conn_keywords) and not any(
                        n in body for n in () ):
                    # only drop connections that reference the removed parts exclusively-ish
                    if any(k in body for k in conn_keywords):
                        drop.update(range(s, e + 1))
    return '\n'.join(l for i, l in enumerate(lines) if i not in drop)


def make(tag, drop_comps=(), drop_conn_kw=()):
    src = (ROOT / 'Hartmann_DeltaSwitch_PhaseLoss.plecs').read_text(encoding='utf-8')
    if drop_comps:
        src = strip(src, comp_names=drop_comps, conn_keywords=drop_conn_kw)
    src = re.sub(r'Name\s+"Hartmann_DeltaSwitch_PhaseLoss"',
                 'Name          "Probe_%s"' % tag, src, count=1)
    f = ROOT / ('Probe_%s.plecs' % tag)
    f.write_text(src, encoding='utf-8')
    return f


def run(f, tstop=0.004):
    name = 'Probe_' + f.stem.split('_', 1)[1]
    p.plecs.load(f.as_posix())
    try:
        r = p.plecs.simulate(name, {'ModelVars': {'Tstop': tstop, 'Pnom': 3000,
                                                  'Rload': 400.0**2 / 3000,
                                                  'Ginit': 3000 / (3 * 115**2),
                                                  't_loss': 1.0},
                                   'SolverOpts': {'MaxStep': 1/(72000*10)}})
        y = np.asarray(r['Values'])
        if y.ndim == 1:
            y = y.reshape(17, -1)
        print('OK  ', f.name, 'Vdc_end', round(float(y[6, -1]), 2))
    except xmlrpc.client.Fault as e:
        print('FAIL', f.name, '::', str(e).splitlines()[0][:130])


cases = [
    ('full', (), ()),                                      # K1 + RC
    ('norc', ('C_loss', 'R_loss'), ('C_loss', 'R_loss')),  # K1 only
]
for tag, comps, kws in cases:
    f = make(tag, comps, kws)
    run(f)
