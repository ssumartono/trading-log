"""Regression checks for interactive requests during a slow terminal fetch."""
import copy
from contextlib import contextmanager
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import server
import test_account_access as fixtures


class ResponsivenessTests(unittest.TestCase):
    setUp=fixtures.OwnershipHTTPTests.setUp
    tearDown=fixtures.OwnershipHTTPTests.tearDown
    call=fixtures.OwnershipHTTPTests.call

    @contextmanager
    def slow_terminal(self):
        config={'brokerId':'2','login':'2','server':'B','path':'terminal.exe','start':'2020-01-01','enabled':True,'auto':False,'importTrades':True,'importFunds':True}
        with server.connect() as db:
            state=server.load(db);state['brokers'][1]['integration']=config
            for fund in state['funds']:fund['type']='Deposit'
            server.save(db,state)
        entered=threading.Event();release=threading.Event();result=[]
        def history(*args):
            entered.set()
            if not release.wait(10):raise TimeoutError('Test did not release terminal')
            return ()
        terminal=SimpleNamespace(initialize=lambda *a,**k:True,shutdown=lambda:None,
            account_info=lambda:SimpleNamespace(login=2,server='B',currency='USD',balance=202,equity=202),
            terminal_info=lambda:SimpleNamespace(connected=True),history_deals_get=history,
            DEAL_TYPE_BUY=0,DEAL_TYPE_SELL=1,DEAL_TYPE_BALANCE=2)
        with patch.dict('sys.modules',{'MetaTrader5':terminal}):
            worker=threading.Thread(target=lambda:result.append(self.call('/api/sync',{})))
            worker.start()
            try:
                self.assertTrue(entered.wait(3),'Sync did not reach terminal fetch')
                yield result
            finally:
                release.set();worker.join(timeout=5)
                self.assertFalse(worker.is_alive(),'Sync did not finish')

    def test_reads_and_edits_continue_and_sync_keeps_concurrent_edit(self):
        with self.slow_terminal() as result:
            start=time.perf_counter()
            code,state=self.call('/api/state');self.assertEqual(code,200)
            self.assertEqual(self.call('/api/sync/status')[0],200)
            edited=copy.deepcopy(state);edited['records'][0]['note']='Edited while MT5 waits';edited['_base']=state
            self.assertEqual(self.call('/api/state',edited)[0],200)
            self.assertLess(time.perf_counter()-start,1.5)
        self.assertEqual(result[0][0],200,result)
        self.assertEqual(self.call('/api/state')[1]['records'][0]['note'],'Edited while MT5 waits')

    def test_changed_configuration_discards_inflight_import(self):
        with self.slow_terminal() as result:
            _,state=self.call('/api/state');edited=copy.deepcopy(state)
            edited['brokers'][0]['integration']['enabled']=False;edited['_base']=state
            self.assertEqual(self.call('/api/state',edited)[0],200)
        self.assertEqual(result[0][0],400,result)
        self.assertIn('Pengaturan akun berubah',result[0][1]['error'])

    def test_transferred_account_discards_inflight_import(self):
        with self.slow_terminal() as result:
            self.assertEqual(self.call('/api/admin/account-owner',{'brokerId':2,'userId':self.admin['id']},self.admin)[0],200)
        self.assertEqual(result[0][0],403,result)
        self.assertEqual(self.call('/api/state')[1]['brokers'],[])

    def test_connections_do_not_repeat_schema_or_start_write_transactions(self):
        with patch.object(server,'initialize_schema',side_effect=AssertionError('Repeated schema initialization')):
            with server.connect() as db:
                self.assertFalse(db.in_transaction)
                self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0],'wal')

    def test_restore_discards_inflight_import_without_recreating_sync_status(self):
        with self.slow_terminal() as result:
            code,snapshot=self.call('/api/admin/backup/create',{},self.admin)
            self.assertEqual(code,200)
            code,_=self.call('/api/admin/backup/restore',dict(name=snapshot['name'],sha256=snapshot['sha256'],confirmation='RESTORE'),self.admin)
            self.assertEqual(code,200)
        self.assertEqual(result[0][0],400,result)
        self.assertIn('restore',result[0][1]['error'])
        with server.readonly() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sync_status').fetchone()[0],0)


if __name__=='__main__':unittest.main()
