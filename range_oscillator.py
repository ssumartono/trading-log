"""Range Oscillator, ported from indicators/RangeOscillator.mq5 (v1.10).

Original Pine script copyright Zeiierman; local MT5 adaptation and this port:
CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/ .
The line, heat buckets and closed-bar breakout markers follow the local source.
"""
import math


def calculate(candles,point=0.01,length=50,multiplier=2.0,heat_levels=2,touches=1):
    if not 1<=length<=1000000 or not math.isfinite(multiplier) or multiplier<0.1:
        raise ValueError('Parameter Range Oscillator tidak valid.')
    if not 2<=heat_levels<=100 or touches<1:
        raise ValueError('Parameter heatmap tidak valid.')
    points=[];signals=[];trs=[];atr200=None;atr2000=None;trend=0
    for i,bar in enumerate(candles):
        close=bar['close'];tr=bar['high']-bar['low']
        if i:tr=max(tr,abs(bar['high']-candles[i-1]['close']),abs(bar['low']-candles[i-1]['close']))
        trs.append(tr)
        if i==199:atr200=sum(trs)/200
        elif i>199:atr200=(atr200*199+tr)/200
        if i==1999:atr2000=sum(trs)/2000
        elif i>1999:atr2000=(atr2000*1999+tr)/2000
        output={'time':bar['time'],'value':None,'colorIndex':22};points.append(output)
        if i<max(199,length):continue
        weighted=weights=0.0
        for k in range(i,i-length,-1):
            previous=candles[k-1]['close']
            if previous==0:continue
            weight=abs(candles[k]['close']-previous)/previous
            weighted+=candles[k]['close']*weight;weights+=weight
        if weights==0:continue
        mean=weighted/weights;spread=(atr2000 if i>=1999 else atr200)*multiplier
        previous_trend=trend
        if close>mean:trend=1
        elif close<mean:trend=-1
        if spread==0:continue
        value=100*(close-mean)/spread
        if not math.isfinite(value):continue
        output['value']=value
        recent=[p['value'] for p in points[max(0,i-99):i+1] if p['value'] is not None]
        high=max(recent);low=min(recent);index=22
        if high>low and trend==previous_trend:
            step=(high-low)/heat_levels
            level=min((low+step*(k+0.5) for k in range(heat_levels)),key=lambda candidate:abs(value-candidate))
            count=sum(level-step/2<=v<level+step/2 for v in recent)
            t=max(0,min(1,(count-touches)/10));cold=1-max(0,min(100,80-count))/100
            opacity=cold+(1-cold)*t
            bucket=math.floor(max(0,min(10,(opacity-0.21)/0.079))+0.5)
            index=(0 if trend==1 else 11)+bucket
        if close>mean+spread:index=23
        elif close<mean-spread:index=24
        output['colorIndex']=index
        previous=points[i-1]['value'] if i else None
        if i<len(candles)-1 and previous is not None:
            buy=value>100 and previous<=100;sell=value< -100 and previous>=-100
            if buy or sell:signals.append({'time':bar['time'],'side':'Buy' if buy else 'Sell','price':bar['low']-30*point if buy else bar['high']+30*point})
    return {'name':'Range Oscillator (Zeiierman)','length':length,'multiplier':multiplier,
        'heatLevels':heat_levels,'minimumTouches':touches,'atrPeriod':2000 if len(candles)>=2000 else 200,
        'historyBars':len(candles),'closedBarSignals':True,'points':points,'signals':signals}
