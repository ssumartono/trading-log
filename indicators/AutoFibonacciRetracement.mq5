#property version "1.00"
#property description "Adaptive ATR swings with EMA trend filter and live Fibonacci retracements"
#property indicator_chart_window
#property indicator_plots 0

enum ENUM_SWING_STYLE { SCALPING=0, TREND_TRADING=1, SWING_TRADING=2, CUSTOM=3 };
input ENUM_SWING_STYLE SwingStyle=TREND_TRADING;
input int CustomATRPeriod=14;
input double CustomReversalATR=3.0;
input int CustomEMAPeriod=34;
input bool UseTrendFilter=true;
input bool LiveSwing=true; // Update endpoint on current candle; reversals use closed candles
input int HistoryBars=3000;
input bool Show786=true;
input bool ShowSwingLine=true;
input bool ShowBoundaryRays=true;
input bool FullLevelRays=false;
input int LabelPositionPercent=65;
input int FontSize=10;
input color Color236=C'255,65,54';
input color Color382=C'129,199,132';
input color Color500=C'76,175,80';
input color Color618=C'0,166,156';
input color Color786=C'86,180,248';
input color HighColor=C'186,65,75';
input color LowColor=C'55,146,65';
input color SwingColor=clrDimGray;

string prefix;
int atrPeriod,emaPeriod;
double reversalATR;
double ratios[7]={0,0.236,0.382,0.5,0.618,0.786,1};
double startPrice=0,endPrice=0;
datetime startTime=0,endTime=0,lastBar=0;
bool ready=false;

void BaseObject(const string name,const color shade)
{
   ObjectSetInteger(0,name,OBJPROP_COLOR,shade);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
}

void Line(const string suffix,datetime t1,double p1,datetime t2,double p2,
          color shade,ENUM_LINE_STYLE style,bool ray)
{
   string name=prefix+suffix;
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_TREND,0,t1,p1,t2,p2);
   ObjectMove(0,name,0,t1,p1);
   ObjectMove(0,name,1,t2,p2);
   BaseObject(name,shade);
   ObjectSetInteger(0,name,OBJPROP_STYLE,style);
   ObjectSetInteger(0,name,OBJPROP_RAY_RIGHT,ray);
   ObjectSetInteger(0,name,OBJPROP_RAY_LEFT,false);
}

void Render()
{
   if(!ready) return;
   int width=(int)ChartGetInteger(0,CHART_WIDTH_IN_PIXELS);
   int height=(int)ChartGetInteger(0,CHART_HEIGHT_IN_PIXELS);
   int x=MathMax(5,MathMin(width-240,width*LabelPositionPercent/100));
   color shades[7];
   shades[0]=(endPrice>startPrice ? HighColor : LowColor);
   shades[1]=Color236; shades[2]=Color382; shades[3]=Color500;
   shades[4]=Color618; shades[5]=Color786;
   shades[6]=(endPrice>startPrice ? LowColor : HighColor);
   if(ShowSwingLine) Line("swing",startTime,startPrice,endTime,endPrice,SwingColor,STYLE_DASH,false);
   for(int k=0;k<7;k++)
   {
      string key=IntegerToString(k);
      double price=endPrice+(startPrice-endPrice)*ratios[k];
      bool enabled=(k!=5 || Show786);
      bool boundary=(k==0 || k==6);
      string ray=prefix+"ray"+key;
      if(enabled && ((boundary && ShowBoundaryRays) || (!boundary && FullLevelRays)))
         Line("ray"+key,endTime,price,endTime+PeriodSeconds(_Period),price,shades[k],boundary?STYLE_DOT:STYLE_SOLID,true);
      else ObjectDelete(0,ray);
      int px,py;
      bool visible=enabled && !boundary && ChartTimePriceToXY(0,0,endTime,price,px,py) && py>FontSize && py<height-FontSize;
      string text=prefix+"label"+key,segment=prefix+"segment"+key;
      if(!visible) { ObjectDelete(0,text); ObjectDelete(0,segment); continue; }
      if(ObjectFind(0,segment)<0) ObjectCreate(0,segment,OBJ_RECTANGLE_LABEL,0,0,0);
      ObjectSetInteger(0,segment,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,segment,OBJPROP_XDISTANCE,x);
      ObjectSetInteger(0,segment,OBJPROP_YDISTANCE,py);
      ObjectSetInteger(0,segment,OBJPROP_XSIZE,45);
      ObjectSetInteger(0,segment,OBJPROP_YSIZE,2);
      ObjectSetInteger(0,segment,OBJPROP_BGCOLOR,shades[k]);
      ObjectSetInteger(0,segment,OBJPROP_BORDER_TYPE,BORDER_FLAT);
      BaseObject(segment,shades[k]);
      if(ObjectFind(0,text)<0) ObjectCreate(0,text,OBJ_LABEL,0,0,0);
      BaseObject(text,shades[k]);
      ObjectSetInteger(0,text,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,text,OBJPROP_ANCHOR,ANCHOR_LEFT);
      ObjectSetInteger(0,text,OBJPROP_XDISTANCE,x+60);
      ObjectSetInteger(0,text,OBJPROP_YDISTANCE,py);
      ObjectSetInteger(0,text,OBJPROP_FONTSIZE,FontSize);
      ObjectSetString(0,text,OBJPROP_FONT,"Arial");
      ObjectSetString(0,text,OBJPROP_TEXT,DoubleToString(ratios[k],3)+" ("+DoubleToString(price,_Digits)+")");
   }
   ChartRedraw(0);
}

