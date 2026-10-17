#property strict
#property version "1.30"
#property description "Manual signals: EMA/SMA setup followed by next-candle breakout and SMA slope confirmation."
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots 6
#property indicator_label1 "EMA"
#property indicator_type1 DRAW_LINE
#property indicator_color1 clrDodgerBlue
#property indicator_width1 2
#property indicator_label2 "SMA"
#property indicator_type2 DRAW_LINE
#property indicator_color2 clrWhite
#property indicator_width2 2
#property indicator_label3 "ENTRY BUY confirmed"
#property indicator_type3 DRAW_ARROW
#property indicator_color3 clrLimeGreen
#property indicator_width3 2
#property indicator_label4 "ENTRY SELL confirmed"
#property indicator_type4 DRAW_ARROW
#property indicator_color4 clrTomato
#property indicator_width4 2
#property indicator_label5 "Calon BUY"
#property indicator_type5 DRAW_ARROW
#property indicator_color5 clrGold
#property indicator_label6 "Calon SELL"
#property indicator_type6 DRAW_ARROW
#property indicator_color6 clrGold
input bool InpShowCandidates=true;
input bool InpAlertCandidates=true;
input bool InpAlertCancelled=false;
input int InpFastPeriod=9;
input int InpSlowPeriod=20;
input bool InpPopupAlerts=true;
input bool InpPushAlerts=false;
input int InpHistoryBars=2000;
input int InpPanelX=16;
input int InpPanelY=28;
input int InpPanelScale=100; // 75..150 percent

double ema[],sma[],buybuf[],sellbuf[],candidateBuy[],candidateSell[];
int fast=INVALID_HANDLE,slow=INVALID_HANDLE;
string prefix;
datetime seenbar=0,signalbar=0;
int signal_side=0;
double signal_ref=0;
bool initialized=false;
int setup_state=0; // 0 none, 1 pending, 2 confirmed, 3 cancelled
bool price_pass=false,ma_pass=false,slope_pass=false;
datetime confirmation_time=0,last_entry_time=0;
int last_entry_side=0;
double last_entry_price=0,trigger_level=0;

int CrossAt(int i)
  {
   if(ema[i+1]<=sma[i+1] && ema[i]>sma[i]) return 1;
   if(ema[i+1]>=sma[i+1] && ema[i]<sma[i]) return -1;
   return 0;
  }
