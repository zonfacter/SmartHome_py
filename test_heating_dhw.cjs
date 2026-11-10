const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{},HeatingLive:{update:(target,html)=>{target.innerHTML=html;}}};
vm.runInNewContext(fs.readFileSync('web/static/js/heating_dhw.js','utf8'),context);
function view(){
  const targets=Object.fromEntries(['dhw-pump-chart','dhw-pump-events','dhw-history-chart'].map(k=>[k,{innerHTML:'',textContent:'',clientWidth:600}]));
  const v=new context.window.HeatingDhwView.View({querySelector:s=>targets[s.slice(1)],querySelectorAll:()=>[]});
  return {v,targets};
}
test('pump lanes show off, unknown and changes distinctly with bounded switch times',()=>{
  const {v,targets}=view();
  v.pumps({first_sample:1000,last_sample:1180,pumps:[{key:'eg',state:false,buckets:[
    {from:1000,to:1060,on_seconds:0,off_seconds:60,unknown_seconds:0,switches:0},
    {from:1060,to:1120,on_seconds:0,off_seconds:0,unknown_seconds:60,switches:1},
    {from:1120,to:1180,on_seconds:0,off_seconds:0,unknown_seconds:60,switches:0}
  ],events:[{from:1060,to:1120,state:true}]}]});
  const svg=targets['dhw-pump-chart'].innerHTML;
  assert.match(svg,/var\(--line\)/);assert.match(svg,/#ca8a26/);assert.match(svg,/url\(#pump-history-unknown\)/);
  assert.match(targets['dhw-pump-events'].innerHTML,/Wechsel zwischen/);
  assert.match(targets['dhw-pump-events'].innerHTML,/<td>Ein<\/td>/);
});
test('missing pump history does not invent an off state',()=>{
  const {v,targets}=view();v.pumps({});
  assert.match(targets['dhw-pump-chart'].innerHTML,/Noch keine/);
  assert.doesNotMatch(targets['dhw-pump-chart'].innerHTML,/zuletzt Aus/);
});
