// Registry of built indicators. MT5-only entries are explicitly unavailable on web.
const indicatorLibrary=[
 {id:'range-oscillator',name:'Range Oscillator',ready:true,description:'Heatmap momentum dengan level +100 / 0 / −100 dan sinyal candle selesai.'},
 {id:'range-filter',name:'Range Filter',ready:false},
 {id:'liquidity-reaper',name:'Liquidity Reaper',ready:false},
 {id:'supply-demand',name:'Supply Demand JOAT',ready:false}
];
function indicatorSelectionKey(brokerId){return 'chart-indicators-'+window.currentUser?.id+'-'+brokerId}
function readIndicatorSelection(brokerId){try{const value=JSON.parse(localStorage.getItem(indicatorSelectionKey(brokerId))||'[]');return Array.isArray(value)?value.filter(x=>x.type==='range-oscillator'&&Number.isInteger(x.length)&&x.length>=2&&x.length<=500&&Number.isFinite(x.multiplier)&&x.multiplier>=.1&&x.multiplier<=20&&typeof x.id==='string').slice(0,8):[]}catch{return []}}
function renderIndicatorsLibrary(root,detail,broker,onLoad){
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 root.innerHTML='<p class="note">Pilih indikator untuk akun aktif, lalu tekan Load. Setiap indikator dimuat pada panel tersendiri di Live Chart.</p>'+indicatorLibrary.map(item=>'<section class="indicator-card"><h2>'+escape(item.name)+'</h2><p class="note">'+escape(item.description||'Indikator tersedia di folder proyek untuk terminal MT5. Adaptasi Live Chart belum tersedia.')+'</p>'+(item.ready?'<form id="indicator-load"><label>Periode <input name="length" type="number" min="2" max="500" value="50" required></label> <label>Multiplier <input name="multiplier" type="number" min="0.1" max="20" step="0.1" value="2" required></label> <button class="primary" '+(!broker?'disabled':'')+'>Load ke Live Chart</button></form><p class="note">© Zeiierman · <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener">CC BY-NC-SA 4.0</a></p>':'<span class="badge">MT5 saja</span>')+'</section>').join('');
 detail.innerHTML='<h2>Indicators Library</h2><p class="note">Live Chart baru dimulai tanpa indikator. Pilihan disimpan di browser ini untuk setiap pengguna dan akun. Maksimal 8 panel indikator.</p>'+(!broker?'<p class="notice">Tambahkan atau pilih akun terlebih dahulu.</p>':'');
 root.querySelector('#indicator-load').onsubmit=e=>{e.preventDefault();if(!broker)return;const selected=readIndicatorSelection(broker.id);if(selected.length>=8){notify('Maksimal 8 indikator. Hapus salah satu dari Live Chart terlebih dahulu.');return}const values=new FormData(e.target);selected.push({id:crypto.randomUUID(),type:'range-oscillator',length:Number(values.get('length')),multiplier:Number(values.get('multiplier'))});try{localStorage.setItem(indicatorSelectionKey(broker.id),JSON.stringify(selected));onLoad()}catch{notify('Pilihan indikator tidak dapat disimpan di browser.')}};
}
