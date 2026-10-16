/* Shared account context and non-blocking operation feedback. */
function accountIdentity(broker){
  if(!broker)return {name:'',login:'',label:''};
  const key=String(broker.accountKey||''),separator=key.lastIndexOf(':');
  const login=String(broker.integration?.login||(separator>=0?key.slice(separator+1):''));
  const suffix=login?' · '+login:'',name=String(broker.name||'');
  const label=(suffix&&name.endsWith(suffix)?name.slice(0,-suffix.length):name)||broker.integration?.server||(separator>=0?key.slice(0,separator):'Broker');
  return {name:label,login,label:label+(login?' · Akun '+login:'')};
}

function setPageHeader(title,broker){
  const heading=document.getElementById('pagetitle');
  if(heading){heading.textContent=title+(broker?' · '+accountIdentity(broker).label:'');heading.dataset.pageTitle=title}
  const subtitle=document.getElementById('pagesubtitle');
  if(subtitle)subtitle.textContent=({'Indicators Library':'Pilih indikator untuk dimuat ke Live Chart akun aktif.','Dashboard':'Ringkasan dan aktivitas akun trading Anda.','Live Chart':'Pantau harga, candle, dan posisi akun terpilih.','AI Trader Assistant':'Diskusikan kondisi pasar dan evaluasi trading akun terpilih.','Analisa Performa Trading':'Statistik per log/deal berdasarkan filter analisis.','Kalender Trading':'Riwayat transaksi berdasarkan tanggal dan waktu WIB.','Semua Log Trading':'Telusuri dan evaluasi log trading akun terpilih.','Broker & Akun':'Ringkasan keuangan dan mutasi dana akun terpilih.','Pengaturan':'Kelola profil, tampilan, dan integrasi akun Anda.','Pengguna & Hak Akses':'Kelola pengguna, peran, dan kepemilikan akun.'})[title]||'Kelola workspace trading Anda.';
}

const operationMessages=new Map(),operationTimers=new Map();
function setAppStatus(key,message,state='info',action=null){
  clearTimeout(operationTimers.get(key));operationTimers.delete(key);
  if(message)operationMessages.set(key,{message,state,action});else operationMessages.delete(key);
  renderAppStatus();
  if(state==='success')operationTimers.set(key,setTimeout(()=>setAppStatus(key,''),6000));
}
function renderAppStatus(){
  const region=document.getElementById('app-status');if(!region)return;
  region.replaceChildren();region.hidden=operationMessages.size===0;
  for(const [key,item] of operationMessages){
    const row=document.createElement('div');row.className='operation-message';row.dataset.state=item.state;
    const text=document.createElement('span');text.textContent=item.message;row.append(text);
    if(item.action){const button=document.createElement('button');button.type='button';button.textContent=item.action.label;button.onclick=item.action.onClick;row.append(button)}
    if(item.state!=='busy'){const dismiss=document.createElement('button');dismiss.type='button';dismiss.textContent='Tutup';dismiss.setAttribute('aria-label','Tutup pesan');dismiss.onclick=()=>setAppStatus(key,'');row.append(dismiss)}
    region.append(row);
  }
}
function notify(message,state='error'){setAppStatus('notice',message,state)}

async function runUIOperation(key,operation,success='Perubahan tersimpan.',busy='Menyimpan perubahan…'){
  setAppStatus(key,busy,'busy');
  try{const result=await operation();setAppStatus(key,success,'success');return result}
  catch(error){setAppStatus(key,error.message||'Proses gagal. Coba lagi.','error');throw error}
}
