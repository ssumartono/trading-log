import sqlite3,unittest
import app_preferences as prefs
from user_auth import endpoint_permission
class PreferencesTests(unittest.TestCase):
    def test_defaults_save_and_validation(self):
        with sqlite3.connect(':memory:') as db:
            prefs.schema(db);self.assertEqual(prefs.read(db)['timezone'],'WIB')
            prefs.write(db,{'timezone':'BROKER','brokerOffsets':{'1':'180','2':'120'}})
            prefs.schema(db);self.assertEqual(prefs.read(db)['brokerOffsets']['1'],180)
            with self.assertRaises(ValueError):prefs.write(db,{'timezone':'BAD'})
            with self.assertRaises(ValueError):prefs.write(db,{'timezone':'UTC','brokerOffsets':{'1':900}})
            with self.assertRaises(ValueError):prefs.write(db,{'timezone':'UTC','brokerOffsets':{'1':1.5}})
            self.assertEqual(prefs.read(db)['timezone'],'BROKER')
            self.assertEqual(endpoint_permission('/api/preferences','POST'),'broker.manage')
if __name__=='__main__':unittest.main()
