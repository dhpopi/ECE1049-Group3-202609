% Hartmann et al., IEEE TIE 2012, Fig.1(b), Fig.6, Table III.
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
