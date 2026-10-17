import unittest
from unittest.mock import patch
from test_account_access import OwnershipHTTPTests

PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII='

class TraderSourcesTests(unittest.TestCase):
    setUp=OwnershipHTTPTests.setUp
    tearDown=OwnershipHTTPTests.tearDown
    call=OwnershipHTTPTests.call

    def test_live_chart_source_includes_indicator_data_and_persists(self):
        chart={'symbol':'EURUSD','timeframe':'M15','fetchedAt':'2026-10-16T10:00:00Z','bid':1,'ask':2,'spread':1,'candles':[{'time':1,'close':1.5}],'indicators':[{'type':'range-oscillator','points':[{'value':40}]}],'positions':[],'timeNote':'Candle terakhir berjalan','tickAgeSeconds':0}
        with patch('live_chart.read_live_chart',return_value=chart) as read,patch('trader_ai.market_context') as market,patch('trader_ai.answer_trader',return_value='Analisis chart') as answer:
            code,result=self.call('/api/trader/chat',{'brokerId':2,'message':'Analisis','includeLiveChart':True,'indicators':[]})
        self.assertEqual(code,200,result);read.assert_called_once();market.assert_not_called()
        self.assertTrue(result['sources']['liveChart'])
        self.assertEqual(answer.call_args.args[4]['indicators'],chart['indicators'])
        self.assertNotIn('account',answer.call_args.args[4])
        _,history=self.call('/api/trader/history',{'brokerId':2})
        self.assertEqual(history[-1]['chartContext']['sourceType'],'liveChart')

    def test_prompt_only_never_reads_market_and_history_retains_sources(self):
        with patch('trader_ai.market_context') as market,patch('trader_ai.answer_trader',return_value='Jawaban umum') as answer:
            code,result=self.call('/api/trader/chat',{'brokerId':2,'message':'Pertanyaan umum','includeMarket':False,'includeLogs':False})
        self.assertEqual(code,200,result);market.assert_not_called()
        self.assertEqual(answer.call_args.args[1:],(None,None))
        self.assertEqual(result['sources'],{'logs':False,'snapshot':False,'screenshot':False})
        code,history=self.call('/api/trader/history',{'brokerId':2})
        self.assertEqual(len(history),2);self.assertEqual(history[-1]['sources'],result['sources'])
        self.assertTrue(all(row['createdAt'] for row in history))

    def test_screenshot_is_sent_only_when_attached(self):
        with patch('trader_ai.market_context') as market,patch('trader_ai.answer_trader',return_value='Analisis gambar') as answer:
            code,result=self.call('/api/trader/chat',{'brokerId':2,'message':'Baca chart','screenshot':PNG})
        self.assertEqual(code,200,result);market.assert_not_called()
        self.assertEqual(answer.call_args.args[3],PNG)
        self.assertTrue(result['sources']['screenshot'])
        with patch('trader_ai.answer_trader') as answer:
            code,result=self.call('/api/trader/chat',{'brokerId':2,'message':'Baca chart','screenshot':'invalid'})
        self.assertEqual(code,400);answer.assert_not_called()

if __name__=='__main__':unittest.main()
