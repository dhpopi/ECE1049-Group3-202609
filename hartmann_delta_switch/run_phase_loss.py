"""Run the phase-loss scenario on the generated variant and report metrics.

The variant model (Hartmann_DeltaSwitch_PhaseLoss.plecs) is produced by
    python build_model.py --phase-loss
It adds one ideal switch K1 in series with grid phase 1, opened at t_loss, and
a 3.4 uF + 10 ohm snubber across it (stand-in for the EMI-filter capacitance
that carries the disconnected phase current).  The controller is untouched.

Usage: python run_phase_loss.py [--pnom 3000] [--tloss 0.06] [--tag pl_3kW]
"""
from pathlib import Path
import argparse, json
import numpy as np
import xmlrpc.client
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
MODEL = 'Hartmann_DeltaSwitch_PhaseLoss'
COLUMNS = ['v1','v2','v3','i1','i2','i3','Vdc','iref1','iref2','iref3',
           's12','s21','s23','s32','s13','s31','Gref']


def simulate(pnom, t_loss, tstop=0.12, fline=800.0, gmax=None):
    p = xmlrpc.client.ServerProxy('http://localhost:1080')
    try:
        p.plecs.close(MODEL)
    except Exception:
        pass
    p.plecs.load((ROOT / (MODEL + '.plecs')).as_posix())
    mv = {'fline': fline, 'Vinit': 400.0, 'Tstop': tstop,
          't_loss': t_loss, 'Pnom': pnom,
          'Rload': 400.0 ** 2 / pnom,
          'Ginit': pnom / (3 * 115.0 ** 2)}
    if gmax is not None:
        mv['Gmax'] = gmax
    try:
        r = p.plecs.simulate(MODEL, {
            'ModelVars': mv,
            'SolverOpts': {'MaxStep': 1 / (72000 * 10),
                           'OutputTimes': np.linspace(0, tstop, int(tstop * 2e6) + 1).tolist()},
        })
    finally:
        # do not keep models open in the PLECS GUI
        try:
            p.plecs.close(MODEL)
        except Exception:
            pass
    t = np.asarray(r['Time'])
    y = np.asarray(r['Values'])
    if y.shape[0] != 17:
        y = y.T
    assert y.shape == (17, len(t)), y.shape
    return t, y


def window_metrics(t, y, mask, f, pnom):
    v, i, vo = y[:3, mask], y[3:6, mask], y[6, mask]
    ir = np.sqrt(np.mean(i * i, axis=1))
    vr = np.sqrt(np.mean(v * v, axis=1))
    return {
        'Irms_A': ir.round(3).tolist(),
        'Vrms_V': vr.round(2).tolist(),
        'PF': (np.mean(v * i, axis=1) / (vr * ir)).round(4).tolist(),
        'Vdc_mean_V': round(float(vo.mean()), 3),
        'Vdc_pp_V': round(float(np.ptp(vo)), 3),
        'Pout_W': round(float(np.mean(vo ** 2 / (400.0 ** 2 / pnom))), 1),
        'Gref_mean_S': round(float(y[16, mask].mean()), 4),
    }


def thd(x, f, fs_per_cycle=2500):
    n = len(x)
    a = np.abs(np.fft.rfft(x)) * 2 / n
    k0 = int(round(f * n / (n / (8 / f) * 8)))  # 8 cycles -> fundamental at bin 8
    k0 = 8
    return float(np.sqrt(np.sum(a[k0 * 2:k0 * 41] ** 2)) / a[k0] * 100)


def metrics(t, y, t_loss, f, pnom):
    # a phase loss very early in the run leaves no settled pre-fault window
    pre_end = t_loss - 2e-4
    pre_start = pre_end - 8 / f
    pre = (t >= pre_start) & (t <= pre_end) if pre_start > 0 else None
    post = t >= t[-1] - 8 / f
    # 2*fN bus ripple over the post window
    tt, vo = t[post], y[6, post]
    ripple = 2 * abs(np.mean((vo - vo.mean()) * np.exp(-2j * np.pi * 2 * f * tt)))
    m = {
        't_loss_s': t_loss,
        'window_before_s': ([round(float(t[pre][0]), 5), round(float(t[pre][-1]), 5)]
                            if pre is not None else None),
        'window_after_s': [round(float(tt[0]), 5), round(float(tt[-1]), 5)],
        'before': window_metrics(t, y, pre, f, pnom) if pre is not None else None,
        'after': window_metrics(t, y, post, f, pnom),
        'i1_absmax_after_A': round(float(np.max(np.abs(y[3, post]))), 4),
        'i2_plus_i3_absmax_A': round(float(np.max(np.abs(y[4, post] + y[5, post]))), 4),
        'Vdc_ripple_2f_V': round(float(ripple), 3),
        'Vdc_min_after_V': round(float(vo.min()), 3),
        'Vdc_max_after_V': round(float(vo.max()), 3),
        'Vdc_min_whole_run_V': round(float(y[6].min()), 3),
        'Gref_max_S': round(float(y[16].max()), 4),
        'current_limit_hit': bool(y[16].max() >= 0.2499),
    }
    # THD of the two remaining phases in the post window (single-phase operation)
    i2 = y[4, post]
    i3 = y[5, post]
    m['THD_after_percent'] = [round(thd(i2, f), 2), round(thd(i3, f), 2)]
    return m


