// This Source Code Form is subject to the Mozilla Public License, v. 2.0.
// https://mozilla.org/MPL/2.0/ | Original Pine: (c) officialjackofalltrades
// MT5 conversion: Liquidity Reaper [JOAT]. Indicator, no order execution.
#property copyright "Original Pine: officialjackofalltrades"
#property version "1.01"
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots 7
#property indicator_type1 DRAW_ARROW
#property indicator_type2 DRAW_ARROW
#property indicator_type3 DRAW_NONE
#property indicator_type4 DRAW_NONE
#property indicator_type5 DRAW_NONE
#property indicator_type6 DRAW_NONE
#property indicator_type7 DRAW_NONE
#property indicator_label1 "Raid Buy"
#property indicator_label2 "Raid Sell"
#property indicator_label3 "Entry"
#property indicator_label4 "SL"
#property indicator_label5 "TP1"
#property indicator_label6 "TP2"
#property indicator_label7 "TP3"

input group "Liquidity Detection"
input int SwingStrength=8;
input int ConfirmationWindow=3;
input int MaxPoolsPerSide=12;
input double MinSweepWickPercent=25;
input group "Volume Filter"
input bool RequireVolumeExpansion=true;
input int VolumeMAPeriod=20;
input double VolumeMultiplier=1.1;
input bool UseRealVolume=false; // default tick volume, usual Forex broker volume
input group "Signals and Display"
input bool ClosedBarSignals=true;
input bool ShowSignalLabels=true;
input bool ShowArrows=true;
input bool ShowRails=true;
input ENUM_LINE_STYLE RailStyle=STYLE_DOT;
input bool ShowZones=true;
input int ZoneLifetimeBars=120;
input int DisplayHistoryBars=500; // display limit only; calculations use full chart history
input color BuyColor=C'56,189,248';
input color SellColor=C'225,29,72';
input color LabelTextColor=clrWhite;
input int FontSize=9;
input group "Entry, SL and Targets"
input bool ShowTargets=true;
input bool UseATRStop=true;
input int ATRPeriod=14;
input double ATRStopMultiplier=1.5;
input double StopPercent=1.0;
input double RRTP1=1.0;
input double RRTP2=2.0;
input double RRTP3=3.0;
input bool ShowSL=true;
input bool ShowTP1=true;
input bool ShowTP2=true;
input bool ShowTP3=true;
input group "Dashboard and Alerts"
input bool ShowDashboard=true;
input ENUM_BASE_CORNER DashboardCorner=CORNER_LEFT_UPPER;
input bool PopupAlert=false;
input bool PushAlert=false;
input bool SoundAlert=false;
input string SoundFile="alert.wav";

double Buy[],Sell[],Entry[],SL[],TP1[],TP2[],TP3[];
struct Pool { double level; int born; int end; bool high; };
struct Pending { bool active; double level; double extreme; double range; int bar; };
struct Zone { double level; double extreme; int born; bool high; };
Pool highs[],lows[],rails[];
Zone zones[];
string prefix;
datetime lastCalculation=0,lastAlert=0;
int previousRates=0;
bool alertsReady=false;

