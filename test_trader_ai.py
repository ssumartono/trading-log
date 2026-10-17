import json,sqlite3,unittest
from types import SimpleNamespace
from unittest.mock import patch
import ai_notes
from trader_ai import market_context,answer_trader,chat_history,validate_chart_image
class TraderTests(unittest.TestCase):
    def test_reject_invalid_screenshot(self):
        for value in ('https://example.com/image.png','data:image/png;base64,invalid',123):
            with self.subTest(value=value),self.assertRaises(ValueError):validate_chart_image(value)
    @patch('trader_ai.urlopen')
    def test_screenshot_is_multimodal_on_both_platforms(self,send):
        image='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII='
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self):return json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'Image analysis'}]}],'choices':[{'message':{'content':'Image analysis'}}]}).encode()
        send.return_value=Response()
        for platform in ('OpenAI','OpenAI Compatible'):
            with patch.object(ai_notes,'SERVER_KEY','test'),patch.object(ai_notes,'SERVER_CONFIG',{'platform':platform,'url':'https://example.com','model':'test'}):
                messages=[{'role':'user','content':'Baca gambar'}]
                answer_trader(messages,None,None,image)
                payload=json.loads(send.call_args.args[0].data)
                parts=payload['messages' if platform=='OpenAI Compatible' else 'input'][-1]['content']
                self.assertEqual(parts[1]['type'],'image_url' if platform=='OpenAI Compatible' else 'input_image')
                self.assertEqual(messages[0]['content'],'Baca gambar')
    def test_all_chart_timeframes_reach_account_validation(self):
        frames=('M1','M5','M15','M30','H1','H4','D1')
        fake=SimpleNamespace(**{'TIMEFRAME_'+name:i for i,name in enumerate(frames)},initialize=lambda *a,**k:True,account_info=lambda:SimpleNamespace(login=2,server='Other'),terminal_info=lambda:SimpleNamespace(connected=True),shutdown=lambda:None)
        state={'brokers':[{'id':1,'integration':{'path':'terminal','login':1,'server':'Expected'}}]}
        with patch.dict('sys.modules',{'MetaTrader5':fake}):
            for frame in frames:
                with self.subTest(frame=frame),self.assertRaisesRegex(ValueError,'berbeda'):
                    market_context(state,{'brokerId':1,'symbol':'EURUSD','timeframe':frame})
            with self.assertRaisesRegex(ValueError,'Timeframe tidak valid'):
                market_context(state,{'brokerId':1,'symbol':'EURUSD','timeframe':'INVALID'})
    def test_reject_other_account(self):
        fake=SimpleNamespace(TIMEFRAME_M5=5,TIMEFRAME_M15=15,TIMEFRAME_H1=60,TIMEFRAME_H4=240,initialize=lambda *a,**k:True,account_info=lambda:SimpleNamespace(login=2,server='Other'),terminal_info=lambda:SimpleNamespace(connected=True),shutdown=lambda:None)
        with patch.dict('sys.modules',{'MetaTrader5':fake}):
            with self.assertRaisesRegex(ValueError,'berbeda'):market_context({'brokers':[{'id':1,'integration':{'path':'terminal','login':1,'server':'Expected'}}]},{'brokerId':1,'symbol':'XAUUSD'})
    def test_chat_history_is_per_account(self):
        db=sqlite3.connect(':memory:');db.execute('CREATE TABLE trader_messages(id INTEGER PRIMARY KEY,broker_id TEXT,role TEXT,content TEXT,created_at TEXT,context TEXT)');db.executemany('INSERT INTO trader_messages VALUES(?,?,?,?,?,?)',[(1,'1','user','A','now',None),(2,'2','user','B','now',None)]);self.assertEqual([m['content'] for m in chat_history(db,1)],['A']);db.close()
    @patch('trader_ai.urlopen')
    def test_model_payload_and_context(self,send):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self):return json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'Skenario perlu konfirmasi.'}]}]}).encode()
        send.return_value=Response()
        with patch.object(ai_notes,'SERVER_KEY','test'),patch.object(ai_notes,'SERVER_CONFIG',{'platform':'OpenAI','url':'https://api.openai.com/v1/responses','model':'test-model'}):
            text=answer_trader([{'role':'user','content':'Evaluasi'}],{'symbol':'XAUUSD','bid':100})
            payload=json.loads(send.call_args.args[0].data);self.assertFalse(payload['store']);self.assertIn('XAUUSD',payload['instructions']);self.assertEqual(text,'Skenario perlu konfirmasi.')
if __name__=='__main__':unittest.main()
