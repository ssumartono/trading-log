import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import server
import user_auth
import account_access


class OwnershipHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True)
        self.patch=patch.object(server,'DB',Path(self.temp.name)/'accounts.sqlite3');self.patch.start()
        with server.connect() as db:
            self.admin=user_auth.create_user(db,{'username':'admin','displayName':'Admin','password':'Test-password123'},True)
            self.trader=user_auth.create_user(db,{'username':'trader','displayName':'Trader','password':'Test-password123','role':'Trader'})
            self.empty=user_auth.create_user(db,{'username':'empty','displayName':'Empty','password':'Test-password123','role':'Trader'})
            self.cookies={u['id']:user_auth.cookie(user_auth.session(db,u['id'])) for u in (self.admin,self.trader,self.empty)}
            self.state={'brokers':[{'id':1,'name':'Admin Account','accountKey':'A:1','initial':100}, {'id':2,'name':'Trader Account','accountKey':'B:2','initial':200}], 'records':[{'id':1,'broker':'Admin Account','note':'private admin','profit':1},{'id':2,'broker':'Trader Account','note':'private trader','profit':2}], 'funds':[{'id':1,'brokerId':1,'amount':5},{'id':2,'brokerId':2,'amount':6}], 'settings':{'brokerId':'1'},'syncRevision':0}
            server.save(db,self.state)
            account_access.schema(db)
            db.execute('UPDATE broker_owners SET user_id=? WHERE broker_id=?',(self.trader['id'],'2'))
            db.execute('INSERT INTO daily_notes(data) VALUES(?)',(json.dumps({'title':'secret','brokerId':1}),))
        self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join();self.patch.stop();self.temp.cleanup()

    def call(self,path,data=None,user=None):
        req=Request('http://127.0.0.1:'+str(self.http.server_port)+path,headers={'Origin':'http://127.0.0.1:3000','Content-Type':'application/json','Cookie':self.cookies[(user or self.trader)['id']]},data=json.dumps(data).encode() if data is not None else None)
        try:
            with urlopen(req,timeout=10) as response:return response.status,json.load(response)
        except HTTPError as error:
            try:return error.code,json.load(error)
            finally:error.close()

    def test_reads_and_account_endpoints(self):
        for user,expected in ((self.admin,[1]),(self.trader,[2]),(self.empty,[])):
            code,state=self.call('/api/state',user=user);self.assertEqual(code,200)
            self.assertEqual([b['id'] for b in state['brokers']],expected)
            self.assertEqual([r['id'] for r in state['records']],expected)
            self.assertEqual([r['id'] for r in state['funds']],expected)
        self.assertEqual(self.call('/api/notes')[1],[])
        self.assertEqual(self.call('/api/trader/history',{'brokerId':1})[0],400)
        self.assertEqual(self.call('/api/logs/context',{'brokerId':1})[0],400)
        self.assertEqual(self.call('/api/attachments',{'kind':'log','target':'1'})[0],400)
        self.assertEqual(self.call('/api/attachments',{'kind':'note','target':'1'})[0],403)
        self.assertEqual(self.call('/api/sync',{},self.empty)[0],403)
        self.assertEqual(self.call('/api/ai/settings')[0],403)

    def test_save_preserves_other_user_and_rejects_tampering(self):
        _,state=self.call('/api/state');updated=copy.deepcopy(state)
        updated['records'][0]['note']='my edit';updated['_base']=state
        self.assertEqual(self.call('/api/state',updated)[0],200)
        with server.connect() as db:
            full=server.load(db)
            self.assertEqual(next(r for r in full['records'] if r['id']==1)['note'],'private admin')
            self.assertEqual(next(r for r in full['records'] if r['id']==2)['note'],'my edit')
            self.assertEqual(len(full['brokers']),2)
        forged=copy.deepcopy(updated);forged['brokers'].append(self.state['brokers'][0])
        self.assertEqual(self.call('/api/state',forged)[0],403)
        forged=copy.deepcopy(updated);forged['settings']['brokerId']='1'
        self.assertEqual(self.call('/api/state',forged)[0],403)
        forged=copy.deepcopy(updated);forged['records'][0]['sourceKey']='A:1:secret'
        self.assertEqual(self.call('/api/state',forged)[0],403)
        forged=copy.deepcopy(updated);forged['records'][0]['id']=1
        self.assertEqual(self.call('/api/state',forged)[0],400)

    def test_delta_save_and_sync_select_only_owned_account(self):
        _,state=self.call('/api/state')
        payload={'records':[{**state['records'][0],'note':'delta edit'}],'funds':[],'brokers':[],'settings':state['settings'],'_base':{'records':state['records'],'funds':[],'brokers':[],'settings':state['settings']}}
        self.assertEqual(self.call('/api/state',payload)[0],200)
        self.assertEqual(self.call('/api/state')[1]['records'][0]['note'],'delta edit')
        with patch.object(server,'synchronize',return_value={'message':'ok'}) as sync:
            self.assertEqual(self.call('/api/sync',{'brokerId':1})[0],200)
            sync.assert_called_once_with(False,broker_id='2')

    def test_backup_restore_preserves_ownership(self):
        import backup_restore
        with server.connect() as db:
            original=dict(db.execute('SELECT broker_id,user_id FROM broker_owners'))
        snapshot=backup_restore.create(server.DB)
        self.assertEqual(self.call('/api/admin/account-owner',{'brokerId':2,'userId':self.admin['id']},self.admin)[0],200)
        backup_restore.restore(server.DB,server.connect,dict(name=snapshot['name'],sha256=snapshot['sha256'],confirmation='RESTORE'))
        with server.connect() as db:
            self.assertEqual(dict(db.execute('SELECT broker_id,user_id FROM broker_owners')),original)

    def test_transfer_revokes_access_and_preferences_are_private(self):
        self.assertEqual(self.call('/api/admin/account-owner',{'brokerId':1,'userId':self.trader['id']})[0],403)
        self.assertEqual(self.call('/api/preferences',{'timezone':'UTC','brokerOffsets':{'1':180}})[0],403)
        self.assertEqual(self.call('/api/preferences',{'timezone':'UTC','brokerOffsets':{'2':180}})[0],200)
        self.assertEqual(self.call('/api/preferences',user=self.admin)[1]['timezone'],'WIB')
        payload={'brokerId':2,'userId':self.admin['id']}
        self.assertEqual(self.call('/api/admin/account-owner',payload,self.admin)[0],200)
        self.assertEqual(self.call('/api/state')[1]['brokers'],[])
        self.assertEqual(self.call('/api/trader/history',{'brokerId':2})[0],400)


if __name__=='__main__':unittest.main()
