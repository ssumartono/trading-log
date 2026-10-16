"""Strategy playbook; independent of MT5 synchronization state."""
import json
from datetime import datetime,timezone

AQR='https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing'
RANGE='https://www.fidelity.com/learning-center/trading-investing/trading/range-trading'
BANDS='https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands'
SEEDS=[
 {'name':'Trend Following','whenApplied':'Saat tren terarah dan struktur higher-high/higher-low atau sebaliknya. Hindari pasar bolak-balik tanpa arah.','timeframe':'H4 / D1; evaluasi H1','rules':'Tentukan arah tren dari struktur harga dan kemiringan MA. Tunggu pullback serta konfirmasi searah tren; keluar bila struktur tren batal. Parameter MA dan stop wajib diuji dahulu.','risk':'Stop di luar swing invalidasi; ukuran posisi mengikuti batas risiko akun. Waspadai whipsaw dan biaya.','evidence':'Keluarga trend following memiliki bukti historis lintas pasar. Aturan pullback/MA contoh ini belum diuji pada akun Anda; riset bukan validasi scalping.','source':AQR},
 {'name':'Breakout & Retest','whenApplied':'Setelah konsolidasi dengan batas jelas; tunggu penutupan di luar level dan retest yang bertahan. Hindari spread melebar.','timeframe':'H1 / H4; konfirmasi M15','rules':'Tandai batas range sebelum breakout. Tunggu candle close di luar batas, lalu retest yang tidak kembali menetap dalam range. Batal bila harga masuk kembali; target struktur berikutnya.','risk':'Stop melewati level invalidasi retest. Risiko false breakout dan slippage; jangan mengejar candle panjang.','evidence':'Setup teknikal terdokumentasi sebagai turunan breakout/range. Sumber menjelaskan konsep range; varian retest ini belum terbukti pada akun Anda.','source':RANGE},
 {'name':'Support & Resistance','whenApplied':'Saat harga bergerak dalam range berulang dengan support/resistance jelas dan belum ada breakout terkonfirmasi.','timeframe':'H1 / H4; konfirmasi M15','rules':'Petakan zona support/resistance dari beberapa reaksi historis. Tunggu penolakan pada batas range; evaluasi target tengah atau sisi berlawanan. Batalkan saat breakout terkonfirmasi.','risk':'Stop di luar batas range; hindari melawan tren kuat. Periksa ruang target setelah spread/komisi.','evidence':'Range trading dan penggunaan support/resistance terdokumentasi; keberhasilan bergantung kondisi pasar dan parameter. Belum dibuktikan dari log akun ini.','source':RANGE},
 {'name':'Bollinger Bands Mean Reversion','whenApplied':'Pasar sideways dengan band relatif datar; bukan tren kuat yang terus menempel band.','timeframe':'H1 / H4; parameter awal BB 20, 2','rules':'Band hanya konteks volatilitas. Tunggu penolakan dan harga kembali masuk band, lalu konfirmasi sebelum entry. Evaluasi mean/MA sebagai target awal; sentuhan band saja bukan sinyal.','risk':'Stop pada invalidasi swing; batalkan jika terjadi breakout/tren kuat. Parameter 20,2 merupakan contoh, perlu backtest.','evidence':'Indikator dan interpretasinya terdokumentasi. Dokumentasi indikator bukan bukti profit strategi atau jaminan performa akun.','source':BANDS}
]

def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS trading_strategies(id INTEGER PRIMARY KEY AUTOINCREMENT,data TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1)')
    db.execute('CREATE TABLE IF NOT EXISTS strategy_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    if not db.execute("SELECT 1 FROM strategy_meta WHERE key='seed_v1'").fetchone():
        stamp=datetime.now(timezone.utc).isoformat()
        for row in SEEDS:db.execute('INSERT INTO trading_strategies(data) VALUES(?)',(json.dumps(dict(row,status='Aktif',appliedAt='',createdAt=stamp,updatedAt=stamp)),))
        db.execute("INSERT INTO strategy_meta VALUES('seed_v1','done')")

def listing(db,state):
    result=[]
    for id,data,revision in db.execute('SELECT id,data,revision FROM trading_strategies ORDER BY id DESC'):
        row=json.loads(data);logs=[r for r in (state or {}).get('records',[]) if r.get('strategy')==row['name']]
        dates=sorted(r['date']+'T'+r.get('time','00:00') for r in logs)
        result.append(dict(row,id=id,revision=revision,usageCount=len(logs),firstApplied=dates[0] if dates else None,lastApplied=dates[-1] if dates else None))
    return result

def write(db,data,state):
    id=data.get('id');old=db.execute('SELECT data,revision FROM trading_strategies WHERE id=?',(id,)).fetchone() if id else None
    if id and not old:raise ValueError('Strategi tidak ditemukan.')
    if old and data.get('revision')!=old[1]:raise ValueError('Strategi telah berubah. Muat ulang sebelum menyimpan.')
    previous=json.loads(old[0]) if old else {}
    used=any(r.get('strategy')==previous.get('name') for r in (state or {}).get('records',[])) if old else False
    if data.get('delete'):
        if not old:raise ValueError('Strategi tidak ditemukan.')
        if used:raise ValueError('Strategi sudah digunakan pada log. Nonaktifkan agar riwayat tetap terjaga.')
        db.execute('DELETE FROM trading_strategies WHERE id=?',(id,));return {'deleted':True}
    limits={'name':120,'whenApplied':2000,'timeframe':160,'rules':8000,'risk':4000,'evidence':4000,'source':1000,'appliedAt':16,'status':20}
    row={k:str(data.get(k,'')).strip() for k in limits}
    if any(len(row[k])>n for k,n in limits.items()):raise ValueError('Isi strategi terlalu panjang.')
    if not row['name'] or not row['whenApplied'] or not row['rules']:raise ValueError('Nama, kapan diaplikasikan, dan aturan wajib diisi.')
    if row['status'] not in ('Aktif','Nonaktif'):raise ValueError('Status tidak valid.')
    if row['appliedAt']:
        try:datetime.strptime(row['appliedAt'],'%Y-%m-%dT%H:%M')
        except ValueError:raise ValueError('Tanggal penerapan tidak valid.') from None
    from urllib.parse import urlparse
    if row['source'] and (urlparse(row['source']).scheme!='https' or not urlparse(row['source']).hostname):raise ValueError('Sumber harus URL HTTPS.')
    for other_id,other_data in db.execute('SELECT id,data FROM trading_strategies'):
        if other_id!=id and json.loads(other_data)['name'].casefold()==row['name'].casefold():raise ValueError('Nama strategi sudah ada.')
    if used and previous['name']!=row['name']:raise ValueError('Nama strategi yang sudah dipakai log tidak dapat diubah. Edit aturannya atau buat strategi baru.')
    stamp=datetime.now(timezone.utc).isoformat();row.update(createdAt=previous.get('createdAt',stamp),updatedAt=stamp)
    if old:db.execute('UPDATE trading_strategies SET data=?,revision=revision+1 WHERE id=?',(json.dumps(row),id))
    else:id=db.execute('INSERT INTO trading_strategies(data) VALUES(?)',(json.dumps(row),)).lastrowid
    return dict(row,id=id,revision=old[1]+1 if old else 1)
