const test = require('node:test');
const assert = require('node:assert/strict');
const { startTemperatureBridge } = require('./tools/iobroker_temperature_bridge.js');
const mapping = [{source:'mqtt.0.probe.temperature',target:'0_userdata.0.Heizung.Temp.Temp_1_test'}];
const sample = (val=40,ts=1700000000000,extra={}) => ({val,ts,ack:true,q:0,...extra});
function fixture(initial=sample()) {
  const writes=[], subscriptions=[];
  const api={on:(pattern,callback)=>subscriptions.push({pattern,callback}),getStateAsync:async()=>initial,
    setStateAsync:async(id,state)=>writes.push({id,...state}),log:()=>{}};
  return {api,writes,subscriptions};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('forwards repeated identical measurements with their original timestamps and quality',async()=>{
  const f=fixture(); await startTemperatureBridge(f.api,mapping);
  assert.equal(f.subscriptions[0].pattern.change,'any'); assert.equal(f.subscriptions[0].pattern.q,'*');
  f.subscriptions[0].callback({state:sample(40,1700000001000)}); await flush();
  assert.equal(f.writes.length,2);assert.equal(f.writes[1].ts,1700000001000);
  assert.equal(f.writes[0].ts,1700000000000);assert.ok(f.writes.every(s=>s.id===mapping[0].target&&s.ack));
  f.subscriptions[0].callback({state:sample(41,1700000002000,{ack:false,q:64})});await flush();
  assert.equal(f.writes[2].q,64);assert.equal(f.writes[2].ack,false);
});
test('late initial read cannot replace a newer event',async()=>{
  const f=fixture();let resolve;f.api.getStateAsync=()=>new Promise(r=>resolve=r);
  const started=startTemperatureBridge(f.api,mapping);
  f.subscriptions[0].callback({state:sample(50,1700000001000)});await flush();
  resolve(sample(40));await started;
  assert.equal(f.writes.length,1);assert.equal(f.writes[0].val,50);
});
test('missing, nonnumeric or unstamped sources never become valid temperature measurements',async()=>{
  for(const initial of [null,{val:40,ack:true},sample('40'),sample(NaN),sample(126)]){
    const f=fixture(initial);await startTemperatureBridge(f.api,mapping);
    assert.ok(f.writes[0].q&64);
  }
});
test('rejects reverse, arbitrary and duplicate writes before registering anything',()=>{
  for(const bad of [[{source:mapping[0].target,target:mapping[0].source}],
    [{source:mapping[0].source,target:'0_userdata.0.Heizung.Pumpe'}], [...mapping,...mapping],[]]){
    const f=fixture();assert.throws(()=>startTemperatureBridge(f.api,bad));
    assert.equal(f.subscriptions.length,0);assert.equal(f.writes.length,0);
  }
});