color Dim(color c,double factor)
{
   return (color)((int)((c & 255)*factor) | ((int)(((c>>8)&255)*factor)<<8) | ((int)(((c>>16)&255)*factor)<<16));
}
void Common(string name,color c)
{
   ObjectSetInteger(0,name,OBJPROP_COLOR,c);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
}
void Line(string id,datetime a,datetime b,double p,color c,ENUM_LINE_STYLE style=STYLE_SOLID,int width=1,bool ray=false)
{
   string n=prefix+id;
   ObjectCreate(0,n,OBJ_TREND,0,a,p,b,p);
   Common(n,c);
   ObjectSetInteger(0,n,OBJPROP_RAY_RIGHT,ray);
   ObjectSetInteger(0,n,OBJPROP_RAY_LEFT,false);
   ObjectSetInteger(0,n,OBJPROP_STYLE,style);
   ObjectSetInteger(0,n,OBJPROP_WIDTH,width);
}
void Text(string id,datetime t,double p,string value,color c,ENUM_ANCHOR_POINT anchor=ANCHOR_LEFT)
{
   string n=prefix+id;
   ObjectCreate(0,n,OBJ_TEXT,0,t,p);
   Common(n,c);
   ObjectSetString(0,n,OBJPROP_TEXT,value);
   ObjectSetString(0,n,OBJPROP_FONT,"Arial");
   ObjectSetInteger(0,n,OBJPROP_FONTSIZE,FontSize);
   ObjectSetInteger(0,n,OBJPROP_ANCHOR,anchor);
}
void Box(string id,datetime a,datetime b,double p,double q,color c)
{
   string n=prefix+id;
   ObjectCreate(0,n,OBJ_RECTANGLE,0,a,p,b,q);
   Common(n,Dim(c,0.28));
   ObjectSetInteger(0,n,OBJPROP_FILL,true);
   ObjectSetInteger(0,n,OBJPROP_BACK,true);
}
void AddPool(Pool &arr[],double level,int born,bool high)
{
   int n=ArraySize(arr);
   if(n>=MaxPoolsPerSide) { for(int j=1;j<n;j++) arr[j-1]=arr[j]; n--; ArrayResize(arr,n); }
   ArrayResize(arr,n+1);
   arr[n].level=level; arr[n].born=born; arr[n].end=-1; arr[n].high=high;
}
void Raid(Pool &arr[],Pending &pending,int i,double extreme,double range,int visible)
{
   for(int j=ArraySize(arr)-1;j>=0;j--)
   {
      if((arr[j].high && extreme>arr[j].level) || (!arr[j].high && extreme<arr[j].level))
      {
         pending.active=true; pending.level=arr[j].level; pending.extreme=extreme;
         pending.range=range; pending.bar=i;
         if(i>=visible) { int n=ArraySize(rails); ArrayResize(rails,n+1); rails[n]=arr[j]; rails[n].end=i; }
         int n=ArraySize(arr);
         for(int k=j+1;k<n;k++) arr[k-1]=arr[k];
         ArrayResize(arr,n-1);
      }
   }
}
bool Confirm(Pending &p,int i,double o,double c,bool volumeOK,bool high)
{
   if(!p.active) return false;
   int elapsed=i-p.bar;
   if(elapsed>ConfirmationWindow) { p.active=false; return false; }
   double wick=(high ? p.extreme-p.level : p.level-p.extreme)/p.range*100;
   if(elapsed>=1 && volumeOK && wick>=MinSweepWickPercent &&
      (high ? c<p.level && c<o : c>p.level && c>o))
   { p.active=false; return true; }
   return false;
}
void AddZone(Pending &p,int i,bool high)
{
   int n=ArraySize(zones); ArrayResize(zones,n+1);
   zones[n].level=p.level; zones[n].extreme=p.extreme; zones[n].born=i; zones[n].high=high;
}
void DashboardRow(int row,string value,color c)
{
   string n=prefix+"dashboard"+IntegerToString(row);
   ObjectCreate(0,n,OBJ_LABEL,0,0,0); Common(n,c);
   bool right=(DashboardCorner==CORNER_RIGHT_UPPER || DashboardCorner==CORNER_RIGHT_LOWER);
   bool bottom=(DashboardCorner==CORNER_LEFT_LOWER || DashboardCorner==CORNER_RIGHT_LOWER);
   ObjectSetInteger(0,n,OBJPROP_CORNER,DashboardCorner);
   ObjectSetInteger(0,n,OBJPROP_ANCHOR,right ? (bottom ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER) : (bottom ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER));
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,15);
   ObjectSetInteger(0,n,OBJPROP_YDISTANCE,20+(bottom ? 11-row : row)*(FontSize+9));
   ObjectSetInteger(0,n,OBJPROP_FONTSIZE,FontSize);
   ObjectSetString(0,n,OBJPROP_FONT,"Consolas");
   ObjectSetString(0,n,OBJPROP_TEXT,value);
}
string Price(double p) { return DoubleToString(p,_Digits); }
int OnInit()
{
   if(SwingStrength<2 || SwingStrength>50 || ConfirmationWindow<1 || ConfirmationWindow>20 ||
      MaxPoolsPerSide<2 || MaxPoolsPerSide>40 || MinSweepWickPercent<0 || MinSweepWickPercent>90 ||
      VolumeMAPeriod<1 || VolumeMultiplier<=0 || ATRPeriod<1 || ATRStopMultiplier<=0 || StopPercent<=0 ||
      RRTP1<=0 || RRTP2<RRTP1 || RRTP3<RRTP2 || ZoneLifetimeBars<10 || ZoneLifetimeBars>500 || DisplayHistoryBars<1 || FontSize<6)
      return INIT_PARAMETERS_INCORRECT;
   prefix="LR_"+IntegerToString(ChartID())+"_"+IntegerToString(GetMicrosecondCount())+"_";
   SetIndexBuffer(0,Buy,INDICATOR_DATA); SetIndexBuffer(1,Sell,INDICATOR_DATA);
   SetIndexBuffer(2,Entry,INDICATOR_DATA); SetIndexBuffer(3,SL,INDICATOR_DATA);
   SetIndexBuffer(4,TP1,INDICATOR_DATA); SetIndexBuffer(5,TP2,INDICATOR_DATA); SetIndexBuffer(6,TP3,INDICATOR_DATA);
   ArraySetAsSeries(Buy,false); ArraySetAsSeries(Sell,false); ArraySetAsSeries(Entry,false);
   ArraySetAsSeries(SL,false); ArraySetAsSeries(TP1,false); ArraySetAsSeries(TP2,false); ArraySetAsSeries(TP3,false);
   PlotIndexSetInteger(0,PLOT_ARROW,233); PlotIndexSetInteger(1,PLOT_ARROW,234);
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,BuyColor); PlotIndexSetInteger(1,PLOT_LINE_COLOR,SellColor);
   if(!ShowArrows) { PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_NONE); PlotIndexSetInteger(1,PLOT_DRAW_TYPE,DRAW_NONE); }
   for(int i=0;i<7;i++) PlotIndexSetDouble(i,PLOT_EMPTY_VALUE,EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME,"Liquidity Reaper [JOAT] MT5 v1.01");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { ObjectsDeleteAll(0,prefix); }

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[])
{
   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false); ArraySetAsSeries(high,false);
   ArraySetAsSeries(low,false); ArraySetAsSeries(close,false); ArraySetAsSeries(tick_volume,false); ArraySetAsSeries(volume,false);
   if(rates_total<2*SwingStrength+3) return 0;
   if(ClosedBarSignals && prev_calculated>0 && previousRates==rates_total && lastCalculation==time[rates_total-1]) return rates_total;
   bool mayAlert=alertsReady && prev_calculated>0;
   previousRates=rates_total; lastCalculation=time[rates_total-1];
   ObjectsDeleteAll(0,prefix);
   ArrayInitialize(Buy,EMPTY_VALUE); ArrayInitialize(Sell,EMPTY_VALUE); ArrayInitialize(Entry,EMPTY_VALUE);
   ArrayInitialize(SL,EMPTY_VALUE); ArrayInitialize(TP1,EMPTY_VALUE); ArrayInitialize(TP2,EMPTY_VALUE); ArrayInitialize(TP3,EMPTY_VALUE);
   ArrayResize(highs,0); ArrayResize(lows,0); ArrayResize(rails,0); ArrayResize(zones,0);
   Pending ph,pl; ph.active=false; pl.active=false;
   int last=rates_total-1-(ClosedBarSignals ? 1 : 0),visible=MathMax(0,last-DisplayHistoryBars+1);
   int buys=0,sells=0,lastRaid=-1,lastDir=0,dir=0,entryBar=-1,endBar=-1;
   double ep=0,sl=0,t1=0,t2=0,t3=0,ext=0,atr=0,trsum=0,vsum=0,vm=1;
   string status="WAITING FOR SETUP";
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0) tick=_Point;
   for(int i=0;i<=last;i++)
   {
      double tr=i==0 ? high[i]-low[i] : MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
      if(i<ATRPeriod) { trsum+=tr; if(i==ATRPeriod-1) atr=trsum/ATRPeriod; }
      else atr=(atr*(ATRPeriod-1)+tr)/ATRPeriod; // Pine ta.atr = Wilder RMA, SMA seed
      double v=(double)(UseRealVolume ? volume[i] : tick_volume[i]); vsum+=v;
      if(i>=VolumeMAPeriod) vsum-=(double)(UseRealVolume ? volume[i-VolumeMAPeriod] : tick_volume[i-VolumeMAPeriod]);
      vm=i>=VolumeMAPeriod-1 && vsum>0 ? v/(vsum/VolumeMAPeriod) : 1;
      bool vok=!RequireVolumeExpansion || vm>=VolumeMultiplier;
      if(i>=2*SwingStrength)
      {
         int p=i-SwingStrength; bool hp=true,lp=true;
         for(int k=p-SwingStrength;k<=i;k++)
         {
            if(k==p) continue;
            // Pine resolves equal pivots to the most recent occurrence.
            if(high[k]>high[p] || (k>p && high[k]==high[p])) hp=false;
            if(low[k]<low[p] || (k>p && low[k]==low[p])) lp=false;
         }
         if(hp) AddPool(highs,high[p],p,true);
         if(lp) AddPool(lows,low[p],p,false);
      }
      Raid(highs,ph,i,high[i],MathMax(high[i]-low[i],tick),visible);
      Raid(lows,pl,i,low[i],MathMax(high[i]-low[i],tick),visible);
      if(ph.active) ph.extreme=MathMax(ph.extreme,high[i]);
      if(pl.active) pl.extreme=MathMin(pl.extreme,low[i]);
      bool sell=Confirm(ph,i,open[i],close[i],vok,true);
      bool buy=Confirm(pl,i,open[i],close[i],vok,false);
      double offset=MathMax((high[i]-low[i])*0.12,10*_Point);
      if(buy) { Buy[i]=low[i]-offset; buys++; lastRaid=i; lastDir=1; }
      if(sell) { Sell[i]=high[i]+offset; sells++; lastRaid=i; lastDir=-1; }
      if(i>=visible && ShowSignalLabels)
      {
         if(buy) Text("buy"+IntegerToString(i),time[i],low[i]-offset,"RIWAYAT BUY "+DoubleToString(vm,1)+"x",Dim(BuyColor,0.65),ANCHOR_RIGHT_UPPER);
         if(sell) Text("sell"+IntegerToString(i),time[i],high[i]+offset,"RIWAYAT SELL "+DoubleToString(vm,1)+"x",Dim(SellColor,0.65),ANCHOR_RIGHT_LOWER);
      }
      if(ShowZones && last-i<=ZoneLifetimeBars)
      { if(buy) AddZone(pl,i,false); if(sell) AddZone(ph,i,true); }
      if((buy || sell) && (!UseATRStop || i>=ATRPeriod-1))
      {
         dir=buy ? 1 : -1; entryBar=i; endBar=i+1; ep=close[i];
         double risk=UseATRStop ? atr*ATRStopMultiplier : ep*StopPercent/100;
         sl=ep-dir*risk; t1=ep+dir*risk*RRTP1; t2=ep+dir*risk*RRTP2; t3=ep+dir*risk*RRTP3;
         ext=ShowTP3 ? t3 : ShowTP2 ? t2 : ShowTP1 ? t1 : 0;
         status=dir>0 ? "BUY ACTIVE" : "SELL ACTIVE";
         Entry[i]=ep; SL[i]=sl; TP1[i]=t1; TP2[i]=t2; TP3[i]=t3;
      }
      if(dir!=0)
      {
         endBar=i+1;
         bool sh=dir==1 ? low[i]<=sl : high[i]>=sl;
         bool th=ext!=0 && (dir==1 ? high[i]>=ext : low[i]<=ext);
         if(i>entryBar && (sh || th))
         { endBar=i; dir=0; status=sh && th ? "SL / TP SAME BAR (AMBIGUOUS)" : sh ? "SL HIT" : "FINAL DISPLAYED TP HIT"; }
      }
      if(i==last && (buy || sell) && mayAlert && time[i]!=lastAlert)
      {
         string msg="REAPER "+(buy ? "BUY " : "SELL ")+_Symbol+" "+EnumToString(_Period)+" Entry "+Price(close[i]);
         if(entryBar==i) msg+=" SL "+Price(sl)+" TP1 "+Price(t1)+" TP2 "+Price(t2)+" TP3 "+Price(t3);
         if(PopupAlert) Alert(msg); if(PushAlert) SendNotification(msg); if(SoundAlert) PlaySound(SoundFile);
         lastAlert=time[i];
      }
   }
   int seconds=PeriodSeconds(_Period);
   if(ShowRails)
   {
      for(int j=0;j<ArraySize(highs);j++) { Pool p=highs[j]; Line("H"+IntegerToString(j),time[p.born],time[last]+seconds,p.level,Dim(SellColor,0.55),RailStyle,1,true); }
      for(int j=0;j<ArraySize(lows);j++) { Pool p=lows[j]; Line("L"+IntegerToString(j),time[p.born],time[last]+seconds,p.level,Dim(BuyColor,0.55),RailStyle,1,true); }
      for(int j=0;j<ArraySize(rails);j++) { Pool p=rails[j]; Line("R"+IntegerToString(j),time[p.born],time[p.end],p.level,Dim(p.high ? SellColor : BuyColor,0.55),RailStyle); }
   }
   for(int j=0;j<ArraySize(zones);j++)
   {
      Zone z=zones[j]; int left=MathMax(0,z.born-ConfirmationWindow),right=z.born+ZoneLifetimeBars;
      datetime rt=right<rates_total ? time[right] : time[rates_total-1]+(datetime)((right-rates_total+1)*seconds);
      Box("Z"+IntegerToString(j),time[left],rt,z.level,z.extreme,z.high ? SellColor : BuyColor);
   }
   // Completed setups retain their historical signal buffers, but never display
   // an entry recommendation, target lines or risk/reward boxes as active.
   if(ShowTargets && entryBar>=0 && dir!=0)
   {
      datetime a=time[entryBar],b=endBar<rates_total ? time[endBar] : time[rates_total-1]+seconds;
      int labelBar=dir==0 ? endBar : endBar-1;
      datetime labelTime=labelBar>=0 && labelBar<rates_total ? time[labelBar] : b;
      color c=Entry[entryBar]>sl ? BuyColor : SellColor;
      if(ShowSL) Box("risk",a,b,ep,sl,SellColor);
      if(ext!=0) Box("reward",a,b,ep,ext,BuyColor);
      Line("entry",a,b,ep,c,STYLE_SOLID,2); Text("entryText",labelTime,ep,(dir>0 ? "BUY AKTIF " : "SELL AKTIF ")+Price(ep),c);
      if(ShowSL) { Line("sl",a,b,sl,SellColor,STYLE_DASH); Text("slText",labelTime,sl,"SL "+Price(sl),SellColor); }
      if(ShowTP1) { Line("tp1",a,b,t1,c); Text("tp1Text",labelTime,t1,"TP1 "+Price(t1),c); }
      if(ShowTP2) { Line("tp2",a,b,t2,c); Text("tp2Text",labelTime,t2,"TP2 "+Price(t2),c); }
      if(ShowTP3) { Line("tp3",a,b,t3,c,STYLE_DOT); Text("tp3Text",labelTime,t3,"TP3 "+Price(t3),c); }
   }
   if(ShowDashboard)
   {
      double above=0,below=0;
      for(int j=0;j<ArraySize(highs);j++) if(highs[j].level>close[last] && (above==0 || highs[j].level<above)) above=highs[j].level;
      for(int j=0;j<ArraySize(lows);j++) if(lows[j].level<close[last] && (below==0 || lows[j].level>below)) below=lows[j].level;
      DashboardRow(0,"LIQUIDITY REAPER | "+_Symbol+" "+EnumToString(_Period),LabelTextColor);
      DashboardRow(1,"Pools Above / Below: "+IntegerToString(ArraySize(highs))+" / "+IntegerToString(ArraySize(lows)),LabelTextColor);
      DashboardRow(2,"Nearest Above: "+(above==0 ? "--" : Price(above)),SellColor);
      DashboardRow(3,"Nearest Below: "+(below==0 ? "--" : Price(below)),BuyColor);
      DashboardRow(4,"Volume: "+DoubleToString(vm,2)+"x | "+(UseRealVolume ? "REAL" : "TICK"),LabelTextColor);
      DashboardRow(5,"Raids BUY / SELL: "+IntegerToString(buys)+" / "+IntegerToString(sells),LabelTextColor);
      DashboardRow(6,"Riwayat sinyal: "+(lastRaid<0 ? "--" : (lastDir==1 ? "BUY " : "SELL ")+IntegerToString(last-lastRaid)+" bars ago"),LabelTextColor);
      DashboardRow(7,"Pending: "+(ph.active ? "HIGH " : "")+(pl.active ? "LOW " : "")+(!ph.active && !pl.active ? "NONE" : ""),LabelTextColor);
      DashboardRow(8,"Setup: "+(dir>0 ? "BUY AKTIF" : dir<0 ? "SELL AKTIF" : "MENUNGGU SETUP BARU"),dir>0 ? BuyColor : dir<0 ? SellColor : LabelTextColor);
      DashboardRow(9,dir!=0 ? "Entry "+Price(ep)+" | SL "+Price(sl) : "Tidak ada setup entry aktif",LabelTextColor);
      DashboardRow(10,dir!=0 ? "TP1 "+Price(t1)+" | TP2 "+Price(t2)+" | TP3 "+Price(t3) : entryBar>=0 ? "Setup terakhir SELESAI: "+status : "Menunggu konfirmasi liquidity sweep",LabelTextColor);
      DashboardRow(11,ClosedBarSignals ? "CONFIRMED CLOSED CANDLE" : "LIVE CANDLE: SIGNAL CAN CHANGE",LabelTextColor);
   }
   alertsReady=true; ChartRedraw(0);
   return rates_total;
}
