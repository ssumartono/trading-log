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
            self.assertEqual([c['time'] for c in result['candles']],[1,2]);self.assertEqual(result['symbol'],'XAUUSD')
            state['brokers'][0]['integration']['login']='2'
            with self.assertRaisesRegex(ValueError,'berbeda'):read_live_chart(state,{'brokerId':1})
if __name__=='__main__':unittest.main()
