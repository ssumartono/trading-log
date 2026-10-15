// Original Pine Script (c) officialjackofalltrades.
// MQL5 adaptation of Supply & Demand Order Blocks [JOAT].
// This Source Code Form is subject to Mozilla Public License 2.0.
// https://mozilla.org/MPL/2.0/ . Indicator only; no order execution.
#property copyright "Original: officialjackofalltrades; MT5 adaptation"
#property version "1.00"
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots 4
#property indicator_type1 DRAW_LINE
#property indicator_label1 "Trend EMA"
#property indicator_color1 C'166,75,255'
#property indicator_width1 2
#property indicator_type2 DRAW_ARROW
#property indicator_label2 "BUY"
#property indicator_color2 C'0,229,255'
#property indicator_type3 DRAW_ARROW
#property indicator_label3 "SELL"
#property indicator_color3 C'255,46,154'
#property indicator_type4 DRAW_COLOR_CANDLES
#property indicator_label4 "Open;High;Low;Close"
#property indicator_color4 C'0,229,255',C'255,46,154',C'90,107,140'
input group "Order Block Detection"
input int DisplacementBars=2;
input double ATRMultiplier=1.5;
input bool RequireFVG=false;
input int ATRLength=14;
input group "Block Management"
input int MaxBlocks=12;
input int ZoneExtension=30;
input int MinBlockAge=2;
input group "Trend Filter"
input bool UseTrend=true;
input int EMALength=50;
input bool ShowEMA=true;
input bool ColorCandles=true;
input bool ShowTrendTint=true;
input group "Trade / Risk"
input double SLBufferATR=0.25;
input double TP1R=1.0;
input double TP2R=2.0;
input double TP3R=3.0;
input bool ShowTradeBoxes=true;
input int TradeExtension=25;
input group "Signals"
input int MinSignalGap=8;
input bool ClosedBarSignals=true;
input bool PopupAlerts=false;
input bool PushAlerts=false;
input bool SoundAlerts=false;
input bool AlertNewBlocks=false;
input group "Dashboard"
enum HUD_POSITION {TopRight,TopLeft,BottomRight,BottomLeft,MiddleRight};
input bool ShowDashboard=true;
input HUD_POSITION DashboardPosition=TopRight;
input int DashboardFontSize=10;
input color DashboardBackground=C'5,7,14';
input group "Performance"
input int HistoryBars=10000; // 0 = all loaded bars; affects zones and win-rate sample

double EMAPlot[],BuyPlot[],SellPlot[],CO[],CH[],CL[],CC[],CI[];
color NeonCyan=C'0,229,255',Mag=C'255,46,154',NeonLime=C'124,255,90',Mute=C'90,107,140';
string prefix;
datetime calculated=0,alerted=0;
bool ready=false,chartDirty=false;
double closedEMA=0;
struct Block {double top,bot,strength; int dir,origin;};
Block blocks[];
int nb=0,wins=0,losses=0,lastSignal=-100000000,tradeDir=0,tradeBar=-1;
bool tracking=false;
double entry=0,stop=0,t1=0,t2=0,t3=0;

