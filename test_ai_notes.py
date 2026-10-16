import json,unittest
from unittest.mock import patch
from ai_notes import draft_note,configure_key,server_key
class FakeResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Draf evaluasi'}]}]}).encode()
class AITests(unittest.TestCase):
    def setUp(self):
        import tempfile,ai_notes
        from pathlib import Path
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.storage=patch.object(ai_notes,'SETTINGS_FILE',Path(self.temp.name)/'settings.dpapi');self.storage.start();self.addCleanup(self.storage.stop)
        for name,value in [('SERVER_KEY',None),('STORAGE_ERROR',None),('SERVER_CONFIG',{'platform':'OpenAI','url':'https://api.openai.com/v1/responses','model':'test-model'})]:
            setting=patch.object(ai_notes,name,value);setting.start();self.addCleanup(setting.stop)
    def test_encrypted_persistence_reload_and_delete(self):
        import ai_notes
        ai_notes.configure_ai({'platform':'OpenAI Compatible','url':'https://example.com/v1/chat/completions','model':'persisted-model','apiKey':'private-persistent-secret'})
        saved=ai_notes.SETTINGS_FILE.read_bytes();self.assertNotIn(b'private-persistent-secret',saved)
        ai_notes.SERVER_KEY=None;ai_notes.SERVER_CONFIG={};ai_notes.load_saved_settings()
        self.assertEqual(server_key(),'private-persistent-secret');self.assertEqual(ai_notes.SERVER_CONFIG['model'],'persisted-model')
        ai_notes.configure_ai({'deleteKey':True});ai_notes.SERVER_KEY=None;ai_notes.load_saved_settings()
        self.assertEqual(server_key(),'');self.assertEqual(ai_notes.SERVER_CONFIG['model'],'persisted-model')
    def test_storage_failure_does_not_change_active_key(self):
        import ai_notes
        ai_notes.SERVER_KEY='previous'
        with patch('ai_secret_store.write',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):configure_key('replacement')
        self.assertEqual(server_key(),'previous')
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
        state={'brokers':[{'id':1,'name':'SecretAccount'}],'records':[{'id':1,'time':'09:00','broker':'SecretAccount','date':'2026-10-15','profit':5,'symbol':'XAUUSD'}]}
        result=draft_note({'apiKey':'test-key','kind':'Lesson Learned','prompt':'Evaluasi','includeLogs':True,'brokerId':1,'eventDate':'2026-10-15T09:00'},state)
        self.assertEqual(result['draft'],'Draf evaluasi');payload=json.loads(send.call_args.args[0].data);self.assertFalse(payload['store']);self.assertNotIn('SecretAccount',payload['input']);self.assertNotIn('test-key',payload['input']);self.assertEqual(json.loads(payload['input'])['ringkasanLog']['netProfit'],5)
    @patch.dict('os.environ',{'OPENAI_API_KEY':''})
    def test_no_key_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'API key'):draft_note({'kind':'Memo','prompt':'Test'},{})
if __name__=='__main__':unittest.main()
