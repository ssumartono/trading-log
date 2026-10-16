import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import server
from sync_health import checkpoint,reconcile,update_status
from time_rules import wib_fields,utc_timestamp,validate_time_config

class AuditFixTests(unittest.TestCase):
    def test_repeated_import_keeps_checkpoint_opening_and_manual_notes(self):
        from collections import namedtuple
        from types import SimpleNamespace
        Deal=namedtuple('Deal','ticket time type profit commission swap fee entry price symbol volume position_id comment')
        deals=[Deal(1,1700000000,2,100,0,0,0,0,0,'',0,0,'Deposit'),Deal(2,1700000060,1,10,0,0,0,1,2000,'XAUUSD',.01,5,'')]
        config={'login':'1','server':'Test','path':'terminal','start':'2020-01-01','enabled':True,'importTrades':True,'importFunds':True}
        account=SimpleNamespace(login=1,server='Test',currency='USD',balance=110,equity=110)
        fake=SimpleNamespace(initialize=lambda *a,**k:True,shutdown=lambda:None,account_info=lambda:account,terminal_info=lambda:SimpleNamespace(connected=True),history_deals_get=lambda *a:deals,DEAL_TYPE_BUY=0,DEAL_TYPE_SELL=1,DEAL_TYPE_BALANCE=2)
        with tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True) as temp,patch.object(server,'DB',Path(temp)/'import.sqlite3'),patch.dict('sys.modules',{'MetaTrader5':fake}):
            with server.connect() as db:server.save(db,{'brokers':[{'id':1,'name':'Test','accountKey':'Test:1','initial':110,'integration':config}],'records':[],'funds':[],'settings':config})
            first=server.synchronize(broker_id=1)
            self.assertEqual(first['reconciliation']['status'],'baseline_created')
            with server.connect() as db:
                state=server.load(db);self.assertEqual(state['brokers'][0]['initial'],0)
                state['records'][0]['note']='Pelajaran manual';server.save(db,state)
                baseline=db.execute('SELECT data FROM balance_checkpoints').fetchone()[0]
            account.balance=115;account.equity=115  # Missing deal must remain visible.
            second=server.synchronize(broker_id=1)
            self.assertEqual(second['new'],0);self.assertEqual(second['reconciliation']['balanceDifference'],5)
            with server.connect() as db:
                state=server.load(db);self.assertEqual(len(state['records']),1);self.assertEqual(state['records'][0]['note'],'Pelajaran manual')
                self.assertEqual(state['brokers'][0]['initial'],0)
                self.assertEqual(db.execute('SELECT data FROM balance_checkpoints').fetchone()[0],baseline)

    def test_wib_midnight_and_explicit_server_offset(self):
        raw=1792087200  # 2026-10-15 18:00 UTC
        from datetime import datetime,timezone
        raw=int(datetime(2026,10,15,18,tzinfo=timezone.utc).timestamp())
        self.assertEqual(wib_fields(raw,{})['date'],'2026-10-16')
        self.assertEqual(wib_fields(raw,{})['time'],'01:00')
        self.assertFalse(wib_fields(raw,{})['timeConfirmed'])
        config={'timestampMode':'server','serverUtcOffsetMinutes':180,'timeConfirmed':True}
        self.assertEqual(utc_timestamp(raw+10800,config),raw)
        self.assertEqual(wib_fields(raw+10800,config)['time'],'01:00')
        with self.assertRaises(ValueError):validate_time_config({'serverUtcOffsetMinutes':900})

    def test_checkpoint_does_not_absorb_missing_balance(self):
        raw=[{'ticket':1,'type':0,'time':10,'profit':0}]
        baseline=checkpoint(100,raw,'2026-10-15','previous_mt5_snapshot');before=copy.deepcopy(baseline)
        raw.append({'ticket':2,'type':1,'time':20,'profit':10})
        broker={'id':1,'name':'Test','accountKey':'Test:1','initial':100}
        state={'records':[{'sourceKey':'Test:1:1','broker':'Test','profit':0},{'sourceKey':'Test:1:2','broker':'Test','profit':10}],'funds':[]}
        result=reconcile(baseline,raw,broker,state,120)
        self.assertEqual(result['status'],'needs_review');self.assertEqual(result['balanceDifference'],10)
        self.assertEqual(baseline,before);self.assertEqual(broker['initial'],100)
        state['records'].pop();result=reconcile(baseline,raw,broker,state,110)
        self.assertEqual(result['missingTradeCount'],1);self.assertEqual(result['projectedDifference'],10)

    def test_backfill_requires_review_even_if_balance_matches(self):
        baseline=checkpoint(100,[{'ticket':1,'type':0,'time':20,'profit':0}],'stamp','previous')
        raw=[{'ticket':1,'type':0,'time':20,'profit':0},{'ticket':2,'type':2,'time':10,'profit':5}]
        broker={'id':1,'name':'Test','accountKey':'Test:1','initial':100}
        state={'records':[{'sourceKey':'Test:1:1','broker':'Test','profit':0}],'funds':[{'sourceKey':'Test:1:2','brokerId':1,'type':'Deposit','amount':5}]}
        result=reconcile(baseline,raw,broker,state,105)
        self.assertEqual(result['historicalBackfillCount'],1);self.assertEqual(result['status'],'needs_review')

    def test_latest_failure_replaces_success_status_not_history(self):
        with tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True) as temp,patch.object(server,'DB',Path(temp)/'sync-test.sqlite3'):
            with server.connect() as db:server.save(db,{'brokers':[{'id':1,'name':'Test'}],'settings':{}})
            result={'message':'OK','time':'2026-10-16T00:00:00Z','deals':2,'new':1,'updated':0,'latestTicket':'2','reconciliation':{'status':'matched'}}
            with patch.object(server,'_synchronize',return_value=result):server.synchronize(broker_id=1)
            with patch.object(server,'_synchronize',side_effect=ValueError('Terminal akun berbeda')):
                with self.assertRaises(ValueError):server.synchronize(broker_id=1)
            with server.readonly() as db:status=json.loads(db.execute('SELECT data FROM sync_status').fetchone()[0])
            self.assertEqual(status['status'],'failed');self.assertEqual(status['error'],'Terminal akun berbeda')
            self.assertEqual(status['lastSuccess'],result['time']);self.assertEqual(status['latestTicket'],'2')

if __name__=='__main__':unittest.main()
