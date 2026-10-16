const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(){
  class Element{
    constructor(){this.dataset={};this.children=[];this.attributes={};this.textContent='';this.hidden=false}
    append(...items){this.children.push(...items)}
    replaceChildren(...items){this.children=[...items]}
    setAttribute(key,value){this.attributes[key]=value}
  }
  const elements=new Map(['pagetitle','pagesubtitle','app-status'].map(id=>[id,new Element()]));
  const timers=new Map();let id=0;
  const context={document:{getElementById:key=>elements.get(key),createElement:()=>new Element()},setTimeout:fn=>{timers.set(++id,fn);return id},clearTimeout:key=>timers.delete(key)};
  vm.createContext(context);vm.runInContext(fs.readFileSync('mockup/app-ui.js','utf8'),context);
  return {context,elements,timers};
}

test('shared headers format each account once and clear old account context',()=>{
  const {context,elements}=setup();
  const broker={name:'Demo Server · 12345',accountKey:'Demo Server:12345',integration:{login:'12345'}};
  context.setPageHeader('Kalender Trading',broker);
  assert.equal(elements.get('pagetitle').textContent,'Kalender Trading · Demo Server · Akun 12345');
  assert.equal(elements.get('pagetitle').dataset.pageTitle,'Kalender Trading');
  context.setPageHeader('Pengaturan');
  assert.equal(elements.get('pagetitle').textContent,'Pengaturan');
  assert.equal(context.accountIdentity({name:'Akun Manual'}).label,'Akun Manual');
});

test('account selection accepts only owned accounts and persists per user',()=>{
  const html=fs.readFileSync('mockup/index.html','utf8');
  const source=html.slice(html.indexOf('function chooseActiveAccount('),html.indexOf('function syncAccountPicker('));
  const storage=new Map();let renders=0;
  const context={brokers:[{id:1,name:'One'},{id:2,name:'Two'}],records:[{id:7,broker:'Two'}],currentUser:{id:9},activeAccount:1,brokerSelected:1,selected:3,performanceState:{drill:'EURUSD',page:4},localStorage:{setItem:(k,v)=>storage.set(k,v)},render:()=>renders++};
  vm.createContext(context);vm.runInContext(source,context);
  context.chooseActiveAccount('2');
  assert.equal(context.activeAccount,2);assert.equal(context.brokerSelected,2);assert.equal(context.selected,7);
  assert.equal(storage.get('tradinglog-account-9'),'2');assert.equal(context.performanceState.drill,null);
  context.chooseActiveAccount('99');assert.equal(context.activeAccount,2);assert.equal(renders,1);
});

test('errors and sync progress remain separate and retry is available',()=>{
  const {context,elements,timers}=setup();let retried=false;
  context.setAppStatus('save','Gagal menyimpan','error',{label:'Coba lagi',onClick:()=>retried=true});
  context.setAppStatus('sync','Sinkronisasi berjalan','busy');
  let rows=elements.get('app-status').children;
  assert.equal(rows.length,2);assert.equal(rows[0].dataset.state,'error');
  rows[0].children[1].onclick();assert.equal(retried,true);
  context.setAppStatus('save','Tersimpan','success');assert.equal(timers.size,1);
  [...timers.values()][0]();rows=elements.get('app-status').children;
  assert.equal(rows.length,1);assert.equal(rows[0].dataset.state,'busy');
});

test('operation feedback shows progress, success, and failure without native dialogs',async()=>{
  const {context,elements}=setup();
  await context.runUIOperation('form',async()=>({saved:true}));
  assert.equal(elements.get('app-status').children[0].dataset.state,'success');
  await assert.rejects(context.runUIOperation('form',async()=>{throw Error('Cannot save')}));
  const row=elements.get('app-status').children[0];assert.equal(row.dataset.state,'error');assert.equal(row.children[0].textContent,'Cannot save');
});
