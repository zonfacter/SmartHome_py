const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context={window:{}};
vm.runInNewContext(fs.readFileSync('web/static/js/heating_observer.js','utf8'),context);
const {progress}=context.window.HeatingObserverView;
const {windowView}=context.window.HeatingObserverView;

test('window learning status keeps unknown and open excluded and reports bounded counts',()=>{
  assert.match(windowView({state:'open',quality:'valid'}),/Fenster offen/);
  assert.match(windowView({state:'closed',quality:'stale'}),/unbekannt/);
  assert.match(windowView(undefined),/unbekannt/);
  assert.match(windowView({state:'closed',quality:'valid',source:'tado_detection',training_allowed:true}),/unbekannt/);
  assert.match(windowView({state:'closed',quality:'valid',source:'contact',training_allowed:false}),/Erholungsphase/);
  assert.match(windowView({state:'closed',quality:'valid',source:'contact',training_allowed:true}),/Trainingsfreigabe/);
  const text=windowView(undefined,{excluded_open:3,excluded_unknown:'<script>',excluded_recovery:-5});
  assert.match(text,/3 Lüftung · 0 unbekannt · 0 Erholung/);
  assert.doesNotMatch(text,/<script>/);
});
test('data readiness reflects the weakest requirement, including heating and cooling',()=>{
  const complete={state:'collecting',pairs:48,days:3,span_hours:48,heated_pairs:6,cooling_pairs:6};
  assert.equal(progress(complete),100);
  assert.equal(progress({...complete,cooling_pairs:0}),0);
  assert.equal(progress({...complete,span_hours:24}),50);
  assert.equal(progress({...complete,pairs:24}),50);
  assert.equal(progress({state:'collecting'}),0);
  assert.equal(progress({state:'validated'}),100);
});
