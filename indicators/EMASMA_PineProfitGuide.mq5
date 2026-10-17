#property strict
#property version "1.10"
#property description "Signal Only: EMA/SMA crossover at candle close. No protection, simulation or orders."
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots 4
#property indicator_label1 "EMA"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_width1 2
#property indicator_label2 "SMA"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrWhite
#property indicator_width2 2
#property indicator_label3 "BUY"
#property indicator_type3 DRAW_ARROW
#property indicator_color3 clrLimeGreen
#property indicator_width3 2
#property indicator_label4 "SELL"
#property indicator_type4 DRAW_ARROW
#property indicator_color4 clrTomato
#property indicator_width4 2
input int InpFastPeriod=9;
input int InpSlowPeriod=20;
input bool InpPopupAlerts=true;
input bool InpPushAlerts=false;
input int InpHistoryBars=2000;
input int InpPanelX=16;
input int InpPanelY=28;
input int InpPanelScale=100; // 75..150 percent

double ema[],sma[],buybuf[],sellbuf[];
int fast=INVALID_HANDLE,slow=INVALID_HANDLE;
string prefix;
datetime seenbar=0,signalbar=0;
int signal_side=0;
double signal_ref=0;
bool initialized=false;

void Notify(string message)
  {
   string msg="EMA/SMA "+_Symbol+" "+EnumToString(_Period)+": "+message;
   Print(msg); if(InpPopupAlerts) Alert(msg); if(InpPushAlerts) SendNotification(msg);
  }
// Segoe UI with measured text fitting keeps content inside the card.
int panel_x=16,panel_y=28,panel_width=460;
double ui_scale=1.0;
int Px(int p) { return (int)MathRound(p*ui_scale); }
string Fit(string value,int points,int available)
  {
   if(available<=0) return "";
   uint w=0,h=0;
   if(!TextSetFont("Segoe UI",-points*10) || !TextGetSize(value,w,h)) return value;
   if((int)w<=available) return value;
   string shorter=value;
   while(StringLen(shorter)>0)
     {
      shorter=StringSubstr(shorter,0,StringLen(shorter)-1);
      if(TextGetSize(shorter+"...",w,h) && (int)w<=available) return shorter+"...";
     }
   return "";
  }
void Box(string key,int x,int y,int width,int height,color fill,color border)
  {
   string n=prefix+key;
   if(ObjectFind(0,n)<0) ObjectCreate(0,n,OBJ_RECTANGLE_LABEL,0,0,0);
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,panel_x+x);ObjectSetInteger(0,n,OBJPROP_YDISTANCE,panel_y+y);
   ObjectSetInteger(0,n,OBJPROP_XSIZE,width);ObjectSetInteger(0,n,OBJPROP_YSIZE,height);
   ObjectSetInteger(0,n,OBJPROP_BGCOLOR,fill);ObjectSetInteger(0,n,OBJPROP_BORDER_COLOR,border);
   ObjectSetInteger(0,n,OBJPROP_BORDER_TYPE,BORDER_FLAT);
   ObjectSetInteger(0,n,OBJPROP_BACK,false);ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false);ObjectSetInteger(0,n,OBJPROP_HIDDEN,true);
  }
void CardText(string key,int x,int y,string value,color c,int size=10,int maxwidth=0)
  {
   string n=prefix+key;
   if(ObjectFind(0,n)<0) ObjectCreate(0,n,OBJ_LABEL,0,0,0);
   int points=MathMax(7,Px(size));
   int available=maxwidth>0?maxwidth:panel_width-x-Px(20);
   ObjectSetInteger(0,n,OBJPROP_CORNER,CORNER_LEFT_UPPER);ObjectSetInteger(0,n,OBJPROP_ANCHOR,ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0,n,OBJPROP_XDISTANCE,panel_x+x);ObjectSetInteger(0,n,OBJPROP_YDISTANCE,panel_y+y);
   ObjectSetInteger(0,n,OBJPROP_COLOR,c);ObjectSetInteger(0,n,OBJPROP_FONTSIZE,points);
   ObjectSetInteger(0,n,OBJPROP_SELECTABLE,false);ObjectSetInteger(0,n,OBJPROP_HIDDEN,true);
   ObjectSetString(0,n,OBJPROP_FONT,"Segoe UI");ObjectSetString(0,n,OBJPROP_TEXT,Fit(value,points,available));
   ObjectSetString(0,n,OBJPROP_TOOLTIP,value);
  }
