// Original Pine: Tension Flow Trend [BigBeluga] - Historical RR, © BigBeluga.
// MT5 adaptation. CC BY-NC-SA 4.0: attribution, noncommercial, share alike.
#property copyright "Original © BigBeluga; MT5 adaptation"
#property link "https://creativecommons.org/licenses/by-nc-sa/4.0/"
#property version "1.00"
#property indicator_chart_window
#property indicator_buffers 5
#property indicator_plots 4
#property indicator_type1 DRAW_COLOR_LINE
#property indicator_color1 C'0,255,187',C'255,0,85'
#property indicator_width1 2
#property indicator_label1 "Trend Baseline"
#property indicator_type2 DRAW_NONE
#property indicator_label2 "Bull START"
#property indicator_type3 DRAW_NONE
#property indicator_label3 "Bear START"
#property indicator_type4 DRAW_NONE
#property indicator_label4 "Z-Score"
#include <Canvas\Canvas.mqh>
input int HMALength=50;
input int ZScoreLength=50;
input double RibbonWidth=0.5;
input int SignalCooldown=30;
input bool ShowStartLabels=true;
input bool ShowEnergyDashboard=true;
input bool ShowRRDashboard=true;
input double StopLossATRMultiplier=2.0;
input double RiskRewardRatio=1.0;
input int BacktestTradeWindow=100;
input color BullColor=C'0,255,187';
input color BearColor=C'255,0,85';
input bool ClosedBarSignals=false; // false reproduces the original Pine live-bar behavior
input int MaxVisibleTrades=250; // Pine's 500 boxes = 250 pairs; stats use all trades
input int PanelFontSize=14;
double H[],HC[],Buy[],Sell[],Z[];
double Raw[],Dist[],A14[],A200[];
datetime Times[];
struct Trade { int start; int finish; int dir; double entry; double sl; double tp; bool active; };
Trade Trades[];
int outcomes[],tradeCount=0,wins=0,losses=0;
CCanvas art,ui;
string prefix;
// Linear-time weighted moving average, chronological arrays.
void WMA(const double &src[],double &dst[],int n,int len,int valid)
{
 ArrayResize(dst,n); ArrayInitialize(dst,EMPTY_VALUE);
 double sum=0,weighted=0,den=(double)len*(len+1)/2;
 for(int i=valid;i<n;i++)
 {
  weighted+=len*src[i]-sum; sum+=src[i];
  if(i>=valid+len) sum-=src[i-len];
  if(i>=valid+len-1) dst[i]=weighted/den;
 }
}
int OnInit()
{
 if(HMALength<1 || ZScoreLength<1 || SignalCooldown<1 || RibbonWidth<0 || StopLossATRMultiplier<=0 || RiskRewardRatio<=0 || BacktestTradeWindow<1 || MaxVisibleTrades<1 || PanelFontSize<8) return INIT_PARAMETERS_INCORRECT;
 SetIndexBuffer(0,H,INDICATOR_DATA); SetIndexBuffer(1,HC,INDICATOR_COLOR_INDEX);
 SetIndexBuffer(2,Buy,INDICATOR_DATA); SetIndexBuffer(3,Sell,INDICATOR_DATA); SetIndexBuffer(4,Z,INDICATOR_DATA);
 PlotIndexSetInteger(0,PLOT_LINE_COLOR,0,BullColor); PlotIndexSetInteger(0,PLOT_LINE_COLOR,1,BearColor);
 IndicatorSetString(INDICATOR_SHORTNAME,"Tension Flow Trend [BigBeluga] - Historical RR");
 prefix="TFT_"+IntegerToString(ChartID())+"_"+IntegerToString(GetTickCount())+"_";
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { art.Destroy(); ui.Destroy(); ChartRedraw(); }
bool XY(int i,double p,int &x,int &y) { return ChartTimePriceToXY(0,0,Times[i],p,x,y); }
void Box(int start,int finish,double p1,double p2,color c)
{
 int x1,y1,x2,y2; if(!XY(start,p1,x1,y1)||!XY(finish,p2,x2,y2)) return;
 int l=MathMax(0,MathMin(x1,x2)),r=MathMin(art.Width()-1,MathMax(x1,x2));
 int t=MathMax(0,MathMin(y1,y2)),b=MathMin(art.Height()-1,MathMax(y1,y2));
 if(l>r||t>b) return;
 art.FillRectangle(l,t,r,b,ColorToARGB(c,38));
 art.Rectangle(l,t,r,b,ColorToARGB(c,153));
}
void Cell(int x,int y,int w,string s,color bg,color fg)
{
 ui.FillRectangle(x,y,x+w-1,y+27,ColorToARGB(bg));
 ui.Rectangle(x,y,x+w-1,y+27,ColorToARGB(C'50,55,65'));
 ui.TextOut(x+w/2,y+14,s,ColorToARGB(fg),TA_CENTER|TA_VCENTER);
}
void Paint()
{
 int n=ArraySize(Times); if(n<2) return;
 int w=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS),h=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS,0);
 if(w<10||h<10) return;
 if(art.Width()!=w||art.Height()!=h)
 {
  art.Destroy(); ui.Destroy();
  if(!art.CreateBitmapLabel(0,0,prefix+"Art",0,0,w,h,COLOR_FORMAT_ARGB_NORMALIZE)) return;
  if(!ui.CreateBitmapLabel(0,0,prefix+"UI",0,0,w,h,COLOR_FORMAT_ARGB_NORMALIZE)) return;
  ObjectSetInteger(0,prefix+"Art",OBJPROP_BACK,true);
  ObjectSetInteger(0,prefix+"Art",OBJPROP_SELECTABLE,false);
  ObjectSetInteger(0,prefix+"UI",OBJPROP_SELECTABLE,false);
 }
 art.Erase(0); ui.Erase(0); ui.FontSet("Arial",PanelFontSize); art.FontSet("Arial",PanelFontSize);
 for(int k=MathMax(0,tradeCount-MaxVisibleTrades);k<tradeCount;k++)
 {
  Trade t=Trades[k]; Box(t.start,t.finish,t.entry,t.sl,BearColor); Box(t.start,t.finish,t.entry,t.tp,BullColor);
  int x,y; if(XY((t.start+t.finish)/2,(t.entry+t.tp)/2,x,y)&&x>0&&x<w&&y>0&&y<h)
   art.TextOut(x,y,"RR: "+DoubleToString(RiskRewardRatio,1),ColorToARGB(clrWhite),TA_CENTER|TA_VCENTER);
 }
 int first=(int)ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR),visible=(int)ChartGetInteger(0,CHART_VISIBLE_BARS);
 int a=MathMax(1,n-2-first),b=MathMin(n-1,n-first+visible);
 for(int i=a;i<=b;i++)
 {
  if(H[i]==EMPTY_VALUE||H[i-1]==EMPTY_VALUE||A14[i]==EMPTY_VALUE) continue;
  int x0,y0,x1,y1,xx,top0,top1,bot0,bot1;
  if(!XY(i-1,H[i-1],x0,y0)||!XY(i,H[i],x1,y1)) continue;
  XY(i-1,H[i-1]+A14[i-1]*RibbonWidth,xx,top0); XY(i,H[i]+A14[i]*RibbonWidth,xx,top1);
  XY(i-1,H[i-1]-A14[i-1]*RibbonWidth,xx,bot0); XY(i,H[i]-A14[i]*RibbonWidth,xx,bot1);
  color c=HC[i]==0?BullColor:BearColor;
  double strength=Z[i]==EMPTY_VALUE?10:MathMin(90,MathMax(10,MathAbs(Z[i])*25));
  double alpha=255*MathMin(100,20+strength)/100;
  for(int x=MathMax(0,x0);x<=MathMin(w-1,x1);x++)
  {
   double f=x1==x0?1:(double)(x-x0)/(x1-x0);
   double mid=y0+(y1-y0)*f,up=top0+(top1-top0)*f,dn=bot0+(bot1-bot0)*f;
   for(int y=MathMax(0,(int)up);y<=MathMin(h-1,(int)dn);y++)
   {
    double q=y<mid?(mid-y)/MathMax(1,mid-up):(y-mid)/MathMax(1,dn-mid);
    art.PixelSet(x,y,ColorToARGB(c,(uchar)MathMin(255,alpha*q)));
   }
  }
 }
 if(ShowStartLabels) for(int i=a;i<=b;i++)
 {
  bool buy=Buy[i]!=EMPTY_VALUE; if(!buy&&Sell[i]==EMPTY_VALUE) continue;
  int x,y; if(!XY(i,buy?Buy[i]:Sell[i],x,y)||x<0||x>w) continue;
  color c=buy?BullColor:BearColor;
  ui.FillRectangle(x-24,y-9,x+24,y+9,ColorToARGB(c,128));
  ui.TextOut(x,y,"START",ColorToARGB(clrWhite),TA_CENTER|TA_VCENTER);
 }
 if(ShowRRDashboard&&w>260)
 {
  int x=w-250,y=15; double rate=wins+losses>0?100.0*wins/(wins+losses):0;
  string labels[5]={"RR Performance","Wins","X  Losses","Win Rate","Sample (last)"};
  string values[5]; values[0]="RR "+DoubleToString(RiskRewardRatio,1)+":1"; values[1]=(string)wins; values[2]=(string)losses; values[3]=DoubleToString(rate,1)+"%"; values[4]=(string)(wins+losses)+" / "+(string)BacktestTradeWindow;
  for(int j=0;j<5;j++)
  {
   color bg=C'19,23,34'; if(j==1) bg=C'18,66,42'; if(j==2) bg=C'78,30,35'; if(j==3) bg=rate>=55?C'34,150,80':rate>=40?clrOrange:C'200,55,55';
   Cell(x,y+j*28,145,labels[j],C'19,23,34',clrWhite); Cell(x+145,y+j*28,95,values[j],bg,clrWhite);
  }
 }
 if(ShowEnergyDashboard&&w>220&&h>100)
 {
  int x=w-220,y=h-75; bool ready=Z[n-1]!=EMPTY_VALUE;
  color c=ready&&MathAbs(Z[n-1])>2?clrOrange:HC[n-1]==0?BullColor:BearColor;
  Cell(x,y,85,"Z-Score",C'19,23,34',clrWhite); Cell(x+85,y,125,ready?DoubleToString(Z[n-1],2):"N/A",C'19,23,34',c);
  Cell(x,y+28,85,"Status",C'19,23,34',clrWhite); Cell(x+85,y+28,125,!ready?"Warming up":MathAbs(Z[n-1])>2?"Overextended":"Strong",C'19,23,34',c);
 }
 art.Update(false); ui.Update();
}
void OnChartEvent(const int id,const long &lp,const double &dp,const string &sp) { if(id==CHARTEVENT_CHART_CHANGE) Paint(); }
int OnCalculate(const int n,const int prev,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tv[],const long &vol[],const int &spread[])
{
 ArraySetAsSeries(time,false); ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);
 ArraySetAsSeries(H,false); ArraySetAsSeries(HC,false); ArraySetAsSeries(Buy,false); ArraySetAsSeries(Sell,false); ArraySetAsSeries(Z,false);
 ArrayCopy(Times,time); ArrayResize(Dist,n); ArrayResize(A14,n); ArrayResize(A200,n);
 ArrayInitialize(H,EMPTY_VALUE); ArrayInitialize(HC,0); ArrayInitialize(Buy,EMPTY_VALUE); ArrayInitialize(Sell,EMPTY_VALUE); ArrayInitialize(Z,EMPTY_VALUE); ArrayInitialize(Dist,0); ArrayInitialize(A14,EMPTY_VALUE); ArrayInitialize(A200,EMPTY_VALUE);
 int half=MathMax(1,HMALength/2),root=MathMax(1,(int)MathRound(MathSqrt(HMALength)));
 double fast[],slow[]; WMA(close,fast,n,half,0); WMA(close,slow,n,HMALength,0);
 ArrayResize(Raw,n); ArrayInitialize(Raw,0);
 for(int i=HMALength-1;i<n;i++) Raw[i]=2*fast[i]-slow[i];
 double hull[]; WMA(Raw,hull,n,root,HMALength-1);
 int valid=HMALength+root-2;
 tradeCount=0; wins=0; losses=0; ArrayResize(Trades,n); ArrayResize(outcomes,BacktestTradeWindow);
 int history=0,write=0,lastSignal=-100;
 double tr14=0,tr200=0;
 for(int i=0;i<n;i++)
 {
  double tr=i==0?high[i]-low[i]:MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
  if(i<14) tr14+=tr; if(i==13) A14[i]=tr14/14; if(i>13) A14[i]=(A14[i-1]*13+tr)/14;
  if(i<200) tr200+=tr; if(i==199) A200[i]=tr200/200; if(i>199) A200[i]=(A200[i-1]*199+tr)/200;
  H[i]=hull[i]; if(i<valid) continue;
  bool up=i>valid&&H[i]>H[i-1]; HC[i]=up?0:1; Dist[i]=close[i]-H[i];
  if(i>=valid+ZScoreLength-1)
  {
   double mean=0,var=0; for(int j=0;j<ZScoreLength;j++) mean+=Dist[i-j]; mean/=ZScoreLength;
   for(int j=0;j<ZScoreLength;j++) var+=(Dist[i-j]-mean)*(Dist[i-j]-mean);
   if(var>0) Z[i]=Dist[i]/MathSqrt(var/ZScoreLength);
  }
  bool allowed=!ClosedBarSignals||i<n-1;
  bool bull=i>valid&&up&&close[i]>H[i]&&close[i-1]<=H[i-1]&&i-lastSignal>=SignalCooldown&&allowed;
  bool bear=i>valid&&!up&&close[i]<H[i]&&close[i-1]>=H[i-1]&&i-lastSignal>=SignalCooldown&&allowed;
  if(bull||bear)
  {
   lastSignal=i;
   double pad=A14[i]==EMPTY_VALUE?10*_Point:A14[i]*0.3;
   if(bull) Buy[i]=low[i]-pad; else Sell[i]=high[i]+pad;
   bool change=i>valid&&HC[i]!=HC[i-1],prior=i>valid+1&&HC[i-1]!=HC[i-2];
   if(!change&&!prior&&A200[i]!=EMPTY_VALUE)
   {
    Trades[tradeCount].start=i; Trades[tradeCount].finish=i; Trades[tradeCount].dir=bull?1:-1;
    Trades[tradeCount].entry=close[i]; double risk=A200[i]*StopLossATRMultiplier;
    Trades[tradeCount].sl=close[i]-Trades[tradeCount].dir*risk;
    Trades[tradeCount].tp=close[i]+Trades[tradeCount].dir*risk*RiskRewardRatio;
    Trades[tradeCount].active=true; tradeCount++;
   }
  }
  // Reverse order and same-entry-bar evaluation deliberately match the supplied Pine.
  for(int k=tradeCount-1;k>=0;k--) if(Trades[k].active)
  {
   Trades[k].finish=i;
   if(!allowed) continue;
   bool sl=Trades[k].dir==1?low[i]<=Trades[k].sl:high[i]>=Trades[k].sl;
   bool tp=Trades[k].dir==1?high[i]>=Trades[k].tp:low[i]<=Trades[k].tp;
   if(sl||tp)
   {
    Trades[k].active=false; outcomes[write]=tp?1:0; write=(write+1)%BacktestTradeWindow; history=MathMin(history+1,BacktestTradeWindow);
   }
  }
 }
 for(int j=0;j<history;j++) { if(outcomes[j]==1) wins++; else losses++; }
 Paint(); return n;
}
