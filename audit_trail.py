"""Append-only application audit events, with secrets removed before storage."""
import json,threading,uuid
from datetime import datetime,timezone
context=threading.local()

def scrub(value):
    if isinstance(value,dict):
        return {k:('[REDACTED]' if any(s in k.lower().replace('_','') for s in ('password','apikey','token','secret','authorization')) else scrub(v)) for k,v in value.items()}
    if isinstance(value,list):return [scrub(v) for v in value]
    return value

def event(db,action,entity,entity_id,before=None,after=None):
    if getattr(context,'disabled',False):return
    actor=getattr(context,'actor',None) or {'username':'system','id':None}
    db.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),str(actor.get('id') or ''),actor.get('username','system'),action,entity,str(entity_id),json.dumps(scrub(before),ensure_ascii=False),json.dumps(scrub(after),ensure_ascii=False)))

def schema(db):
    existed=bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_events'").fetchone())
    db.execute('CREATE TABLE IF NOT EXISTS audit_events(id TEXT PRIMARY KEY,time TEXT NOT NULL,user_id TEXT,actor TEXT,action TEXT,entity TEXT,entity_id TEXT,before_json TEXT,after_json TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS audit_time ON audit_events(time DESC)')
    db.execute("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT,'Audit trail tidak dapat diubah'); END")
    db.execute("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT,'Audit trail tidak dapat dihapus'); END")
    register(db)
    install_triggers(db)
    if not existed:event(db,'enabled','audit','workspace',None,{'message':'Audit mulai aktif; perubahan sebelum waktu ini tidak direkonstruksi.'})

def register(db):
    db.create_function('audit_enabled',0,lambda:0 if getattr(context,'disabled',False) else 1)
    db.create_function('audit_actor',0,lambda:(getattr(context,'actor',None) or {}).get('username','system'))
    db.create_function('audit_user',0,lambda:str((getattr(context,'actor',None) or {}).get('id','')))
    db.create_function('audit_uuid',0,lambda:str(uuid.uuid4()))
    db.create_function('audit_scrub',1,lambda s:json.dumps(scrub(json.loads(s)),ensure_ascii=False))
def install_triggers(db):
    tables={'daily_notes':['id','data','revision'],'trading_strategies':['id','data','revision'],'app_preferences':['key','data'],'app_users':['id','username','display_name','email','password_hash','role','active'],'app_roles':['name','permissions']}
    for table,columns in tables.items():
        identity=columns[0]
        def row(alias):
            parts=[]
            for col in columns:
                expr=f"json({alias}.{col})" if col in ('data','permissions') else f'{alias}.{col}'
                parts.extend(["'"+col+"'",expr])
            return 'audit_scrub(json_object('+','.join(parts)+'))'
        for operation in ('INSERT','UPDATE','DELETE'):
            old='NULL' if operation=='INSERT' else row('OLD');new='NULL' if operation=='DELETE' else row('NEW');alias='OLD' if operation=='DELETE' else 'NEW'
            condition='audit_enabled()=1'
            if operation=='UPDATE':condition+=' AND ('+' OR '.join(f'OLD.{col} IS NOT NEW.{col}' for col in columns)+')'
            db.execute(f"CREATE TRIGGER IF NOT EXISTS audit_{table}_{operation.lower()} AFTER {operation} ON {table} WHEN {condition} BEGIN INSERT INTO audit_events VALUES(audit_uuid(),strftime('%Y-%m-%dT%H:%M:%fZ','now'),audit_user(),audit_actor(),'{operation.lower()}','{table}',CAST({alias}.{identity} AS TEXT),{old},{new}); END")

def state_changes(db,before,after):
    before=before or {};after=after or {}
    for entity in ('records','funds','brokers'):
        old={str(r['id']):r for r in before.get(entity,[])};new={str(r['id']):r for r in after.get(entity,[])}
        for key in old.keys()|new.keys():
            if old.get(key)!=new.get(key):event(db,'create' if key not in old else 'delete' if key not in new else 'update',entity,key,old.get(key),new.get(key))
    if before.get('settings')!=after.get('settings'):event(db,'update','integration_settings','global',before.get('settings'),after.get('settings'))

def listing(db,data):
    page=max(0,int(data.get('page',0)));size=int(data.get('size',25));clauses=[];args=[]
    if size not in (5,10,25,50):raise ValueError('Ukuran halaman audit tidak valid.')
    for key,column in [('actor','actor'),('entity','entity'),('action','action')]:
        value=str(data.get(key,'')).strip()
        if value:clauses.append(column+'=?');args.append(value[:100])
    for key,operator in [('start','>='),('end','<=')]:
        value=str(data.get(key,''))
        if value:
            datetime.strptime(value,'%Y-%m-%d');clauses.append('substr(time,1,10)'+operator+'?');args.append(value)
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    count=db.execute('SELECT COUNT(*) FROM audit_events'+where,args).fetchone()[0];page=min(page,max(0,(count-1)//size))
    rows=[]
    for row in db.execute('SELECT * FROM audit_events'+where+' ORDER BY time DESC,id DESC LIMIT ? OFFSET ?',args+[size,page*size]):
        item=dict(zip(['id','time','userId','actor','action','entity','entityId','before','after'],row));item['before']=json.loads(item['before']) if item['before'] else None;item['after']=json.loads(item['after']) if item['after'] else None;rows.append(item)
    return {'rows':rows,'count':count,'page':page,'size':size,'actors':[r[0] for r in db.execute('SELECT DISTINCT actor FROM audit_events ORDER BY actor')],'entities':[r[0] for r in db.execute('SELECT DISTINCT entity FROM audit_events ORDER BY entity')]}
