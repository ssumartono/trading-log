let appTimePreferences={timezone:'WIB',brokerOffsets:{}},appTimeBrokerId=null;
function appTimeOffset(brokerId=appTimeBrokerId){
  if(appTimePreferences.timezone==='UTC')return 0;
  if(appTimePreferences.timezone==='BROKER')return Number(appTimePreferences.brokerOffsets[String(brokerId)]??0);
  return 420;
}
function appTimeLabel(brokerId=appTimeBrokerId){
  if(appTimePreferences.timezone!=='BROKER')return appTimePreferences.timezone;
  const value=appTimePreferences.brokerOffsets[String(brokerId)];
  if(value===undefined)return 'UTC (offset broker belum diatur)';
  const n=Number(value);return 'Broker UTC'+(n>=0?'+':'−')+Math.floor(Math.abs(n)/60)+':'+String(Math.abs(n)%60).padStart(2,'0');
}
function appFormatTime(value,options={},brokerId=appTimeBrokerId){
  return new Date(new Date(value).getTime()+appTimeOffset(brokerId)*60000).toLocaleString('id-ID',{...options,timeZone:'UTC'});
}
async function loadAppTime(){const response=await fetch('/api/preferences',{cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'Pengaturan waktu gagal dimuat');appTimePreferences=data}
function mountAppTimeSettings(root,brokers){
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const section=document.createElement('section');section.className='account';section.style.cssText='padding:22px;margin:0 0 22px';
  section.innerHTML='<h2>Broker Time System</h2><form><label>Zona waktu tampilan<select name="timezone"><option value="WIB">WIB (UTC+7)</option><option value="BROKER">Waktu Broker</option><option value="UTC">UTC</option></select></label><p class="note">Berlaku untuk sumbu waktu Live Chart, tooltip, tick dan timestamp sistem. Tanggal/jam input jurnal, kalender, filter periode dan laporan trading tetap WIB dan diberi label WIB agar pengelompokan riwayat konsisten.</p><div class="fields">'+brokers.map(b=>'<label>Offset tampilan '+esc(b.name)+' (menit dari UTC)<input data-offset="'+b.id+'" type="number" min="-720" max="840" step="15" value="'+esc(appTimePreferences.brokerOffsets[String(b.id)]??'')+'" placeholder="Contoh UTC+3 = 180"></label>').join('')+'</div><p class="notice">Offset tampilan broker berbeda dari basis timestamp MT5. Sesuaikan dengan jam chart terminal, termasuk perubahan musim bila ada. Timestamp sumber dan harga candle tidak diubah. Broker tanpa offset ditampilkan sebagai UTC dengan peringatan.</p><button class="primary" type="submit">Simpan pengaturan global</button><p role="status" class="note"></p></form>';
  root.prepend(section);const form=section.querySelector('form'),status=section.querySelector('[role=status]');form.elements.timezone.value=appTimePreferences.timezone;
  form.onsubmit=async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;setAppStatus('display-time','Menyimpan pengaturan waktu…','busy');try{const brokerOffsets={};section.querySelectorAll('[data-offset]').forEach(input=>brokerOffsets[input.dataset.offset]=input.value);const response=await fetch('/api/preferences',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({timezone:form.elements.timezone.value,brokerOffsets})}),result=await response.json();if(!response.ok)throw Error(result.error||'Gagal menyimpan');appTimePreferences=result;setAppStatus('display-time','Pengaturan waktu tersimpan.','success');status.textContent='Tersimpan permanen. Tampilan waktu mengikuti '+appTimeLabel()+'. Buka Live Chart untuk melihat perubahan.'}catch(error){setAppStatus('display-time',error.message,'error');status.textContent=error.message}finally{button.disabled=false}};
}