void Panel()
  {
   if(prefix=="") return;
   ui_scale=InpPanelScale/100.0;
   int chart_width=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS);
   panel_x=MathMin(InpPanelX,MathMax(0,chart_width-Px(320)));
   panel_y=InpPanelY;
   panel_width=MathMax(100,MathMin(Px(460),chart_width-panel_x-Px(12)));
   color bg=C'17,24,36',edge=C'43,56,74',muted=C'143,160,180',white=C'234,241,249';
   color accent=signal_side==1?C'63,213,160':signal_side==-1?C'255,121,119':C'112,165,231';
   color band=signal_side==1?C'20,52,48':signal_side==-1?C'54,32,40':C'28,42,61';
   // Background layers are created before all text labels.
   Box("card",0,0,panel_width,Px(316),bg,edge);
   Box("accent",0,0,Px(4),Px(316),accent,accent);
   Box("signal_band",Px(18),Px(74),panel_width-Px(36),Px(58),band,band);
   Box("divider",Px(20),Px(202),panel_width-Px(40),1,edge,edge);
   Box("footer",Px(18),Px(260),panel_width-Px(36),Px(38),C'24,33,47',C'24,33,47');
   CardText("title",Px(20),Px(16),"EMA / SMA",white,14,panel_width-Px(140));
   CardText("version",panel_width-Px(108),Px(22),"SIGNAL",muted,8,Px(94));
   string tf=EnumToString(_Period);StringReplace(tf,"PERIOD_","");
   CardText("symbol",Px(20),Px(46),_Symbol+"  /  "+tf+"    EMA "+(string)InpFastPeriod+"  /  SMA "+(string)InpSlowPeriod,muted,10);
   CardText("direction",Px(30),Px(82),signal_side==1?"BUY":signal_side==-1?"SELL":"WAIT",accent,20,Px(100));
   CardText("opposite",Px(138),Px(88),signal_side!=0?"CROSSOVER SELESAI":"MENUNGGU CROSSOVER",white,10);
   CardText("confirmation",Px(138),Px(109),"Eksekusi manual",muted,8);
   int column=panel_width/2+Px(10);
   CardText("time_label",Px(20),Px(150),"WAKTU CANDLE SINYAL",muted,8,column-Px(30));
   CardText("price_label",column,Px(150),"CLOSE SINYAL",muted,8);
   CardText("time",Px(20),Px(171),signalbar>0?TimeToString(signalbar,TIME_DATE|TIME_MINUTES):"--",white,10,column-Px(30));
   CardText("price",column,Px(169),signal_side!=0?DoubleToString(signal_ref,_Digits):"--",white,13);
   CardText("hold",Px(20),Px(215),signal_side==0?"Menunggu sinyal pertama dalam riwayat chart.":"Sinyal terakhir "+(signal_side==1?"BUY":"SELL")+". Menunggu crossover berikutnya.",white,10);
   CardText("history",Px(20),Px(238),"Sinyal terakhir bukan instruksi entry baru.",muted,9);
   CardText("manual",Px(30),Px(271),"SIGNAL SAJA / Tidak ada transaksi otomatis",C'190,206,225',9,panel_width-Px(60));
   CardText("version_small",Px(20),Px(302),"v1.10 | EMA biru / SMA putih | Candle selesai",muted,7);
   ChartRedraw();
  }
