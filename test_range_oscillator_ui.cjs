const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('mockup/live-chart-ui.js','utf8'),context);

test('oscillator preserves missing data as whitespace and breakout values beyond 100',()=>{
  const result=context.rangeOscillatorSeries({points:[{time:1,value:null,colorIndex:22},{time:2,value:150,colorIndex:23},{time:3,value:-140,colorIndex:24}],signals:[{time:2,side:'Buy',price:99.7}]},'#ffffff');
  assert.equal('value' in result.line[0],false);assert.equal('value' in result.shading[0],false);
  assert.equal(result.line[1].value,150);assert.equal(result.line[2].value,-140);
  assert.equal(result.markers[0].shape,'arrowUp');assert.equal(result.markers[0].price,99.7);
});

test('reference levels stay visible without clipping breakouts',()=>{
  let result=context.rangeOscillatorAutoscale({priceRange:{minValue:-15,maxValue:30}});
  assert.equal(result.priceRange.minValue,-100);assert.equal(result.priceRange.maxValue,100);
  result=context.rangeOscillatorAutoscale({priceRange:{minValue:-250,maxValue:300}});
  assert.equal(result.priceRange.minValue,-250);assert.equal(result.priceRange.maxValue,300);
});

test('MT5 palette blends into the current theme and shading differs from the line',()=>{
  assert.equal(context.rangeOscillatorColor(23,'#fff'),'rgb(9,255,0)');
  assert.equal(context.rangeOscillatorColor(24,'#fff'),'rgb(255,0,0)');
  assert.notEqual(context.rangeOscillatorColor(0,'#fff'),context.rangeOscillatorColor(0,'#111'));
  assert.notEqual(context.rangeOscillatorColor(23,'#fff'),context.rangeOscillatorColor(23,'#fff',true));
});
