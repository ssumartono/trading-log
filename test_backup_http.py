import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import server

class BackupHTTPTests(unittest.TestCase):
    def test_admin_roundtrip_and_viewer_denial(self):
        with tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True) as temp,patch.object(server,'DB',Path(temp)/'http.sqlite3'):
            with server.connect() as db:server.save(db,{'records':[{'id':1,'note':'original','profit':1,'broker':'Test'}],'funds':[],'brokers':[{'id':1,'name':'Test'}],'settings':{},'syncRevision':0})
            http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(http.server_port)
            def call(path,data=None,cookie='',binary=False):
                body=data if binary else json.dumps(data or {}).encode()
                request=Request(base+path,data=body,headers={'Origin':'http://127.0.0.1:3000','Content-Type':'application/octet-stream' if binary else 'application/json','Cookie':cookie})
                try:
                    with urlopen(request,timeout=15) as response:
                        content=response.read();return response.status,(content if response.headers.get_content_type()=='application/vnd.sqlite3' else json.loads(content)),response.headers.get('Set-Cookie','')
                except HTTPError as error:
                    try:return error.code,json.load(error),''
                    finally:error.close()
            try:
                _,_,admin=call('/api/auth/setup',{'username':'admin','displayName':'Admin','password':'Test-password123'})
                call('/api/admin/users',{'username':'reader','displayName':'Reader','password':'Test-password123','role':'Viewer'},admin)
                _,_,reader=call('/api/auth/login',{'username':'reader','password':'Test-password123'})
                for endpoint in ('/api/admin/backup/list','/api/admin/backup/create','/api/admin/backup/restore','/api/admin/backup/download','/api/admin/audit'):
                    self.assertEqual(call(endpoint,cookie=reader)[0],403)
                    self.assertEqual(call(endpoint)[0],401)
                status,snapshot,_=call('/api/admin/backup/create',cookie=admin);self.assertEqual(status,200)
                self.assertEqual(call('/api/admin/backup/preview',{'name':snapshot['name']},admin)[1]['sha256'],snapshot['sha256'])
                status,content,_=call('/api/admin/backup/download',{'name':snapshot['name']},admin);self.assertEqual(status,200);self.assertTrue(content.startswith(b'SQLite format 3'))
                self.assertEqual(call('/api/admin/backup/upload',content,admin,binary=True)[0],200)
                edited={'records':[{'id':1,'note':'edited','profit':1,'broker':'Test'}],'funds':[],'brokers':[{'id':1,'name':'Test'}],'settings':{},'syncRevision':0}
                self.assertEqual(call('/api/state',edited,admin)[0],200)
                status,audit,_=call('/api/admin/audit',{'actor':'admin','entity':'records'},admin);self.assertEqual(status,200);self.assertEqual(audit['rows'][0]['after']['note'],'edited')
                self.assertEqual(call('/api/admin/backup/restore',dict(name=snapshot['name'],sha256=snapshot['sha256'],confirmation='NO'),admin)[0],400)
                status,result,_=call('/api/admin/backup/restore',dict(name=snapshot['name'],sha256=snapshot['sha256'],confirmation='RESTORE'),admin);self.assertEqual(status,200);self.assertTrue(result['restored'])
                self.assertEqual(call('/api/admin/audit',cookie=admin)[0],401)
                status,_,new_admin=call('/api/auth/login',{'username':'admin','password':'Test-password123'});self.assertEqual(status,200)
                with server.connect() as db:self.assertEqual(server.load(db)['records'][0]['note'],'original')
                events=call('/api/admin/audit',cookie=new_admin)[1]['rows'];self.assertTrue(any(row['action']=='restore' for row in events))
            finally:http.shutdown();http.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
