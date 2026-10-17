const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('memo AI uses shared note context and preserves apply/append/undo',async()=>{
 const fields=new Map();
 const section={style:{},classList:{add(){}},isConnected:true,querySelector:q=>{if(!fields.has(q))fields.set(q,{value:'',disabled:false});return fields.get(q)}};
 const root={append:s=>assert.equal(s,section)};
 const source={title:'Evaluation',body:'Original',kind:'Memo',eventDate:'2026-10-17T10:00',brokerId:'3'};
 const form={elements:Object.fromEntries(Object.entries(source).map(([k,value])=>[k,{value}])),isConnected:true,scrollIntoView(){}};
 let editor=null,request;
 const ctx={document:{createElement:()=>section},fetch:async(_url,options)=>{request=JSON.parse(options.body);return {ok:true,json:async()=>({draft:'AI draft',kind:'Memo'})}},confirm:()=>true};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('mockup/note-ai-main.js','utf8'),ctx);
 ctx.mountMemoAI(root,[],()=>editor,()=>editor=form,()=>source);
 assert.ok(!/id="ai(kind|date|account)"/.test(section.innerHTML));
 section.querySelector('#ailogs').checked=false;section.querySelector('#aiprompt').value='Improve';await fields.get('#aigenerate').onclick();
 assert.equal(request.includeLogs,false);assert.equal(request.logPeriod,'day');assert.equal(request.body,'Original');assert.equal(request.eventDate,source.eventDate);assert.equal(request.brokerId,'3');
 fields.get('#aiapply').onclick();assert.equal(form.elements.body.value,'AI draft');assert.equal(form.elements.kind.value,'Catatan Harian');
 fields.get('#aiundo').onclick();assert.equal(form.elements.body.value,'Original');assert.equal(form.elements.kind.value,'Memo');
 fields.get('#aicopymemo').onclick();assert.equal(form.elements.body.value,'AI draft');assert.equal(form.elements.kind.value,'Memo');
 fields.get('#aiundo').onclick();assert.equal(form.elements.body.value,'Original');
 fields.get('#aiappend').onclick();assert.equal(form.elements.body.value,'Original\n\nAI draft');
 fields.get('#ailogs').checked=true;await fields.get('#aigenerate').onclick();assert.equal(request.includeLogs,true);
});


