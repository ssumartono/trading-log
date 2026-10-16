import copy, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import server

class BrokerRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True)
        self.dbpatch=patch.object(server,'DB',Path(self.temp.name)/'test.sqlite3');self.dbpatch.start()
        self.config={'login':'123','server':'Test-Live','path':'terminal.exe','start':'2020-01-01','enabled':True,'auto':True,'interval':'60','importTrades':True,'importFunds':True}
        self.mt5=SimpleNamespace(initialize=lambda *a,**k:True,account_info=lambda:SimpleNamespace(login=123,server='Test-Live',currency='USD',balance=100),terminal_info=lambda:SimpleNamespace(connected=True),shutdown=lambda:None)
        self.modulepatch=patch.dict('sys.modules',{'MetaTrader5':self.mt5});self.modulepatch.start()
        with server.connect() as db: server.save(db,{'brokers':[],'records':[],'funds':[],'settings':copy.deepcopy(self.config)})
    def tearDown(self):
        import gc
        self.modulepatch.stop();self.dbpatch.stop();gc.collect();self.temp.cleanup()
    def test_verified_registration_keeps_per_account_config(self):
        result=server.register_broker(self.config)
        with server.connect() as db: state=server.load(db)
        self.assertEqual(len(state['brokers']),1)
        self.assertEqual(state['brokers'][0]['accountKey'],'Test-Live:123')
        self.assertEqual(state['brokers'][0]['integration']['path'],'terminal.exe')
        self.assertFalse(state['brokers'][0]['integration']['auto'])
        self.assertEqual(str(result['brokerId']),state['settings']['brokerId'])
        with self.assertRaisesRegex(ValueError,'sudah terdaftar'): server.register_broker(self.config)
    def test_registration_assigns_authenticated_owner(self):
        import user_auth,account_access
        with server.connect() as db:
            user=user_auth.create_user(db,{'username':'owner','displayName':'Owner','password':'Test-password123'},True)
        result=server.register_broker(self.config,user)
        with server.connect() as db:
            self.assertEqual(account_access.ids(db,user),{str(result['brokerId'])})
            self.assertEqual(account_access.view(db,server.load(db),user)['settings']['brokerId'],str(result['brokerId']))

    def test_wrong_terminal_account_does_not_create_broker(self):
        self.mt5.account_info=lambda:SimpleNamespace(login=999,server='Test-Live',currency='USD',balance=100)
        with self.assertRaisesRegex(ValueError,'Login manual ke'): server.register_broker(self.config)
        with server.connect() as db: self.assertEqual(server.load(db)['brokers'],[])

if __name__=='__main__': unittest.main()
