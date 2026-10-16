"""Explicit broker timestamps -> UTC storage -> WIB presentation."""
from datetime import datetime,timezone,timedelta
WIB=timezone(timedelta(hours=7))
def validate_time_config(config):
    mode=config.get('timestampMode','utc')
    if mode not in ('utc','server'):raise ValueError('Basis waktu harus UTC atau waktu server broker.')
    try:offset=int(config.get('serverUtcOffsetMinutes',0))
    except (ValueError,TypeError):raise ValueError('Offset broker harus berupa menit.') from None
    if offset < -720 or offset > 840:raise ValueError('Offset broker harus antara UTC−12 dan UTC+14.')
    return offset if mode=='server' else 0
def utc_timestamp(raw,config):return int(raw)-validate_time_config(config)*60
def wib_fields(raw,config):
    stamp=datetime.fromtimestamp(utc_timestamp(raw,config),timezone.utc).astimezone(WIB)
    return {'date':stamp.strftime('%Y-%m-%d'),'time':stamp.strftime('%H:%M'),'timestampUtc':utc_timestamp(raw,config),'sourceTime':int(raw),'timeBasis':config.get('timestampMode','utc'),'timeConfirmed':bool(config.get('timeConfirmed',False))}