int OnInit()
  {
   if(InpPanelX<0 || InpPanelY<0 || InpPanelScale<75 || InpPanelScale>150 || InpFastPeriod<1 || InpSlowPeriod<=InpFastPeriod || InpHistoryBars<50 || InpHistoryBars>20000) return INIT_PARAMETERS_INCORRECT;
   SetIndexBuffer(0,ema,INDICATOR_DATA);SetIndexBuffer(1,sma,INDICATOR_DATA);
   SetIndexBuffer(2,buybuf,INDICATOR_DATA);SetIndexBuffer(3,sellbuf,INDICATOR_DATA);
   ArraySetAsSeries(ema,true);ArraySetAsSeries(sma,true);ArraySetAsSeries(buybuf,true);ArraySetAsSeries(sellbuf,true);
   PlotIndexSetInteger(2,PLOT_ARROW,233);PlotIndexSetInteger(3,PLOT_ARROW,234);
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,InpFastPeriod-1);PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,InpSlowPeriod-1);
   fast=iMA(_Symbol,_Period,InpFastPeriod,0,MODE_EMA,PRICE_CLOSE);
   slow=iMA(_Symbol,_Period,InpSlowPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(fast==INVALID_HANDLE || slow==INVALID_HANDLE) return INIT_FAILED;
   prefix="SignalOnly_"+(string)ChartID()+"_"+(string)GetMicrosecondCount()+"_";
   IndicatorSetString(INDICATOR_SHORTNAME,"EMA SMA Signal Only v1.10");return INIT_SUCCEEDED;
  }
int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
  {
   if(rates_total<InpSlowPeriod+2) return 0;
   ArraySetAsSeries(time,true);ArraySetAsSeries(high,true);ArraySetAsSeries(low,true);ArraySetAsSeries(close,true);
   // Full buffer copies keep historical plots aligned if chart history expands.
   if(CopyBuffer(fast,0,0,rates_total,ema)!=rates_total || CopyBuffer(slow,0,0,rates_total,sma)!=rates_total) return prev_calculated;
   if(prev_calculated==0) { ArrayInitialize(buybuf,EMPTY_VALUE);ArrayInitialize(sellbuf,EMPTY_VALUE); }
   buybuf[0]=EMPTY_VALUE;sellbuf[0]=EMPTY_VALUE;
   int count=MathMin(rates_total-InpSlowPeriod-1,InpHistoryBars);
   for(int i=count;i>=1;i--)
     {
      buybuf[i]=EMPTY_VALUE;sellbuf[i]=EMPTY_VALUE;
      double offset=MathMax(high[i]-low[i],10*_Point)*0.25;
      if(ema[i+1]<=sma[i+1] && ema[i]>sma[i]) buybuf[i]=low[i]-offset;
      if(ema[i+1]>=sma[i+1] && ema[i]<sma[i]) sellbuf[i]=high[i]+offset;
     }
   bool first=!initialized || prev_calculated==0;
   bool newbar=initialized && time[0]!=seenbar;
   if(first || newbar)
     {
      signal_side=0;signalbar=0;signal_ref=0;
      for(int i=1;i<=count;i++)
        {
         int side=buybuf[i]!=EMPTY_VALUE?1:sellbuf[i]!=EMPTY_VALUE?-1:0;
         if(side!=0) { signal_side=side;signalbar=time[i];signal_ref=close[i];break; }
        }
      // Suppress startup/history-backfill alerts. Alert only the newly closed bar.
      if(!first && newbar && signalbar==time[1] && signal_side!=0)
         Notify(signal_side==1?"BUY - crossover candle selesai":"SELL - crossover candle selesai");
      initialized=true;seenbar=time[0];
     }
   Panel();return rates_total;
  }
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
  { if(id==CHARTEVENT_CHART_CHANGE) Panel(); }
void OnDeinit(const int reason)
  {
   if(fast!=INVALID_HANDLE)IndicatorRelease(fast);if(slow!=INVALID_HANDLE)IndicatorRelease(slow);
   if(prefix!="")ObjectsDeleteAll(0,prefix);
  }
