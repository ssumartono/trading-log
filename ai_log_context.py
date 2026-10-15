"""Bounded, account-scoped, read-only retrieval from the SQLite application state."""
import re
from datetime import datetime,timezone,timedelta

def retrieve_logs(state,data,now=None):
    broker=next((b for b in state.get('brokers',[]) if str(b['id'])==str(data.get('brokerId'))),None)
    if broker is None:raise ValueError('Pilih akun untuk membaca log SQLite.')
    today=(now or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=7))).date()
    period=str(data.get('logPeriod','day'));ticket=str(data.get('logTicket','')).strip()
    if not ticket:
        match=re.search(r'\b(?:ticket|tiket|order|posisi)\s*(?:nomor|no\.?|#|:)?\s*(\d{5,})\b',str(data.get('message') or data.get('prompt') or ''),re.I)
        if match:ticket=match.group(1)
    start=end=None
    if ticket:
        if not ticket.isdigit() or len(ticket)>30:raise ValueError('Ticket harus berupa angka.')
    elif period=='day':
        start=end=str(data.get('eventDate') or today.isoformat())[:10]
    elif period in ('today','7','30','90'):
        end=today.isoformat();start=(today-timedelta(days=0 if period=='today' else int(period)-1)).isoformat()
    elif period=='custom':start=str(data.get('logStart',''));end=str(data.get('logEnd',''))
    elif period!='all':raise ValueError('Periode log tidak valid.')
    if start is not None:
        try:
            a=datetime.fromisoformat(start).date();b=datetime.fromisoformat(end).date()
            if a>b:raise ValueError()
        except (ValueError,TypeError):raise ValueError('Rentang tanggal log tidak valid.') from None
    symbol=str(data.get('logSymbol','')).strip()
    rows=[r for r in state.get('records',[]) if (r.get('accountKey')==broker.get('accountKey') if r.get('accountKey') and broker.get('accountKey') else r.get('broker')==broker['name']) and (not start or start<=r['date']<=end) and (not symbol or r['symbol']==symbol) and (not ticket or ticket in (str(r.get('ticket','')),str(r.get('orderId','')),str(r.get('positionId',''))))]
    rows.sort(key=lambda r:(r['date'],r['time'],r['id']),reverse=True)
    positive=sum(r['profit'] for r in rows if r['profit']>0);negative=-sum(r['profit'] for r in rows if r['profit']<0)
    def groups(field):
        result={}
        for row in rows:
            key=row.get(field) or 'Belum diisi';group=result.setdefault(str(key),{'count':0,'netProfit':0});group['count']+=1;group['netProfit']=round(group['netProfit']+row['profit'],2)
        return dict(sorted(result.items(),key=lambda kv:-kv[1]['count'])[:30])
    # Keep source references small while always including the best and worst log.
    chosen={r['id']:r for r in rows[:34]}
    for row in sorted(rows,key=lambda r:r['profit'])[:3]+sorted(rows,key=lambda r:r['profit'],reverse=True)[:3]:chosen[row['id']]=row
    allowed=('id','date','time','symbol','side','status','ticket','orderId','positionId','lot','price','entry','exit','profit','commission','swap','fee','strategy','indicator','note')
    details=[{k:(str(r[k])[:1500] if k in ('strategy','indicator','note') else r[k]) for k in allowed if k in r} for r in sorted(chosen.values(),key=lambda r:(r['date'],r['time'],r['id']),reverse=True)]
    return {'source':'SQLite · read-only','retrievedAt':datetime.now(timezone.utc).isoformat(),'filters':{'period':period,'from':start,'to':end,'symbol':symbol or None,'ticket':ticket or None,'ticketOverridesPeriod':bool(ticket)},'logCount':len(rows),'netProfit':round(positive-negative,2),'profitLogs':sum(r['profit']>0 for r in rows),'lossLogs':sum(r['profit']<0 for r in rows),'flatLogs':sum(r['profit']==0 for r in rows),'profitFactor':round(positive/negative,3) if negative else None,'symbols':groups('symbol'),'strategies':groups('strategy'),'indicators':groups('indicator'),'details':details,'detailCount':len(details),'detailsTruncated':len(rows)>len(details),'interpretation':'Ringkasan memakai semua log hasil filter; detail maksimal 40 log (terbaru + terbaik/terburuk). Catatan detail dipotong 1500 karakter. Per log/deal, bukan per posisi. P/L sudah termasuk biaya. Jika kosong, nyatakan tidak ditemukan. Penyebab trading hanya boleh berdasarkan catatan/fakta; jangan mengarang.'}
