// Original Pine script © Zeiierman.
// MT5 adaptation: CC BY-NC-SA 4.0, noncommercial, share alike.
// https://creativecommons.org/licenses/by-nc-sa/4.0/
#property copyright "Original © Zeiierman; MT5 adaptation"
#property link "https://creativecommons.org/licenses/by-nc-sa/4.0/"
#property version "1.10"
#property indicator_separate_window
#property indicator_buffers 7
#property indicator_plots 2
#property indicator_type1 DRAW_COLOR_HISTOGRAM
#property indicator_type2 DRAW_COLOR_LINE
#property indicator_label1 "Oscillator shading"
#property indicator_label2 "Range Oscillator"
#property indicator_width1 2
#property indicator_width2 2
#property indicator_level1 100
#property indicator_level2 0
#property indicator_level3 -100
#property indicator_levelcolor clrGray
#property indicator_levelstyle STYLE_DOT

input int MinimumRangeLength=50;
input double RangeWidthMultiplier=2.0;
input int NumberOfHeatLevels=2;
input int MinimumTouchesPerLevel=1;
input color StrongBullishColor=C'9,255,0';
input color StrongBearishColor=clrRed;
input color WeakBearishColor=clrMaroon;
input color WeakBullishColor=clrGreen;
input color TransitionColor=clrBlue;
input bool ShowShading=true;
input bool ShowBuySell=true;
input bool ClosedBarSignals=true; // Confirm signals after the candle closes
input int SignalOffsetPoints=30;

string signalPrefix;

void RemoveSignals()
{
   if(signalPrefix!="") ObjectsDeleteAll(0,signalPrefix,0,-1);
}

void OnDeinit(const int reason)
{
   RemoveSignals();
   ChartRedraw(0);
}

void MarkSignal(datetime barTime,double price,bool buy)
{
   string name=signalPrefix+IntegerToString((long)barTime);
   color c=buy?StrongBullishColor:StrongBearishColor;
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_ARROW,0,barTime,price);
   else ObjectMove(0,name,0,barTime,price);
   ObjectSetInteger(0,name,OBJPROP_ARROWCODE,buy?233:234);
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,buy?ANCHOR_TOP:ANCHOR_BOTTOM);
   ObjectSetInteger(0,name,OBJPROP_COLOR,c);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,2);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,name,OBJPROP_HIDDEN,true);
   ObjectSetString(0,name,OBJPROP_TOOLTIP,buy?"Buy: oscillator crossed above +100":"Sell: oscillator crossed below -100");
   string label=name+"_text";
   if(ObjectFind(0,label)<0) ObjectCreate(0,label,OBJ_TEXT,0,barTime,price);
   else ObjectMove(0,label,0,barTime,price);
   ObjectSetString(0,label,OBJPROP_TEXT,buy?"\nBuy":"Sell\n");
   ObjectSetInteger(0,label,OBJPROP_ANCHOR,buy?ANCHOR_LEFT_UPPER:ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0,label,OBJPROP_COLOR,c);
   ObjectSetInteger(0,label,OBJPROP_FONTSIZE,9);
   ObjectSetInteger(0,label,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,label,OBJPROP_HIDDEN,true);
}

double Shade[],ShadeColor[],Osc[],OscColor[],ATR200[],ATR2000[],Trend[];

color Blend(color foreground,color background,double opacity)
{
   uint f=(uint)foreground,b=(uint)background;
   int r=(int)MathRound((f&255)*opacity+(b&255)*(1-opacity));
   int g=(int)MathRound(((f>>8)&255)*opacity+((b>>8)&255)*(1-opacity));
   int blue=(int)MathRound(((f>>16)&255)*opacity+((b>>16)&255)*(1-opacity));
   return (color)(r|(g<<8)|(blue<<16));
}

