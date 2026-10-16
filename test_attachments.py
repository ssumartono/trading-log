import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import attachments,server,backup_restore,user_auth

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j3ioAAAAASUVORK5CYII=')
class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True);self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.sqlite3';p=patch.object(server,'DB',self.path);p.start();self.addCleanup(p.stop)
        self.state={'records':[{'id':1,'profit':0}],'brokers':[{'id':2,'name':'Test'}],'funds':[],'settings':{}}
        self.user={'id':1,'username':'admin','permissions':list(user_auth.PERMISSIONS)}
        with server.connect() as db:
            server.save(db,self.state);user_auth.create_user(db,{'username':'admin','displayName':'Admin','password':'Testing-password1'},True)
            db.execute('INSERT INTO daily_notes VALUES(1,?,1)',(json.dumps({'title':'Memo'}),))
    def call(self,**data):
        with server.connect() as db:return attachments.operate(db,self.state,{'kind':'log','target':'1',**data},self.user)
    def test_relations_permissions_and_invalid_images(self):
        for kind,target in [('log','1'),('note','1'),('chart','2')]:
            rows=self.call(kind=kind,target=target,action='add',content=base64.b64encode(PNG).decode(),caption='Entry')
            self.assertEqual(len(rows),1)
        self.assertEqual(len(self.call()),1)
        item=self.call()[0]
        self.assertTrue(self.call(action='image',id=item['id'])['url'].startswith('data:image/png;base64,'))
        self.call(action='edit',id=item['id'],caption='Exit');self.assertEqual(self.call()[0]['caption'],'Exit')
        with self.assertRaises(ValueError):self.call(action='image',kind='chart',target='2',id=item['id'])
        with self.assertRaises(ValueError):self.call(target='99')
        with self.assertRaises(ValueError):self.call(action='add',content=base64.b64encode(b'<svg/>').decode())
        self.user['permissions']=['data.view']
        self.assertEqual(len(self.call()),1)
        with self.assertRaises(PermissionError):self.call(action='delete',id=item['id'])
    def test_backup_restore_includes_image_bytes(self):
        item=self.call(action='add',content=base64.b64encode(PNG).decode())[0]
        snapshot=backup_restore.create(self.path)
        self.call(action='delete',id=item['id']);self.assertEqual(self.call(),[])
        backup_restore.restore(self.path,server.connect,{'name':snapshot['name'],'sha256':snapshot['sha256'],'confirmation':'RESTORE'})
        self.assertEqual(len(self.call()),1)
        self.assertEqual(base64.b64decode(self.call(action='image',id=item['id'])['url'].split(',')[1]),PNG)

if __name__=='__main__':unittest.main()
