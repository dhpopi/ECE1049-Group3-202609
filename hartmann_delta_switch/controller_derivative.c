double e=PAR(0)-InputSignal(2,0);
double raw=ContState(0)+PAR(2)*e;
double d=PAR(3)*e;
if((raw<=0 && d<0)||(raw>=PAR(4) && d>0)) d=0;
ContDeriv(0)=d;
