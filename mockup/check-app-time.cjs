const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),ctx={};vm.createContext(ctx);vm.runInContext(fs.readFileSync(__dirname+'/app-time.js','utf8'),ctx);
assert.equal(ctx.appTimeOffset(),420);assert.equal(ctx.appTimeLabel(),'WIB');const stamp='2026-10-15T18:00:00Z';assert.ok(ctx.appFormatTime(stamp).includes('16/10/2026'));
vm.runInContext("appTimePreferences={timezone:'UTC',brokerOffsets:{}}",ctx);assert.equal(ctx.appTimeOffset(),0);assert.ok(ctx.appFormatTime(stamp).includes('15/10/2026'));
vm.runInContext("appTimePreferences={timezone:'BROKER',brokerOffsets:{'1':180,'2':120}}",ctx);assert.equal(ctx.appTimeOffset(1),180);assert.equal(ctx.appTimeOffset(2),120);assert.equal(ctx.appTimeLabel(1),'Broker UTC+3:00');assert.ok(ctx.appTimeLabel(3).includes('belum diatur'));assert.equal(ctx.appTimeOffset(3),0);
for(const name of ['app-time.js','live-chart-ui.js','trader-ui.js','sync-health-ui.js'])new vm.Script(fs.readFileSync(__dirname+'/'+name,'utf8'));
console.log('PASS: WIB/UTC midnight, account-specific broker display offsets, explicit missing offset, UI syntax');