int OnInit()
{
   if(CustomATRPeriod<2 || CustomATRPeriod>1000 || CustomEMAPeriod<2 || CustomEMAPeriod>1000 ||
      !MathIsValidNumber(CustomReversalATR) || CustomReversalATR<=0 || HistoryBars<100 || HistoryBars>100000 ||
      LabelPositionPercent<5 || LabelPositionPercent>90 || FontSize<6 || FontSize>24)
      return INIT_PARAMETERS_INCORRECT;
   atrPeriod=14; emaPeriod=34; reversalATR=3;
   if(SwingStyle==SCALPING) { emaPeriod=13; reversalATR=1.5; }
   if(SwingStyle==SWING_TRADING) { emaPeriod=89; reversalATR=5; }
   if(SwingStyle==CUSTOM) { atrPeriod=CustomATRPeriod; emaPeriod=CustomEMAPeriod; reversalATR=CustomReversalATR; }
   if(HistoryBars<MathMax(atrPeriod,emaPeriod)+10) return INIT_PARAMETERS_INCORRECT;
   prefix="AutoFib_"+IntegerToString((long)GetMicrosecondCount())+"_";
   IndicatorSetString(INDICATOR_SHORTNAME,"Auto Fibonacci Retracement");
   return INIT_SUCCEEDED;
}

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[])
{
   if(rates_total<MathMax(atrPeriod,emaPeriod)+5) return 0;
   ArraySetAsSeries(time,true); ArraySetAsSeries(high,true);
   ArraySetAsSeries(low,true); ArraySetAsSeries(close,true);
   // Replay only on new bars/history changes. Bar zero may extend a swing but cannot reverse it.
   if(prev_calculated==0 || time[0]!=lastBar || prev_calculated!=rates_total)
   {
      int oldest=MathMin(rates_total-2,HistoryBars);
      double atr=high[oldest]-low[oldest],ema=close[oldest];
      double lo=low[oldest],hi=high[oldest],extreme=0;
      datetime lt=time[oldest],ht=time[oldest],et=0;
      int direction=0;
      ready=false;
      for(int i=oldest-1;i>=1;i--)
      {
         double tr=MathMax(high[i]-low[i],MathMax(MathAbs(high[i]-close[i+1]),MathAbs(low[i]-close[i+1])));
         atr+=(tr-atr)/atrPeriod;
         ema+=(close[i]-ema)*2.0/(emaPeriod+1);
         double threshold=MathMax(_Point,atr*reversalATR);
         if(oldest-i<MathMax(atrPeriod,emaPeriod))
         { lo=low[i]; hi=high[i]; lt=time[i]; ht=time[i]; continue; }
         if(direction==0)
         {
            if(low[i]<lo) { lo=low[i]; lt=time[i]; }
            if(high[i]>hi) { hi=high[i]; ht=time[i]; }
            if(time[i]>lt && close[i]-lo>=threshold && (!UseTrendFilter || close[i]>ema))
            { direction=1; startPrice=lo; startTime=lt; extreme=high[i]; et=time[i]; }
            else if(time[i]>ht && hi-close[i]>=threshold && (!UseTrendFilter || close[i]<ema))
            { direction=-1; startPrice=hi; startTime=ht; extreme=low[i]; et=time[i]; }
         }
         else if(direction==1)
         {
            if(high[i]>=extreme) { extreme=high[i]; et=time[i]; }
            if(time[i]>et && extreme-close[i]>=threshold && (!UseTrendFilter || close[i]<ema))
            { startPrice=extreme; startTime=et; direction=-1; extreme=low[i]; et=time[i]; }
         }
         else
         {
            if(low[i]<=extreme) { extreme=low[i]; et=time[i]; }
            if(time[i]>et && close[i]-extreme>=threshold && (!UseTrendFilter || close[i]>ema))
            { startPrice=extreme; startTime=et; direction=1; extreme=high[i]; et=time[i]; }
         }
      }
      if(direction!=0) { endPrice=extreme; endTime=et; ready=true; }
      else ObjectsDeleteAll(0,prefix);
      lastBar=time[0];
   }
   if(ready && LiveSwing)
   {
      if((endPrice>startPrice && high[0]>endPrice) || (endPrice<startPrice && low[0]<endPrice))
      { endPrice=(endPrice>startPrice?high[0]:low[0]); endTime=time[0]; }
   }
   Render();
   return rates_total;
}

void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam)
{
   if(id==CHARTEVENT_CHART_CHANGE) Render();
}

void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0,prefix);
   ChartRedraw(0);
}