int OnInit()
{
   if(MinimumRangeLength<1 || MinimumRangeLength>1000000 ||
      !MathIsValidNumber(RangeWidthMultiplier) || RangeWidthMultiplier<0.1 ||
      NumberOfHeatLevels<2 || NumberOfHeatLevels>100 || MinimumTouchesPerLevel<1 || SignalOffsetPoints<0)
      return INIT_PARAMETERS_INCORRECT;
   signalPrefix="RO_"+IntegerToString(ChartID())+"_"+IntegerToString((long)GetMicrosecondCount())+"_";
   SetIndexBuffer(0,Shade,INDICATOR_DATA);
   SetIndexBuffer(1,ShadeColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(2,Osc,INDICATOR_DATA);
   SetIndexBuffer(3,OscColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(4,ATR200,INDICATOR_CALCULATIONS);
   SetIndexBuffer(5,ATR2000,INDICATOR_CALCULATIONS);
   SetIndexBuffer(6,Trend,INDICATOR_CALCULATIONS);
   IndicatorSetString(INDICATOR_SHORTNAME,"Range Oscillator (Zeiierman) MT5");
   IndicatorSetInteger(INDICATOR_DIGITS,1);
   color background=(color)ChartGetInteger(0,CHART_COLOR_BACKGROUND);
   for(int p=0;p<2;p++)
   {
      PlotIndexSetInteger(p,PLOT_COLOR_INDEXES,25);
      PlotIndexSetInteger(p,PLOT_DRAW_BEGIN,MathMax(199,MinimumRangeLength));
      PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
      for(int k=0;k<25;k++)
      {
         color c=TransitionColor;
         if(k<22) c=Blend(k<11?WeakBullishColor:WeakBearishColor,background,0.21+0.079*(k%11));
         if(k==23) c=StrongBullishColor;
         if(k==24) c=StrongBearishColor;
         PlotIndexSetInteger(p,PLOT_LINE_COLOR,k,p==0?Blend(c,background,0.25):c);
      }
   }
   if(!ShowShading) PlotIndexSetInteger(0,PLOT_DRAW_TYPE,DRAW_NONE);
   return INIT_SUCCEEDED;
}

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],
                const double &close[],const long &tick_volume[],const long &volume[],const int &spread[])
{
   ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);
   ArraySetAsSeries(time,false);
   int start=prev_calculated>0 && prev_calculated<=rates_total?prev_calculated-1:0;
   if(start==0) RemoveSignals();
   for(int i=start;i<rates_total;i++)
   {
      Osc[i]=EMPTY_VALUE; Shade[i]=EMPTY_VALUE; OscColor[i]=22; ShadeColor[i]=22;
      Trend[i]=i>0?Trend[i-1]:0;
      double tr=high[i]-low[i];
      if(i>0) tr=MathMax(tr,MathMax(MathAbs(high[i]-close[i-1]),MathAbs(low[i]-close[i-1])));
      ATR200[i]=EMPTY_VALUE; ATR2000[i]=EMPTY_VALUE;
      if(i==199 || i==1999)
      {
         int period=i+1; double sum=0;
         for(int j=0;j<period;j++)
         {
            double t=high[j]-low[j];
            if(j>0) t=MathMax(t,MathMax(MathAbs(high[j]-close[j-1]),MathAbs(low[j]-close[j-1])));
            sum+=t;
         }
         if(i==199) ATR200[i]=sum/200.0;
         else ATR2000[i]=sum/2000.0;
      }
      if(i>199) ATR200[i]=(ATR200[i-1]*199+tr)/200.0;
      if(i>1999) ATR2000[i]=(ATR2000[i-1]*1999+tr)/2000.0;
      if(i<199 || i<MinimumRangeLength) continue;
      double weighted=0,weights=0;
      for(int j=0;j<MinimumRangeLength;j++)
      {
         int k=i-j;
         if(close[k-1]==0) continue;
         double w=MathAbs(close[k]-close[k-1])/close[k-1];
         weighted+=close[k]*w; weights+=w;
      }
      if(weights==0) continue;
      double ma=weighted/weights;
      double range=(i>=1999?ATR2000[i]:ATR200[i])*RangeWidthMultiplier;
      if(close[i]>ma) Trend[i]=1;
      else if(close[i]<ma) Trend[i]=-1;
      if(range==0) continue;
      Osc[i]=100*(close[i]-ma)/range;
      double hi=Osc[i],lo=Osc[i];
      for(int j=MathMax(0,i-99);j<i;j++)
         if(Osc[j]!=EMPTY_VALUE) { hi=MathMax(hi,Osc[j]); lo=MathMin(lo,Osc[j]); }
      int index=22;
      if(hi>lo && (i==0 || Trend[i]==Trend[i-1]))
      {
         double step=(hi-lo)/NumberOfHeatLevels,best=1.0e100,level=lo;
         for(int k=0;k<NumberOfHeatLevels;k++)
         {
            double candidate=lo+step*(k+0.5),d=MathAbs(Osc[i]-candidate);
            if(d<best) { best=d; level=candidate; }
         }
         int count=0;
         for(int j=MathMax(0,i-99);j<=i;j++)
            if(Osc[j]!=EMPTY_VALUE && Osc[j]>=level-step/2 && Osc[j]<level+step/2) count++;
         // Original uses the same weak color at both gradient endpoints.
         double t=MathMax(0.0,MathMin(1.0,(count-MinimumTouchesPerLevel)/10.0));
         double cold=1.0-MathMax(0.0,MathMin(100.0,80.0-count))/100.0;
         double opacity=cold+(1-cold)*t;
         int bucket=(int)MathRound(MathMax(0.0,MathMin(10.0,(opacity-0.21)/0.079)));
         index=(Trend[i]==1?0:11)+bucket;
      }
      if(close[i]>ma+range) index=23;
      else if(close[i]<ma-range) index=24;
      OscColor[i]=index; ShadeColor[i]=index; Shade[i]=Osc[i];
   }
   // Revisit the just-closed bar on a new candle, as well as the live bar.
   for(int i=MathMax(1,start-1);i<rates_total;i++)
   {
      bool buy=false,sell=false;
      if(ShowBuySell && (!ClosedBarSignals || i<rates_total-1) &&
         Osc[i]!=EMPTY_VALUE && Osc[i-1]!=EMPTY_VALUE)
      {
         buy=Osc[i]>100 && Osc[i-1]<=100;
         sell=Osc[i]<-100 && Osc[i-1]>=-100;
      }
      if(buy || sell)
         MarkSignal(time[i],buy?low[i]-SignalOffsetPoints*_Point:high[i]+SignalOffsetPoints*_Point,buy);
      else
      {
         string name=signalPrefix+IntegerToString((long)time[i]);
         ObjectDelete(0,name); ObjectDelete(0,name+"_text");
      }
   }
   return rates_total;
}
