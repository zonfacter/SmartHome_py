const test=require('node:test');const assert=require('node:assert/strict');
const s=require('./web/static/js/heating_symbols.js'),p=require('./web/static/js/heating_plan.js');
const node=(id,type,x=300,y=300,rotation=0)=>({id,type,x,y,rotation,port_layout:'hydronic',label:'',note:'',sensor:''});
test('equipment has functional ports and the tank coil remains separate from drinking-water ports',()=>{
  assert.deepEqual(s.ports(node('b','boiler')).map(p=>p.label),['VL','RL']);
  assert.deepEqual(s.ports(node('t','tank')).map(p=>p.id),['dhw','circulation','cold','coil_flow','coil_return']);
  assert.equal(s.ports(node('p','pump')).length,2);assert.equal(s.ports(node('m','mixer')).length,3);
  assert.equal(s.ports(node('e','expansion_vessel')).length,1);assert.equal(s.ports(node('l','label')).length,0);
  for(const type of Object.keys(s.types)){const n=node('x',type);assert.equal(new Set(s.ports(n).map(p=>p.id)).size,s.ports(n).length);if(type!=='label')assert.ok(s.symbol(n).length>30);}
});
test('ports rotate with equipment while names and identity remain intact',()=>{
  const n=node('b','boiler',300,300,90);assert.deepEqual(s.anchor(n,'flow'),{x:330,y:380});assert.deepEqual(s.normal(n,'flow'),{x:0,y:1});
  assert.equal(s.ports(n)[0].label,'VL');const b=s.bounds(n);assert.ok(b.bottom>=380);
});
test('legacy cardinal anchors remain at their original positions',()=>{
  const old={id:'old',type:'tank',x:100,y:100,rotation:0};assert.deepEqual(s.anchor(old,'e'),{x:152,y:100});
  const imported=p.cleanImport({title:'Altbestand',nodes:[old],edges:[]});assert.equal(imported.nodes[0].port_layout,'legacy');assert.deepEqual(s.anchor(imported.nodes[0],'e'),{x:152,y:100});
});
test('named-port plans round-trip without losing documented flow direction or pipe media',()=>{
  const raw={schema:2,title:'Schema',nodes:[node('b','boiler'),node('t','tank',700,600)],edges:[{id:'e',from:{node:'b',port:'flow'},to:{node:'t',port:'coil_flow'},medium:'hot',flow:'forward',points:[]}]};
  const normalized=p.cleanImport(raw);assert.equal(p.stable(p.cleanImport(normalized)),p.stable(normalized));
  for(const mutate of [d=>d.edges[0].to.port='n',d=>d.edges[0].flow='javascript',d=>d.nodes[0].port_layout='guess',d=>d.schema=3]){const d=structuredClone(raw);mutate(d);assert.throws(()=>p.cleanImport(d));}
});
test('orthogonal paths leave rotated ports along their outward normals',()=>{
  for(const rotation of [0,90,180,270]){const a=node('a','boiler',200,200,rotation),b=node('b','tank',700,600),e={from:{node:'a',port:'flow'},to:{node:'b',port:'coil_flow'},points:[]},points=p.pipePoints({nodes:[a,b]},e),normal=s.normal(a,'flow');
    assert.equal(points[1].x-points[0].x,normal.x*24);assert.equal(points[1].y-points[0].y,normal.y*24);
    for(let i=1;i<points.length;i++)assert.ok(points[i].x===points[i-1].x||points[i].y===points[i-1].y);
  }
});
test('crossings get a bridge without changing connectivity; endpoint junctions do not',()=>{
  const vertical=[{x:100,y:0},{x:100,y:200}],horizontal=[{x:0,y:100},{x:200,y:100}],snapshot=JSON.stringify([vertical,horizontal]);
  assert.match(p.crossingPath(horizontal,[vertical]),/Q/);assert.match(p.crossingPath(vertical,[horizontal]),/Q/);
  assert.doesNotMatch(p.crossingPath([{x:100,y:100},{x:200,y:100}],[vertical]),/Q/);
  assert.equal(JSON.stringify([vertical,horizontal]),snapshot);
});
test('flow arrows are explicit, reverse correctly and do not appear on an unassigned pipe',()=>{
  const points=[{x:0,y:0},{x:100,y:0}];assert.equal(p.flowArrow(points,'none'),'');assert.match(p.flowArrow(points,'forward'),/^57,0/);assert.match(p.flowArrow(points,'reverse'),/^43,0/);
  assert.notEqual(s.media.hot.dash,s.media.cold.dash);assert.notEqual(s.media.dhw.dash,s.media.dhw_circulation.dash);
});