color Blend(color fg,color bg,double opacity)
{
 int a=(int)fg,b=(int)bg;
 int r=(int)MathRound((a&255)*opacity+(b&255)*(1-opacity));
 int g=(int)MathRound(((a>>8)&255)*opacity+((b>>8)&255)*(1-opacity));
 int bl=(int)MathRound(((a>>16)&255)*opacity+((b>>16)&255)*(1-opacity));
 return (color)(r+(g<<8)+(bl<<16));
}
void Base(string name)
{
 ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
 ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
}
void Rect(string id,datetime a,double top,datetime b,double bot,color c,bool fill=true)
{
 string n=prefix+id;
 ObjectCreate(0,n,OBJ_RECTANGLE,0,a,top,b,bot);
 ObjectMove(0,n,0,a,top); ObjectMove(0,n,1,b,bot);
 ObjectSetInteger(0,n,OBJPROP_COLOR,c); ObjectSetInteger(0,n,OBJPROP_FILL,fill);
 ObjectSetInteger(0,n,OBJPROP_BACK,true); Base(n);
}
void Text(string id,datetime t,double p,string text,color c,ENUM_ANCHOR_POINT anchor=ANCHOR_LEFT_UPPER)
{
 string n=prefix+id; ObjectCreate(0,n,OBJ_TEXT,0,t,p); ObjectMove(0,n,0,t,p);
 ObjectSetString(0,n,OBJPROP_TEXT,text); ObjectSetString(0,n,OBJPROP_FONT,"Arial");
 ObjectSetInteger(0,n,OBJPROP_FONTSIZE,9);ObjectSetInteger(0,n,OBJPROP_COLOR,c);
 ObjectSetInteger(0,n,OBJPROP_ANCHOR,anchor);Base(n);
}
void Level(string id,datetime a,datetime b,double p,color c,ENUM_LINE_STYLE style)
{
 string n=prefix+id;ObjectCreate(0,n,OBJ_TREND,0,a,p,b,p);
 ObjectMove(0,n,0,a,p);ObjectMove(0,n,1,b,p);
 ObjectSetInteger(0,n,OBJPROP_RAY_RIGHT,false);ObjectSetInteger(0,n,OBJPROP_COLOR,c);
 ObjectSetInteger(0,n,OBJPROP_STYLE,style);Base(n);
}
void Drop(int k) {for(int j=k;j<nb-1;j++) blocks[j]=blocks[j+1];nb--;ArrayResize(blocks,nb);}
void Add(int i,int dir,double strength,const double &o[],const double &h[],const double &l[],const double &c[])
{
 for(int off=DisplacementBars;off<=DisplacementBars+3;off++)
 {
  int j=i-off;if(j<0) continue;
  if((dir==1 && c[j]<o[j]) || (dir==-1 && c[j]>o[j]))
  {ArrayResize(blocks,nb+1);blocks[nb].top=h[j];blocks[nb].bot=l[j];blocks[nb].dir=dir;
   blocks[nb].origin=j;blocks[nb].strength=strength;nb++;break;}
 }
}
string Meter(int n,int total) {string s="";for(int j=0;j<total;j++)s+=(j<n?"|":".");return s;}
void HUD(int demand,int supply,double near,int conviction,int signal,int trend)
{
 if(!ShowDashboard)return;
 int rowH=DashboardFontSize+16,width=350,height=rowH*8+12;
 long cw=ChartGetInteger(0,CHART_WIDTH_IN_PIXELS),ch=ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
 bool right=DashboardPosition==TopRight||DashboardPosition==BottomRight||DashboardPosition==MiddleRight;
 bool bottom=DashboardPosition==BottomRight||DashboardPosition==BottomLeft;
 int x=right?(int)MathMax(8,cw-width-16):12;
 int y=bottom?(int)MathMax(8,ch-height-30):16;
 if(DashboardPosition==MiddleRight)y=(int)MathMax(8,(ch-height)/2);
 string n=prefix+"HUD";ObjectCreate(0,n,OBJ_RECTANGLE_LABEL,0,0,0);
 ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x);ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y);
 ObjectSetInteger(0,n,OBJPROP_XSIZE,width);ObjectSetInteger(0,n,OBJPROP_YSIZE,height);
 ObjectSetInteger(0,n,OBJPROP_BGCOLOR,DashboardBackground);ObjectSetInteger(0,n,OBJPROP_COLOR,C'22,35,61');Base(n);
 string rows[8];color colors[8];
 rows[0]="ORDERFLOW DEPTH  |  JOAT MT5";colors[0]=C'166,75,255';
 rows[1]="NEAREST OB   "+(near<0?"--":DoubleToString(near,_Digits));colors[1]=C'255,194,75';
 rows[2]="Demand "+(string)demand+"   "+Meter(MathMin(8,demand),8);colors[2]=NeonCyan;
 rows[3]="Supply "+(string)supply+"   "+Meter(MathMin(8,supply),8);colors[3]=Mag;
 rows[4]=(demand>supply?"DEMAND-HEAVY":supply>demand?"SUPPLY-HEAVY":"BALANCED")+" | "+(trend>0?"UPTREND":trend<0?"DOWNTREND":"FLAT");colors[4]=clrWhite;
 rows[5]="Conviction "+Meter((int)MathRound(conviction/10.0),10)+" "+(string)conviction;colors[5]=conviction>=66?NeonCyan:C'255,194,75';
 rows[6]="Signal: "+(signal>0?"BUY":signal<0?"SELL":"Waiting")+(ClosedBarSignals?" [closed]":" [live]");colors[6]=signal>0?NeonCyan:signal<0?Mag:Mute;
 int resolved=wins+losses;
 rows[7]="Win (TP1): "+(resolved>0?DoubleToString(100.0*wins/resolved,0)+"% ("+(string)resolved+")":"--");colors[7]=NeonLime;
 for(int j=0;j<8;j++)
 {n=prefix+"HUD"+(string)j;ObjectCreate(0,n,OBJ_LABEL,0,0,0);ObjectSetInteger(0,n,OBJPROP_XDISTANCE,x+12);
 ObjectSetInteger(0,n,OBJPROP_YDISTANCE,y+6+j*rowH);ObjectSetString(0,n,OBJPROP_TEXT,rows[j]);
 ObjectSetString(0,n,OBJPROP_FONT,"Consolas");ObjectSetInteger(0,n,OBJPROP_FONTSIZE,DashboardFontSize);
 ObjectSetInteger(0,n,OBJPROP_COLOR,colors[j]);Base(n);}
}
int OnInit()
{
 if(DisplacementBars<1||DisplacementBars>3||ATRMultiplier<0.3||ATRLength<1||EMALength<2||MaxBlocks<2||MaxBlocks>60||ZoneExtension<5||MinBlockAge<0||SLBufferATR<0||TP1R<=0||TP2R<TP1R||TP3R<TP2R||TradeExtension<5||MinSignalGap<0||DashboardFontSize<6||DashboardFontSize>24||HistoryBars<0)return INIT_PARAMETERS_INCORRECT;
 SetIndexBuffer(0,EMAPlot);SetIndexBuffer(1,BuyPlot);SetIndexBuffer(2,SellPlot);
 SetIndexBuffer(3,CO);SetIndexBuffer(4,CH);SetIndexBuffer(5,CL);SetIndexBuffer(6,CC);SetIndexBuffer(7,CI,INDICATOR_COLOR_INDEX);
 PlotIndexSetInteger(1,PLOT_ARROW,233);PlotIndexSetInteger(2,PLOT_ARROW,234);
 for(int j=0;j<4;j++)PlotIndexSetDouble(j,PLOT_EMPTY_VALUE,EMPTY_VALUE);
 prefix="JOAT_"+(string)ChartID()+"_"+(string)GetMicrosecondCount()+"_";
 IndicatorSetString(INDICATOR_SHORTNAME,"S&D Order Blocks [JOAT] MT5");
 IndicatorSetInteger(INDICATOR_DIGITS,_Digits);return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ObjectsDeleteAll(0,prefix);ChartRedraw();}
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
{if(id==CHARTEVENT_CHART_CHANGE)chartDirty=true;}
int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
{
 ArraySetAsSeries(time,false);ArraySetAsSeries(open,false);ArraySetAsSeries(high,false);ArraySetAsSeries(low,false);ArraySetAsSeries(close,false);
 if(rates_total<MathMax(ATRLength+1,DisplacementBars+5))return 0;
 int end=rates_total-1-(ClosedBarSignals?1:0);
  if(ClosedBarSignals && prev_calculated==rates_total && calculated==time[end] && !chartDirty)
 {
  int live=rates_total-1;
  double e=2.0/(EMALength+1)*close[live]+(1-2.0/(EMALength+1))*closedEMA;
  EMAPlot[live]=ShowEMA?e:EMPTY_VALUE;
  if(ColorCandles){CO[live]=open[live];CH[live]=high[live];CL[live]=low[live];CC[live]=close[live];CI[live]=close[live]>e?0:close[live]<e?1:2;}
  return rates_total;
 }
 chartDirty=false;
 calculated=time[end];
 ObjectsDeleteAll(0,prefix);ArrayInitialize(EMAPlot,EMPTY_VALUE);ArrayInitialize(BuyPlot,EMPTY_VALUE);ArrayInitialize(SellPlot,EMPTY_VALUE);
 ArrayInitialize(CO,EMPTY_VALUE);ArrayInitialize(CH,EMPTY_VALUE);ArrayInitialize(CL,EMPTY_VALUE);ArrayInitialize(CC,EMPTY_VALUE);ArrayInitialize(CI,0);
 nb=0;ArrayResize(blocks,0);wins=0;losses=0;lastSignal=-100000000;tracking=false;tradeBar=-1;
 double ema=close[0],atr=0,sumTR=0,alpha=2.0/(EMALength+1);
 bool prevUp=false,prevDn=false,newUp=false,newDn=false;
 int demand=0,supply=0,conviction=0,signal=0,trend=0;
 double near=-1;
 double rawEMA[];ArrayResize(rawEMA,rates_total);
 int start=HistoryBars==0?0:MathMax(0,end-HistoryBars+1);
 color bg=(color)ChartGetInteger(0,CHART_COLOR_BACKGROUND);
 int seconds=PeriodSeconds();if(seconds<=0)seconds=60;
 for(int i=0;i<rates_total;i++)
 {
  if(i>0)ema=alpha*close[i]+(1-alpha)*ema;
  rawEMA[i]=ema;
  EMAPlot[i]=ShowEMA?ema:EMPTY_VALUE;
  int tr=close[i]>ema?1:close[i]<ema?-1:0;
  if(ColorCandles){CO[i]=open[i];CH[i]=high[i];CL[i]=low[i];CC[i]=close[i];CI[i]=tr>0?0:tr<0?1:2;}
  double range=i==0?high[i]-low[i]:MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
  if(i<ATRLength){sumTR+=range;if(i==ATRLength-1)atr=sumTR/ATRLength;}
  else atr=(atr*(ATRLength-1)+range)/ATRLength;
  if(i==end)closedEMA=ema;
  if(i>end)continue;
  bool valid=i>=ATRLength-1 && i>=DisplacementBars;
  double leg=i>=DisplacementBars?close[i]-close[i-DisplacementBars]:0;
  bool strongUp=valid && leg>ATRMultiplier*atr,strongDn=valid && -leg>ATRMultiplier*atr;
  newUp=strongUp&&!prevUp&&(!RequireFVG||(i>=2&&low[i]>high[i-2]));
  newDn=strongDn&&!prevDn&&(!RequireFVG||(i>=2&&high[i]<low[i-2]));
  prevUp=strongUp;prevDn=strongDn;
  if(i<start)continue;
  double safe=MathMax(atr,_Point);
  if(newUp)Add(i,1,MathMin(1,leg/(safe*3)),open,high,low,close);
  if(newDn)Add(i,-1,MathMin(1,-leg/(safe*3)),open,high,low,close);
  for(int j=nb-1;j>=0;j--)if(blocks[j].dir==1?close[i]<blocks[j].bot:close[i]>blocks[j].top)Drop(j);
  while(nb>MaxBlocks)Drop(0);
  bool buy=false,sell=false;double sigTop=0,sigBot=0,strength=0;demand=0;supply=0;near=-1;
  for(int j=nb-1;j>=0;j--)
  {
   double dist=MathAbs(close[i]-(blocks[j].top+blocks[j].bot)/2);
   if(near<0||dist<near)near=dist;
   bool tap=false;
   if(blocks[j].dir==1){demand++;tap=low[i]<=blocks[j].top&&close[i]>blocks[j].bot&&close[i]>open[i]&&(!UseTrend||tr>0);}
   else{supply++;tap=high[i]>=blocks[j].bot&&close[i]<blocks[j].top&&close[i]<open[i]&&(!UseTrend||tr<0);}
   if(tap&&i-blocks[j].origin>=MinBlockAge)
   {if(blocks[j].dir==1)buy=true;else sell=true;sigTop=blocks[j].top;sigBot=blocks[j].bot;strength=blocks[j].strength;}
  }
  buy=buy&&!sell;
  if(i-lastSignal<MinSignalGap){buy=false;sell=false;}
  signal=buy?1:sell?-1:0;trend=tr;
  double proximity=near<0?0:MathMax(0,1-near/(safe*3));
  conviction=(int)MathRound(100*MathMin(1,0.4*proximity+0.25*(UseTrend&&tr!=0?1:0.5)+0.15*MathMin(1,(demand+supply)/6.0)+0.2*(signal!=0?strength:0)+(signal!=0?0.15:0)));
  if(tracking)
  {
   bool win=tradeDir==1?high[i]>=t1:low[i]<=t1;
   bool loss=tradeDir==1?low[i]<=stop:high[i]>=stop;
   if(win){wins++;tracking=false;}else if(loss){losses++;tracking=false;}
  }
  if(signal!=0)
  {
   if(tracking)losses++;
   lastSignal=i;tradeBar=i;tradeDir=signal;entry=close[i];stop=buy?sigBot-SLBufferATR*atr:sigTop+SLBufferATR*atr;
   double risk=MathAbs(entry-stop);t1=entry+signal*risk*TP1R;t2=entry+signal*risk*TP2R;t3=entry+signal*risk*TP3R;tracking=true;
   double offset=MathMax(0.18*safe,10*_Point);
   if(buy)BuyPlot[i]=low[i]-offset;else SellPlot[i]=high[i]+offset;
   Text("SIG"+(string)i,time[i],buy?low[i]-2*offset:high[i]+2*offset,buy?"BUY":"SELL",buy?NeonCyan:Mag,buy?ANCHOR_LEFT_UPPER:ANCHOR_LEFT_LOWER);
  }
 }
 datetime right=time[rates_total-1]+(datetime)(seconds*ZoneExtension);
 for(int j=0;j<nb;j++)
 {
  Block b=blocks[j];color c=b.dir==1?NeonCyan:Mag;
  double transparency=MathMin(92,86-b.strength*24+MathMin(22,(end-b.origin)*0.35));
  Rect("ZONE"+(string)j,time[b.origin],b.top,right,b.bot,Blend(c,bg,(100-transparency)/100));
  Rect("EDGE"+(string)j,time[b.origin],b.top,right,b.bot,Blend(c,bg,(130-transparency)/100),false);
  Text("ZONE_TXT"+(string)j,time[b.origin],b.dir==1?b.top:b.bot,b.dir==1?"Demand":"Supply",c,b.dir==1?ANCHOR_LEFT_UPPER:ANCHOR_LEFT_LOWER);
 }
 if(ShowTrendTint&&UseTrend)
 {
  int first=(int)ChartGetInteger(0,CHART_FIRST_VISIBLE_BAR),visible=(int)ChartGetInteger(0,CHART_VISIBLE_BARS);
  int a=MathMax(start,rates_total-1-first),b=MathMin(end,a+visible+2);
  double pmin=ChartGetDouble(0,CHART_PRICE_MIN),pmax=ChartGetDouble(0,CHART_PRICE_MAX);
  for(int i=a;i<=b;i++)if(rawEMA[i]!=EMPTY_VALUE)
   Rect("TINT"+(string)i,time[i],pmax,time[i]+seconds,pmin,Blend(close[i]>rawEMA[i]?NeonCyan:Mag,bg,0.05));
 }
 if(ShowTradeBoxes&&tradeBar>=0)
 {
  datetime r=time[rates_total-1]+(datetime)(seconds*TradeExtension),a=time[tradeBar];
  Rect("RISK",a,MathMax(entry,stop),r,MathMin(entry,stop),Blend(Mag,bg,0.18));
  Rect("REWARD",a,MathMax(entry,t3),r,MathMin(entry,t3),Blend(NeonLime,bg,0.14));
  double prices[5];prices[0]=entry;prices[1]=stop;prices[2]=t1;prices[3]=t2;prices[4]=t3;
  string names[5]={"ENTRY","SL","TP1","TP2","TP3"};
  for(int j=0;j<5;j++){color c=j==0?NeonCyan:j==1?Mag:NeonLime;
   Level("LEVEL"+(string)j,a,r,prices[j],c,j==0?STYLE_SOLID:j==1?STYLE_DASH:STYLE_DOT);
   Text("PRICE"+(string)j,r,prices[j]," "+names[j]+" "+DoubleToString(prices[j],_Digits),c);}
 }
 HUD(demand,supply,near,conviction,signal,trend);
 if(ready&&time[end]!=alerted)
 {
  string msg=signal!=0?(signal>0?"BUY: demand rejection":"SELL: supply rejection"):AlertNewBlocks?(newUp?"New bullish displacement":newDn?"New bearish displacement":""):"";
  if(msg!=""){msg="JOAT "+_Symbol+" "+EnumToString(_Period)+": "+msg;
   if(PopupAlerts)Alert(msg);if(PushAlerts)SendNotification(msg);if(SoundAlerts)PlaySound("alert.wav");alerted=time[end];}
 }
 ready=true;ChartRedraw();return rates_total;
}

