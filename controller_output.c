double v[3], vr[3];
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
