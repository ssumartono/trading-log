const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/index.html','utf8');
const code=html.slice(html.indexOf('function dashboardSummary('),html.indexOf('function dashboardView()'));
const ctx={};vm.createContext(ctx);vm.runInContext(code,ctx);
let result=ctx.dashboardSummary({id:1,name:'A',initial:100},[{broker:'A',profit:20,lot:.5},{broker:'B',profit:999,lot:1}],[{brokerId:1,type:'Deposit',amount:50},{brokerId:1,type:'Withdraw',amount:10},{brokerId:1,type:'Adjustment',amount:3,signedAmount:-3},{brokerId:2,type:'Deposit',amount:999}]);
assert.equal(result.balance,157);assert.equal(result.net,20);assert.equal(result.adjustment,-3);assert.equal(result.volume,.5);assert.equal(result.trades.length,1);
result=ctx.dashboardSummary({id:2,name:'Empty',initial:0},[],[]);assert.equal(result.balance,0);assert.equal(result.trades.length,0);
assert.ok(html.includes("page='dashboard'"));assert.ok(html.includes("box.onclick=choose"));
console.log('PASS: account isolation, balance with adjustments, empty account, dashboard navigation');
