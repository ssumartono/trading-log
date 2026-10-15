"""Local TradingLog API and read-only MT5 importer."""
import json, sqlite3, threading, time
import copy
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'tradinglog.sqlite3'
DB.parent.mkdir(exist_ok=True)
LOCK = threading.RLock()
WIB = timezone(timedelta(hours=7))

class DatabaseConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

def connect():
    db = sqlite3.connect(DB,timeout=30,factory=DatabaseConnection)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS mt5_deals (server TEXT, login INTEGER, ticket INTEGER, data TEXT NOT NULL, PRIMARY KEY(server,login,ticket))')
    db.execute('CREATE TABLE IF NOT EXISTS sync_runs (id INTEGER PRIMARY KEY, time TEXT, result TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS daily_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1)')
    db.execute('CREATE TABLE IF NOT EXISTS trader_messages (id INTEGER PRIMARY KEY AUTOINCREMENT,broker_id TEXT,role TEXT,content TEXT,created_at TEXT,context TEXT)')
    from user_auth import schema
    schema(db)
    return db

def load(db):
    row = db.execute('SELECT data FROM state WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None

def save(db, state):
    db.execute('INSERT INTO state VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (json.dumps(state),))

def apply_deal_price(row, deal):
    if 'order' in deal: row['orderId']=str(deal['order'])
    if deal['type'] in (0,1):
        row['dealSide']='Buy' if deal['type']==0 else 'Sell'
        # A closing buy execution closes a sell position, and vice versa.
        row['side']=('Sell' if deal['type']==0 else 'Buy') if deal['entry'] in (1,3) else row['dealSide']
    row['price']=deal['price']
    row['mt5Entry']=int(deal['entry'])
    row['entry']=deal['price'] if deal['entry']==0 else None
    row['exit']=deal['price'] if deal['entry'] in (1,3) else None

def restore_imported_prices(db,state):
    raw={f'{srv}:{login}:{ticket}':json.loads(data) for srv,login,ticket,data in db.execute('SELECT server,login,ticket,data FROM mt5_deals')}
    for row in state['records']:
        deal=raw.get(row.get('sourceKey'))
        if deal: apply_deal_price(row,deal)

def enforce_source_ownership(current, incoming):
    for name,editable in [('records',{'strategy','indicator','note'}),('funds',{'note'})]:
        old={r['id']:r for r in current[name] if r.get('sourceKey')}
        new={r['id']:r for r in incoming[name]}
        if old.keys()-new.keys():
            raise ValueError('Log hasil sinkronisasi tidak dapat dihapus manual.')
        for id,row in old.items():
            annotations={k:new[id].get(k,row.get(k,'')) for k in editable}
            new[id].clear();new[id].update(copy.deepcopy(row));new[id].update(annotations)
    brokers={b['id']:b for b in current['brokers']}
    for broker in incoming['brokers']:
        original=brokers.get(broker['id'])
        if original and original.get('accountKey'):
            for key in ('name','initial','accountKey','mt5Balance','mt5Equity'):
                if key in original:broker[key]=original[key]

def merge_manual_edits(current, incoming, base):
    """Apply only browser edits; retain unseen imported rows and MT5 updates."""
    result=copy.deepcopy(current)
    def patch_fields(target,new,old,protected=()):
        for key,value in new.items():
            if key in protected or value==old.get(key): continue
            if isinstance(value,dict) and isinstance(old.get(key),dict):
                target.setdefault(key,{})
                patch_fields(target[key],value,old[key])
            else:
                if key in old and target.get(key)!=old.get(key) and target.get(key)!=value:
                    raise ValueError(f'Field {key} juga diedit pada sesi lain. Perubahan Anda tetap ada; periksa kembali sebelum menyimpan.')
                target[key]=copy.deepcopy(value)
    for name in ('records','funds','brokers'):
        old={r['id']:r for r in base[name]};new={r['id']:r for r in incoming[name]};live={r['id']:r for r in result[name]}
        for id,row in new.items():
            if id not in old:
                if id in live: raise ValueError('ID log baru bertabrakan dengan impor terbaru. Silakan coba tambah log lagi.')
                live[id]=copy.deepcopy(row)
            elif id in live:
                protected=('id','sourceKey','accountKey')
                if live[id].get('sourceKey'):
                    protected=tuple(set(row)-({'strategy','indicator','note'} if name=='records' else {'note'}))
                patch_fields(live[id],row,old[id],protected)
            elif row!=old[id]: raise ValueError('Log yang diedit telah dihapus oleh sesi lain.')
        for id in old.keys()-new.keys():
            if id in live:
                # Removing a row is explicit, never inferred from new sync rows.
                del live[id]
        result[name]=list(live.values())
    patch_fields(result['settings'],incoming['settings'],base['settings'],('lastSync','lastMessage'))
    result['syncRevision']=current.get('syncRevision',0)
    return result

def validate_config(config):
    config['path']=str(config.get('path','')).strip().strip('"')
    config['server']=str(config.get('server','')).strip()
    config['login']=str(config.get('login','')).strip()
    if not str(config.get('login','')).isdigit() or not str(config.get('server','')).strip() or not str(config.get('path','')).strip():
        raise ValueError('Nomor akun, server, dan lokasi terminal wajib diisi.')
    datetime.fromisoformat(config['start'])

def register_broker(config):
    import MetaTrader5 as mt5
    validate_config(config)
    with LOCK, connect() as db:
        state=load(db)
        if state is None: raise ValueError('Buka aplikasi terlebih dahulu.')
        key=f"{config['server']}:{int(config['login'])}"
        if any(b.get('accountKey')==key for b in state['brokers']):
            raise ValueError('Akun ini sudah terdaftar. Pilih akun yang sudah ada.')
        try:
            if not mt5.initialize(config['path'],timeout=15000): raise ValueError('Koneksi MT5 gagal: '+str(mt5.last_error()))
            account=mt5.account_info();terminal=mt5.terminal_info()
            if not account or not terminal or not terminal.connected: raise ValueError('Terminal belum terhubung.')
            if account.login!=int(config['login']) or account.server!=config['server']:
                raise ValueError(f"Terminal aktif pada {account.login} / {account.server}. Login manual ke {config['login']} / {config['server']} di MT5, selesaikan OTP/sertifikat jika diminta, lalu ulangi Tes koneksi.")
            if account.currency!='USD': raise ValueError('Versi ini mendukung akun USD.')
            config=dict(config,enabled=True,auto=False)
            broker={'id':max([b['id'] for b in state['brokers']]+[0])+1,'name':f'{account.server} · {account.login}','initial':account.balance,'accountKey':key,'integration':config}
            config['brokerId']=str(broker['id']);state['brokers'].append(broker);state['settings']=config
            state['syncRevision']=state.get('syncRevision',0)+1
            save(db,state)
            return {'message':'Koneksi berhasil. Broker terdaftar; pilih Sync sekarang untuk mengimpor riwayat.','brokerId':broker['id']}
        finally: mt5.shutdown()

def disconnect_active():
    import MetaTrader5 as mt5
    with LOCK, connect() as db:
        state=load(db)
        if not state: raise ValueError('Buka aplikasi terlebih dahulu.')
        settings=state['settings']
        # A single terminal can serve only one logged-in account at a time.
        for item in state['brokers']:
            config=item.get('integration',{})
            if str(config.get('path','')).replace('\\','/').lower()==str(settings.get('path','')).replace('\\','/').lower():
                config['enabled']=False
                config['auto']=False
                config['lastMessage']='Integrasi dilepas sebelum pendaftaran akun baru pada terminal yang sama.'
        broker=next((b for b in state['brokers'] if str(b['id'])==str(settings.get('brokerId'))),None)
        if broker:
            config=broker.get('integration') or dict(settings)
            config['enabled']=False
            config['auto']=False
            config['lastMessage']='Koneksi integrasi dilepas untuk menambahkan akun broker baru.'
            broker['integration']=config
        settings['enabled']=False
        settings['auto']=False
        mt5.shutdown()
        state['syncRevision']=state.get('syncRevision',0)+1
        save(db,state)
        return {'message':'Integrasi broker aktif dilepas. Login ke akun baru di terminal MT5, lalu tes koneksi.'}

def synchronize(test=False, broker_id=None):
    import MetaTrader5 as mt5
    with LOCK, connect() as db:
        state = load(db)
        if not state:
            raise ValueError('Buka aplikasi terlebih dahulu.')
        broker_id=broker_id or state['settings'].get('brokerId')
        configured=next((b for b in state['brokers'] if str(b['id'])==str(broker_id)),None)
        if configured is None: raise ValueError('Daftarkan akun broker melalui Pengaturan terlebih dahulu.')
        config = configured.get('integration') or state['settings']
        validate_config(config)
        if not config.get('enabled'):
            raise ValueError('Aktifkan integrasi MT5 pada Pengaturan.')
        try:
            if not mt5.initialize(config['path'], timeout=15000):
                raise ValueError('Koneksi MT5 gagal: ' + str(mt5.last_error()))
            account = mt5.account_info()
            terminal = mt5.terminal_info()
            if not account or not terminal.connected:
                raise ValueError('Terminal MT5 belum terhubung.')
            if account.login != int(config['login']) or account.server != config['server']:
                raise ValueError('Akun/server aktif di terminal berbeda dari Pengaturan. Login ke akun yang sesuai di MT5.')
            if account.currency != 'USD':
                raise ValueError('Versi aplikasi ini hanya mendukung akun USD.')
            if test:
                return {'message': f'Terhubung ke {account.login} · {account.server} · {account.currency}'}
            start = datetime.fromisoformat(config['start']).replace(tzinfo=WIB).astimezone(timezone.utc)
            now = datetime.now(timezone.utc)
            if start > now:
                raise ValueError('Tanggal impor tidak boleh di masa depan.')
            # Some broker histories expose server-wall-clock timestamps ahead of UTC.
            # The terminal returns executed history only; allow a one-day query margin.
            deals = mt5.history_deals_get(start, now + timedelta(days=1))
            if deals is None:
                raise ValueError('Riwayat MT5 gagal: ' + str(mt5.last_error()))
            key = f'{account.server}:{account.login}'
            brokers = state['brokers']
            broker = next((b for b in brokers if b.get('accountKey') == key), None)
            if broker is None or broker['id']!=configured['id']:
                raise ValueError('Identitas akun berbeda. Tambahkan akun baru melalui Pengaturan.')
            broker['integration']=config
            config['brokerId'] = str(broker['id'])
            config['enabled'] = True
            net = lambda d: sum(float(getattr(d, k, 0)) for k in ('profit','commission','swap','fee'))
            broker['initial'] = round(account.balance - sum(net(d) for d in deals), 2)
            broker['mt5Balance'] = account.balance
            broker['mt5Equity'] = account.equity
            added = 0
            for deal in deals:
                raw = deal._asdict()
                existing = db.execute('SELECT 1 FROM mt5_deals WHERE server=? AND login=? AND ticket=?', (account.server,account.login,deal.ticket)).fetchone()
                added += not bool(existing)
                db.execute('INSERT INTO mt5_deals VALUES(?,?,?,?) ON CONFLICT(server,login,ticket) DO UPDATE SET data=excluded.data', (account.server,account.login,deal.ticket,json.dumps(raw)))
                stamp = datetime.fromtimestamp(deal.time, timezone.utc).astimezone(WIB)
                source = key + ':' + str(deal.ticket)
                base = {'sourceKey': source, 'date': stamp.strftime('%Y-%m-%d'), 'time': stamp.strftime('%H:%M'), 'ticket': str(deal.ticket), 'accountKey':key}
                if deal.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and config.get('importTrades'):
                    # Each row is an execution deal, not an invented round-trip position.
                    collection = state['records']
                    row = next((r for r in collection if r.get('sourceKey') == source), None)
                    if row is None:
                        row = {'id':max([r['id'] for r in collection]+[0])+1, 'strategy':'', 'indicator':'', 'note':''}
                        collection.append(row)
                    row.update(base)
                    row.update(symbol=deal.symbol, side='Buy' if deal.type==mt5.DEAL_TYPE_BUY else 'Sell', broker=broker['name'], lot=deal.volume,
                               profit=round(net(deal), 2), entry=deal.price, exit=deal.price, mt5Entry=int(deal.entry), positionId=str(deal.position_id),
                               status={0:'Entry',1:'Exit',2:'Reversal',3:'Close by'}.get(deal.entry,'Deal'), commission=deal.commission, swap=deal.swap, fee=deal.fee)
                    apply_deal_price(row,raw)
                elif deal.type not in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and config.get('importFunds'):
                    collection=state['funds']
                    row=next((f for f in collection if f.get('sourceKey')==source),None)
                    if row is None:
                        row={'id':max([f['id'] for f in collection]+[0])+1,'note':deal.comment or ''}
                        collection.append(row)
                    amount=net(deal)
                    kind=('Deposit' if amount>=0 else 'Withdraw') if deal.type==mt5.DEAL_TYPE_BALANCE else 'Adjustment'
                    row.update(base)
                    row.update(brokerId=broker['id'],type=kind,amount=abs(amount),signedAmount=amount,mt5Type=int(deal.type))
            # Keep the opening balance consistent with ALL retained imported history,
            # even if the user narrows the import window after an earlier full import.
            retained=[json.loads(data) for data, in db.execute('SELECT data FROM mt5_deals WHERE server=? AND login=?',(account.server,account.login))]
            broker['initial']=round(account.balance-sum(sum(float(d.get(k,0)) for k in ('profit','commission','swap','fee')) for d in retained),2)
            result={'message':f'Sinkronisasi selesai: {len(deals)} deal diperiksa, {added} deal baru.', 'time':now.isoformat(), 'deals':len(deals),'new':added}
            config['lastSync']=result['time'];config['lastMessage']=result['message']
            if str(state['settings'].get('brokerId'))==str(broker['id']): state['settings']=dict(config)
            state['syncRevision']=state.get('syncRevision',0)+1
            save(db,state)
            db.execute('INSERT INTO sync_runs(time,result) VALUES(?,?)',(result['time'],json.dumps(result)))
            return result
        finally:
            mt5.shutdown()

def write_note(db,data):
    title=str(data.get('title','')).strip();body=str(data.get('body',''))
    if not title or len(title)>160 or len(body)>30000: raise ValueError('Judul wajib diisi (maksimal 160 karakter); isi maksimal 30.000 karakter.')
    datetime.fromisoformat(data['eventDate'])
    if data.get('kind') not in ('Catatan Harian','Memo','Event','Lesson Learned'): raise ValueError('Jenis catatan tidak valid.')
    if data.get('folder') not in ('inbox','archive','trash'): raise ValueError('Folder tidak valid.')
    account=data.get('brokerId')
    if account is not None:
        state=load(db)
        if not any(str(b['id'])==str(account) for b in (state or {}).get('brokers',[])): raise ValueError('Akun tidak ditemukan.')
    note={k:data.get(k) for k in ('eventDate','kind','brokerId','folder')}
    note.update(title=title,body=body,important=bool(data.get('important')),updatedAt=datetime.now(timezone.utc).isoformat())
    if data.get('id'):
        old=db.execute('SELECT data,revision FROM daily_notes WHERE id=?',(int(data['id']),)).fetchone()
        if not old: raise ValueError('Catatan tidak ditemukan.')
        if old[1]!=data.get('revision'): raise ValueError('Catatan berubah di sesi lain. Buka kembali catatan sebelum menyimpan.')
        note['createdAt']=json.loads(old[0])['createdAt']
        db.execute('UPDATE daily_notes SET data=?,revision=revision+1 WHERE id=?',(json.dumps(note),data['id']))
        return dict(note,id=data['id'],revision=old[1]+1)
    note['createdAt']=note['updatedAt']
    cursor=db.execute('INSERT INTO daily_notes(data) VALUES(?)',(json.dumps(note),))
    return dict(note,id=cursor.lastrowid,revision=1)

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data,session_cookie=None):
        body=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
        if session_cookie:self.send_header('Set-Cookie',session_cookie)
        self.end_headers();self.wfile.write(body)
    def auth_gate(self,method):
        from user_auth import current_user,endpoint_permission,require
        with LOCK,connect() as db:self.user=current_user(db,self.headers.get('Cookie'))
        permission=endpoint_permission(self.path,method)
        try:
            if not self.user:raise PermissionError('Silakan login terlebih dahulu.')
            if permission:require(self.user,permission)
            if permission=='ai.use':require(self.user,'data.view')
            return True
        except PermissionError as e:
            self.reply(401 if not self.user else 403,{'error':str(e)});return False
    def auth_post(self):
        from user_auth import create_user,login,session,cookie,current_user,update_user,require,save_role,token_from_cookie
        length=int(self.headers.get('Content-Length','0'))
        if length>20000:raise ValueError('Input terlalu besar.')
        data=json.loads(self.rfile.read(length));status=200;session_cookie=None
        with LOCK,connect() as db:
            user=current_user(db,self.headers.get('Cookie'))
            if self.path=='/api/auth/setup':
                user=create_user(db,data,first=True);session_cookie=cookie(session(db,user['id']));result={'user':user}
            elif self.path=='/api/auth/login':
                user=login(db,data)
                if user:session_cookie=cookie(session(db,user['id']));result={'user':user}
                else:status=401;result={'error':'Username atau password salah.'}
            elif self.path=='/api/auth/logout':
                import hashlib
                token=token_from_cookie(self.headers.get('Cookie'));db.execute('DELETE FROM app_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),));session_cookie=cookie('');result={'loggedOut':True}
            elif self.path=='/api/auth/profile':
                if not user:raise PermissionError('Silakan login terlebih dahulu.')
                result={'user':update_user(db,user,data,profile=True),'passwordChanged':bool(data.get('password'))}
                if data.get('password'):session_cookie=cookie(session(db,user['id']))
            elif self.path=='/api/admin/users':
                require(user,'users.manage')
                if user['role']!='Administrator':
                    from user_auth import public_user
                    target=public_user(db,int(data['id'])) if data.get('id') else None
                    role=data.get('role',target['role'] if target else 'Viewer')
                    rights=db.execute('SELECT permissions FROM app_roles WHERE name=?',(role,)).fetchone()
                    if (target and target['role']=='Administrator') or role=='Administrator' or (rights and not set(json.loads(rights[0])).issubset(user['permissions'])):
                        raise PermissionError('Tidak boleh memberikan atau mengubah akses yang melebihi hak akses Anda.')
                result={'user':update_user(db,user,data) if data.get('id') else create_user(db,data)}
            elif self.path=='/api/admin/roles':
                require(user,'roles.manage')
                if user['role']!='Administrator' and not set(data.get('permissions',[])).issubset(user['permissions']):raise PermissionError('Tidak boleh memberikan hak akses yang tidak Anda miliki.')
                save_role(db,data);result={'saved':True}
            else:raise ValueError('Endpoint tidak ditemukan.')
        self.reply(status,result,session_cookie)
    def do_GET(self):
        if self.path=='/api/auth/status':
            from user_auth import current_user
            with LOCK,connect() as db:result={'setupRequired':not db.execute('SELECT 1 FROM app_users LIMIT 1').fetchone(),'user':current_user(db,self.headers.get('Cookie'))}
            return self.reply(200,result)
        if self.path.startswith('/api/') and not self.auth_gate('GET'):return
        if self.path in ('/api/admin/users','/api/admin/roles'):
            from user_auth import public_user,PERMISSIONS
            with LOCK,connect() as db:
                roles=[{'name':name,'permissions':json.loads(p)} for name,p in db.execute('SELECT name,permissions FROM app_roles ORDER BY name')]
                result={'roles':roles,'permissions':PERMISSIONS}
                if self.path.endswith('/users'):result['users']=[public_user(db,id) for id, in db.execute('SELECT id FROM app_users ORDER BY id')]
            return self.reply(200,result)
        if self.path=='/api/ai/settings':
            from ai_notes import key_status
            self.reply(200,key_status())
        elif self.path=='/api/notes':
            with connect() as db:
                self.reply(200,[dict(json.loads(data),id=id,revision=rev) for id,data,rev in db.execute('SELECT id,data,revision FROM daily_notes ORDER BY id DESC')])
        elif self.path=='/api/state':
            with LOCK, connect() as db: self.reply(200,load(db))
        elif self.path in ('/','/index.html'):
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write((ROOT/'mockup/index.html').read_bytes())
        elif self.path=='/vendor/lightweight-charts.js':
            self.send_response(200);self.send_header('Content-Type','application/javascript');self.end_headers();self.wfile.write((ROOT/'mockup/vendor/lightweight-charts.js').read_bytes())
        elif self.path in ('/performance.js','/table-pagination.js','/table-sorting.js','/notes.js','/note-ai.js','/note-ai-main.js','/ai-settings.js','/trader-ui.js','/live-chart-ui.js','/ai-logs-ui.js','/users-ui.js'):
            self.send_response(200);self.send_header('Content-Type','application/javascript; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write((ROOT/'mockup'/self.path.lstrip('/')).read_bytes())
        else: self.reply(404,{'error':'Not found'})
    def do_POST(self):
        if self.headers.get('Origin') not in ('http://127.0.0.1:3000','http://localhost:3000'):
            return self.reply(403,{'error':'Origin tidak diizinkan'})
        try:
            if self.path.startswith('/api/auth/') or self.path in ('/api/admin/users','/api/admin/roles'):
                return self.auth_post()
            if not self.auth_gate('POST'):return
            if self.path=='/api/logs/context':
                from ai_log_context import retrieve_logs
                length=int(self.headers.get('Content-Length','0'))
                if length>15000:raise ValueError('Filter terlalu besar.')
                data=json.loads(self.rfile.read(length))
                with LOCK,connect() as db: result=retrieve_logs(load(db) or {},data)
                self.reply(200,result)
            elif self.path=='/api/chart':
                from live_chart import read_live_chart
                length=int(self.headers.get('Content-Length','0'))
                if length>4000:raise ValueError('Input chart terlalu besar.')
                data=json.loads(self.rfile.read(length))
                with LOCK,connect() as db: result=read_live_chart(load(db),data)
                self.reply(200,result)
            elif self.path in ('/api/trader/history','/api/trader/context','/api/trader/chat','/api/trader/clear'):
                from trader_ai import market_context,answer_trader,chat_history
                length=int(self.headers.get('Content-Length','0'))
                if length>15000:raise ValueError('Pesan terlalu besar.')
                data=json.loads(self.rfile.read(length));broker_id=str(data.get('brokerId',''))
                from user_auth import require
                if data.get('includeMarket'):require(self.user,'market.view')
                with LOCK,connect() as db:
                    state=load(db)
                    if not any(str(b['id'])==broker_id for b in state['brokers']):raise ValueError('Akun trading tidak ditemukan.')
                    if self.path=='/api/trader/clear':
                        db.execute('DELETE FROM trader_messages WHERE broker_id=?',(broker_id,))
                        return self.reply(200,{'cleared':True})
                    history=chat_history(db,broker_id)
                if self.path=='/api/trader/history':return self.reply(200,history)
                context=None
                if self.path=='/api/trader/context' or data.get('includeMarket'):
                    with LOCK:context=market_context(state,data)
                if self.path=='/api/trader/context':return self.reply(200,context)
                message=str(data.get('message','')).strip()
                if not message or len(message)>5000:raise ValueError('Pesan wajib diisi, maksimal 5.000 karakter.')
                messages=[{'role':m['role'],'content':m['content']} for m in history[-20:]]+[{'role':'user','content':message}]
                log_context=None
                if data.get('includeLogs'):
                    from ai_log_context import retrieve_logs
                    log_context=retrieve_logs(state,data)
                answer=answer_trader(messages,context,log_context)
                with LOCK,connect() as db:
                    stamp=datetime.now(timezone.utc).isoformat()
                    for role,text in [('user',message),('assistant',answer)]:
                        db.execute('INSERT INTO trader_messages(broker_id,role,content,created_at,context) VALUES(?,?,?,?,?)',(broker_id,role,text,stamp,json.dumps({'marketContext':context,'logContext':log_context}) if role=='assistant' and (context or log_context) else None))
                self.reply(200,{'answer':answer,'context':context,'logContext':log_context})
            elif self.path=='/api/ai/settings':
                from ai_notes import configure_ai
                length=int(self.headers.get('Content-Length','0'))
                if length>4000:raise ValueError('Input terlalu besar.')
                data=json.loads(self.rfile.read(length))
                self.reply(200,configure_ai(data))
            elif self.path=='/api/notes/ai':
                from ai_notes import draft_note
                length=int(self.headers.get('Content-Length','0'))
                if length>100000: raise ValueError('Input AI terlalu besar.')
                data=json.loads(self.rfile.read(length))
                from user_auth import require
                require(self.user,'notes.edit')
                with LOCK, connect() as db: state=load(db)
                self.reply(200,draft_note(data,state or {'records':[],'brokers':[]}))
            elif self.path=='/api/notes':
                length=int(self.headers.get('Content-Length','0'))
                if length>100000: raise ValueError('Catatan terlalu panjang.')
                data=json.loads(self.rfile.read(length))
                with LOCK, connect() as db:
                    self.reply(200,write_note(db,data))
            elif self.path=='/api/state':
                length=int(self.headers.get('Content-Length','0'))
                if length>5000000: raise ValueError('Data terlalu besar')
                data=json.loads(self.rfile.read(length))
                if not all(isinstance(data.get(k),list) for k in ('records','brokers','funds')): raise ValueError('Format state tidak valid')
                with LOCK, connect() as db:
                    current=load(db)
                    base=data.pop('_base',None)
                    if current and base:
                        data=merge_manual_edits(current,data,base)
                    elif current and current.get('syncRevision',0)!=data.get('syncRevision',0):
                        raise ValueError('Data diperbarui oleh sinkronisasi. Refresh halaman sebelum menyimpan perubahan.')
                    if current:
                        old={b['id']:b for b in current['brokers']}
                        for b in data['brokers']:
                            if b['id'] not in old: raise ValueError('Broker baru harus didaftarkan melalui Pengaturan dan Tes koneksi.')
                            if b.get('accountKey')!=old[b['id']].get('accountKey'): raise ValueError('Identitas akun broker tidak dapat diubah.')
                            config=b.get('integration')
                            if config:
                                validate_config(config)
                                if f"{config['server']}:{int(config['login'])}"!=b.get('accountKey'): raise ValueError('Gunakan Tambah akun broker untuk identitas MT5 yang berbeda.')
                    if current: enforce_source_ownership(current,data)
                    if current:
                        from user_auth import require
                        if current['records']!=data['records'] or current['funds']!=data['funds']:require(self.user,'logs.edit')
                        if current['brokers']!=data['brokers'] or current['settings']!=data['settings']:require(self.user,'settings.manage')
                    restore_imported_prices(db,data)
                    save(db,data)
                self.reply(200,{'saved':True})
            elif self.path in ('/api/sync','/api/connection'):
                self.reply(200,synchronize(self.path=='/api/connection'))
            elif self.path=='/api/brokers/register':
                length=int(self.headers.get('Content-Length','0'))
                if length>16000: raise ValueError('Konfigurasi terlalu besar')
                self.reply(200,register_broker(json.loads(self.rfile.read(length))))
            elif self.path=='/api/disconnect':
                self.reply(200,disconnect_active())
            else: self.reply(404,{'error':'Not found'})
        except PermissionError as exc:self.reply(403,{'error':str(exc)})
        except Exception as exc: self.reply(400,{'error':str(exc)})
    def log_message(self,*args): pass

def scheduler():
    last={}
    while True:
        time.sleep(5)
        try:
            with LOCK, connect() as db: state=load(db)
            for broker in (state or {}).get('brokers',[]):
                settings=broker.get('integration',{})
                if settings.get('enabled') and settings.get('auto') and time.time()-last.get(broker['id'],0)>=max(60,int(settings.get('interval',60))):
                    last[broker['id']]=time.time();synchronize(broker_id=broker['id'])
        except Exception as exc:
            with LOCK, connect() as db:
                db.execute('INSERT INTO sync_runs(time,result) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps({'error':str(exc)})))

if __name__=='__main__':
    with connect() as db:
        state=load(db)
        if state:
            restore_imported_prices(db,state)
            state['syncRevision']=state.get('syncRevision',0)+1
            for broker in state['brokers']:
                if str(broker['id'])==str(state['settings'].get('brokerId')) and 'integration' not in broker:
                    broker['integration']=dict(state['settings'])
            save(db,state)
    threading.Thread(target=scheduler,daemon=True).start()
    print('TradingLog: http://127.0.0.1:3000',flush=True)
    ThreadingHTTPServer(('127.0.0.1',3000),Handler).serve_forever()
