// Range Filter: original @DonovanWall; adapted @guikroth; Pine v5 @tvenn.
// MT5 conversion. Indicator only; does not place orders.
#property version "1.00"
#property indicator_chart_window
#property indicator_buffers 21
#property indicator_plots 8
#property indicator_type1 DRAW_FILLING
#property indicator_type2 DRAW_FILLING
#property indicator_type3 DRAW_COLOR_LINE
#property indicator_type4 DRAW_LINE
#property indicator_type5 DRAW_LINE
#property indicator_type6 DRAW_ARROW
#property indicator_type7 DRAW_ARROW
#property indicator_type8 DRAW_COLOR_CANDLES
#property indicator_label1 "Upper range;Filter"
#property indicator_label2 "Lower range;Filter"
#property indicator_label3 "Range Filter"
#property indicator_label4 "High Target"
#property indicator_label5 "Low Target"
#property indicator_label6 "Buy"
#property indicator_label7 "Sell"
#property indicator_label8 "Open;High;Low;Close"

input ENUM_APPLIED_PRICE Source=PRICE_CLOSE;
input int SamplingPeriod=100;
input double RangeMultiplier=3.0;
input color UpColor=clrWhite;
input color MidColor=C'144,191,249';
input color DownColor=clrBlue;
input bool ShowBands=true;
input bool FillBands=true;
input bool ColorCandles=true;
input bool ClosedBarSignals=true; // false matches Pine's live, changing bar signals
input int ArrowOffsetPoints=20;
input bool PopupAlert=false;
input bool PushAlert=false;
input bool SoundAlert=false;
input string SoundFile="alert.wav";

double UpperFill[],UpperBase[],LowerFill[],LowerBase[];
double Filter[],FilterColor[],Upper[],Lower[],Buy[],Sell[];
double CandleOpen[],CandleHigh[],CandleLow[],CandleClose[],CandleColor[];
double Price[],AverageRange[],SmoothRange[],Upward[],Downward[],State[];
datetime lastAlert=0;
bool alertsReady=false;

int OnInit()
{
   if(SamplingPeriod<1 || SamplingPeriod>1000000 ||
      !MathIsValidNumber(RangeMultiplier) || RangeMultiplier<0.1 || ArrowOffsetPoints<0)
      return INIT_PARAMETERS_INCORRECT;
   SetIndexBuffer(0,UpperFill,INDICATOR_DATA);
   SetIndexBuffer(1,UpperBase,INDICATOR_DATA);
   SetIndexBuffer(2,LowerFill,INDICATOR_DATA);
   SetIndexBuffer(3,LowerBase,INDICATOR_DATA);
   SetIndexBuffer(4,Filter,INDICATOR_DATA);
   SetIndexBuffer(5,FilterColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(6,Upper,INDICATOR_DATA);
   SetIndexBuffer(7,Lower,INDICATOR_DATA);
   SetIndexBuffer(8,Buy,INDICATOR_DATA);
   SetIndexBuffer(9,Sell,INDICATOR_DATA);
   SetIndexBuffer(10,CandleOpen,INDICATOR_DATA);
   SetIndexBuffer(11,CandleHigh,INDICATOR_DATA);
   SetIndexBuffer(12,CandleLow,INDICATOR_DATA);
   SetIndexBuffer(13,CandleClose,INDICATOR_DATA);
   SetIndexBuffer(14,CandleColor,INDICATOR_COLOR_INDEX);
   SetIndexBuffer(15,Price,INDICATOR_CALCULATIONS);
   SetIndexBuffer(16,AverageRange,INDICATOR_CALCULATIONS);
   SetIndexBuffer(17,SmoothRange,INDICATOR_CALCULATIONS);
   SetIndexBuffer(18,Upward,INDICATOR_CALCULATIONS);
   SetIndexBuffer(19,Downward,INDICATOR_CALCULATIONS);
   SetIndexBuffer(20,State,INDICATOR_CALCULATIONS);
   for(int p=0;p<8;p++)
   {
      PlotIndexSetDouble(p,PLOT_EMPTY_VALUE,EMPTY_VALUE);
      PlotIndexSetInteger(p,PLOT_DRAW_BEGIN,1);
   }
   // Native MT5 filling is opaque; use subdued colors instead of Pine alpha.
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,0,C'65,70,80');
   PlotIndexSetInteger(0,PLOT_LINE_COLOR,1,C'65,70,80');
   PlotIndexSetInteger(1,PLOT_LINE_COLOR,0,C'25,35,65');
   PlotIndexSetInteger(1,PLOT_LINE_COLOR,1,C'25,35,65');
   PlotIndexSetInteger(2,PLOT_COLOR_INDEXES,3);
   PlotIndexSetInteger(7,PLOT_COLOR_INDEXES,3);
   color colors[3]; colors[0]=UpColor; colors[1]=MidColor; colors[2]=DownColor;
   for(int c=0;c<3;c++)
   {
      PlotIndexSetInteger(2,PLOT_LINE_COLOR,c,colors[c]);
      PlotIndexSetInteger(7,PLOT_LINE_COLOR,c,colors[c]);
   }
   PlotIndexSetInteger(2,PLOT_LINE_WIDTH,2);
   PlotIndexSetInteger(3,PLOT_LINE_COLOR,UpColor);
   PlotIndexSetInteger(4,PLOT_LINE_COLOR,DownColor);
   PlotIndexSetInteger(5,PLOT_LINE_COLOR,UpColor);
   PlotIndexSetInteger(6,PLOT_LINE_COLOR,DownColor);
   PlotIndexSetInteger(5,PLOT_ARROW,233);
   PlotIndexSetInteger(6,PLOT_ARROW,234);
   IndicatorSetString(INDICATOR_SHORTNAME,"Range Filter ("+IntegerToString(SamplingPeriod)+", "+DoubleToString(RangeMultiplier,2)+")");
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
   return INIT_SUCCEEDED;
}