def plot(t, y, m, t_loss, tag, pnom):
    fig, ax = plt.subplots(4, 1, figsize=(11, 10), layout='constrained')
    cols = ['#2463aa', '#d87521', '#299074']
    ms = t * 1e3
    tl = t_loss * 1e3
    zoom = (t >= t_loss - 3e-3) & (t <= t_loss + 7e-3)
    for k in range(3):
        ax[0].plot(ms, y[3 + k], color=cols[k], lw=0.7, label=f'Phase {k+1}')
        ax[1].plot(ms[zoom], y[3 + k, zoom], color=cols[k], lw=1.1)
    for a, title in ((ax[0], 'Input currents, full run'),
                     (ax[1], 'Input currents, phase-loss transient')):
        a.axvline(tl, color='k', ls='--', lw=1)
        a.set_ylabel('Current (A)')
        a.grid(alpha=0.25)
        a.set_title(title, fontsize=10, loc='left')
        a.set_xlabel('Time (ms)')
    ax[0].legend(ncol=3, loc='lower right')

    ax[2].plot(ms, y[6], color='#644899', lw=0.7)
    ax[2].axvline(tl, color='k', ls='--', lw=1)
    ax[2].set_ylabel('DC bus (V)')
    ax[2].set_xlabel('Time (ms)')
    ax[2].grid(alpha=0.25)
    ax[2].set_title('DC bus voltage', fontsize=10, loc='left')

    ax[3].plot(ms[zoom], y[6, zoom], color='#644899', lw=1.0)
    ax[3].axvline(tl, color='k', ls='--', lw=1)
    ax[3].set_ylabel('DC bus (V)')
    ax[3].set_xlabel('Time (ms)')
    ax[3].grid(alpha=0.25)
    ax[3].set_title('DC bus, phase-loss transient', fontsize=10, loc='left')

    tls = ('%.2f' % tl) if tl < 10 else ('%.0f' % tl)
    fig.suptitle('Hartmann delta-switch rectifier | PLECS 5.0 | phase loss\n'
                 f'Po = {pnom/1000:.1f} kW, 800 Hz, L1 lost at {tls} ms, controller unchanged')
    fig.savefig(OUT / f'{tag}.png', dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pnom', type=float, default=3000.0)
    ap.add_argument('--tloss', type=float, default=0.06)
    ap.add_argument('--gmax', type=float, default=None,
                    help='override the conductance limit (default: model value 0.25 S)')
    ap.add_argument('--tag', default='phase_loss_3kW')
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    t, y = simulate(a.pnom, a.tloss, gmax=a.gmax)
    m = metrics(t, y, a.tloss, 800.0, a.pnom)
    if a.gmax is not None:
        m['Gmax_used_S'] = a.gmax

    # control: identical model, switch never opens
    tc, yc = simulate(a.pnom, 1.0, gmax=a.gmax)
    mc = metrics(tc, yc, a.tloss, 800.0, a.pnom)

    np.savez_compressed(OUT / f'{a.tag}.npz', time=t, values=y, columns=COLUMNS)
    sel = t >= t[-1] - 4 / 800.0
    np.savetxt(OUT / f'{a.tag}_steady.csv', np.column_stack((t[sel], y[:, sel].T)),
               delimiter=',', header='time_s,' + ','.join(COLUMNS), comments='', fmt='%.9g')
    plot(t, y, m, a.tloss, a.tag, a.pnom)

    summary = {'phase_loss': m, 'control': mc}
    (OUT / f'{a.tag}.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
