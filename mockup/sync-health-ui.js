/* Read-only polling never refreshes or replaces a user's edit form. */
function mountSyncHealth(content,brokerId){
  const box=document.createElement('section');box.className='notice';box.style.cssText='margin:0 0 18px;overflow-wrap:anywhere';box.setAttribute('aria-live','polite');box.innerHTML='<b>Status sinkronisasi akun</b><p>Memuat status…</p>';content.prepend(box);
  let stopped=false,timer;
  const escape=value=>String(value??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const date=value=>value?appFormatTime(value,{},brokerId)+' '+appTimeLabel(brokerId):'Belum pernah';
  const amount=value=>Number(value||0).toFixed(2);
  const labels={unknown:'Belum diperiksa',running:'Sedang berlangsung',connected:'Tes koneksi berhasil',success:'Sinkronisasi berhasil',failed:'Percobaan terakhir gagal'};
  async function refresh(){
    try{
      const response=await fetch('/api/sync/status',{cache:'no-store'});const rows=await response.json();if(!response.ok)throw Error(rows.error||'Status tidak tersedia');if(stopped)return;
      const selected=rows.filter(row=>!brokerId||brokerId==='new'||String(row.brokerId)===String(brokerId));
      box.innerHTML='<b>Status sinkronisasi akun</b>'+selected.map(row=>{
        const r=row.reconciliation;
        return '<div style="padding:12px 0;border-bottom:1px solid var(--border,#ccd5e0)"><b>'+escape(row.accountName)+'</b> · <strong class="'+(row.status==='failed'?'negative':'')+'">'+escape(labels[row.status]||row.status)+'</strong><p>Percobaan terakhir: '+escape(date(row.lastAttempt))+'<br>Sinkronisasi berhasil terakhir: '+escape(date(row.lastSuccess))+'</p>'+
          (row.error?'<p class="negative">'+escape(row.error)+'</p>':'')+
          (row.lastSuccess?'<p>Hasil sinkronisasi berhasil terakhir: '+escape(row.new??0)+' baru · '+escape(row.updated??0)+' diperbarui · ticket terbaru '+escape(row.latestTicket)+'</p>':'')+
          (r?'<details><summary>Rekonsiliasi saldo terakhir: '+(r.status==='needs_review'?'Perlu diperiksa':r.status==='baseline_created'?'Checkpoint pertama dibuat':'Cocok')+'</summary><p>Selisih terhadap checkpoint: $'+amount(r.balanceDifference)+' · Selisih terhadap log: $'+amount(r.projectedDifference)+'<br>Deal belum masuk log: '+escape(r.missingTradeCount)+' · Mutasi belum masuk log: '+escape(r.missingFundCount)+' · Backfill historis: '+escape(r.historicalBackfillCount)+'<br>Checkpoint: '+escape(date(r.baselineRecordedAt))+'</p><p>'+escape(r.note)+'</p></details>':'')+
          (!row.timeConfirmed?'<p>Basis waktu belum dikonfirmasi. Cocokkan waktu log dengan MT5, lalu atur basis waktu dan offset pada Pengaturan akun.</p>':'')+'</div>';
      }).join('')+(selected.length?'':'<p>Belum ada akun terdaftar.</p>');
    }catch(error){if(!stopped)box.innerHTML='<b>Status sinkronisasi belum dapat dimuat</b><p>'+escape(error.message)+'</p>'}
    finally{if(!stopped)timer=setTimeout(refresh,5000)}
  }
  window.syncHealthCleanup=()=>{stopped=true;clearTimeout(timer)};refresh();
}
