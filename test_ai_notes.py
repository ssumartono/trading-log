import json,unittest
from unittest.mock import patch
from ai_notes import draft_note,configure_key,server_key
class FakeResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Draf evaluasi'}]}]}).encode()
class AITests(unittest.TestCase):
    @patch('ai_notes.urlopen')
    def test_compatible_platform_uses_saved_url_and_model(self,send):
        import ai_notes
        oldconfig=dict(ai_notes.SERVER_CONFIG);oldkey=ai_notes.SERVER_KEY
        class ChatResponse(FakeResponse):
            def read(self):return json.dumps({'choices':[{'message':{'content':'Memo draf'},'finish_reason':'stop'}]}).encode()
        send.return_value=ChatResponse()
        try:
            ai_notes.configure_ai({'platform':'OpenAI Compatible','url':'https://example.com/v1/chat/completions','model':'my-model','apiKey':'private'})
            result=draft_note({'kind':'Memo','prompt':'Ringkas'},{})
            request=send.call_args.args[0];self.assertEqual(request.full_url,'https://example.com/v1/chat/completions');payload=json.loads(request.data);self.assertEqual(payload['model'],'my-model');self.assertIn('messages',payload);self.assertEqual(result['draft'],'Memo draf')
            self.assertNotIn('private',json.dumps(ai_notes.key_status()))
        finally:ai_notes.SERVER_CONFIG=oldconfig;ai_notes.SERVER_KEY=oldkey
    def test_server_key_status_never_returns_secret(self):
        import ai_notes
        old=ai_notes.SERVER_KEY
        try:
            status=configure_key('test-private-key')
            self.assertTrue(status['configured']);self.assertNotIn('test-private-key',json.dumps(status));self.assertEqual(server_key(),'test-private-key')
            self.assertFalse(configure_key('')['configured'])
        finally:ai_notes.SERVER_KEY=old
    @patch('ai_notes.urlopen',return_value=FakeResponse())
    def test_summary_and_draft_no_account_identity(self,send):
        state={'brokers':[{'id':1,'name':'SecretAccount'}],'records':[{'broker':'SecretAccount','date':'2026-10-15','profit':5,'symbol':'XAUUSD'}]}
        result=draft_note({'apiKey':'test-key','kind':'Lesson Learned','prompt':'Evaluasi','includeLogs':True,'brokerId':1,'eventDate':'2026-10-15T09:00'},state)
        self.assertEqual(result['draft'],'Draf evaluasi');payload=json.loads(send.call_args.args[0].data);self.assertFalse(payload['store']);self.assertNotIn('SecretAccount',payload['input']);self.assertNotIn('test-key',payload['input']);self.assertEqual(json.loads(payload['input'])['ringkasanLog']['netProfit'],5)
    @patch.dict('os.environ',{'OPENAI_API_KEY':''})
    def test_no_key_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'API key'):draft_note({'kind':'Memo','prompt':'Test'},{})
if __name__=='__main__':unittest.main()
