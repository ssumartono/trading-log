// Original Pine: Consolidation Range with Signals © Zeiierman.
// MT5 adaptation licensed CC BY-NC-SA 4.0 (noncommercial, share alike).
#property copyright "Original © Zeiierman; MT5 adaptation"
#property link "https://creativecommons.org/licenses/by-nc-sa/4.0/"
#property version "1.10"
#include <Canvas\Canvas.mqh>
#property indicator_chart_window
#property indicator_buffers 12
#property indicator_plots 9
#property indicator_type1 DRAW_FILLING
#property indicator_type2 DRAW_FILLING
#property indicator_type3 DRAW_COLOR_LINE
#property indicator_type4 DRAW_LINE
#property indicator_type5 DRAW_LINE
#property indicator_type6 DRAW_LINE
#property indicator_type7 DRAW_LINE
#property indicator_type8 DRAW_ARROW
#property indicator_type9 DRAW_ARROW
#property indicator_label1 "Upper zone"
#property indicator_label2 "Lower zone"
#property indicator_label3 "Range filter"
#property indicator_label4 "MID1"
#property indicator_label5 "MID2"
#property indicator_label6 "MID3"
#property indicator_label7 "MID4"
#property indicator_label8 "Buy"
#property indicator_label9 "Sell"
enum RangeDetection { ADX_Method, Volatility_Method };
input RangeDetection Method=ADX_Method;
input int RangePeriod=10;
input double RangeMultiplier=1.8;
input double ADXThreshold=17;
input int ADXSmoothing=10;
input double StdDevMultiplier=0.8;
input double VarianceMultiplier=0.8;
input double ATRMultiplier=0.9;
input color UpperColor=C'0,96,230';
input color LowerColor=C'41,250,250';
input color UpperFill=C'10,35,78';
input color LowerFill=C'16,65,76';
input bool ShowTargets=true;
input int CooldownBars=20;
input double SLMultiplier=0.4;
input double TP1Multiplier=0.5;
input double TP2Multiplier=1.0;
input double TP3Multiplier=2.0;
input bool ShowSL=true;
input bool ShowTP1=true;
input bool ShowTP2=true;
input bool ShowTP3=true;
input int LevelLengthBars=20;
input int MaxSignalGroups=3;
input int LabelFontSize=9;
input int LabelMinimumGap=5;
input bool ShowLevelPrices=false;
input color EntryColor=clrBlue;
input color StopColor=clrRed;
input color BuyTargetColor=C'9,193,15';
input color SellTargetColor=C'255,105,203';
input bool ClosedBarSignals=true;
input bool ShowArrows=false;
input bool PopupAlerts=false;
input bool PushAlerts=false;
input bool SoundAlerts=false;
double U[],UB[],L[],LB[],F[],FC[],M1[],M2[],M3[],M4[],Buy[],Sell[];
string prefix;
datetime lastBar=0,lastAlert=0;
bool initialized=false;
CCanvas zoneCanvas,labelCanvas;
struct LevelTag { datetime t; double price; string text; color col; };
LevelTag tags[];
color Blend(color a,color b,double weight)
{
 int ar=(int)a&255,ag=((int)a>>8)&255,ab=((int)a>>16)&255;
 int br=(int)b&255,bg=((int)b>>8)&255,bb=((int)b>>16)&255;
 return (color)((int)(ar+(br-ar)*weight)|((int)(ag+(bg-ag)*weight)<<8)|((int)(ab+(bb-ab)*weight)<<16));
}
void Paint()
{
 int w=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS),h=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
 if(w<2 || h<2 || ArraySize(F)<1) return;
 if(zoneCanvas.Width()!=w || zoneCanvas.Height()!=h)
 {
  zoneCanvas.Destroy(); labelCanvas.Destroy();
  if(!zoneCanvas.CreateBitmapLabel(0,0,prefix+"ZoneCanvas",0,0,w,h,COLOR_FORMAT_ARGB_NORMALIZE)) return;
  if(!labelCanvas.CreateBitmapLabel(0,0,prefix+"TagCanvas",0,0,w,h,COLOR_FORMAT_ARGB_NORMALIZE)) return;
  ObjectSetInteger(0,prefix+"ZoneCanvas",OBJPROP_BACK,true);
  ObjectSetInteger(0,prefix+"TagCanvas",OBJPROP_BACK,false);
  ObjectSetInteger(0,prefix+"ZoneCanvas",OBJPROP_SELECTABLE,false);
  ObjectSetInteger(0,prefix+"TagCanvas",OBJPROP_SELECTABLE,false);
 }
 zoneCanvas.Erase(0); labelCanvas.Erase(0);
 int n=ArraySize(F),first=(int)ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR),shown=(int)ChartGetInteger(0,CHART_VISIBLE_BARS);
 int a=MathMax(2000,n-1-first-1),b=MathMin(n-1,n-first+shown);
 color bg=(color)ChartGetInteger(0,CHART_COLOR_BACKGROUND);
 for(int i=a;i<=b;i++)
 {
  if(F[i]==EMPTY_VALUE) continue;
  datetime t=iTime(_Symbol,_Period,n-1-i);
  datetime next=(i+1<n)?iTime(_Symbol,_Period,n-2-i):t+PeriodSeconds(_Period);
  int x,y,x2,yt,yb,dummy;
  if(!ChartTimePriceToXY(0,0,t,F[i],x,y) || !ChartTimePriceToXY(0,0,next,F[i],x2,dummy)) continue;
  ChartTimePriceToXY(0,0,t,M2[i],dummy,yt); ChartTimePriceToXY(0,0,t,M4[i],dummy,yb);
  int left=MathMax(0,x),right=MathMin(w-1,x2);
  if(right<left) continue;
  for(int z=0;z<12;z++)
  {
   double v1=(double)z/12,v2=(double)(z+1)/12;
   uint uc=ColorToARGB(Blend(bg,UpperColor,0.03+0.31*v2));
   uint lc=ColorToARGB(Blend(bg,LowerColor,0.03+0.31*v2));
   zoneCanvas.FillRectangle(left,(int)(y+(yt-y)*v2),right,(int)(y+(yt-y)*v1),uc);
   zoneCanvas.FillRectangle(left,(int)(y+(yb-y)*v1),right,(int)(y+(yb-y)*v2),lc);
  }
  zoneCanvas.Line(left,yt,right,yt,ColorToARGB(UpperColor));
  zoneCanvas.Line(left,yb,right,yb,ColorToARGB(LowerColor));
  zoneCanvas.Line(left,y,right,y,ColorToARGB(FC[i]==0?UpperColor:LowerColor));
  int ym; ChartTimePriceToXY(0,0,t,M1[i],dummy,ym);
  zoneCanvas.Line(left,ym,right,ym,ColorToARGB(Blend(bg,UpperColor,0.5)));
  ChartTimePriceToXY(0,0,t,M3[i],dummy,ym);
  zoneCanvas.Line(left,ym,right,ym,ColorToARGB(Blend(bg,LowerColor,0.5)));
  if(i==a || F[i-1]==EMPTY_VALUE)
   zoneCanvas.Line(left,yt,left,yb,ColorToARGB(Blend(bg,LowerColor,0.6)));
  if(i==b || i+1>=n || F[i+1]==EMPTY_VALUE)
   zoneCanvas.Line(right,yt,right,yb,ColorToARGB(Blend(bg,UpperColor,0.6)));
 }
 labelCanvas.FontSet("Arial",-LabelFontSize*10,FW_BOLD);
 int usedY[],usedX[],usedW[]; int used=0;
 ArrayResize(usedY,ArraySize(tags)); ArrayResize(usedX,ArraySize(tags)); ArrayResize(usedW,ArraySize(tags));
 // Newest labels receive priority; older groups are hidden if they would overlap.
 for(int j=ArraySize(tags)-1;j>=0;j--)
 {
  int x,y;
  if(!ChartTimePriceToXY(0,0,tags[j].t,tags[j].price,x,y)) continue;
  string text=tags[j].text+(ShowLevelPrices?" "+DoubleToString(tags[j].price,_Digits):"");
  int tw=(int)labelCanvas.TextWidth(text)+18,th=(int)labelCanvas.TextHeight(text)+8;
  int left=x+6,top=y-th/2;
  if(left<0 || left+tw>=w-55 || top<0 || top+th>=h) continue;
  bool overlap=false;
  for(int k=0;k<used;k++)
   if(left<usedX[k]+usedW[k]+LabelMinimumGap && left+tw+LabelMinimumGap>usedX[k] && MathAbs(top-usedY[k])<th+LabelMinimumGap) { overlap=true; break; }
  if(overlap) continue;
  usedX[used]=left; usedY[used]=top; usedW[used]=tw; used++;
  uint c=ColorToARGB(tags[j].col);
  labelCanvas.FillRectangle(left,top,left+tw,top+th,c);
  for(int z=0;z<6;z++) labelCanvas.Line(left-z,y-z,left-z,y+z,c);
  labelCanvas.TextOut(left+9,top+4,text,ColorToARGB(clrWhite));
 }
 zoneCanvas.Update(); labelCanvas.Update(); ChartRedraw();
}
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
{
 if(id==CHARTEVENT_CHART_CHANGE) Paint();
}

