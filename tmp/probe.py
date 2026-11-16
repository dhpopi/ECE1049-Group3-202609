import xmlrpc.client, numpy as np, traceback, sys

p = xmlrpc.client.ServerProxy('http://localhost:1080')

def run(model, tstop, pnom, variant, dense=False, tloss=0.06):
    p.plecs.load(rf'C:\UofT\PhD\Course\ECE1049\hartmann_delta_switch\{variant}')
    opts = {'ModelVars': {'Tstop': tstop, 'Pnom': pnom,
                          'Rload': 1e5 if pnom is None else 400.0**2/pnom,
                          'Ginit': 3000/(3*115**2), 't_loss': tloss},
            'SolverOpts': {'MaxStep': 1/(72000*10)}}
    if dense:
        opts['SolverOpts']['OutputTimes'] = np.linspace(0, tstop, int(tstop*2e6)+1).tolist()
    try:
        r = p.plecs.simulate(model, opts)
        print('OK  ', model, tstop, pnom, 'points', len(r['Time']), 'Vdc_end', round(float(np.asarray(r['Values'])[-1 if len(np.asarray(r['Values']).shape)==1 else 6][-1]),2))
    except xmlrpc.client.Fault as e:
        msg = str(e).splitlines()[0]
        print('FAIL', model, tstop, pnom, '::', msg[:160])

run('Hartmann_DeltaSwitch', 0.003, 3000.0, 'Hartmann_DeltaSwitch.plecs')
run('Hartmann_DeltaSwitch_PhaseLoss', 0.003, 5000.0, 'Hartmann_DeltaSwitch_PhaseLoss.plecs', tloss=1.0)
run('Hartmann_DeltaSwitch_PhaseLoss', 0.003, 3000.0, 'Hartmann_DeltaSwitch_PhaseLoss.plecs', tloss=1.0)
run('Hartmann_DeltaSwitch_PhaseLoss', 0.003, 3000.0, 'Hartmann_DeltaSwitch_PhaseLoss.plecs', dense=True)
