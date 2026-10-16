"""Managed SQLite snapshots and transactional, validated data-only restores."""
import hashlib,json,re,secrets,sqlite3
from pathlib import Path
from datetime import datetime,timezone
import audit_trail

OPTIONAL={'attachments','broker_owners','user_account_settings','account_access_meta'}
TABLES=('broker_owners','user_account_settings','account_access_meta','attachments','state','mt5_deals','sync_runs','sync_status','balance_checkpoints','daily_notes','trader_messages','app_roles','app_users','trading_strategies','strategy_meta','app_preferences')
MAX_SIZE=64*1024*1024
class Connection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()
def open_database(*args,**kwargs):return sqlite3.connect(*args,factory=Connection,**kwargs)
def directory(database):
    folder=Path(database).parent/'backups';folder.mkdir(exist_ok=True);return folder
def path_for(database,name):
    if not re.fullmatch(r'(?:backup|uploaded|before-restore)-[0-9TZa-f-]+\.sqlite3',str(name)):raise ValueError('Nama cadangan tidak valid.')
    path=(directory(database)/name).resolve()
    if path.parent!=directory(database).resolve() or not path.is_file():raise ValueError('Cadangan tidak ditemukan.')
    return path
def digest(path):
    with open(path,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def inspect(path,current):
    path=Path(path)
    if path.stat().st_size>MAX_SIZE:raise ValueError('Ukuran cadangan maksimal 64 MB.')
    try:
        with open_database(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as source,open_database(Path(current).resolve().as_uri()+'?mode=ro',uri=True) as live:
            source.execute('PRAGMA trusted_schema=OFF')
            if source.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Integritas SQLite gagal.')
            definitions={name:sql for name,sql in source.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
            for table in TABLES:
                if table in OPTIONAL and table not in definitions:continue
                if table not in definitions or not definitions[table].lstrip().upper().startswith('CREATE TABLE'):raise ValueError('Tabel cadangan tidak lengkap: '+table)
                columns=lambda db:[(r[1],r[2],r[5]) for r in db.execute('PRAGMA table_info('+table+')')]
                if columns(source)!=columns(live):raise ValueError('Versi struktur cadangan berbeda: '+table)
            row=source.execute('SELECT data FROM state WHERE id=1').fetchone();state=json.loads(row[0]) if row else None
            if state is not None and not all(isinstance(state.get(key),list) for key in ('records','brokers','funds')):raise ValueError('Format state tidak valid.')
            if not source.execute("SELECT 1 FROM app_users WHERE role='Administrator' AND active=1 LIMIT 1").fetchone():raise ValueError('Cadangan harus berisi Administrator aktif.')
            administrators=[]
            for username,password in source.execute("SELECT username,password_hash FROM app_users WHERE role='Administrator' AND active=1"):
                if not re.fullmatch(r'[0-9a-f]{32}:[0-9a-f]{64}',password):raise ValueError('Hash password Administrator tidak valid.')
                administrators.append(username)
            # Validate all JSON before touching live data; never execute backup schema/triggers.
            for table,column in [('attachments','data'),('state','data'),('mt5_deals','data'),('daily_notes','data'),('trader_messages','context'),('app_roles','permissions'),('trading_strategies','data'),('app_preferences','data'),('sync_status','data'),('balance_checkpoints','data')]:
                if table in OPTIONAL and table not in definitions:continue
                for value, in source.execute('SELECT '+column+' FROM '+table):
                    if value is not None:json.loads(value)
            if 'attachments' in definitions:
                from attachments import validate_image
                for meta,content in source.execute('SELECT data,content FROM attachments'):
                    if json.loads(meta).get('mime')!=validate_image(content):raise ValueError('Lampiran cadangan tidak valid.')
            counts={table:source.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in TABLES if table!='state' and table in definitions}
            counts.update(records=len((state or {}).get('records',[])),funds=len((state or {}).get('funds',[])),brokers=len((state or {}).get('brokers',[])))
            return {'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path),'createdAt':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'counts':counts,'administrators':administrators,'valid':True}
    except (sqlite3.Error,ValueError,TypeError,KeyError) as error:
        if isinstance(error,ValueError) and not isinstance(error,json.JSONDecodeError):raise
        raise ValueError('Berkas bukan cadangan TradingLog yang valid.') from None

def create(database,prefix='backup'):
    name=prefix+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)+'.sqlite3';target=directory(database)/name
    try:
        with open_database(Path(database).resolve().as_uri()+'?mode=ro',uri=True) as source,open_database(target) as destination:
            source.backup(destination);destination.execute('DELETE FROM app_sessions')
        return inspect(target,database)
    except Exception:
        target.unlink(missing_ok=True);raise

def upload(database,content):
    if len(content)>MAX_SIZE or not content.startswith(b'SQLite format 3\x00'):raise ValueError('Pilih cadangan SQLite, maksimal 64 MB.')
    target=directory(database)/('uploaded-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)+'.sqlite3')
    try:
        target.write_bytes(content);return inspect(target,database)
    except Exception:
        target.unlink(missing_ok=True);raise

def listing(database):
    result=[]
    for path in directory(database).glob('*.sqlite3'):
        try:result.append({'name':path.name,'bytes':path.stat().st_size,'createdAt':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()})
        except OSError:continue
    return sorted(result,key=lambda r:r['createdAt'],reverse=True)

def restore(database,connect,data):
    if data.get('confirmation')!='RESTORE':raise ValueError('Ketik RESTORE untuk mengonfirmasi pemulihan.')
    path=path_for(database,data.get('name'));preview=inspect(path,database)
    if data.get('sha256')!=preview['sha256']:raise ValueError('Cadangan berubah. Validasi ulang sebelum restore.')
    safety=create(database,'before-restore')
    audit_trail.context.disabled=True
    try:
        with open_database(path.as_uri()+'?mode=ro&immutable=1',uri=True) as source,connect() as live:
            source.execute('PRAGMA trusted_schema=OFF');live.execute('BEGIN IMMEDIATE') if not live.in_transaction else None
            for table in TABLES:
                live.execute('DELETE FROM '+table)
                if table in OPTIONAL and not source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():continue
                cursor=source.execute('SELECT * FROM '+table);placeholders=','.join('?' for _ in cursor.description)
                while True:
                    rows=cursor.fetchmany(500)
                    if not rows:break
                    live.executemany('INSERT INTO '+table+' VALUES('+placeholders+')',rows)
            # Every browser must reauthenticate; restored integrations stay paused.
            live.execute('DELETE FROM app_sessions')
            row=live.execute('SELECT data FROM state WHERE id=1').fetchone()
            if row:
                state=json.loads(row[0]);state['syncRevision']=state.get('syncRevision',0)+1
                state.get('settings',{}).update(auto=False,enabled=False)
                for broker in state.get('brokers',[]):broker.get('integration',{}).update(auto=False,enabled=False)
                live.execute('UPDATE state SET data=? WHERE id=1',(json.dumps(state),))
            for user_id,raw in live.execute('SELECT user_id,data FROM user_account_settings').fetchall():
                config=json.loads(raw);config.update(enabled=False,auto=False)
                live.execute('UPDATE user_account_settings SET data=? WHERE user_id=?',(json.dumps(config),user_id))
            import account_access
            account_access.schema(live)
            live.execute('DELETE FROM sync_status')
            # Existing audit survives restore; import older events only by unique ID.
            if source.execute("SELECT 1 FROM sqlite_master WHERE name='audit_events' AND type='table'").fetchone():
                expected=[r[1] for r in live.execute('PRAGMA table_info(audit_events)')]
                if [r[1] for r in source.execute('PRAGMA table_info(audit_events)')]==expected:
                    for row in source.execute('SELECT * FROM audit_events'):
                        values=list(row)
                        for index in (7,8):
                            if values[index] is not None:values[index]=json.dumps(audit_trail.scrub(json.loads(values[index])))
                        live.execute('INSERT OR IGNORE INTO audit_events VALUES(?,?,?,?,?,?,?,?,?)',values)
            audit_trail.context.disabled=False
            audit_trail.event(live,'restore','backup',path.name,None,{'sha256':preview['sha256'],'safetyBackup':safety['name'],'integrationsPaused':True})
    finally:audit_trail.context.disabled=False
    return {'restored':True,'safetyBackup':safety['name'],'message':'Restore selesai. Semua sesi dicabut dan integrasi MT5 dijeda. Login kembali menggunakan akun pada cadangan.'}