bool ConfirmAt(int i,int side,const double &high[],const double &low[],const double &close[],bool &p,bool &m,bool &slope)
  {
   p=side==1?close[i]>high[i+1]:close[i]<low[i+1];
   m=side==1?ema[i]>sma[i]:ema[i]<sma[i];
   slope=side==1?sma[i]>sma[i+1]:sma[i]<sma[i+1];
   return p && m && slope;
  }

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
   color accent=setup_state==1?C'238,190,88':setup_state==3?muted:signal_side==1?C'63,213,160':signal_side==-1?C'255,121,119':C'112,165,231';
   color band=setup_state==1?C'52,44,29':setup_state==3?C'33,40,51':signal_side==1?C'20,52,48':signal_side==-1?C'54,32,40':C'28,42,61';
   Box("card",0,0,panel_width,Px(404),bg,edge);
   Box("accent",0,0,Px(4),Px(404),accent,accent);
   Box("signal_band",Px(18),Px(74),panel_width-Px(36),Px(64),band,band);
   Box("divider",Px(20),Px(205),panel_width-Px(40),1,edge,edge);
   Box("footer",Px(18),Px(346),panel_width-Px(36),Px(35),C'24,33,47',C'24,33,47');
   CardText("title",Px(20),Px(16),"EMA / SMA",white,14,panel_width-Px(140));
   CardText("version",panel_width-Px(108),Px(22),"CONFIRM ENTRY",muted,8,Px(94));
   string tf=EnumToString(_Period);StringReplace(tf,"PERIOD_","");
   CardText("symbol",Px(20),Px(46),_Symbol+" / "+tf+"   EMA "+(string)InpFastPeriod+" / SMA "+(string)InpSlowPeriod,muted,10);
   string state=setup_state==1?"CALON":setup_state==2?"TERKONFIRMASI":setup_state==3?"DIBATALKAN":"MENUNGGU CROSSOVER";
   CardText("direction",Px(30),Px(80),signal_side==1?"BUY":signal_side==-1?"SELL":"WAIT",accent,18,Px(100));
   CardText("opposite",Px(138),Px(84),state,white,10);
   CardText("confirmation",Px(30),Px(114),setup_state==1?"Tunggu candle berikutnya selesai. Belum entry.":setup_state==2?"Panah entry pada candle konfirmasi selesai.":setup_state==3?"Lewati calon entry. Tunggu crossover baru.":"Crossover adalah calon, bukan entry langsung.",muted,8);
   int column=panel_width/2+Px(10);
   CardText("time_label",Px(20),Px(152),"CANDLE CALON SINYAL",muted,8,column-Px(30));
   CardText("price_label",column,Px(152),signal_side==1?"HIGH UNTUK DILEWATI":"LOW UNTUK DILEWATI",muted,8);
   CardText("time",Px(20),Px(176),signalbar>0?TimeToString(signalbar,TIME_DATE|TIME_MINUTES):"--",white,10,column-Px(30));
   CardText("price",column,Px(174),signal_side!=0?DoubleToString(trigger_level,_Digits):"--",white,12);
   string waiting="MENUNGGU";
   CardText("rule_price",Px(20),Px(217),"1  Close melewati High/Low calon: "+(setup_state==1?waiting:setup_state==0?"--":price_pass?"LOLOS":"GAGAL"),white,9);
   CardText("rule_ma",Px(20),Px(240),"2  EMA tetap searah terhadap SMA: "+(setup_state==1?waiting:setup_state==0?"--":ma_pass?"LOLOS":"GAGAL"),white,9);
   CardText("rule_slope",Px(20),Px(263),"3  Kemiringan SMA sesuai arah: "+(setup_state==1?waiting:setup_state==0?"--":slope_pass?"LOLOS":"GAGAL"),white,9);
   CardText("last_entry",Px(20),Px(292),"Entry terkonfirmasi terakhir: "+(last_entry_side==0?"--":(last_entry_side==1?"BUY ":"SELL ")+TimeToString(last_entry_time,TIME_DATE|TIME_MINUTES)),muted,9);
   CardText("exit_rule",Px(20),Px(315),signal_side==0?"Exit posisi: acuan crossover berlawanan.":"Cross "+(signal_side==1?"BUY":"SELL")+": periksa exit "+(signal_side==1?"SELL":"BUY")+" manual, terpisah dari entry.",muted,9);
   CardText("manual",Px(30),Px(356),"MANUAL / Sinyal historis bukan entry baru",C'190,206,225',9,panel_width-Px(60));
   CardText("version_small",Px(20),Px(388),"v1.30 | Tanpa order, SL, TP atau trailing otomatis",muted,7);
   ChartRedraw();
  }
int OnInit()
  {
   if(InpPanelX<0 || InpPanelY<0 || InpPanelScale<75 || InpPanelScale>150 || InpFastPeriod<1 || InpSlowPeriod<=InpFastPeriod || InpHistoryBars<50 || InpHistoryBars>20000) return INIT_PARAMETERS_INCORRECT;
   SetIndexBuffer(0,ema,INDICATOR_DATA);SetIndexBuffer(1,sma,INDICATOR_DATA);
   SetIndexBuffer(2,buybuf,INDICATOR_DATA);SetIndexBuffer(3,sellbuf,INDICATOR_DATA);
   SetIndexBuffer(4,candidateBuy,INDICATOR_DATA);SetIndexBuffer(5,candidateSell,INDICATOR_DATA);
   ArraySetAsSeries(candidateBuy,true);ArraySetAsSeries(candidateSell,true);
   ArraySetAsSeries(ema,true);ArraySetAsSeries(sma,true);ArraySetAsSeries(buybuf,true);ArraySetAsSeries(sellbuf,true);
   PlotIndexSetInteger(4,PLOT_ARROW,159);PlotIndexSetInteger(5,PLOT_ARROW,159);
   PlotIndexSetInteger(4,PLOT_DRAW_TYPE,InpShowCandidates?DRAW_ARROW:DRAW_NONE);PlotIndexSetInteger(5,PLOT_DRAW_TYPE,InpShowCandidates?DRAW_ARROW:DRAW_NONE);
   PlotIndexSetInteger(2,PLOT_ARROW,233);PlotIndexSetInteger(3,PLOT_ARROW,234);
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,InpFastPeriod-1);PlotIndexSetInteger(1,PLOT_DRAW_BEGIN,InpSlowPeriod-1);
   fast=iMA(_Symbol,_Period,InpFastPeriod,0,MODE_EMA,PRICE_CLOSE);
   slow=iMA(_Symbol,_Period,InpSlowPeriod,0,MODE_SMA,PRICE_CLOSE);
   if(fast==INVALID_HANDLE || slow==INVALID_HANDLE) return INIT_FAILED;
   prefix="SignalOnly_"+(string)ChartID()+"_"+(string)GetMicrosecondCount()+"_";
   IndicatorSetString(INDICATOR_SHORTNAME,"EMA SMA Confirmed Manual v1.30");return INIT_SUCCEEDED;
  }
