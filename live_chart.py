from datetime import datetime,timezone

def read_live_chart(state,data):
    requested=data.get('indicators',[])
    if not isinstance(requested,list) or len(requested)>8:raise ValueError('Maksimal 8 indikator per chart.')
    specs=[]
    for item in requested:
        if not isinstance(item,dict) or item.get('type')!='range-oscillator':raise ValueError('Indikator belum mendukung Live Chart.')
        length=item.get('length',50);multiplier=item.get('multiplier',2)
        if type(length) is not int or not 2<=length<=500 or type(multiplier) not in (int,float) or not 0.1<=multiplier<=20:raise ValueError('Parameter indikator tidak valid.')
        ident=item.get('id')
        if not isinstance(ident,str) or len(ident)>80 or any(x['id']==ident for x in specs):raise ValueError('Identitas indikator tidak valid.')
        specs.append(dict(id=ident,length=length,multiplier=multiplier))
    from time_rules import utc_timestamp,validate_time_config
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
        tick=mt5.symbol_info_tick(symbol);rates=mt5.copy_rates_from_pos(symbol,frames[frame],0,3000 if specs else 300);positions=mt5.positions_get(symbol=symbol)
        if tick is None or tick.time<=0:raise ValueError('Harga belum tersedia pada simbol ini.')
        if rates is None or len(rates)==0:raise ValueError('Candle belum tersedia. Buka chart simbol di terminal MT5 lalu coba lagi.')
        if positions is None:raise ValueError('Posisi terbuka tidak dapat dibaca.')
        candles=sorted({utc_timestamp(r['time'],config):{'time':utc_timestamp(r['time'],config),'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close']),'volume':int(r['tick_volume'])} for r in rates}.values(),key=lambda r:r['time'])
        from range_oscillator import calculate
        indicators=[]
        for spec in specs:
            result=calculate(candles,point=info.point,length=spec['length'],multiplier=spec['multiplier'])
            result['id']=spec['id'];result['type']='range-oscillator'
            result['points']=[p for p in result['points'] if p['time']>=candles[-300:][0]['time']]
            result['signals']=[p for p in result['signals'] if p['time']>=candles[-300:][0]['time']]
            indicators.append(result)
        candles=candles[-300:]
        tick_age=datetime.now(timezone.utc).timestamp()-utc_timestamp(tick.time,config)
        return {'symbol':symbol,'timeframe':frame,'symbols':visible,'digits':info.digits,'point':info.point,'bid':tick.bid,'ask':tick.ask,'spread':round(tick.ask-tick.bid,info.digits),'tickTime':utc_timestamp(tick.time,config),'rawTickTime':tick.time,'tickAgeSeconds':round(tick_age),'sourceOffsetMinutes':validate_time_config(config),'timestampMode':config.get('timestampMode','utc'),'timeConfirmed':bool(config.get('timeConfirmed',False)),'fetchedAt':datetime.now(timezone.utc).isoformat(),
        'candles':candles,'indicators':indicators,'account':{'balance':account.balance,'equity':account.equity,'floatingProfit':account.profit,'currency':account.currency},
        'positions':[{'ticket':str(p.ticket),'side':'Buy' if p.type==0 else 'Sell','volume':p.volume,'entry':p.price_open,'sl':p.sl,'tp':p.tp,'profit':p.profit} for p in positions],
        'timeNote':'Waktu dinormalisasi sesuai Pengaturan broker dan ditampilkan WIB. Candle terakhir masih berjalan.' if config.get('timeConfirmed') else 'Basis waktu broker belum dikonfirmasi di Pengaturan; tampilan sementara mengasumsikan UTC.'}
    finally:mt5.shutdown()
