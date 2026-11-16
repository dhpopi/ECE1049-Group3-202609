"""Run the native PLECS model via localhost RPC and verify actual solver outputs.
Requires PLECS running with Preferences > RPC interface port = 1080,
and Python packages numpy and matplotlib. No alternate circuit solver is used.
"""
from pathlib import Path
import argparse, json, xmlrpc.client
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
MODEL='Hartmann_DeltaSwitch'
COLUMNS=['v1','v2','v3','i1','i2','i3','Vdc','iref1','iref2','iref3','s12','s21','s23','s32','s13','s31','Gref']

def metrics(t,y,f):
    # Exactly eight line cycles at the end, interpolated uniformly at 2 MHz.
    start=t[-1]-8/f
    n=round(8/f*2e6)
    tu=start+np.arange(n)/(f*n/8)
    z=np.array([np.interp(tu,t,row) for row in y])
    v,i,vo=z[:3],z[3:6],z[6]
    vr=np.sqrt(np.mean(v*v,axis=1));ir=np.sqrt(np.mean(i*i,axis=1))
    pin=np.mean((v*i).sum(axis=0));po=np.mean(vo**2/32)
    pf=np.mean(v*i,axis=1)/(vr*ir)
    a=np.abs(np.fft.rfft(i,axis=1))*2/n
    thd=np.sqrt(sum(a[:,8*h]**2 for h in range(2,41)))/a[:,8]*100
    # Check clamping directly against measured voltage signs, excluding zero crossings.
    ga=z[10:16]; pairs=[(0,1),(1,0),(1,2),(2,1),(0,2),(2,0)]
    # Interpolation blends gates around edges; only OFF pair checks matter here.
    violation=0
    for k,(aa,bb) in enumerate(pairs):
        same=(v[aa]*v[bb]>0)&(abs(v[aa])>1)&(abs(v[bb])>1)
        violation+=int(np.count_nonzero(ga[k,same]>0.01))
    return dict(fline_Hz=f,window_s=[float(start),float(t[-1])],Vdc_mean_V=float(vo.mean()),
        Vdc_pp_V=float(np.ptp(vo)),Pout_W=float(po),Pin_W=float(pin),
        Iphase_rms_A=ir.tolist(),PF_phase=pf.tolist(),THD_2_to_40_percent=thd.tolist(),
        max_abs_current_A=float(np.max(abs(y[3:6]))),
        Vdc_min_entire_run_V=float(y[6].min()),Vdc_max_entire_run_V=float(y[6].max()),
        clamping_violations=violation,kcl_max_A=float(np.max(abs(y[3:6].sum(axis=0)))))

def plot_case(t,y,name,f):
    fig,ax=plt.subplots(4,1,figsize=(11,9),layout='constrained')
    ss=t>=t[-1]-3/f
    colors=['#2463aa','#d87521','#299074']
    for k,c in enumerate(colors):
        ax[0].plot(t[ss]*1000,y[k,ss],color=c,lw=1,label=f'Phase {k+1}')
        ax[1].plot(t[ss]*1000,y[k+3,ss],color=c,lw=.7)
    ax[0].set_ylabel('Grid voltage (V)');ax[0].legend(ncol=3,loc='upper right')
    ax[1].set_ylabel('Input current (A)');ax[1].set_xlabel('Time (ms)')
    ax[2].plot(t*1000,y[6],color='#644899',lw=1)
    ax[2].axhline(400,color='gray',ls='--',lw=.7);ax[2].set_ylabel('DC bus (V)');ax[2].set_xlabel('Time (ms)')
    for k,c in enumerate(colors):ax[3].plot(t[ss]*1000,y[k+3,ss]-y[k+7,ss],color=c,lw=.7)
    ax[3].set_ylabel('i - i_ref (A)');ax[3].set_xlabel('Time (ms)')
    for a in ax:a.grid(alpha=.2)
    fig.suptitle(f'Hartmann delta-switch rectifier | PLECS 4.9 | {name}')
    fig.savefig(OUT/f'{name}.png',dpi=160);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--post-only',action='store_true');ap.add_argument('--case');args=ap.parse_args()
    cases=[('baseline_800Hz',800,400,10),('baseline_400Hz',400,400,10),
           ('recovery_280V',800,280,10),('convergence_800Hz',800,400,40)]
    if not args.post_only:
        p=xmlrpc.client.ServerProxy('http://localhost:1080')
        try:p.plecs.close(MODEL)
        except xmlrpc.client.Fault:pass
        p.plecs.load((ROOT/f'{MODEL}.plecs').as_posix())
    allmetrics={}
    for name,f,vi,div in cases:
        if not args.post_only and (args.case is None or args.case==name):
            print('Simulating',name,flush=True)
            r=p.plecs.simulate(MODEL,{'ModelVars':{'fline':f,'Vinit':vi,'Tstop':.12},
                'SolverOpts':{'MaxStep':1/(72000*div),'OutputTimes':np.linspace(0,.12,240001).tolist()}})
            t=np.asarray(r['Time']);y=np.asarray(r['Values'])
            if y.shape[0]!=17:y=y.T
            if len(t)<2 or y.shape!=(17,len(t)):raise RuntimeError(f'Invalid output shape {y.shape}')
            np.savez_compressed(OUT/f'{name}.npz',time=t,values=y,columns=COLUMNS)
        else:
            d=np.load(OUT/f'{name}.npz');t,y=d['time'],d['values']
        m=metrics(t,y,f);allmetrics[name]=m
        print(name,json.dumps(m),flush=True)
        plot_case(t,y,name,f)
        # Convenient CSV of the last four cycles, retaining 0.5-us sampling.
        sel=t>=.12-4/f
        np.savetxt(OUT/f'{name}_steady.csv',np.column_stack((t[sel],y[:,sel].T)),delimiter=',',
                   header='time_s,'+','.join(COLUMNS),comments='',fmt='%.9g')
        assert np.isfinite(y).all()
        assert abs(m['Vdc_mean_V']-400)<1
        assert abs(m['Pout_W']-5000)<25
        assert min(m['PF_phase'])>.97
        assert max(m['THD_2_to_40_percent'])<6
        assert m['kcl_max_A']<1e-6
        assert m['clamping_violations']==0
    a,b=allmetrics['baseline_800Hz'],allmetrics['convergence_800Hz']
    convergence={'delta_Vdc_V':abs(a['Vdc_mean_V']-b['Vdc_mean_V']),
                 'delta_Pout_W':abs(a['Pout_W']-b['Pout_W']),
                 'max_delta_Irms_A':max(abs(np.array(a['Iphase_rms_A'])-b['Iphase_rms_A']))}
    assert convergence['delta_Vdc_V']<.1 and convergence['max_delta_Irms_A']<.05
    allmetrics['convergence_comparison']=convergence
    (OUT/'verification.json').write_text(json.dumps(allmetrics,indent=2))
    print('PASS: all four native PLECS runs and step-size convergence checks.',flush=True)

if __name__=='__main__':main()
