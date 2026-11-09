const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const help=require('./web/static/js/heating_help.js');
const item=(value,kind='temperature',unit='')=>({value,kind,unit,quality:'valid',label:'Testwert'});

test('new diagnostic rows and interpretation help render without controls or losing unknown codes',()=>{
  let html='';
  const nodes={};
  const context={window:{},HeatingHelp:help,HeatingLive:{update:(_,s)=>{html=s;}},
    document:{activeElement:null,getElementById:id=>(nodes[id]??={})}};
  vm.runInNewContext(fs.readFileSync('web/static/js/heating_diagnostics.js','utf8'),context);
  const container={querySelectorAll:()=>[]};
  const view=new context.window.HeatingDiagnostics.View(container);
  view.render({plant:{dhw_request_source:item('Speicherfühler','dhw_request_source'),
    burner_type:item('Code 1','burner_type'),stage2_release_integral:item(10,'integral','K·min')},
    floors:{eg:{metrics:{}},og:{metrics:{}}}},'overview');
  assert.ok(html.includes('Speicherfühler'));
  assert.ok(html.includes('Code 1'));
  assert.ok(html.includes('10 K·min'));
  assert.ok(!html.includes('<input'));
  assert.ok(help.getHelp('dhw_dedicated','anlage',{}).check.includes('Zirkulationsleitung'));
  assert.ok(help.getHelp('burner_type','anlage',{}).check.includes('tatsächlich angeschlossene'));
});

test('stored adaptation factors are distinguished from VM learning and inactive adaptation',()=>{
  const snapshot={floors:{og:{metrics:{adaptation:item(false),adaptation_zaf1:item(15)}}}};
  const info=help.getHelp('adaptation_zaf1','og',snapshot);
  assert.ok(info.notes.some(n=>n.includes('Aus gemeldet')));
  assert.ok(info.check.includes('Lernfortschritt'));
});

test('signal definition text is displayed and escaped without declaring a proven pump cause',()=>{
  let html='';
  const context={window:{},HeatingLive:{update:(_,s)=>{html=s;}},
    document:{activeElement:null}};
  vm.runInNewContext(fs.readFileSync('web/static/js/heating_pumps.js','utf8'),context);
  const view=new context.window.HeatingPumps.View({querySelectorAll:()=>[]});
  view.render({floors:{eg:{controller:'M',pump_diagnosis:{summary:'Q1 ausgeschaltet',cause:'Schaltgrund offen',
    pump_contact:false,observed_at:1,read_skew_seconds:30,limits:'Grenzen',facts:[],hints:[],
    signals:[{quality:'valid',label:'Sperre',raw:'64 01',percent_field:100,attributes_hex:'0x01',attribute_bits:[0],
      interpretation:'Reduktion <script>unsafe</script>',lpb_object:504,protocol_valid:true,unknown_attribute_bits:[],
      definition_source:{url:'https://example.invalid/source',scope:'Genaue Wirkung offen'}}]}}}},'eg');
  assert.ok(html.includes('Gültigkeitsbit: gesetzt'));
  assert.ok(html.includes('Schaltgrund offen'));
  assert.ok(html.includes('&lt;script&gt;unsafe&lt;/script&gt;'));
  assert.ok(!html.includes('<script>unsafe'));
});
