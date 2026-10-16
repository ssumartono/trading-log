import math
import unittest
from range_oscillator import calculate


def bars(count,close=lambda i:100+i):
    return [{'time':i+1,'open':close(i),'high':close(i)+1,'low':close(i)-1,'close':close(i)} for i in range(count)]


class RangeOscillatorTests(unittest.TestCase):
    def test_warmup_is_empty_and_first_value_matches_weighted_mean(self):
        rows=bars(201);result=calculate(rows)
        self.assertTrue(all(p['value'] is None for p in result['points'][:199]))
        for i in (199,200):
            weights=[(rows[k]['close']-rows[k-1]['close'])/rows[k-1]['close'] for k in range(i-49,i+1)]
            mean=sum(rows[k]['close']*weight for k,weight in zip(range(i-49,i+1),weights))/sum(weights)
            self.assertAlmostEqual(result['points'][i]['value'],100*(rows[i]['close']-mean)/4)
        self.assertEqual(result['atrPeriod'],200)

    def test_switch_to_atr2000_uses_the_2000_bar_seed(self):
        rows=bars(2001,lambda i:100+i*.2)
        for i,row in enumerate(rows):row.update(high=row['close']+(1 if i<1000 else 3),low=row['close']-(1 if i<1000 else 3))
        result=calculate(rows)
        for i,atr in [(1999,4),(2000,(4*1999+6)/2000)]:
            weights=[abs(rows[k]['close']-rows[k-1]['close'])/rows[k-1]['close'] for k in range(i-49,i+1)]
            mean=sum(rows[k]['close']*weight for k,weight in zip(range(i-49,i+1),weights))/sum(weights)
            self.assertAlmostEqual(result['points'][i]['value'],100*(rows[i]['close']-mean)/(atr*2))
        self.assertEqual(result['atrPeriod'],2000)

    def test_constant_prices_remain_empty_without_fake_zero_values(self):
        result=calculate(bars(2200,lambda i:100))
        self.assertTrue(all(p['value'] is None for p in result['points']))
        self.assertEqual(result['signals'],[])

    def test_breakout_markers_use_closed_bars_and_threshold_crossings(self):
        rows=bars(600,lambda i:100+20*math.sin(i/12)+i*.001)
        result=calculate(rows,point=.01);points=result['points']
        self.assertEqual({s['side'] for s in result['signals']},{'Buy','Sell'})
        for signal in result['signals']:
            i=signal['time']-1
            self.assertLess(i,len(rows)-1)
            if signal['side']=='Buy':
                self.assertGreater(points[i]['value'],100);self.assertLessEqual(points[i-1]['value'],100)
                self.assertAlmostEqual(signal['price'],rows[i]['low']-.3)
            else:
                self.assertLess(points[i]['value'],-100);self.assertGreaterEqual(points[i-1]['value'],-100)
                self.assertAlmostEqual(signal['price'],rows[i]['high']+.3)
        for point in points:
            self.assertIn(point['colorIndex'],range(25))
            if point['value'] is not None and point['value']>100:self.assertEqual(point['colorIndex'],23)
            if point['value'] is not None and point['value']< -100:self.assertEqual(point['colorIndex'],24)

    def test_invalid_parameters_are_rejected(self):
        for params in ({'length':0},{'multiplier':float('nan')},{'heat_levels':1},{'touches':0}):
            with self.assertRaises(ValueError):calculate([],**params)


if __name__=='__main__':unittest.main()
