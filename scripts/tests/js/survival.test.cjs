const test=require('node:test'),assert=require('node:assert/strict');
const {estimate,logRank}=require('../../../static/survival.js');
test('tied death and censor retain both in the risk set',()=>{const result=estimate([{time:1,event:true},{time:1,event:false},{time:2,event:true}]);assert.equal(result[0].risk,3);assert(Math.abs(result[0].survival-2/3)<1e-12);assert.equal(result[1].risk,1);assert.equal(result[1].survival,0);});
test('censoring alone never lowers survival',()=>{assert.deepEqual(estimate([{time:0,event:false},{time:3,event:false}]).map(p=>p.survival),[1,1]);assert.deepEqual(estimate([]),[]);});
test('reject invalid times and event flags',()=>{assert.throws(()=>estimate([{time:-1,event:true}]));assert.throws(()=>estimate([{time:1,event:'death'}]));});

test('log-rank handles tied deaths/censoring with known chi-square',()=>{
 const r=[{group:'CD',time:1,event:true},{group:'CD',time:1,event:false},{group:'WD',time:1,event:true},{group:'WD',time:2,event:true}];
 const v=logRank(r);assert.equal(v.chiSquare,0);assert.equal(v.p,1);assert(Math.abs(v.variance-1/3)<1e-12);
});
test('log-rank matches chi-square one reference and handles no information',()=>{
 const v=logRank([{group:'CD',time:1,event:true},{group:'WD',time:2,event:false}]);
 assert.equal(v.chiSquare,1);assert(Math.abs(v.p-0.317310507862914)<1e-7);
 assert.equal(logRank([{group:'CD',time:1,event:false},{group:'WD',time:2,event:false}]),null);
 assert.equal(logRank([{group:'CD',time:1,event:true}]),null);
});
