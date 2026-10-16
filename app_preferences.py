"""Global display preferences, separate from MT5 source timestamp rules."""
import json

def schema(db):db.execute('CREATE TABLE IF NOT EXISTS app_preferences(key TEXT PRIMARY KEY,data TEXT NOT NULL)')
def read(db,user_id=None):
    key='display_time' if user_id is None else 'display_time:'+str(user_id)
    row=db.execute('SELECT data FROM app_preferences WHERE key=?',(key,)).fetchone()
    if not row and user_id is not None:
        first=db.execute("SELECT id FROM app_users WHERE role='Administrator' ORDER BY id LIMIT 1").fetchone()
        if first and first[0]==user_id:row=db.execute("SELECT data FROM app_preferences WHERE key='display_time'").fetchone()
    return json.loads(row[0]) if row else {'timezone':'WIB','brokerOffsets':{}}
def write(db,data,user_id=None):
    mode=data.get('timezone');offsets=data.get('brokerOffsets',{})
    if mode not in ('WIB','BROKER','UTC') or not isinstance(offsets,dict):raise ValueError('Zona waktu tidak valid.')
    clean={}
    for key,value in offsets.items():
        if len(str(key))>40:raise ValueError('Identitas broker tidak valid.')
        if value in ('',None):continue
        try:
            number=int(value)
            if float(value)!=number:raise ValueError()
        except (ValueError,TypeError):raise ValueError('Offset broker harus berupa menit bulat.') from None
        if not -720<=number<=840:raise ValueError('Offset broker harus antara UTC−12 dan UTC+14.')
        clean[str(key)]=number
    result={'timezone':mode,'brokerOffsets':clean}
    key='display_time' if user_id is None else 'display_time:'+str(user_id)
    db.execute('INSERT INTO app_preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET data=excluded.data',(key,json.dumps(result)))
    return result
