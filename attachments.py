"""Screenshot attachments stored atomically inside SQLite snapshots."""
import base64,binascii,json,struct
from datetime import datetime,timezone
import audit_trail

MAX_BYTES=5*1024*1024
def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY,data TEXT NOT NULL,content BLOB NOT NULL)')

def prune(db,state):
    valid={'log':{str(r['id']) for r in state.get('records',[])},'chart':{str(b['id']) for b in state.get('brokers',[])}}
    for id,data in db.execute('SELECT id,data FROM attachments').fetchall():
        meta=json.loads(data)
        if meta['kind'] in valid and meta['target'] not in valid[meta['kind']]:
            db.execute('DELETE FROM attachments WHERE id=?',(id,))
            audit_trail.event(db,'delete','attachment',id,meta,{'reason':'Data induk dihapus'})

def validate_image(content):
    if not content or len(content)>MAX_BYTES:raise ValueError('Gambar maksimal 5 MB.')
    if content.startswith(b'\x89PNG\r\n\x1a\n') and len(content)>24 and content[12:16]==b'IHDR':
        width,height=struct.unpack('>II',content[16:24])
        if not width or not height or width*height>40000000:raise ValueError('Dimensi gambar terlalu besar atau tidak valid.')
        return 'image/png'
    if content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9'):return 'image/jpeg'
    if content.startswith(b'RIFF') and content[8:12]==b'WEBP':return 'image/webp'
    raise ValueError('Gunakan gambar PNG, JPEG, atau WebP.')

def target(db,state,data):
    kind=str(data.get('kind',''));key=str(data.get('target',''))
    if kind=='log':exists=any(str(r['id'])==key for r in state.get('records',[]))
    elif kind=='note':exists=db.execute('SELECT 1 FROM daily_notes WHERE id=?',(key,)).fetchone()
    elif kind=='chart':exists=any(str(b['id'])==key for b in state.get('brokers',[]))
    else:raise ValueError('Jenis lampiran tidak valid.')
    if not exists:raise ValueError('Log, catatan, atau akun tidak ditemukan. Simpan catatan terlebih dahulu.')
    return kind,key

def operate(db,state,data,user):
    from user_auth import require
    action=data.get('action','list');kind,key=target(db,state,data)
    if kind=='note':
        from account_access import note_visible
        note=json.loads(db.execute('SELECT data FROM daily_notes WHERE id=?',(key,)).fetchone()[0])
        if not note_visible(db,note,user):raise PermissionError('Catatan bukan milik pengguna ini.')
    require(user,'notes.view' if kind=='note' else 'market.view' if kind=='chart' else 'data.view')
    if action not in ('list','image'):require(user,'notes.edit' if kind=='note' else 'logs.edit')
    if action=='image':
        row=db.execute('SELECT data,content FROM attachments WHERE id=?',(data.get('id'),)).fetchone()
        if not row:raise ValueError('Lampiran tidak ditemukan.')
        meta=json.loads(row[0])
        if (meta['kind'],meta['target'])!=(kind,key):raise ValueError('Relasi lampiran tidak sesuai.')
        return {'url':'data:'+validate_image(row[1])+';base64,'+base64.b64encode(row[1]).decode()}
    if action=='add':
        try:content=base64.b64decode(data.get('content',''),validate=True)
        except (ValueError,binascii.Error):raise ValueError('Data gambar tidak valid.') from None
        mime=validate_image(content)
        count=db.execute("SELECT count(*) FROM attachments WHERE json_extract(data,'$.kind')=? AND json_extract(data,'$.target')=?",(kind,key)).fetchone()[0]
        if count>=20:raise ValueError('Maksimal 20 gambar per log, catatan, atau akun chart.')
        meta={'kind':kind,'target':key,'caption':str(data.get('caption',''))[:500],'name':str(data.get('name','Screenshot'))[:160],'mime':mime,'bytes':len(content),'createdAt':datetime.now(timezone.utc).isoformat(),'context':str(data.get('context',''))[:500]}
        row=db.execute('INSERT INTO attachments(data,content) VALUES(?,?)',(json.dumps(meta),content))
        audit_trail.event(db,'add','attachment',row.lastrowid,None,meta)
    elif action in ('delete','edit'):
        row=db.execute('SELECT data FROM attachments WHERE id=?',(data.get('id'),)).fetchone()
        if not row:raise ValueError('Lampiran tidak ditemukan.')
        old=json.loads(row[0])
        if (old['kind'],old['target'])!=(kind,key):raise ValueError('Relasi lampiran tidak sesuai.')
        if action=='delete':db.execute('DELETE FROM attachments WHERE id=?',(data['id'],));new=None
        else:
            new={**old,'caption':str(data.get('caption',''))[:500]};db.execute('UPDATE attachments SET data=? WHERE id=?',(json.dumps(new),data['id']))
        audit_trail.event(db,action,'attachment',data['id'],old,new)
    elif action!='list':raise ValueError('Tindakan lampiran tidak valid.')
    return [dict(json.loads(meta),id=id) for id,meta in db.execute("SELECT id,data FROM attachments WHERE json_extract(data,'$.kind')=? AND json_extract(data,'$.target')=? ORDER BY id DESC",(kind,key))]
