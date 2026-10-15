import sqlite3,unittest,time
from user_auth import schema,create_user,login,session,cookie,current_user,require,update_user,save_role,public_user
class AuthTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');schema(self.db)
        self.admin=create_user(self.db,{'username':'admin','displayName':'Admin','password':'Safe-password123'},first=True)
    def tearDown(self):self.db.close()
    def viewer(self):return create_user(self.db,{'username':'viewer','displayName':'Viewer','role':'Viewer','password':'Safe-password123'})
    def test_setup_once_hashed_password_and_session(self):
        with self.assertRaises(ValueError):create_user(self.db,{'username':'admin2','displayName':'Admin2','password':'Safe-password123'},first=True)
        stored=self.db.execute('SELECT password_hash FROM app_users').fetchone()[0];self.assertNotIn('Safe-password123',stored)
        self.assertIsNone(login(self.db,{'username':'admin','password':'wrong'}))
        self.assertEqual(login(self.db,{'username':'ADMIN','password':'Safe-password123'})['id'],self.admin['id'])
        token=session(self.db,self.admin['id']);self.assertEqual(current_user(self.db,cookie(token))['id'],self.admin['id'])
        self.assertIn('HttpOnly',cookie(token));self.assertIn('SameSite=Strict',cookie(token))
        self.db.execute('UPDATE app_sessions SET expires=0');self.assertIsNone(current_user(self.db,cookie(token)))
    def test_permissions_disable_and_last_admin(self):
        viewer=self.viewer()
        with self.assertRaises(PermissionError):require(viewer,'logs.edit')
        token=session(self.db,viewer['id']);update_user(self.db,self.admin,{'id':viewer['id'],'active':False})
        self.assertIsNone(current_user(self.db,cookie(token)))
        with self.assertRaises(ValueError):update_user(self.db,self.admin,{'id':self.admin['id'],'active':False})
        with self.assertRaises(ValueError):save_role(self.db,{'name':'Administrator','permissions':[]})
    def test_profile_cannot_escalate_and_password_revokes_session(self):
        viewer=self.viewer();token=session(self.db,viewer['id'])
        changed=update_user(self.db,viewer,{'displayName':'Updated','role':'Administrator'},profile=True);self.assertEqual(changed['role'],'Viewer')
        with self.assertRaises(ValueError):update_user(self.db,viewer,{'password':'New-password123','currentPassword':'wrong'},profile=True)
        update_user(self.db,viewer,{'password':'New-password123','currentPassword':'Safe-password123'},profile=True)
        self.assertIsNone(current_user(self.db,cookie(token)))
    def test_roles_updated_immediately_and_login_lockout(self):
        viewer=self.viewer();token=session(self.db,viewer['id'])
        save_role(self.db,{'name':'Viewer','permissions':['data.view','logs.edit']})
        require(current_user(self.db,cookie(token)),'logs.edit')
        for _ in range(5):self.assertIsNone(login(self.db,{'username':'viewer','password':'bad'}))
        with self.assertRaises(ValueError):login(self.db,{'username':'viewer','password':'Safe-password123'})
if __name__=='__main__':unittest.main()