int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],const double &open[],const double &high[],const double &low[],const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
  {
   if(rates_total<InpSlowPeriod+3) return 0;
   ArraySetAsSeries(time,true);ArraySetAsSeries(high,true);ArraySetAsSeries(low,true);ArraySetAsSeries(close,true);
   if(CopyBuffer(fast,0,0,rates_total,ema)!=rates_total || CopyBuffer(slow,0,0,rates_total,sma)!=rates_total) return prev_calculated;
   if(prev_calculated==0)
     { ArrayInitialize(buybuf,EMPTY_VALUE);ArrayInitialize(sellbuf,EMPTY_VALUE);ArrayInitialize(candidateBuy,EMPTY_VALUE);ArrayInitialize(candidateSell,EMPTY_VALUE); }
   buybuf[0]=EMPTY_VALUE;sellbuf[0]=EMPTY_VALUE;candidateBuy[0]=EMPTY_VALUE;candidateSell[0]=EMPTY_VALUE;
   int count=MathMin(rates_total-InpSlowPeriod-2,InpHistoryBars);
   for(int i=count;i>=1;i--)
     {
      buybuf[i]=EMPTY_VALUE;sellbuf[i]=EMPTY_VALUE;candidateBuy[i]=EMPTY_VALUE;candidateSell[i]=EMPTY_VALUE;
      double offset=MathMax(high[i]-low[i],10*_Point)*0.25;
      int raw=CrossAt(i);
      if(raw==1) candidateBuy[i]=low[i]-offset;
      if(raw==-1) candidateSell[i]=high[i]+offset;
      int setup=CrossAt(i+1);bool p=false,m=false,sl=false;
      if(setup!=0 && ConfirmAt(i,setup,high,low,close,p,m,sl))
        { if(setup==1) buybuf[i]=low[i]-offset*2;else sellbuf[i]=high[i]+offset*2; }
     }
   bool first=!initialized || prev_calculated==0;
   bool newbar=initialized && time[0]!=seenbar;
   if(first || newbar)
     {
      signal_side=0;signalbar=0;signal_ref=0;setup_state=0;confirmation_time=0;
      price_pass=false;ma_pass=false;slope_pass=false;trigger_level=0;
      last_entry_side=0;last_entry_time=0;last_entry_price=0;
      for(int i=1;i<=count;i++)
        {
         if(last_entry_side==0 && (buybuf[i]!=EMPTY_VALUE || sellbuf[i]!=EMPTY_VALUE))
           { last_entry_side=buybuf[i]!=EMPTY_VALUE?1:-1;last_entry_time=time[i];last_entry_price=close[i]; }
         if(signal_side==0)
           {
            int side=CrossAt(i);
            if(side!=0)
              {
               signal_side=side;signalbar=time[i];signal_ref=close[i];trigger_level=side==1?high[i]:low[i];
               if(i==1) setup_state=1;
               else { confirmation_time=time[i-1];setup_state=ConfirmAt(i-1,side,high,low,close,price_pass,ma_pass,slope_pass)?2:3; }
              }
           }
         if(last_entry_side!=0 && signal_side!=0) break;
        }
      if(!first && newbar)
        {
         if(buybuf[1]!=EMPTY_VALUE || sellbuf[1]!=EMPTY_VALUE)
            Notify(buybuf[1]!=EMPTY_VALUE?"ENTRY BUY TERKONFIRMASI - eksekusi manual":"ENTRY SELL TERKONFIRMASI - eksekusi manual");
         else if(CrossAt(2)!=0 && InpAlertCancelled) Notify("Calon entry DIBATALKAN: konfirmasi candle berikutnya gagal");
         if(CrossAt(1)!=0 && InpAlertCandidates)
            Notify(CrossAt(1)==1?"CALON BUY / periksa exit SELL. Tunggu konfirmasi entry":"CALON SELL / periksa exit BUY. Tunggu konfirmasi entry");
        }
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
