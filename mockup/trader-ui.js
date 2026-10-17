/* Render a limited Markdown subset. Raw HTML is always escaped. */
function traderMarkdown(value){
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function inline(text){
    return String(text).split(/(`[^`]+`)/g).map(part=>part.startsWith('`')?'<code>'+escape(part.slice(1,-1))+'</code>':escape(part).replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/__([^_\n]+)__/g,'<strong>$1</strong>').replace(/\*([^*\n]+)\*/g,'<em>$1</em>')).join('');
  }
  const lines=String(value??'').replace(/\r\n?/g,'\n').split('\n');let i=0,result='';
  const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(s=>s.trim().replace(/\\\|/g,'|'));
  const divider=line=>line?.includes('|')&&cells(line).every(s=>/^:?-{3,}:?$/.test(s));
  const list=line=>line.match(/^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/);
  const block=at=>/^(?:\s*$|\s*```|#{1,6}\s|\s*>|\s*([-*_])(?:\s*\1){2,}\s*$)/.test(lines[at]||'')||list(lines[at]||'')||divider(lines[at+1]);
  while(i<lines.length){
    let line=lines[i];if(!line.trim()){i++;continue}
    if(/^\s*```/.test(line)){let code=[];i++;while(i<lines.length&&!/^\s*```/.test(lines[i]))code.push(lines[i++]);if(i<lines.length)i++;result+='<pre><code>'+escape(code.join('\n'))+'</code></pre>';continue}
    if(line.includes('|')&&divider(lines[i+1])){
      const headers=cells(line),align=cells(lines[i+1]).map(s=>s.startsWith(':')&&s.endsWith(':')?'center':s.endsWith(':')?'right':'left');i+=2;
      result+='<div class="trader-table-scroll" role="region" aria-label="Tabel jawaban AI, geser untuk melihat kolom" tabindex="0"><table><thead><tr>'+headers.map((s,n)=>'<th scope="col" style="text-align:'+align[n]+'">'+inline(s)+'</th>').join('')+'</tr></thead><tbody>';
      while(i<lines.length&&lines[i].trim()&&lines[i].includes('|')){const row=cells(lines[i++]);result+='<tr>'+headers.map((_,n)=>'<td style="text-align:'+align[n]+'">'+inline(row[n]||'')+'</td>').join('')+'</tr>'}
      result+='</tbody></table></div>';continue;
    }
    const heading=line.match(/^(#{1,6})\s+(.+)$/);if(heading){const level=Math.min(heading[1].length+2,6);result+='<h'+level+'>'+inline(heading[2])+'</h'+level+'>';i++;continue}
    if(/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)){result+='<hr>';i++;continue}
    if(/^\s*>/.test(line)){let quote=[];while(i<lines.length&&/^\s*>/.test(lines[i]))quote.push(inline(lines[i++].replace(/^\s*>\s?/,'')));result+='<blockquote>'+quote.join('<br>')+'</blockquote>';continue}
    const item=list(line);if(item){const ordered=Boolean(item[2]),tag=ordered?'ol':'ul';result+='<'+tag+(ordered?' start="'+Number(item[2])+'"':'')+'>';while(i<lines.length){const next=list(lines[i]);if(!next||Boolean(next[2])!==ordered)break;result+='<li>'+inline(next[3])+'</li>';i++}result+='</'+tag+'>';continue}
    const paragraph=[inline(line)];i++;while(i<lines.length&&!block(i))paragraph.push(inline(lines[i++]));result+='<p>'+paragraph.join('<br>')+'</p>';
  }
  return result;
}
let traderEpoch=0;const traderDrafts=new Map();
async function renderTrader(root,detail,broker,records,options={}){
 const epoch=++traderEpoch,esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 if(!broker){root.textContent='Pilih akun terlebih dahulu.';return}
 const live=()=>epoch===traderEpoch&&root.isConnected;
 const api=async(path,data={})=>{const r=await fetch('/api/trader/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brokerId:broker.id,...data})});const v=await r.json();if(!r.ok)throw Error(v.error||'Permintaan gagal');return v};
 root.classList.add('live-assistant');
 root.innerHTML=`<p class="note">Susun permintaan, pilih sumber, lalu kirim ke AI.</p>
 <form id="traderform" class="trader-request">
 <h3>1. Pertanyaan untuk AI</h3><label>Prompt standar<select id="traderpreset"><option value="">Tulis pertanyaan sendiri</option><option value="market">Analisis kondisi market</option><option value="scenario">Skenario BUY / SELL</option><option value="risk">Evaluasi risiko posisi</option><option value="performance">Evaluasi data trading</option></select></label>
 <label>Prompt Anda<textarea id="tradermessage" rows="4" maxlength="5000" required placeholder="Pilih prompt standar atau ketik pertanyaan Anda…"></textarea></label>
 <h3>2. Pilih sumber analisis</h3><fieldset class="trader-sources"><legend>Opsional · boleh lebih dari satu</legend>
 <label><input id="traderlive" type="checkbox" checked> Live Chart (Default)</label>
 <label><input id="traderdata" type="checkbox"> Data trading</label>
 <label><input id="tradermarket" type="checkbox"> Snapshot market</label>
 <label><input id="traderscreen" type="checkbox"> Tangkapan layar</label></fieldset>
 <p id="traderchartsource" class="notice" role="status"></p>
 <div id="traderlogs" hidden></div>
 <div id="tradershot" hidden><button type="button" id="tradercapture">Tangkap chart</button><p class="note">Pratinjau gambar yang akan dikirim. Tangkap ulang setelah mengubah chart.</p><img id="traderpreview" alt="Pratinjau chart untuk AI" hidden><p id="tradershotlabel" class="muted"></p></div>
 <p class="notice">Centang sumber yang ingin disertakan. AI merespons setelah Anda menekan Kirim ke AI.</p>
 <h3>3. Kirim permintaan</h3><div class="memo-actions"><button class="primary" type="submit" id="tradersend">Kirim ke AI</button></div></form>
 <p id="traderstatus" class="note" role="status"></p>
 <div class="trader-results-heading"><h3>Hasil & percakapan</h3><button type="button" id="traderclear">Percakapan baru</button></div>
 <p class="notice trader-chart-relation" role="status"></p><div id="traderchat" class="trader-chat" aria-label="Riwayat percakapan"><p class="note trader-empty">Belum ada percakapan. AI merespons setelah Anda mengirim permintaan.</p></div>`;
 const $=id=>root.querySelector('#'+id),message=$('tradermessage');let shot=null,lastContext=null,sending=false;
 message.value=traderDrafts.get(broker.id)||'';message.oninput=()=>traderDrafts.set(broker.id,message.value);
 const presets={market:'Analisis kondisi market dari sumber yang saya lampirkan. Pisahkan fakta, interpretasi, dan hal yang belum dapat dipastikan.',scenario:'Susun skenario BUY dan SELL dari sumber terlampir, kondisi konfirmasi, pembatalan skenario dan risikonya. Jangan mengarang harga yang tidak tersedia.',risk:'Evaluasi risiko posisi dan eksposur akun berdasarkan sumber yang saya lampirkan. Jelaskan data yang masih diperlukan.',performance:'Evaluasi data trading terlampir: pola hasil, konsistensi, kelemahan dan langkah perbaikan. Sebutkan transaksi sumber yang relevan.'};
 $('traderpreset').onchange=()=>{if(presets[$('traderpreset').value]){message.value=presets[$('traderpreset').value];traderDrafts.set(broker.id,message.value)}message.focus()};
 const logs=attachAILogs($('traderlogs'),()=>({brokerId:broker.id,message:message.value}),{checkbox:$('traderdata'),period:'30'});
 function chart(){return options.getChart?.()||{ready:false}}
 function sync(){if(!live())return;const c=chart();$('traderchartsource').textContent=c.ready?'Chart aktif: '+c.symbol+' · '+c.timeframe+'. Live Chart mengirim candle dan indikator aktif saat Kirim; candle terakhir masih berjalan.':'Chart belum siap. Tampilkan chart untuk memakai snapshot atau tangkapan layar.';const relation=root.querySelector('.trader-chart-relation');relation.hidden=!lastContext;relation.textContent=lastContext?((c.ready&&lastContext.symbol===c.symbol&&lastContext.timeframe===c.timeframe)?'Hasil terakhir terkait chart aktif: ':'Hasil sebelumnya berasal dari chart berbeda: ')+lastContext.symbol+' · '+lastContext.timeframe+' · snapshot '+appFormatTime(lastContext.fetchedAt,{},broker.id)+' '+appTimeLabel(broker.id):'';relation.classList.toggle('negative',Boolean(lastContext&&(!c.ready||lastContext.symbol!==c.symbol||lastContext.timeframe!==c.timeframe)));}
 options.onSync?.(sync);sync();
 $('traderdata').onchange=()=>{$('traderlogs').hidden=!$('traderdata').checked};
 $('tradermarket').onchange=sync;
 $('traderscreen').onchange=()=>{$('tradershot').hidden=!$('traderscreen').checked;sync()};
 $('tradercapture').onclick=()=>{try{const c=chart();if(!c.ready)throw Error('Tampilkan chart terlebih dahulu.');const image=options.capture?.();if(!image)throw Error('Chart belum tersedia.');if(image.length>2800000)throw Error('Gambar terlalu besar (maksimal 2 MB). Perkecil chart lalu tangkap ulang.');shot={image,symbol:c.symbol,timeframe:c.timeframe,capturedAt:new Date().toISOString()};$('traderpreview').src=image;$('traderpreview').hidden=false;$('tradershotlabel').textContent=shot.symbol+' · '+shot.timeframe+' · '+appFormatTime(shot.capturedAt,{},broker.id)+' '+appTimeLabel(broker.id);$('traderstatus').textContent='Pratinjau siap. Belum dikirim ke AI.'}catch(e){$('traderstatus').textContent=e.message}};
 function bubble(role,text,ctx,createdAt,sources){$('traderchat').querySelector('.trader-empty')?.remove();const article=document.createElement('article');article.className='trader-bubble '+(role==='user'?'trader-user':'');const header=document.createElement('div');header.className='trader-message-header';const title=document.createElement('strong');title.textContent=role==='user'?'Anda':'AI Trader Assistant';const time=document.createElement('time');time.className='muted trader-message-time';const date=new Date(createdAt);if(createdAt&&Number.isFinite(date.getTime())){time.dateTime=date.toISOString();time.textContent=appFormatTime(date.toISOString(),{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'},broker.id)+' '+appTimeLabel(broker.id)}else time.textContent='Waktu pesan tidak tersedia';header.append(title,time);const body=document.createElement('div');body.className='trader-text';if(role==='assistant')body.innerHTML=traderMarkdown(text);else body.textContent=text;article.append(header,body);
 if(sources){const note=document.createElement('p');note.className='muted';note.textContent='Sumber: '+([sources.liveChart?'Live Chart':null,sources.logs?'Data trading':null,sources.snapshot?'Snapshot market':null,sources.screenshot?'Tangkapan layar':null].filter(Boolean).join(' + ')||'Prompt saja');article.append(note)}
 if(ctx){const note=document.createElement('p');note.className='muted';note.textContent=ctx.symbol+' · '+ctx.timeframe+' · snapshot '+appFormatTime(ctx.fetchedAt,{},broker.id)+' '+appTimeLabel(broker.id);const show=document.createElement('button');show.type='button';show.textContent='Tampilkan '+ctx.symbol+' · '+ctx.timeframe+' di chart';show.onclick=()=>options.showChart?.(ctx);article.append(note,show)}$('traderchat').append(article);}
 function context(ctx){lastContext=ctx;detail.textContent='';if(ctx){const p=document.createElement('p');p.className='note';p.textContent=ctx.symbol+' · '+ctx.timeframe+' · '+appFormatTime(ctx.fetchedAt,{},broker.id)+' '+appTimeLabel(broker.id)+' | Bid '+ctx.bid+' | Ask '+ctx.ask+' | '+ctx.summary.candleCount+(ctx.sourceType==='liveChart'?' candle (terakhir masih berjalan)':' candle tertutup')+(ctx.dataWarning?' | '+ctx.dataWarning:'');detail.append(p)}else detail.textContent='Tidak ada snapshot market pada jawaban ini.';sync()}
 $('traderform').onsubmit=async e=>{e.preventDefault();if(sending)return;const text=message.value.trim();if(!text)return;const c=chart();if(($('traderlive').checked||$('tradermarket').checked||$('traderscreen').checked)&&!c.ready){$('traderstatus').textContent='Tampilkan chart yang dipilih sebelum mengirim sumber chart.';return}if($('traderscreen').checked&&(!shot||shot.symbol!==c.symbol||shot.timeframe!==c.timeframe)){$('traderstatus').textContent='Tangkap chart aktif terlebih dahulu; pratinjau harus sesuai simbol dan timeframe.';return}
 const request={includeLiveChart:$('traderlive').checked,indicators:options.getIndicators?.()||[],message:text,symbol:c.symbol||'',timeframe:c.timeframe||'M15',...logs.read(),includeLogs:$('traderdata').checked,includeMarket:$('tradermarket').checked,screenshot:$('traderscreen').checked?shot.image:null};
 sending=true;$('tradersend').disabled=true;$('traderclear').disabled=true;$('traderstatus').textContent='Mengirim sumber terpilih dan menyiapkan jawaban AI…';
 try{const r=await api('chat',request);if(!live())return;bubble('user',text,null,r.userCreatedAt,r.sources);bubble('assistant',r.answer,r.chartContext||r.context,r.assistantCreatedAt,r.sources);context(r.chartContext||r.context);logs.display(r.logContext);if(message.value.trim()===text){message.value='';traderDrafts.delete(broker.id)}$('traderstatus').textContent='Jawaban tersimpan. Sumber tercantum pada percakapan.';$('traderchat').scrollTop=$('traderchat').scrollHeight}catch(err){if(live())$('traderstatus').textContent=err.message}finally{sending=false;if(live()){$('tradersend').disabled=false;$('traderclear').disabled=false}}};
 $('traderclear').onclick=async()=>{if(!confirm('Hapus riwayat percakapan akun ini?'))return;try{await api('clear');if(live()){$('traderchat').textContent='Belum ada percakapan.';context(null)}}catch(e){if(live())$('traderstatus').textContent=e.message}};
 try{const history=await api('history');if(!live())return;history.forEach(m=>bubble(m.role,m.content,m.chartContext||m.context,m.createdAt,m.sources));const last=[...history].reverse().find(m=>m.role==='assistant');context(last?.chartContext||last?.context||null)}catch(e){if(live())$('traderstatus').textContent=e.message}
}
