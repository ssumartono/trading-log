/* Pagination for data tables, including tables rebuilt by filters and CRUD. */
(()=>{
const attached=new WeakSet(),state=new Map();let scheduled=false;
function paginate(){
  scheduled=false;
  const tables=[...document.querySelectorAll('#content table')];
  tables.forEach((table,index)=>{
    if(attached.has(table)||table.classList.contains('perf-heat')||table.closest('#perflogs')||table.closest('.trader-text')||table.closest('#auditrows'))return;
    const rows=[...table.tBodies].flatMap(body=>[...body.rows]),defaultSize=window.matchMedia('(max-width:650px)').matches?5:10;
    if(rows.length<=defaultSize)return;
    attached.add(table);
    const account=document.querySelector('aside .account[aria-pressed="true"]')?.getAttribute('aria-label')||'';
    const key=document.getElementById('pagetitle').textContent+'|'+account+'|'+index;
    const signature=rows.length+'|'+rows[0].textContent+'|'+rows.at(-1).textContent;
    let current=state.get(key);if(!current||current.signature!==signature)current={page:0,size:defaultSize,signature};state.set(key,current);
    const bar=document.createElement('div');bar.className='table-pagination';bar.setAttribute('aria-label','Navigasi halaman tabel');
    const status=document.createElement('span');status.className='muted';status.setAttribute('role','status');
    const label=document.createElement('label');label.textContent='Baris ';const size=document.createElement('select');size.setAttribute('aria-label','Jumlah baris per halaman');[5,10,20,50].forEach(n=>size.add(new Option(String(n),String(n))));size.value=current.size;label.append(size);
    const first=document.createElement('button'),prev=document.createElement('button'),next=document.createElement('button'),last=document.createElement('button');
    first.textContent='«';first.setAttribute('aria-label','Halaman pertama');prev.textContent='‹ Sebelumnya';next.textContent='Berikutnya ›';last.textContent='»';last.setAttribute('aria-label','Halaman terakhir');
    [first,prev,next,last].forEach(button=>button.type='button');bar.append(status,label,first,prev,next,last);
    const wrapper=table.closest('.tablewrap')||table.parentElement;wrapper.insertAdjacentElement('afterend',bar);
    function draw(){const pages=Math.ceil(rows.length/current.size);current.page=Math.max(0,Math.min(current.page,pages-1));const start=current.page*current.size;rows.forEach((row,i)=>row.hidden=i<start||i>=start+current.size);status.textContent=(start+1)+'–'+Math.min(rows.length,start+current.size)+' dari '+rows.length+' · Halaman '+(current.page+1)+'/'+pages;first.disabled=prev.disabled=current.page===0;next.disabled=last.disabled=current.page===pages-1}
    table.addEventListener('table-sorted',()=>{rows.splice(0,rows.length,...[...table.tBodies].flatMap(b=>[...b.rows]));current.page=0;draw()});function move(page){current.page=page;draw();wrapper.scrollIntoView({block:'nearest'})}
    first.onclick=()=>move(0);prev.onclick=()=>move(current.page-1);next.onclick=()=>move(current.page+1);last.onclick=()=>move(Math.ceil(rows.length/current.size)-1);size.onchange=()=>{current.size=+size.value;current.page=0;draw()};draw();
  });
}
function schedule(){if(!scheduled){scheduled=true;requestAnimationFrame(paginate)}}
const observer=new MutationObserver(schedule);observer.observe(document.getElementById('content'),{childList:true,subtree:true});schedule();
})();
