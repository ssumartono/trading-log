from datetime import datetime,timezone

def read_live_chart(state,data):
    import MetaTrader5 as mt5
    broker=next((b for b in state['brokers'] if str(b['id'])==str(data.get('brokerId'))),None)
    if not broker or not broker.get('integration'):raise ValueError('Pilih akun yang memiliki integrasi MT5.')
    config=broker['integration'];frame=data.get('timeframe','M15')
    frames={'M1':mt5.TIMEFRAME_M1,'M5':mt5.TIMEFRAME_M5,'M15':mt5.TIMEFRAME_M15,'M30':mt5.TIMEFRAME_M30,'H1':mt5.TIMEFRAME_H1,'H4':mt5.TIMEFRAME_H4,'D1':mt5.TIMEFRAME_D1}
    if frame not in frames:raise ValueError('Timeframe tidak valid.')
    try:
        if not mt5.initialize(config['path'],timeout=15000):raise ValueError('Koneksi terminal MT5 gagal.')
        account=mt5.account_info();terminal=mt5.terminal_info()
        if not account or not terminal or not terminal.connected:raise ValueError('Terminal MT5 sedang tidak terhubung.')
        if str(account.login)!=str(config['login']) or account.server!=config['server']:raise ValueError('Akun MT5 aktif berbeda. Login terminal ke akun yang dipilih agar chart sesuai.')
        symbols=mt5.symbols_get()
        if symbols is None:raise ValueError('Daftar simbol tidak dapat dibaca.')
        visible=[s.name for s in symbols if s.visible]
        symbol=str(data.get('symbol','')).strip() or next((s for s in visible if s.upper().startswith('XAUUSD')),visible[0] if visible else '')
        info=mt5.symbol_info(symbol)
        if not info:raise ValueError('Simbol tidak ditemukan. Gunakan nama simbol yang persis sama dengan MT5.')
        if not info.visible:raise ValueError('Tampilkan simbol ini di Market Watch MT5 terlebih dahulu.')
        tick=mt5.symbol_info_tick(symbol);rates=mt5.copy_rates_from_pos(symbol,frames[frame],0,300);positions=mt5.positions_get(symbol=symbol)
        if tick is None or tick.time<=0:raise ValueError('Harga belum tersedia pada simbol ini.')
        if rates is None or len(rates)==0:raise ValueError('Candle belum tersedia. Buka chart simbol di terminal MT5 lalu coba lagi.')
        if positions is None:raise ValueError('Posisi terbuka tidak dapat dibaca.')
        candles=sorted({int(r['time']):{'time':int(r['time']),'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close']),'volume':int(r['tick_volume'])} for r in rates}.values(),key=lambda r:r['time'])
        return {'symbol':symbol,'timeframe':frame,'symbols':visible,'digits':info.digits,'point':info.point,'bid':tick.bid,'ask':tick.ask,'spread':round(tick.ask-tick.bid,info.digits),'tickTime':tick.time,'fetchedAt':datetime.now(timezone.utc).isoformat(),
        'candles':candles,'account':{'balance':account.balance,'equity':account.equity,'floatingProfit':account.profit,'currency':account.currency},
        'positions':[{'side':'Buy' if p.type==0 else 'Sell','volume':p.volume,'entry':p.price_open,'sl':p.sl,'tp':p.tp,'profit':p.profit} for p in positions],
        'timeNote':'Sumbu waktu memakai timestamp mentah server MT5. Offset broker dapat berbeda dari WIB. Candle terakhir masih berjalan.'}
    finally:mt5.shutdown()
