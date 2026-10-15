"""SQLite users, roles and opaque HttpOnly sessions for a shared local workspace."""
import hashlib,hmac,json,re,secrets,time
from http.cookies import SimpleCookie

PERMISSIONS={'data.view':'Lihat dashboard, log & analisis','logs.edit':'Edit log dan mutasi manual','market.view':'Live Chart & snapshot MT5','notes.view':'Baca catatan','notes.edit':'Buat/edit catatan','ai.use':'Gunakan AI Assistant','sync.manage':'Tes koneksi & sinkronisasi','settings.manage':'Konfigurasi broker & API AI','users.manage':'Management Users','roles.manage':'Rules & Access'}
DEFAULTS={'Administrator':list(PERMISSIONS),'Trader':['data.view','logs.edit','market.view','notes.view','notes.edit','ai.use'],'Viewer':['data.view','market.view','notes.view']}

def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS app_roles(name TEXT PRIMARY KEY,permissions TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS app_users(id INTEGER PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE NOT NULL,display_name TEXT NOT NULL,email TEXT NOT NULL DEFAULT "",password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,failures INTEGER DEFAULT 0,locked_until REAL DEFAULT 0)')
    db.execute('CREATE TABLE IF NOT EXISTS app_sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires REAL NOT NULL)')
    for role,permissions in DEFAULTS.items():db.execute('INSERT OR IGNORE INTO app_roles VALUES(?,?)',(role,json.dumps(permissions)))

def password_hash(value):
    value=str(value)
    if not 12<=len(value)<=256:raise ValueError('Password harus 12–256 karakter.')
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',value.encode(),bytes.fromhex(salt),600000).hex()

def verify(value,stored):
    try:
        salt,digest=stored.split(':');actual=hashlib.pbkdf2_hmac('sha256',str(value).encode(),bytes.fromhex(salt),600000).hex()
        return hmac.compare_digest(actual,digest)
    except (ValueError,TypeError):return False

def public_user(db,id):
    row=db.execute('SELECT id,username,display_name,email,role,active FROM app_users WHERE id=?',(id,)).fetchone()
    if not row:return None
    role=db.execute('SELECT permissions FROM app_roles WHERE name=?',(row[4],)).fetchone()
    return dict(zip(('id','username','displayName','email','role','active'),row),permissions=list(PERMISSIONS) if row[4]=='Administrator' else json.loads(role[0]) if role else [])

def token_from_cookie(value):
    try:
        cookies=SimpleCookie();cookies.load(value or '');return cookies['tradinglog_session'].value if 'tradinglog_session' in cookies else ''
    except Exception:return ''

def current_user(db,cookie):
    token=token_from_cookie(cookie)
    if not token:return None
    row=db.execute('SELECT user_id FROM app_sessions WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    user=public_user(db,row[0]) if row else None
    return user if user and user['active'] else None

def session(db,id):
    token=secrets.token_urlsafe(32);db.execute('DELETE FROM app_sessions WHERE expires<=?',(time.time(),));db.execute('INSERT INTO app_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),id,time.time()+43200));return token

def cookie(token):return 'tradinglog_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age='+('43200' if token else '0')

def require(user,permission):
    if not user:raise PermissionError('Silakan login terlebih dahulu.')
    if permission not in user['permissions']:raise PermissionError('Anda tidak memiliki hak akses: '+PERMISSIONS.get(permission,permission))

def create_user(db,data,first=False):
    if first and db.execute('SELECT COUNT(*) FROM app_users').fetchone()[0]:raise ValueError('Administrator awal sudah dibuat.')
    username=str(data.get('username','')).strip();name=str(data.get('displayName','')).strip();email=str(data.get('email','')).strip();role='Administrator' if first else data.get('role','Viewer')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,50}',username):raise ValueError('Username 3–50 karakter: huruf, angka, titik, garis bawah atau minus.')
    if not name or len(name)>100 or len(email)>200:raise ValueError('Nama wajib diisi, maksimal 100 karakter.')
    if not db.execute('SELECT 1 FROM app_roles WHERE name=?',(role,)).fetchone():raise ValueError('Role tidak ditemukan.')
    if db.execute('SELECT 1 FROM app_users WHERE username=?',(username,)).fetchone():raise ValueError('Username sudah terdaftar.')
    row=db.execute('INSERT INTO app_users(username,display_name,email,password_hash,role) VALUES(?,?,?,?,?)',(username,name,email,password_hash(data.get('password','')),role))
    return public_user(db,row.lastrowid)

def login(db,data):
    username=str(data.get('username',''))[:50];password=str(data.get('password',''))
    if len(password)>256:raise ValueError('Username atau password salah.')
    row=db.execute('SELECT id,password_hash,active,failures,locked_until FROM app_users WHERE username=?',(username,)).fetchone()
    if not row:hashlib.pbkdf2_hmac('sha256',password.encode(),b'login-dummy-salt',600000)
    if row and row[4]>time.time():raise ValueError('Terlalu banyak percobaan. Coba lagi setelah 5 menit.')
    if not row or not verify(password,row[1]) or not row[2]:
        if row:db.execute('UPDATE app_users SET failures=failures+1,locked_until=? WHERE id=?',(time.time()+300 if row[3]>=4 else 0,row[0]))
        return None
    db.execute('UPDATE app_users SET failures=0,locked_until=0 WHERE id=?',(row[0],))
    return public_user(db,row[0])

def update_user(db,actor,data,profile=False):
    id=actor['id'] if profile else int(data['id']);old=public_user(db,id)
    if not old:raise ValueError('Pengguna tidak ditemukan.')
    name=str(data.get('displayName',old['displayName'])).strip();email=str(data.get('email',old['email'])).strip();role=old['role'] if profile else data.get('role',old['role']);active=old['active'] if profile else int(bool(data.get('active',old['active'])))
    if not name or len(name)>100 or len(email)>200:raise ValueError('Profil tidak valid.')
    if not db.execute('SELECT 1 FROM app_roles WHERE name=?',(role,)).fetchone():raise ValueError('Role tidak ditemukan.')
    if old['role']=='Administrator' and old['active'] and (role!='Administrator' or not active):
        if db.execute('SELECT COUNT(*) FROM app_users WHERE role="Administrator" AND active=1').fetchone()[0]<=1:raise ValueError('Administrator aktif terakhir tidak dapat dinonaktifkan atau diturunkan.')
    password=str(data.get('password',''))
    if password:
        if profile:
            stored=db.execute('SELECT password_hash FROM app_users WHERE id=?',(id,)).fetchone()[0]
            if not verify(data.get('currentPassword',''),stored):raise ValueError('Password saat ini salah.')
        db.execute('UPDATE app_users SET password_hash=?,failures=0,locked_until=0 WHERE id=?',(password_hash(password),id));db.execute('DELETE FROM app_sessions WHERE user_id=?',(id,))
    if not active or role!=old['role']:db.execute('DELETE FROM app_sessions WHERE user_id=?',(id,))
    db.execute('UPDATE app_users SET display_name=?,email=?,role=?,active=? WHERE id=?',(name,email,role,active,id));return public_user(db,id)

def save_role(db,data):
    name=str(data.get('name','')).strip();permissions=data.get('permissions',[])
    if not name or len(name)>60 or not isinstance(permissions,list) or any(p not in PERMISSIONS for p in permissions):raise ValueError('Role atau hak akses tidak valid.')
    if name=='Administrator':raise ValueError('Hak akses Administrator tidak dapat diubah.')
    db.execute('INSERT INTO app_roles VALUES(?,?) ON CONFLICT(name) DO UPDATE SET permissions=excluded.permissions',(name,json.dumps(sorted(set(permissions)))))

def endpoint_permission(path,method):
    if path=='/api/state':return 'data.view'
    if path=='/api/notes':return 'notes.view' if method=='GET' else 'notes.edit'
    if path in ('/api/chart','/api/trader/context'):return 'market.view'
    if path=='/api/ai/settings':return 'settings.manage'
    if path.startswith('/api/admin/users'):return 'users.manage'
    if path.startswith('/api/admin/roles'):return 'roles.manage'
    if path in ('/api/notes/ai','/api/trader/chat','/api/trader/history','/api/trader/clear'):return 'ai.use'
    if path=='/api/logs/context':return 'data.view'
    if path in ('/api/sync','/api/connection','/api/disconnect'):return 'sync.manage'
    if path=='/api/brokers/register':return 'settings.manage'
    return None
