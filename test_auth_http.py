import copy,json,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import server
class HTTPAuthTests(unittest.TestCase):
    def test_http_login_and_role_access(self):
        with tempfile.TemporaryDirectory(dir=server.ROOT/'data',ignore_cleanup_errors=True) as temp,patch.object(server,'DB',Path(temp)/'auth-test.sqlite3'):
            with server.connect() as db:
                server.save(db,{'records':[{'id':1,'profit':1,'note':''}],'funds':[],'brokers':[],'settings':{},'syncRevision':0})
            http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(http.server_port)
            def call(path,data=None,cookie=''):
                req=Request(base+path,headers={'Origin':'http://127.0.0.1:3000','Content-Type':'application/json','Cookie':cookie},data=json.dumps(data).encode() if data is not None else None)
                try:
                    with urlopen(req,timeout=10) as response:return response.status,json.load(response),response.headers.get('Set-Cookie','')
                except HTTPError as error:
                    try:return error.code,json.load(error),''
                    finally:error.close()
            try:
                self.assertEqual(call('/api/state')[0],401)
                status,result,admin=call('/api/auth/setup',{'username':'admin','displayName':'Administrator','password':'Test-password123'});self.assertEqual(status,200)
                self.assertEqual(call('/api/state',cookie=admin)[0],200)
                self.assertEqual(call('/api/admin/users',{'username':'reader','displayName':'Reader','password':'Test-password123','role':'Viewer'},admin)[0],200)
                _,_,reader=call('/api/auth/login',{'username':'reader','password':'Test-password123'})
                self.assertEqual(call('/api/admin/users',cookie=reader)[0],403)
                self.assertEqual(call('/api/ai/settings',cookie=reader)[0],403)
                self.assertEqual(call('/api/notes',{'title':'Forbidden'},reader)[0],403)
                _,state,_=call('/api/state',cookie=reader);edited=copy.deepcopy(state);edited['records'][0]['note']='Should not save';edited['_base']=state
                self.assertEqual(call('/api/state',edited,reader)[0],403)
                self.assertEqual(call('/api/auth/logout',{},reader)[0],200)
                self.assertEqual(call('/api/state',cookie=reader)[0],401)
                self.assertEqual(call('/api/auth/setup',{'username':'other','displayName':'Other','password':'Test-password123'})[0],400)
                self.assertEqual(call('/api/admin/roles',{'name':'Manager','permissions':['data.view','users.manage']},admin)[0],200)
                self.assertEqual(call('/api/admin/users',{'username':'manager','displayName':'Manager','password':'Test-password123','role':'Manager'},admin)[0],200)
                _,_,manager=call('/api/auth/login',{'username':'manager','password':'Test-password123'})
                self.assertEqual(call('/api/admin/users',{'username':'escalate','displayName':'Escalate','password':'Test-password123','role':'Administrator'},manager)[0],403)
            finally:http.shutdown();http.server_close();thread.join()
if __name__=='__main__':unittest.main()
