import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import server,audit_trail,backup_restore
from user_auth import create_user,session

class BackupAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True);self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'test.sqlite3';self.dbpatch=patch.object(server,'DB',self.database);self.dbpatch.start();self.addCleanup(self.dbpatch.stop)
        self.actor=patch.object(audit_trail.context,'actor',{'id':1,'username':'tester'},create=True);self.actor.start();self.addCleanup(self.actor.stop)
        with server.connect() as db:
            self.user=create_user(db,{'username':'admin','displayName':'Admin','password':'Test-password123'},first=True)
            self.state={'records':[{'id':1,'date':'2026-10-16','time':'10:00','profit':1,'note':'old'}],'brokers':[{'id':1,'name':'Test','integration':{'enabled':True,'auto':True}}],'funds':[],'settings':{'enabled':True,'auto':True},'syncRevision':1}
            server.save(db,self.state);session(db,self.user['id'])

    def test_snapshot_restore_retains_audit_sessions_cleared_and_sync_paused(self):
        snapshot=backup_restore.create(self.database)
        with backup_restore.open_database(backup_restore.path_for(self.database,snapshot['name'])) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM app_sessions').fetchone()[0],0)
        with server.connect() as db:
            changed=copy.deepcopy(self.state);changed['records'][0]['note']='new';server.save(db,changed)
            ids={row[0] for row in db.execute('SELECT id FROM audit_events')}
        result=backup_restore.restore(self.database,server.connect,{'name':snapshot['name'],'sha256':snapshot['sha256'],'confirmation':'RESTORE'})
        self.assertTrue(result['restored']);self.assertTrue(backup_restore.path_for(self.database,result['safetyBackup']).exists())
        with server.connect() as db:
            state=server.load(db);self.assertEqual(state['records'][0]['note'],'old');self.assertFalse(state['settings']['auto']);self.assertFalse(state['brokers'][0]['integration']['enabled'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_sessions').fetchone()[0],0)
            self.assertTrue(ids.issubset({r[0] for r in db.execute('SELECT id FROM audit_events')}))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_events WHERE action='restore'").fetchone()[0],1)

    def test_validation_confirmation_hash_and_traversal(self):
        snapshot=backup_restore.create(self.database)
        with self.assertRaises(ValueError):backup_restore.upload(self.database,b'not sqlite')
        with self.assertRaises(ValueError):backup_restore.path_for(self.database,'../test.sqlite3')
        for data in [{'confirmation':''},{'confirmation':'RESTORE','sha256':'incorrect'}]:
            with self.assertRaises(ValueError):backup_restore.restore(self.database,server.connect,dict(name=snapshot['name'],**data))
        with server.connect() as db:self.assertEqual(server.load(db),self.state)
        content=backup_restore.path_for(self.database,snapshot['name']).read_bytes()
        uploaded=backup_restore.upload(self.database,content);self.assertTrue(uploaded['valid']);self.assertEqual(uploaded['sha256'],snapshot['sha256'])

    def test_restore_failure_rolls_back_all_business_data(self):
        snapshot=backup_restore.create(self.database)
        with server.connect() as db:
            state=copy.deepcopy(self.state);state['records'][0]['note']='keep after failure';server.save(db,state)
        with patch('audit_trail.event',side_effect=ValueError('simulated failure')):
            with self.assertRaises(ValueError):backup_restore.restore(self.database,server.connect,dict(name=snapshot['name'],sha256=snapshot['sha256'],confirmation='RESTORE'))
        with server.connect() as db:self.assertEqual(server.load(db)['records'][0]['note'],'keep after failure')

    def test_audit_redacts_secrets_records_diff_and_is_append_only(self):
        with server.connect() as db:
            state=copy.deepcopy(self.state);state['records'][0]['note']='edited';server.save(db,state)
            audit_trail.event(db,'test','config',1,{'apiKey':'private-key','nested':{'password':'private-password'}},{'token_hash':'private-token'})
            data=audit_trail.listing(db,{'actor':'tester','entity':'records'})
            self.assertEqual(data['rows'][0]['actor'],'tester');self.assertEqual(data['rows'][0]['before']['note'],'old');self.assertEqual(data['rows'][0]['after']['note'],'edited')
            stored=' '.join(str(r) for r in db.execute('SELECT * FROM audit_events'))
            for value in ('private-key','private-password','private-token','Test-password123'):self.assertNotIn(value,stored)
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE audit_events SET actor='other'")
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM audit_events')

if __name__=='__main__':unittest.main()