void Level(string key,datetime t,datetime end,double price,string label,color col)
{
 string name=prefix+"LV_"+key;
 ObjectCreate(0,name,OBJ_TREND,0,t,price,end,price);
 ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,false);
 ObjectSetInteger(0,name,OBJPROP_COLOR,col);
 ObjectSetInteger(0,name,OBJPROP_WIDTH,2);
 ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
 int n=ArraySize(tags); ArrayResize(tags,n+1);
 tags[n].t=end; tags[n].price=price; tags[n].text=label; tags[n].col=col;
}
int OnInit()
{
 if(RangePeriod<2 || ADXSmoothing<1 || RangeMultiplier<=0 || CooldownBars<0 || LevelLengthBars<1 || MaxSignalGroups<1 || LabelFontSize<6 || LabelMinimumGap<0 || SLMultiplier<=0 || TP1Multiplier<=0 || TP2Multiplier<=0 || TP3Multiplier<=0 || StdDevMultiplier<=0 || VarianceMultiplier<=0 || ATRMultiplier<=0) return INIT_PARAMETERS_INCORRECT;
 SetIndexBuffer(0,U); SetIndexBuffer(1,UB); SetIndexBuffer(2,L); SetIndexBuffer(3,LB);
 SetIndexBuffer(4,F); SetIndexBuffer(5,FC,INDICATOR_COLOR_INDEX);
 SetIndexBuffer(6,M1); SetIndexBuffer(7,M2); SetIndexBuffer(8,M3); SetIndexBuffer(9,M4);
 SetIndexBuffer(10,Buy); SetIndexBuffer(11,Sell);
 PlotIndexSetInteger(0,PLOT_LINE_COLOR,UpperFill); PlotIndexSetInteger(1,PLOT_LINE_COLOR,LowerFill);
 PlotIndexSetInteger(2,PLOT_COLOR_INDEXES,2);
 PlotIndexSetInteger(2,PLOT_LINE_COLOR,0,UpperColor); PlotIndexSetInteger(2,PLOT_LINE_COLOR,1,LowerColor);
 for(int p=3;p<=6;p++) PlotIndexSetInteger(p,PLOT_LINE_COLOR,p<=4?UpperColor:LowerColor);
 PlotIndexSetInteger(7,PLOT_ARROW,233); PlotIndexSetInteger(8,PLOT_ARROW,234);
 PlotIndexSetInteger(7,PLOT_LINE_COLOR,BuyTargetColor); PlotIndexSetInteger(8,PLOT_LINE_COLOR,SellTargetColor);
 for(int p=0;p<9;p++) PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
 for(int p=0;p<7;p++) PlotIndexSetInteger(p,PLOT_DRAW_TYPE,DRAW_NONE);
 prefix="CRZ_"+IntegerToString(ChartID())+"_"+IntegerToString(GetTickCount())+"_";
 IndicatorSetString(INDICATOR_SHORTNAME,"Consolidation Range (Zeiierman MT5)");
 IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { zoneCanvas.Destroy(); labelCanvas.Destroy(); ObjectsDeleteAll(0,prefix); }
int OnCalculate(const int total,const int calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
{
 ArraySetAsSeries(time,false); ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);
 if(total<2002) { Comment("Consolidation Range: memerlukan minimal 2002 bar riwayat."); return 0; }
 if(ClosedBarSignals && calculated==total && lastBar==time[total-1]) return total;
 lastBar=time[total-1];
 ArrayInitialize(U,EMPTY_VALUE); ArrayInitialize(UB,EMPTY_VALUE); ArrayInitialize(L,EMPTY_VALUE); ArrayInitialize(LB,EMPTY_VALUE);
 ArrayInitialize(F,EMPTY_VALUE); ArrayInitialize(M1,EMPTY_VALUE); ArrayInitialize(M2,EMPTY_VALUE); ArrayInitialize(M3,EMPTY_VALUE); ArrayInitialize(M4,EMPTY_VALUE);
 ArrayInitialize(Buy,EMPTY_VALUE); ArrayInitialize(Sell,EMPTY_VALUE);
 ObjectsDeleteAll(0,prefix+"LV_"); ArrayResize(tags,0);
 double st[],vr[],at[],ret[]; ArrayResize(st,total); ArrayResize(vr,total); ArrayResize(at,total); ArrayResize(ret,total);
 ArrayInitialize(st,0); ArrayInitialize(vr,0); ArrayInitialize(at,0); ArrayInitialize(ret,0);
 double trR=0,plusR=0,minusR=0,adx=0,dxSum=0,rSum=0,filt=0,hiPrev=0,loPrev=0;
 int dxCount=0,lastSignal=-1000000,trend=0;
 bool visible=false,haveRange=false;
 int signalBars[]; ArrayResize(signalBars,total); int count=0;
 double signalBase[],signalR[]; int signalDir[];
 ArrayResize(signalBase,total); ArrayResize(signalR,total); ArrayResize(signalDir,total);
 int end=ClosedBarSignals?total-2:total-1;
 for(int i=1;i<=end;i++)
 {
  double tr=MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
  double up=high[i]-high[i-1],dn=low[i-1]-low[i];
  double pd=(up>dn && up>0)?up:0,md=(dn>up && dn>0)?dn:0;
  if(i<=RangePeriod) { trR+=tr/RangePeriod; plusR+=pd/RangePeriod; minusR+=md/RangePeriod; }
  else { trR+=(tr-trR)/RangePeriod; plusR+=(pd-plusR)/RangePeriod; minusR+=(md-minusR)/RangePeriod; }
  at[i]=trR;
  if(i>=RangePeriod)
  {
   double denom=plusR+minusR;
   double dx=denom>0?100*MathAbs(plusR-minusR)/denom:0;
   if(dxCount<ADXSmoothing) { dxSum+=dx; dxCount++; adx=dxSum/ADXSmoothing; }
   else adx+=(dx-adx)/ADXSmoothing;
  }
  ret[i]=(close[i]>0 && close[i-1]>0)?MathLog(close[i]/close[i-1]):0;
  if(i>=RangePeriod)
  {
   double mean=0,var=0;
   for(int j=i-RangePeriod+1;j<=i;j++) mean+=ret[j]/RangePeriod;
   for(int j=i-RangePeriod+1;j<=i;j++) var+=(ret[j]-mean)*(ret[j]-mean)/RangePeriod;
   vr[i]=var; st[i]=MathSqrt(var);
  }
  bool detected=false;
  if(Method==ADX_Method) detected=dxCount>=ADXSmoothing && adx<ADXThreshold;
  else if(i>=2*RangePeriod-1)
  {
   double sa=0,va=0,aa=0;
   for(int j=i-RangePeriod+1;j<=i;j++) { sa+=st[j]/RangePeriod; va+=vr[j]/RangePeriod; aa+=at[j]/RangePeriod; }
   detected=st[i]<sa*StdDevMultiplier && vr[i]<va*VarianceMultiplier && at[i]<aa*ATRMultiplier;
  }
  rSum+=2.618*MathAbs(high[i]-low[i-1]);
  if(i>2000) rSum-=2.618*MathAbs(high[i-2000]-low[i-2001]);
  if(i<2000) continue;
  double r=rSum/2000*RangeMultiplier;
  if(r<=0) continue;
  double prev=filt;
  // Pine pricejump simplifies to close when the distance reaches r.
  if(close[i]>=prev+r || close[i]<=prev-r) filt=close[i];
  else if(close[i]>prev) filt=(close[i]-r<prev)?prev:close[i]-r;
  else filt=(close[i]+r>prev)?prev:close[i]+r;
  bool rising=filt>prev,falling=filt<prev;
  if(rising) trend=0; else if(falling) trend=1;
  if(detected) { visible=true; hiPrev=filt+r; loPrev=filt-r; haveRange=true; }
  if(!detected && haveRange && (close[i-1]>hiPrev || close[i-1]<loPrev)) visible=false;
  if(visible)
  {
   F[i]=filt; FC[i]=trend;
   M1[i]=filt+r/3; M2[i]=filt+2*r/3; M3[i]=filt-r/3; M4[i]=filt-2*r/3;
   U[i]=M2[i]; UB[i]=filt; L[i]=filt; LB[i]=M4[i];
  }
  bool signal=visible && (rising || falling) && i-lastSignal>=CooldownBars;
  if(signal)
  {
   if(ShowArrows) { if(rising) Buy[i]=low[i]-r*0.08; else Sell[i]=high[i]+r*0.08; }
   if(ShowTargets)
   {
    signalBars[count]=i; signalBase[count]=filt; signalR[count]=r; signalDir[count]=rising?1:-1; count++;
    lastSignal=i; // Original updates cooldown only when ShowTargets is enabled.
   }
   if(i==end && initialized && time[i]!=lastAlert)
   {
    lastAlert=time[i]; string msg=_Symbol+" "+EnumToString(_Period)+(rising?" BUY":" SELL")+" | Consolidation Range | "+DoubleToString(close[i],_Digits);
    if(PopupAlerts) Alert(msg); if(PushAlerts) SendNotification(msg); if(SoundAlerts) PlaySound("alert.wav");
   }
  }
 }
 for(int k=MathMax(0,count-MaxSignalGroups);k<count;k++)
 {
  int i=signalBars[k],d=signalDir[k]; double b=signalBase[k],r=signalR[k];
  datetime finish=(i+LevelLengthBars<total)?time[i+LevelLengthBars]:time[total-1]+(datetime)((i+LevelLengthBars-total+1)*PeriodSeconds(_Period));
  string key=IntegerToString((long)time[i]); color col=d>0?BuyTargetColor:SellTargetColor;
  Level(key+"E",time[i],finish,close[i],"Entry",EntryColor);
  if(ShowSL) Level(key+"S",time[i],finish,b-d*r*SLMultiplier,"SL",StopColor);
  if(ShowTP1) Level(key+"1",time[i],finish,b+d*r*TP1Multiplier,"TP 1",col);
  if(ShowTP2) Level(key+"2",time[i],finish,b+d*r*TP2Multiplier,"TP 2",col);
  if(ShowTP3) Level(key+"3",time[i],finish,b+d*r*TP3Multiplier,"TP 3",col);
 }
 initialized=true;
 Paint();
 return total;
}
