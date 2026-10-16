let liveChartCleanup=null;
function livePositionLines(positions,colors){
 const lines=[];
 positions.forEach((p,index)=>{
  const label=(p.ticket?'#'+p.ticket:'#'+(index+1))+' · '+p.side+' '+p.volume;
  for(const [key,title,color,style] of [['entry',label,p.side==='Buy'?colors.gain:colors.loss,2],['sl','SL '+label,colors.loss,1],['tp','TP '+label,colors.gain,1]]){
   const price=Number(p[key]);if(!Number.isFinite(price)||price<=0)continue;
   lines.push({price,color,lineWidth:key==='entry'?1:2,lineStyle:style,axisLabelVisible:true,lineVisible:true,title});
  }
 });return lines;
}
function livePositionAutoscale(original,positions){
 if(!original?.priceRange)return original;
 const levels=positions.flatMap(p=>[p.entry,p.sl,p.tp]).map(Number).filter(p=>Number.isFinite(p)&&p>0);
 if(!levels.length)return original;
 return {...original,priceRange:{...original.priceRange,minValue:Math.min(original.priceRange.minValue,...levels),maxValue:Math.max(original.priceRange.maxValue,...levels)}};
}
// Palette from indicators/RangeOscillator.mq5, including the local heat buckets.
function rangeOscillatorColor(index,background,shading=false){
 const hex=String(background||'#ffffff').replace('#','');
 const bg=/^[0-9a-f]{3}$/i.test(hex)?[...hex].map(c=>parseInt(c+c,16)):/^[0-9a-f]{6}$/i.test(hex)?[0,2,4].map(i=>parseInt(hex.slice(i,i+2),16)):(String(background).match(/[\d.]+/g)||[255,255,255]).slice(0,3).map(Number);
 const blend=(front,opacity)=>front.map((value,i)=>Math.round(value*opacity+bg[i]*(1-opacity)));
 let color=index===23?[9,255,0]:index===24?[255,0,0]:[0,0,255];
 if(index>=0&&index<22)color=blend(index<11?[0,128,0]:[128,0,0],.21+.079*(index%11));
 if(shading)color=blend(color,.25);
 return 'rgb('+color.join(',')+')';
}
function rangeOscillatorAutoscale(original){
 const range=original?.priceRange||{minValue:-100,maxValue:100};
 return {...(original||{}),priceRange:{minValue:Math.min(-100,range.minValue),maxValue:Math.max(100,range.maxValue)}};
}
function rangeOscillatorSeries(data,background){
 const points=data?.points||[];
 return {line:points.map(p=>Number.isFinite(p.value)?{time:p.time,value:p.value,color:rangeOscillatorColor(p.colorIndex,background)}:{time:p.time}),
 shading:points.map(p=>Number.isFinite(p.value)?{time:p.time,value:p.value,color:rangeOscillatorColor(p.colorIndex,background,true)}:{time:p.time}),
 markers:(data?.signals||[]).map(s=>({time:s.time,position:'atPriceMiddle',price:s.price,shape:s.side==='Buy'?'arrowUp':'arrowDown',color:s.side==='Buy'?'#09ff00':'#ff0000',text:s.side}))};
}
function renderLiveChart(root,detail,broker){
 appTimeBrokerId=broker?.id??null;
 setPageHeader('Live Chart',broker);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 if(!broker){root.innerHTML='<p class="note">Tambahkan akun MT5 melalui Pengaturan untuk membuka Live Chart.</p>';detail.innerHTML='';return}
 const selection=readIndicatorSelection(broker.id);
 let prefs={symbol:'',timeframe:'M15'};try{prefs={...prefs,...JSON.parse(localStorage.getItem('livechart-'+broker.id)||'{}')}}catch{}
 root.innerHTML='<div class="live-toolbar"><label>Simbol<input id="lcsymbol" list="lcsymbols" value="'+esc(prefs.symbol)+'" placeholder="Otomatis dari MT5" maxlength="80"><datalist id="lcsymbols"></datalist></label><label>Timeframe<select id="lcframe">'+['M1','M5','M15','M30','H1','H4','D1'].map(f=>'<option '+(f===prefs.timeframe?'selected':'')+'>'+f+'</option>').join('')+'</select></label><button id="lcload">Tampilkan</button><button id="lcreset">Reset zoom</button><label class="live-toggle"><input id="lcauto" type="checkbox" checked> Auto · 5 detik</label></div><div class="live-quote" id="lcquote">'+esc(broker.name)+'</div><p id="lcstatus" class="muted" role="status">Menghubungkan ke MT5…</p><div id="lcohlc" class="muted" style="min-height:20px;margin:8px 0"></div><div class="live-toolbar"><button id="lcindicators">Indicators Library</button><button id="lcclear">Hapus semua indikator</button></div><div id="lcactiveindicators"></div><div id="lccanvas" class="live-canvas" role="img" aria-label="Candlestick harga market MT5"></div><p class="notice">Data dari terminal MT5 akun terpilih · polling 5 detik · candle terakhir masih berjalan. Sumbu waktu dan tooltip: '+esc(appTimeLabel(broker.id))+' · diatur melalui Broker Time System.</p><p class="muted">Chart menggunakan <a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView Lightweight Charts™</a> · Copyright (c) 2025 TradingView, Inc.</p>';
 detail.innerHTML='<h2 style="font-size:17px">Akun aktif</h2><p class="note">'+esc(broker.name)+'</p><p class="notice">Terminal harus login ke akun yang sama. Chart hanya membaca data dan tidak mengeksekusi order.</p>';
 const $=id=>root.querySelector('#'+id),box=$('lccanvas');let disposed=false,timer=null,controller=null,chart=null,candles=null,indicatorPanels=[],latest=null,lastTime=null,busy=false,first=true,priceLines=[];
 box.style.height=(Math.max(460,Math.min(760,innerHeight*.72))+selection.length*180)+'px';
 let gallery=null;
 function attachmentsPanel(){gallery=mountAttachments(detail,'chart',broker.id,()=>prefs.symbol+' · '+prefs.timeframe,()=>{if(!chart)throw Error('Chart belum tersedia');return chart.takeScreenshot()})}
 box.oncontextmenu=e=>{e.preventDefault();document.getElementById('chart-attachment-menu')?.remove();const menu=document.createElement('div');menu.id='chart-attachment-menu';menu.style.cssText='position:fixed;z-index:10000;background:var(--surface);padding:10px;border:1px solid var(--line);border-radius:8px;display:grid;gap:6px;left:'+Math.min(e.clientX,innerWidth-220)+'px;top:'+Math.min(e.clientY,innerHeight-160)+'px';menu.innerHTML='<button>Tangkap chart sebagai lampiran</button><button>Unggah screenshot</button><button>Lihat lampiran akun</button>';menu.querySelectorAll('button').forEach((b,i)=>b.onclick=()=>{menu.remove();if(i===0)gallery?.capture();else if(i===1)gallery?.upload();else gallery?.show()});document.body.append(menu);setTimeout(()=>document.addEventListener('pointerdown',event=>{if(!menu.contains(event.target))menu.remove()},{once:true}),0)};
 attachmentsPanel();
 function colors(){const css=getComputedStyle(document.documentElement);return {surface:css.getPropertyValue('--surface').trim(),text:css.getPropertyValue('--text').trim(),line:css.getPropertyValue('--line').trim(),gain:css.getPropertyValue('--gain').trim(),loss:css.getPropertyValue('--loss').trim()}}
 function theme(){if(!chart)return;const c=colors();chart.applyOptions({layout:{background:{type:'solid',color:c.surface},textColor:c.text,fontFamily:'Arial'},grid:{vertLines:{color:c.line},horzLines:{color:c.line}},rightPriceScale:{borderColor:c.line},timeScale:{borderColor:c.line}});candles.applyOptions({upColor:c.gain,downColor:c.loss,wickUpColor:c.gain,wickDownColor:c.loss});if(latest)drawOscillator(true)}
 function ohlc(bar){$('lcohlc').textContent=bar?'O '+bar.open+'   H '+bar.high+'   L '+bar.low+'   C '+bar.close+'':''}
 function drawOscillator(reset=false){
   if(!latest)return;
   indicatorPanels.forEach(panel=>{
    const result=latest.indicators?.find(x=>x.id===panel.spec.id),data=rangeOscillatorSeries(result,colors().surface);
    if(reset){panel.shading.setData(data.shading);panel.line.setData(data.line)}
    else data.line.forEach((point,i)=>{if(point.time>=lastTime){panel.line.update(point);panel.shading.update(data.shading[i])}});
    panel.markers.setMarkers(data.markers);
    const value=result?.points.at(-1)?.value;
    $('indicator-value-'+panel.spec.id).textContent=Number.isFinite(value)?value.toFixed(1):'Menunggu riwayat candle';
   });
 }
 function build(){
   if(!window.LightweightCharts)throw Error('Library chart belum termuat. Refresh halaman.');
   chart=LightweightCharts.createChart(box,{autoSize:true,height:Math.max(460,Math.min(760,innerHeight*.72)),layout:{attributionLogo:true},timeScale:{timeVisible:true,secondsVisible:false,rightOffset:8,tickMarkFormatter:time=>appFormatTime(Number(time)*1000,{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'},broker.id)},crosshair:{mode:LightweightCharts.CrosshairMode.Normal},localization:{timeFormatter:time=>appFormatTime(Number(time)*1000,{},broker.id)+' '+appTimeLabel(broker.id)}});
   candles=chart.addSeries(LightweightCharts.CandlestickSeries,{borderVisible:false,autoscaleInfoProvider:original=>livePositionAutoscale(original(),latest?.positions||[])});
   indicatorPanels=selection.map((spec,index)=>{
    const pane=index+1;
    const shading=chart.addSeries(LightweightCharts.HistogramSeries,{priceFormat:{type:'price',precision:1,minMove:.1},lastValueVisible:false,priceLineVisible:false},pane);
    const line=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:2,priceFormat:{type:'price',precision:1,minMove:.1},priceLineVisible:false,title:'RO '+spec.length+' × '+spec.multiplier,autoscaleInfoProvider:original=>rangeOscillatorAutoscale(original())},pane);
    line.priceScale().applyOptions({scaleMargins:{top:.12,bottom:.12}});
    for(const value of [100,0,-100])line.createPriceLine({price:value,color:'#808080',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dotted,axisLabelVisible:true,title:String(value)});
    chart.panes()[pane].setHeight(180);
    return {spec,line,shading,markers:LightweightCharts.createSeriesMarkers(candles,[])};
   });
   chart.priceScale('right').applyOptions({scaleMargins:{top:.08,bottom:.08}});
   chart.subscribeCrosshairMove(param=>{const bar=param.seriesData.get(candles);ohlc(bar||latest?.candles.at(-1));indicatorPanels.forEach(panel=>{const value=param.time?param.seriesData.get(panel.line)?.value:latest?.indicators?.find(x=>x.id===panel.spec.id)?.points.at(-1)?.value;$('indicator-value-'+panel.spec.id).textContent=Number.isFinite(value)?value.toFixed(1):'—'})});
   theme();
 }
 const observer=new MutationObserver(theme);observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
 liveChartCleanup=()=>{disposed=true;document.getElementById('chart-attachment-menu')?.remove();clearTimeout(timer);controller?.abort();observer.disconnect();indicatorPanels.forEach(p=>p.markers.detach());chart?.remove();chart=null};
 function schedule(){clearTimeout(timer);if(!disposed&&$('lcauto')?.checked)timer=setTimeout(()=>load(false),5000)}
 async function load(reset){if(disposed||busy)return;if(document.hidden&&!reset){schedule();return}busy=true;controller=new AbortController();const requested={brokerId:broker.id,symbol:reset?$('lcsymbol').value.trim():prefs.symbol,timeframe:reset?$('lcframe').value:prefs.timeframe,indicators:selection};$('lcload').disabled=true;
 try{const response=await fetch('/api/chart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(requested),signal:controller.signal});const data=await response.json();if(!response.ok)throw Error(data.error||'Market tidak dapat dibaca.');if(disposed)return;
 const changed=latest&&(latest.symbol!==data.symbol||latest.timeframe!==data.timeframe);latest=data;prefs={symbol:data.symbol,timeframe:data.timeframe};try{localStorage.setItem('livechart-'+broker.id,JSON.stringify(prefs))}catch{}$('lcsymbol').value=data.symbol;$('lcsymbols').innerHTML=data.symbols.map(s=>'<option value="'+esc(s)+'">').join('');if(!chart)build();candles.applyOptions({priceFormat:{type:'price',precision:data.digits,minMove:data.point}});
 const bars=data.candles.map(({time,open,high,low,close})=>({time,open,high,low,close})),c=colors();
 const resetSeries=first||changed||reset;
 if(resetSeries){candles.setData(bars);chart.timeScale().setVisibleLogicalRange({from:Math.max(0,bars.length-100),to:bars.length+5});first=false}else{bars.forEach((b,i)=>{if(b.time>=lastTime){candles.update(b)}})}drawOscillator(resetSeries);lastTime=bars.at(-1).time;
 priceLines.forEach(line=>candles.removePriceLine(line));priceLines=livePositionLines(data.positions,c).map(options=>candles.createPriceLine(options));
 $('lcquote').textContent=data.symbol+' · '+data.timeframe+'   Bid '+data.bid+'   Ask '+data.ask+'   Spread '+data.spread;ohlc(data.candles.at(-1));const age=data.tickAgeSeconds??(Date.now()/1000-data.tickTime);const sourceOffset=Number(data.sourceOffsetMinutes||0);const sourceLabel='UTC'+(sourceOffset>=0?'+':'−')+Math.floor(Math.abs(sourceOffset)/60)+':'+String(Math.abs(sourceOffset)%60).padStart(2,'0');$('lcstatus').textContent='Dibaca '+appFormatTime(data.fetchedAt,{hour:'2-digit',minute:'2-digit',second:'2-digit'},broker.id)+' '+appTimeLabel(broker.id)+' · '+data.candles.length+' candle · sumber '+sourceLabel+' → '+appTimeLabel(broker.id)+(!data.timeConfirmed?' · Konfirmasi basis waktu broker di Pengaturan.':'')+(age< -60?' · Waktu tick mendahului jam saat ini '+Math.round(-age/60)+' menit. Periksa Basis timestamp dan Offset server di Pengaturan broker.':age>120?' · Tick terakhir '+Math.round(age/60)+' menit lalu. Periksa koneksi atau jam perdagangan.':'');
 const savedGallery=detail.lastElementChild;
 detail.innerHTML='<h2 style="font-size:17px">'+esc(broker.name)+'</h2><dl>'+[['Balance',data.account.balance+' '+data.account.currency],['Equity',data.account.equity],['Floating P/L',data.account.floatingProfit],['Posisi '+data.symbol,data.positions.length],['Tick '+appTimeLabel(broker.id),appFormatTime(data.tickTime*1000,{},broker.id)]].map(([k,v])=>'<div><dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd></div>').join('')+'</dl><h2 style="font-size:15px">Posisi pada chart</h2>'+ (data.positions.map(p=>'<p class="note"><b>'+esc(p.side)+' '+p.volume+' lot · #'+esc(p.ticket)+'</b><br>Entry '+p.entry+' · P/L '+p.profit+'<br>SL '+(p.sl||'—')+' · TP '+(p.tp||'—')+'</p>').join('')||'<p class="note">Tidak ada posisi terbuka pada simbol ini.</p>')+'<p class="notice">Geser chart untuk melihat riwayat, gunakan roda mouse atau pinch untuk zoom. Garis Entry menunjukkan Buy/Sell; TP berwarna hijau dan SL merah. Level bernilai 0 berarti belum dipasang di MT5 dan tidak digambar. Skala harga mencakup seluruh level posisi pada simbol ini.</p>';
 if(savedGallery?.querySelector('[data-gallery]'))detail.append(savedGallery);else attachmentsPanel();
 }catch(e){if(!disposed&&e.name!=='AbortError'){$('lcstatus').textContent=e.message+(latest?' Chart menampilkan snapshot terakhir.':'');}}finally{busy=false;if(!disposed){$('lcload').disabled=false;schedule()}}}
 $('lcindicators').onclick=()=>{document.querySelector('[data-page="indicators"]').click()};
 $('lcclear').disabled=!selection.length;
 $('lcactiveindicators').innerHTML=selection.length?selection.map(spec=>'<div class="range-oscillator-meta"><strong>Range Oscillator · '+spec.length+' × '+spec.multiplier+'</strong><span id="indicator-value-'+esc(spec.id)+'">Menunggu data…</span><button data-remove-indicator="'+esc(spec.id)+'">Hapus</button></div>').join('')+'<p class="note">© Zeiierman · CC BY-NC-SA 4.0 · Level +100 / 0 / −100 · Sinyal candle selesai.</p>':'<p class="note">Tanpa indikator. Pilih melalui Indicators Library.</p>';
 function removeIndicators(id){try{localStorage.setItem(indicatorSelectionKey(broker.id),JSON.stringify(id?selection.filter(x=>x.id!==id):[]));liveChartCleanup();renderLiveChart(root,detail,broker)}catch{notify('Pilihan indikator tidak dapat disimpan.')}}
 $('lcclear').onclick=()=>removeIndicators();root.querySelectorAll('[data-remove-indicator]').forEach(button=>button.onclick=()=>removeIndicators(button.dataset.removeIndicator));
 $('lcload').onclick=()=>load(true);$('lcreset').onclick=()=>chart?.timeScale().fitContent();$('lcauto').onchange=()=>{$('lcauto').checked?load(false):clearTimeout(timer)};load(true);
}
