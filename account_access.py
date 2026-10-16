"""User/account ownership and server-side projections of the shared import store."""
import copy
import json


def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS broker_owners(broker_id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES app_users(id))')
    db.execute('CREATE TABLE IF NOT EXISTS user_account_settings(user_id INTEGER PRIMARY KEY REFERENCES app_users(id),data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS account_access_meta(key TEXT PRIMARY KEY)')
    if not db.execute("SELECT 1 FROM account_access_meta WHERE key='permissions_v1'").fetchone():
        for name,raw in db.execute('SELECT name,permissions FROM app_roles').fetchall():
            rights=json.loads(raw)
            if name=='Trader' or 'settings.manage' in rights:
                rights=sorted(set(rights)|{'broker.manage'}|({'sync.manage'} if name=='Trader' else set()))
                db.execute('UPDATE app_roles SET permissions=? WHERE name=?',(json.dumps(rights),name))
        db.execute("INSERT INTO account_access_meta VALUES('permissions_v1')")
    migrate_legacy_owners(db)


def migrate_legacy_owners(db,state=None):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='account_access_meta'").fetchone():return
    if db.execute("SELECT 1 FROM account_access_meta WHERE key='ownership_v1'").fetchone():return
    # Legacy accounts belong to the first administrator, never to the next visitor.
    admin=db.execute("SELECT id FROM app_users WHERE role='Administrator' ORDER BY id LIMIT 1").fetchone()
    if not admin:return
    if state is None:
        row=db.execute('SELECT data FROM state WHERE id=1').fetchone()
        state=json.loads(row[0]) if row else None
    if state is not None:
        for broker in state.get('brokers',[]):
            db.execute('INSERT OR IGNORE INTO broker_owners VALUES(?,?)',(str(broker['id']),admin[0]))
        db.execute("INSERT INTO account_access_meta VALUES('ownership_v1')")


def ids(db,user):
    return {r[0] for r in db.execute('SELECT broker_id FROM broker_owners WHERE user_id=?',(user['id'],))}


def require_broker(db,user,broker_id):
    if str(broker_id) not in ids(db,user):
        raise PermissionError('Akun trading bukan milik pengguna ini.')


def belongs(row,brokers):
    checks=[]
    if row.get('accountKey'):checks.append(row['accountKey'] in {b.get('accountKey') for b in brokers})
    if row.get('brokerId') is not None:checks.append(str(row['brokerId']) in {str(b['id']) for b in brokers})
    if row.get('broker'):checks.append(row['broker'] in {b['name'] for b in brokers})
    return bool(checks) and all(checks)


def view(db,state,user):
    if state is None:return None
    allowed=ids(db,user)
    result={k:copy.deepcopy(v) for k,v in state.items() if k not in ('brokers','records','funds')}
    result['brokers']=[copy.deepcopy(b) for b in state.get('brokers',[]) if str(b['id']) in allowed]
    keys={b.get('accountKey') for b in result['brokers'] if b.get('accountKey')}
    names={b['name'] for b in result['brokers']}
    def visible(row):
        checks=[]
        if row.get('accountKey'):checks.append(row['accountKey'] in keys)
        if row.get('brokerId') is not None:checks.append(str(row['brokerId']) in allowed)
        if row.get('broker'):checks.append(row['broker'] in names)
        return bool(checks) and all(checks)
    for name in ('records','funds'):
        result[name]=[copy.deepcopy(r) for r in state.get(name,[]) if visible(r)]
    row=db.execute('SELECT data FROM user_account_settings WHERE user_id=?',(user['id'],)).fetchone()
    settings=json.loads(row[0]) if row else state.get('settings',{})
    if str(settings.get('brokerId')) not in allowed:
        settings=copy.deepcopy(result['brokers'][0].get('integration',{})) if result['brokers'] else {}
        settings.setdefault('brokerId',str(result['brokers'][0]['id']) if result['brokers'] else 'new')
    selected=next((b for b in result['brokers'] if str(b['id'])==str(settings.get('brokerId'))),None)
    if selected and selected.get('integration'):settings=copy.deepcopy(selected['integration'])
    defaults={'enabled':False,'auto':False,'interval':'60','brokerId':'new','login':'','server':'','path':'C:/Program Files/MetaTrader 5/terminal64.exe','start':'2000-01-01','importTrades':True,'importFunds':True}
    result['settings']={**defaults,**settings}
    return result


def broker_view(db,user):
    brokers=[json.loads(row[0]) for row in db.execute("SELECT j.value FROM state, json_each(state.data,'$.brokers') AS j JOIN broker_owners AS o ON o.broker_id=CAST(json_extract(j.value,'$.id') AS TEXT) WHERE state.id=1 AND o.user_id=?",(user['id'],))]
    return {'brokers':brokers}


def validate_payload(db,user,data,current):
    allowed=ids(db,user);brokers={str(b['id']):b for b in current.get('brokers',[])}
    for part in (data,data.get('_base') or {}):
        for broker in part.get('brokers',[]):
            if str(broker['id']) not in allowed:raise PermissionError('Akun trading bukan milik pengguna ini.')
        for name in ('records','funds'):
            live={r['id']:r for r in current.get(name,[])}
            for row in part.get(name,[]):
                if row.get('sourceKey') and row.get('sourceKey')!=live.get(row['id'],{}).get('sourceKey'):
                    raise PermissionError('Identitas sumber log tidak dapat ditambahkan atau diubah manual.')
                if not belongs(row,list(brokers.values())):
                    raise PermissionError('Log dan mutasi harus terkait akun milik pengguna.')
        selected=part.get('settings',{}).get('brokerId','new')
        if selected not in ('new',None,'') and str(selected) not in allowed:
            raise PermissionError('Akun trading bukan milik pengguna ini.')


def combine(db,full,scoped,updated,user):
    result=dict(full)
    for name in ('records','funds','brokers'):
        visible={r['id'] for r in scoped[name]}
        hidden=[r for r in full[name] if r['id'] not in visible]
        hidden_ids={r['id'] for r in hidden}
        if any(r['id'] in hidden_ids for r in updated[name]):
            raise ValueError('ID data bertabrakan. Muat ulang lalu coba lagi.')
        result[name]=hidden+updated[name]
    for broker_id in {str(b['id']) for b in scoped['brokers']}-{str(b['id']) for b in updated['brokers']}:
        db.execute('DELETE FROM broker_owners WHERE broker_id=?',(broker_id,))
    db.execute('INSERT INTO user_account_settings VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data',(user['id'],json.dumps(updated['settings'])))
    # Background import reads each broker's integration, not another user's selection.
    return result


def note_visible(db,note,user):
    if note.get('brokerId') is not None and str(note['brokerId']) not in ids(db,user):return False
    if note.get('ownerUserId') is not None:return note['ownerUserId']==user['id']
    if note.get('brokerId') is not None:return str(note['brokerId']) in ids(db,user)
    admin=db.execute("SELECT id FROM app_users WHERE role='Administrator' ORDER BY id LIMIT 1").fetchone()
    return bool(admin and admin[0]==user['id'])
