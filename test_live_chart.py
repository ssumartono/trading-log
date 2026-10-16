import unittest
from types import SimpleNamespace
from unittest.mock import patch
from live_chart import read_live_chart
class ChartTests(unittest.TestCase):
    def fake(self):
        rates=[{'time':2,'open':10,'high':12,'low':9,'close':11,'tick_volume':5},{'time':1,'open':9,'high':11,'low':8,'close':10,'tick_volume':7}]
        info=SimpleNamespace(name='XAUUSD',visible=True,digits=2,point=.01)
        fake=SimpleNamespace(**{'TIMEFRAME_'+k:i for i,k in enumerate(['M1','M5','M15','M30','H1','H4','D1'])})
        fake.initialize=lambda *a,**k:True;fake.shutdown=lambda:None;fake.account_info=lambda:SimpleNamespace(login=1,server='A',balance=100,equity=100,profit=0,currency='USD');fake.terminal_info=lambda:SimpleNamespace(connected=True);fake.symbols_get=lambda:[info];fake.symbol_info=lambda s:info;fake.symbol_info_tick=lambda s:SimpleNamespace(time=2,bid=11,ask=11.1);fake.copy_rates_from_pos=lambda *a:rates;fake.positions_get=lambda **k:[]
        return fake
    def test_candles_sorted_and_account_verified(self):
        state={'brokers':[{'id':1,'integration':{'path':'terminal','login':'1','server':'A'}}]}
        with patch.dict('sys.modules',{'MetaTrader5':self.fake()}):
            result=read_live_chart(state,{'brokerId':1,'timeframe':'M15'})
            self.assertEqual(result['indicators'],[])
            self.assertEqual([c['time'] for c in result['candles']],[1,2]);self.assertEqual(result['symbol'],'XAUUSD')
            state['brokers'][0]['integration']['login']='2'
            with self.assertRaisesRegex(ValueError,'berbeda'):read_live_chart(state,{'brokerId':1})
    def test_position_tp_sl_and_ticket_from_mt5(self):
        fake=self.fake();fake.positions_get=lambda **k:[SimpleNamespace(ticket=123,type=0,volume=.01,price_open=10,sl=9,tp=12,profit=1)]
        state={'brokers':[{'id':1,'integration':{'path':'terminal','login':'1','server':'A'}}]}
        with patch.dict('sys.modules',{'MetaTrader5':fake}):result=read_live_chart(state,{'brokerId':1})
        self.assertEqual(result['positions'][0]['ticket'],'123');self.assertEqual(result['positions'][0]['sl'],9);self.assertEqual(result['positions'][0]['tp'],12)
    def test_indicator_uses_extra_history_and_aligns_to_visible_candles(self):
        fake=self.fake();requests=[]
        def history(*args):
            requests.append(args)
            return [{'time':i+1,'open':100+i*.1,'high':101+i*.1,'low':99+i*.1,'close':100+i*.1,'tick_volume':5} for i in range(2400)]
        fake.copy_rates_from_pos=history
        state={'brokers':[{'id':1,'integration':{'path':'terminal','login':'1','server':'A'}}]}
        with patch.dict('sys.modules',{'MetaTrader5':fake}):result=read_live_chart(state,{'brokerId':1,'indicators':[{'id':'first','type':'range-oscillator','length':50},{'id':'second','type':'range-oscillator','length':20,'multiplier':3}]})
        self.assertEqual(len(result['indicators']),2)
        self.assertEqual(result['indicators'][1]['length'],20)
        self.assertEqual(requests[0][-1],3000)
        self.assertEqual(len(result['candles']),300)
        indicator=result['indicators'][0]
        self.assertEqual(indicator['historyBars'],2400);self.assertEqual(indicator['atrPeriod'],2000)
        self.assertEqual([p['time'] for p in indicator['points']],[p['time'] for p in result['candles']])
        self.assertTrue(all(p['value'] is not None for p in indicator['points']))
    def test_invalid_indicator_requests_rejected(self):
        for indicators in [[{'type':'unknown'}],[{'id':'a','type':'range-oscillator','length':501}],[{'id':'a','type':'range-oscillator','multiplier':float('nan')}],[{'id':'a','type':'range-oscillator'}]*9]:
            with self.assertRaises(ValueError):read_live_chart({},dict(indicators=indicators))
    def test_broker_plus_three_normalizes_candles_and_tick_to_utc(self):
        from datetime import datetime,timezone
        utc=int(datetime(2026,10,16,3,35,tzinfo=timezone.utc).timestamp())
        fake=self.fake();fake.symbol_info_tick=lambda s:SimpleNamespace(time=utc+10800,bid=11,ask=11.1)
        fake.copy_rates_from_pos=lambda *a:[{'time':utc+10800,'open':10,'high':12,'low':9,'close':11,'tick_volume':5}]
        state={'brokers':[{'id':1,'integration':{'path':'terminal','login':'1','server':'A','timestampMode':'server','serverUtcOffsetMinutes':180,'timeConfirmed':True}}]}
        with patch.dict('sys.modules',{'MetaTrader5':fake}):result=read_live_chart(state,{'brokerId':1,'timeframe':'M1'})
        self.assertEqual(result['tickTime'],utc);self.assertEqual(result['candles'][0]['time'],utc)
        self.assertEqual(result['sourceOffsetMinutes'],180);self.assertTrue(result['timeConfirmed'])
if __name__=='__main__':unittest.main()
