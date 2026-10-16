const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('selection defaults empty and is scoped to user and account',()=>{
 const data=new Map(),context={window:{currentUser:{id:1}},localStorage:{getItem:key=>data.get(key)}};vm.createContext(context);vm.runInContext(fs.readFileSync('mockup/indicators-library.js','utf8'),context);
 assert.equal(context.readIndicatorSelection(5).length,0);
 data.set(context.indicatorSelectionKey(5),JSON.stringify([{id:'one',type:'range-oscillator',length:50,multiplier:2},{id:'two',type:'range-oscillator',length:20,multiplier:3}]));
 assert.equal(context.readIndicatorSelection(5).length,2);assert.equal(context.readIndicatorSelection(6).length,0);
 context.window.currentUser.id=2;assert.equal(context.readIndicatorSelection(5).length,0);
});
test('invalid saved selection cannot break chart startup',()=>{
 let value='invalid';const context={window:{currentUser:{id:1}},localStorage:{getItem:()=>value}};vm.createContext(context);vm.runInContext(fs.readFileSync('mockup/indicators-library.js','utf8'),context);
 assert.equal(context.readIndicatorSelection(1).length,0);value='{}';assert.equal(context.readIndicatorSelection(1).length,0);value='[{"type":"unknown"}]';assert.equal(context.readIndicatorSelection(1).length,0);
});
