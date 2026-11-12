"""Build a native, editable PLECS 4.9 switching model from explicit components."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
q = lambda x: json.dumps(str(x), ensure_ascii=True)
parts, wires = [], []
geometry={}

def component(kind, name, x, y, params=None, direction='right', extra=''):
    geometry[name]=(kind,x,y,direction,params or {})
    show='off' if kind in ['Label','From','Goto','SignalMux','SignalDemux','Ground'] else 'on'
    s = f'Component {{\n Type {kind}\n Name {q(name)}\n Show {show}\n Position [{x}, {y}]\n Direction {direction}\n Flipped off\n LabelPosition south\n'
    for k,v in (params or {}).items():
        s += f' Parameter {{ Variable {q(k)} Value {q(v)} Show off }}\n'
    parts.append(s + extra + '\n}')

def net(endpoints, point=None, signal=False):
    a,t = endpoints[0]
    s=f'Connection {{ Type {"Signal" if signal else "Wire"}\n SrcComponent {q(a)} SrcTerminal {t}\n'
    if point: s+=f' Points [{point[0]}, {point[1]}]\n'
    for b,u in endpoints[1:]:
        dest=f'DstComponent {q(b)} DstTerminal {u}'
        s+= (' Branch { '+dest+' }\n') if len(endpoints)>2 else dest+'\n'
    wires.append(s+'}')

def signal(a,t,b,u):
    # Native SignalMux numbering: output=1, inputs=2..N+1.
    muxes={'i_abc':3,'v_abc':3,'Results':6}
    if a in muxes: t=1
    if b in muxes: u+=1
    net([(a,t),(b,u)],signal=True)
def tag(name, terminal, label, x, y, signal_tag=False, source=False):
    cname=f'{name}_{label}_{terminal}'
    kind=('Goto' if source else 'From') if signal_tag else 'Label'
    component(kind,cname,x,y,{'Tag':label,'Visibility':1})
    signal(name,terminal,cname,1) if signal_tag and source else (signal(cname,1,name,terminal) if signal_tag else net([(name,terminal),(cname,1)]))

init='''% Hartmann et al., IEEE TIE 2012, Fig.1(b), Fig.6, Table III.
% Paper simulation: 115 Vrms phase, 800 Hz, 400 Vdc, 5 kW, 72 kHz, 330 uH.
Vph=115; fline=800; Vref=400; Pnom=5000; fsw=72000;
Lboost=330e-6; Cdc=18*82e-6; Rload=Vref^2/Pnom;
% Engineering assumptions: small winding resistance and ideal semiconductor losses.
RL=0.02; Rsw=0.001; Rd=0.001; Vd=0;
% Physical-unit current gain for ~4 kHz bandwidth; paper kp=0.25 uses unstated scaling.
Kcurrent=2*pi*4000*Lboost;
% Outer PI: 20 Hz natural frequency, zeta~0.707, conductance output in S.
Kpv=2*0.707*(2*pi*20)*Cdc*Vref/(3*Vph^2);
Kiv=(2*pi*20)^2*Cdc*Vref/(3*Vph^2);
Gmax=0.25; Ginit=Pnom/(3*Vph^2);
% Precharged capacitor; this baseline is not an inrush/precharge-hardware simulation.
Vinit=400; Tstop=0.12;
'''
(ROOT/'parameters.m').write_text(init)

component('ThreePhaseVoltageSource','Grid_115Vrms',100,190,{'V':'sqrt(2)*Vph','w':'fline','phi':'pi/2','neutral':1},'up')
component('Ground','Neutral',55,275,{},'up')
ne=[('Grid_115Vrms',4),('Neutral',1)]
for i,y in enumerate([140,190,240],1):
    component('Resistor',f'Rw{i}',180,y,{'R':'RL'})
    component('Inductor',f'L{i}',260,y,{'L':'Lboost','i_init':'0'})
    component('Ammeter',f'I{i}',330,y)
    component('Voltmeter',f'V{i}',145,330+65*(i-1),{},'up')
    net([('Grid_115Vrms',i),(f'Rw{i}',1),(f'V{i}',1)],(140,y))
    ne.append((f'V{i}',2))
    net([(f'Rw{i}',2),(f'L{i}',1)])
    net([(f'L{i}',2),(f'I{i}',1)])
    tag(f'I{i}',2,f'AC{i}',390,y)
    tag(f'I{i}',3,f'i{i}',330,y-35,True,True)
    tag(f'V{i}',3,f'v{i}',200,330+65*(i-1),True,True)
net(ne,(55,275))

# Six-diode bridge, explicitly wired at the phase midpoints.
pos=[]; neg=[]
for i,x in enumerate([510,620,730],1):
    for suffix,y in [('p',150),('n',260)]:
        component('Diode',f'D{i}{suffix}',x,y,{'Vf':'Vd','Ron':'Rd'},'down')
    component('Label',f'Bridge_AC{i}',x-35,205,{'Tag':f'AC{i}','Visibility':1})
    net([(f'D{i}p',1),(f'D{i}n',2),(f'Bridge_AC{i}',1)],(x,205))
    pos.append((f'D{i}p',2)); neg.append((f'D{i}n',1))
component('Capacitor','Cdc_1476uF',840,205,{'C':'Cdc','v_init':'Vinit'},'down')
component('Resistor','Load_5kW',960,205,{'R':'Rload'},'down')
component('Voltmeter','Vdc',1060,205,{},'up')
net(pos+[('Cdc_1476uF',1),('Load_5kW',1),('Vdc',1)],(840,100))
net(neg+[('Cdc_1476uF',2),('Load_5kW',2),('Vdc',2)],(840,310))
tag('Vdc',3,'vdc',1120,205,True,True)

# Common-source back-to-back MOSFETs, including body diodes (Fig.2a).
gates=['s12','s21','s23','s32','s13','s31']
for (a,b),y in zip([(1,2),(2,3),(1,3)],[390,495,600]):
    component('MosfetWithDiode',f'S{a}{b}',570,y,{'Ron':'Rsw','s_init':0},'right')
    component('MosfetWithDiode',f'S{b}{a}',690,y,{'Ron':'Rsw','s_init':0},'left')
    net([(f'S{a}{b}',2),(f'S{b}{a}',2)])
    tag(f'S{a}{b}',1,f'AC{a}',490,y)
    tag(f'S{b}{a}',1,f'AC{b}',770,y)
    tag(f'S{a}{b}',3,f's{a}{b}',570,y+40,True)
    tag(f'S{b}{a}',3,f's{b}{a}',690,y+40,True)

declarations='''#include <math.h>
#define PAR(i) ParamRealData(i,0)
static double limit(double x,double lo,double hi) { return x<lo?lo:(x>hi?hi:x); }
static int a[6]={0,1,1,2,0,2};
static int b[6]={1,0,2,1,2,0};
'''
output='''double v[3], vr[3];
double err=PAR(0)-InputSignal(2,0);
double raw=ContState(0)+PAR(2)*err;
double g=limit(raw,0,PAR(4));
double vo=fmax(InputSignal(2,0),50.0);
for(int k=0;k<3;k++) {
 v[k]=InputSignal(1,k);
 double ir=g*v[k];
 OutputSignal(1,k)=ir;
 vr[k]=v[k]-PAR(1)*(ir-InputSignal(0,k));
 ZCSignal(6+k)=v[k];
}
for(int k=0;k<6;k++) {
 double z=InputSignal(3,0)-(vr[a[k]]-vr[b[k]])/vo;
 ZCSignal(k)=z;
 if(IsMajorStep) {
   /* Table III: same-sign phase pair is clamped OFF;
      negative-to-positive device is held ON. */
   if(v[a[k]]*v[b[k]]>=0) OutputSignal(0,k)=0;
   else if(v[a[k]]<0) OutputSignal(0,k)=1;
   else OutputSignal(0,k)=z>0;
 }
}
OutputSignal(2,0)=g;
ZCSignal(9)=raw;
ZCSignal(10)=raw-PAR(4);
'''
derivative='''double e=PAR(0)-InputSignal(2,0);
double raw=ContState(0)+PAR(2)*e;
double d=PAR(3)*e;
if((raw<=0 && d<0)||(raw>=PAR(4) && d>0)) d=0;
ContDeriv(0)=d;
'''
for name,code in [('controller_declarations.c',declarations),('controller_output.c',output),('controller_derivative.c',derivative)]:
    (ROOT/name).write_text(code)
component('CScript','Hartmann_Control',310,790,{
 'NumInputs':'[3 3 1 1]','NumOutputs':'[6 3 1]','NumContStates':1,'NumDiscStates':0,
 'NumZCSignals':11,'DirectFeedthrough':1,'Ts':0,'TerminalBasedSampleTimes':1,
 'Parameters':'Vref,Kcurrent,Kpv,Kiv,Gmax,Ginit','LangStandard':2,'GnuExtensions':1,
 'RuntimeCheck':2,'Declarations':declarations,'StartFcn':'ContState(0)=PAR(5);',
 'OutputFcn':output,'DerivativeFcn':derivative,'UpdateFcn':'','TerminateFcn':''},'up')
for prefix,x,port,y in [('i',100,1,735),('v',100,2,815)]:
    component('SignalMux',f'{prefix}_abc',x,y,{'Width':3})
    for k in range(1,4):tag(f'{prefix}_abc',k,f'{prefix}{k}',x-60,y-10+10*(k-1),True)
    signal(f'{prefix}_abc',4,'Hartmann_Control',port)
tag('Hartmann_Control',3,'vdc',210,840,True)
component('TriangleGenerator','Carrier_72kHz',100,900,{'Min':0,'Max':1,'f':'fsw','DutyCycle':0.5,'Delay':0})
signal('Carrier_72kHz',1,'Hartmann_Control',4)
component('SignalDemux','Gate_Demux',650,780,{'Width':6})
signal('Hartmann_Control',5,'Gate_Demux',1)
for k,g in enumerate(gates):tag('Gate_Demux',k+2,g,730,755+k*10,True,True)

# One vector output for script-based verification; scopes provide interactive plots.
component('SignalMux','Results',850,900,{'Width':'[3 3 1 3 6 1]'})
signal('v_abc',4,'Results',1)
signal('i_abc',4,'Results',2)
tag('Results',3,'vdc',755,895,True)
signal('Hartmann_Control',6,'Results',4)
signal('Hartmann_Control',5,'Results',5)
signal('Hartmann_Control',7,'Results',6)
component('Output','SimulationData',1000,900,{'Index':1,'Width':17})
signal('Results',7,'SimulationData',1)
def scope(name,x,y,labels):
    axes=''
    for label in labels:
        axes+=f'Axis {{ Name {q(label)} AutoScale 1 MinValue -1 MaxValue 1 Signals {{}} SignalTypes [] AxisLabel {q(label)} Untangle 0 KeepBaseline off BaselineValue 0 }}\n'
    component('Scope',name,x,y,{},'up',f'Location [200, 100; 1200, 850]\nAxes {q(len(labels))}\nOpen "0"\nTs "-1"\nSampleLimit "0"\nXAxisLabel "Time (s)"\nShowLegend "1"\n'+axes)
scope('Main_Waveforms',1020,650,['v_abc (V)','i_abc (A)','Vdc (V)','i_ref (A)'])
signal('v_abc',4,'Main_Waveforms',1);signal('i_abc',4,'Main_Waveforms',2)
tag('Main_Waveforms',3,'vdc',920,650,True)
signal('Hartmann_Control',6,'Main_Waveforms',4)
scope('MOSFET_Gates',1030,730,['s12 s21 s23 s32 s13 s31'])
signal('Hartmann_Control',5,'MOSFET_Gates',1)

# Merge fanout signal connections, since a terminal may only have one Connection.
import re
group={}; electrical=[]
for w in wires:
    if 'Type Signal' not in w:electrical.append(w);continue
    m=re.search(r'SrcComponent ("[^"]*") SrcTerminal (\d+)',w)
    key=m.groups(); dest=re.search(r'DstComponent ("[^"]*") DstTerminal (\d+)',w).groups()
    group.setdefault(key,[]).append(dest)
wires=electrical
def sigpos(name,term,src=False):
    kind,x,y,dr,pa=geometry[name]
    term=int(term)
    if kind=='CScript': return (x+30,y+(term-6)*10) if src else (x-30,y+(term-2.5)*10)
    if kind=='SignalMux':
        n=6 if name=='Results' else 3
        return (x+10,y) if src else (x-10,y+(term-2-(n-1)/2)*10)
    if kind=='Scope':return (x-20,y+(term-(2.5 if name=='Main_Waveforms' else 1))*10)
    if kind=='TriangleGenerator':return x+15,y
    return x,y

for (name,term),destinations in group.items():
    plain=json.loads(name)
    # Keep vector fanouts local with named signal tags instead of canvas-spanning wires.
    if plain in ['i_abc','v_abc','Hartmann_Control','Carrier_72kHz']:
        sx,sy=sigpos(plain,term,True)
        lab={'i_abc':'Iabc','v_abc':'Vabc','Carrier_72kHz':'carrier'}.get(plain,{'5':'gates','6':'Iref','7':'Gref'}.get(term,'sig'))
        gn='Send_'+lab
        component('Goto',gn,sx+55,sy,{'Tag':lab,'Visibility':1})
        wires.append(f'Connection {{ Type Signal SrcComponent {name} SrcTerminal {term} DstComponent {q(gn)} DstTerminal 1 }}')
        for j,(dn,dt) in enumerate(destinations):
            dx,dy=sigpos(json.loads(dn),dt)
            fn=f'Receive_{lab}_{j}'
            component('From',fn,dx-65,dy,{'Tag':lab,'Visibility':1})
            wires.append(f'Connection {{ Type Signal SrcComponent {q(fn)} SrcTerminal 1 DstComponent {dn} DstTerminal {dt} }}')
        continue
    s=f'Connection {{ Type Signal SrcComponent {name} SrcTerminal {term}\n'
    for name2,term2 in destinations:
        d=f'DstComponent {name2} DstTerminal {term2}'
        s+=('Branch { '+d+' }\n') if len(destinations)>1 else d+'\n'
    wires.append(s+'}')

annotations=[(400,35,'Hartmann 2012 | Three-phase Delta-switch rectifier | 5 kW'),
 (630,345,'Delta branches: common-source MOSFET pairs with body diodes'),
 (280,665,'Fig.6: voltage PI + phase current P + voltage feedforward + star/delta + Table III PWM'),
 (650,950,'Baseline: precharged 400 V bus; no EMI filter or thermal model. Parameters: Simulation > Simulation Parameters > Initialization.')]
ann='\n'.join(f'Annotation {{ Name {q(t)} Position [{x}, {y}] }}' for x,y,t in annotations)
header=f'''Plecs {{
Name "Hartmann_DeltaSwitch"
Version "4.9"
CircuitModel "ContStateSpace"
StartTime "0"
TimeSpan "Tstop"
Solver "auto"
MaxStep "1/(fsw*10)"
InitStep "-1"
FixedStep "1e-7"
Refine "1"
ZCStepSize "1e-10"
RelTol "1e-6"
AbsTol "1e-8"
MaxConsecutiveZCs "1000"
InitializationCommands {q(init)}
InitialState "1"
Terminal {{ Type Output Index "1" }}
Schematic {{
Location [0, 30; 1500, 1020]
ZoomFactor 1
SliderPosition [0, 0]
ShowBrowser off
'''
path=ROOT/'Hartmann_DeltaSwitch.plecs'
path.write_text(header+'\n'.join(parts+wires)+'\n'+ann+'\n}\n}\n')
print(path)
