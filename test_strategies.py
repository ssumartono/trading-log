import sqlite3,unittest
import strategies
from user_auth import endpoint_permission

class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close);strategies.schema(self.db);self.state={'records':[]}
    def test_seed_is_once_and_deletion_stays_deleted(self):
        self.assertEqual(len(strategies.listing(self.db,self.state)),4)
        row=strategies.listing(self.db,self.state)[0];strategies.write(self.db,dict(row,delete=True),self.state)
        strategies.schema(self.db);self.assertEqual(len(strategies.listing(self.db,self.state)),3)
    def test_crud_conflict_and_validation(self):
        data={'name':'Custom','rules':'Rule','whenApplied':'Range','status':'Aktif','appliedAt':'2026-10-16T10:30'}
        row=strategies.write(self.db,data,self.state)
        with self.assertRaisesRegex(ValueError,'sudah ada'):strategies.write(self.db,data,self.state)
        updated=strategies.write(self.db,dict(row,rules='Updated'),self.state);self.assertEqual(updated['revision'],2)
        with self.assertRaisesRegex(ValueError,'berubah'):strategies.write(self.db,row,self.state)
        with self.assertRaises(ValueError):strategies.write(self.db,dict(updated,source='javascript:alert(1)'),self.state)
        strategies.write(self.db,dict(updated,delete=True),self.state)
        self.assertFalse(any(r['name']=='Custom' for r in strategies.listing(self.db,self.state)))
    def test_log_usage_protects_name_delete_but_allows_deactivation(self):
        row=strategies.listing(self.db,self.state)[0]
        self.state['records']=[{'strategy':row['name'],'date':'2026-10-16','time':'11:00'},{'strategy':row['name'],'date':'2026-10-15','time':'10:00'}]
        entry=next(r for r in strategies.listing(self.db,self.state) if r['id']==row['id'])
        self.assertEqual(entry['usageCount'],2);self.assertEqual(entry['firstApplied'],'2026-10-15T10:00');self.assertEqual(entry['lastApplied'],'2026-10-16T11:00')
        with self.assertRaises(ValueError):strategies.write(self.db,dict(entry,delete=True),self.state)
        with self.assertRaises(ValueError):strategies.write(self.db,dict(entry,name='Renamed'),self.state)
        saved=strategies.write(self.db,dict(entry,status='Nonaktif'),self.state);self.assertEqual(saved['status'],'Nonaktif')
        self.assertEqual(endpoint_permission('/api/strategies','GET'),'data.view');self.assertEqual(endpoint_permission('/api/strategies','POST'),'logs.edit')

if __name__=='__main__':unittest.main()
