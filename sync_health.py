"""Independent balance checkpoints and read-only synchronization health."""
import json
from datetime import datetime,timezone

def net(deal):return sum(float(deal.get(k,0)) for k in ('profit','commission','swap','fee'))
def checkpoint(balance,raw,stamp,kind):return {'balance':float(balance),'netByTicket':{str(d['ticket']):net(d) for d in raw},'maxTime':max([int(d['time']) for d in raw]+[0]),'recordedAt':stamp,'kind':kind}
def reconcile(baseline,raw,broker,state,observed,new_baseline=False):
    expected=baseline['balance']+sum(net(d)-baseline['netByTicket'].get(str(d['ticket']),0) for d in raw)
    backfill=[str(d['ticket']) for d in raw if str(d['ticket']) not in baseline['netByTicket'] and d['time']<=baseline['maxTime']]
    key=broker['accountKey'];trade_keys={r.get('sourceKey') for r in state['records']};fund_keys={f.get('sourceKey') for f in state['funds']}
    missing_trades=[str(d['ticket']) for d in raw if d['type'] in (0,1) and key+':'+str(d['ticket']) not in trade_keys]
    missing_funds=[str(d['ticket']) for d in raw if d['type'] not in (0,1) and key+':'+str(d['ticket']) not in fund_keys]
    projected=broker['initial']+sum(r['profit'] for r in state['records'] if r.get('broker')==broker['name'])+sum(f.get('signedAmount',f['amount'] if f['type']=='Deposit' else -f['amount']) for f in state['funds'] if f['brokerId']==broker['id'])
    difference=round(float(observed)-expected,2);projection_diff=round(float(observed)-projected,2)
    status='baseline_created' if new_baseline else 'matched'
    if abs(difference)>.01 or abs(projection_diff)>.01 or missing_trades or missing_funds or backfill:status='needs_review'
    return {'status':status,'observedBalance':round(observed,2),'expectedBalance':round(expected,2),'balanceDifference':difference,'projectedBalance':round(projected,2),'projectedDifference':projection_diff,'missingTradeCount':len(missing_trades),'missingFundCount':len(missing_funds),'missingTickets':(missing_trades+missing_funds)[:20],'historicalBackfillCount':len(backfill),'baselineRecordedAt':baseline['recordedAt'],'baselineKind':baseline['kind'],'note':'Checkpoint saldo dipertahankan; saldo awal tidak diubah otomatis untuk menutupi selisih. Cocok bukan jaminan seluruh riwayat broker tersedia; backfill historis perlu ditinjau.'}

def update_status(db,broker_id,changes):
    row=db.execute('SELECT data FROM sync_status WHERE broker_id=?',(str(broker_id),)).fetchone();status=json.loads(row[0]) if row else {}
    status.update(changes);status['brokerId']=str(broker_id)
    db.execute('INSERT INTO sync_status VALUES(?,?) ON CONFLICT(broker_id) DO UPDATE SET data=excluded.data',(str(broker_id),json.dumps(status)))
    return status