double AppliedPrice(const int i,const double &o[],const double &h[],const double &l[],const double &c[])
{
   switch(Source)
   {
      case PRICE_OPEN: return o[i];
      case PRICE_HIGH: return h[i];
      case PRICE_LOW: return l[i];
      case PRICE_MEDIAN: return (h[i]+l[i])/2.0;
      case PRICE_TYPICAL: return (h[i]+l[i]+c[i])/3.0;
      case PRICE_WEIGHTED: return (h[i]+l[i]+2.0*c[i])/4.0;
      default: return c[i];
   }
}

int OnCalculate(const int rates_total,const int prev_calculated,const datetime &time[],
                const double &open[],const double &high[],const double &low[],const double &close[],
                const long &tick_volume[],const long &volume[],const int &spread[])
{
   if(rates_total<3) return 0;
   ArraySetAsSeries(time,false); ArraySetAsSeries(open,false);
   ArraySetAsSeries(high,false); ArraySetAsSeries(low,false); ArraySetAsSeries(close,false);
   int start=prev_calculated>0 && prev_calculated<=rates_total ? prev_calculated-1 : 0;
   if(start==0) alertsReady=false;
   double a=2.0/(SamplingPeriod+1.0);
   double b=1.0/SamplingPeriod; // EMA period 2*SamplingPeriod-1
   for(int i=start;i<rates_total;i++)
   {
      Price[i]=AppliedPrice(i,open,high,low,close);
      Buy[i]=Sell[i]=EMPTY_VALUE;
      UpperFill[i]=UpperBase[i]=LowerFill[i]=LowerBase[i]=EMPTY_VALUE;
      CandleOpen[i]=CandleHigh[i]=CandleLow[i]=CandleClose[i]=EMPTY_VALUE;
      CandleColor[i]=1;
      if(i==0)
      {
         Filter[i]=Upper[i]=Lower[i]=EMPTY_VALUE; FilterColor[i]=1;
         AverageRange[i]=SmoothRange[i]=EMPTY_VALUE;
         Upward[i]=Downward[i]=State[i]=0;
         continue;
      }
      double delta=MathAbs(Price[i]-Price[i-1]);
      AverageRange[i]=i==1 ? delta : a*delta+(1-a)*AverageRange[i-1];
      // Store the second EMA before multiplying, so recursive state stays exact.
      SmoothRange[i]=i==1 ? AverageRange[i] : b*AverageRange[i]+(1-b)*SmoothRange[i-1];
      double r=SmoothRange[i]*RangeMultiplier;
      double previous=i==1 ? 0.0 : Filter[i-1]; // Pine nz(filter[1])
      Filter[i]=Price[i]>previous ? MathMax(previous,Price[i]-r) : MathMin(previous,Price[i]+r);
      Upward[i]=i==1 ? 0 : Filter[i]>previous ? Upward[i-1]+1 : Filter[i]<previous ? 0 : Upward[i-1];
      Downward[i]=i==1 ? 0 : Filter[i]<previous ? Downward[i-1]+1 : Filter[i]>previous ? 0 : Downward[i-1];
      FilterColor[i]=Upward[i]>0 ? 0 : Downward[i]>0 ? 2 : 1;
      double upper=Filter[i]+r,lower=Filter[i]-r;
      Upper[i]=ShowBands ? upper : EMPTY_VALUE;
      Lower[i]=ShowBands ? lower : EMPTY_VALUE;
      if(ShowBands && FillBands)
      {
         UpperFill[i]=upper; UpperBase[i]=Filter[i];
         LowerFill[i]=lower; LowerBase[i]=Filter[i];
      }
      bool changed=Price[i]!=Price[i-1];
      bool longCond=Price[i]>Filter[i] && changed && Upward[i]>0;
      bool shortCond=Price[i]<Filter[i] && changed && Downward[i]>0;
      State[i]=longCond ? 1 : shortCond ? -1 : State[i-1];
      bool eligible=!ClosedBarSignals || i<rates_total-1;
      if(eligible && longCond && State[i-1]==-1) Buy[i]=low[i]-ArrowOffsetPoints*_Point;
      if(eligible && shortCond && State[i-1]==1) Sell[i]=high[i]+ArrowOffsetPoints*_Point;
      if(ColorCandles)
      {
         CandleOpen[i]=open[i]; CandleHigh[i]=high[i]; CandleLow[i]=low[i]; CandleClose[i]=close[i];
         CandleColor[i]=longCond ? 0 : shortCond ? 2 : 1;
      }
   }
   int signalBar=ClosedBarSignals ? rates_total-2 : rates_total-1;
   if(!alertsReady) { lastAlert=time[signalBar]; alertsReady=true; }
   else if(time[signalBar]!=lastAlert && (Buy[signalBar]!=EMPTY_VALUE || Sell[signalBar]!=EMPTY_VALUE))
   {
      lastAlert=time[signalBar];
      string message=StringFormat("Range Filter %s | %s %s | %s",Buy[signalBar]!=EMPTY_VALUE ? "BUY" : "SELL",
                                  _Symbol,EnumToString(_Period),TimeToString(time[signalBar]));
      if(PopupAlert) Alert(message);
      if(PushAlert) SendNotification(message);
      if(SoundAlert) PlaySound(SoundFile);
   }
   return rates_total;
}
