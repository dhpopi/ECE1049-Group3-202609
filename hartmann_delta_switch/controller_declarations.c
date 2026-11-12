#include <math.h>
#define PAR(i) ParamRealData(i,0)
static double limit(double x,double lo,double hi) { return x<lo?lo:(x>hi?hi:x); }
static int a[6]={0,1,1,2,0,2};
static int b[6]={1,0,2,1,2,0};
