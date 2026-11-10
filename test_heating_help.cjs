const test=require('node:test');
const assert=require('node:assert/strict');
const {getHelp,guideChecks,button,format}=require('./web/static/js/heating_help.js');
const item=(value,quality='valid',unit='')=>({value,quality,unit});
const snapshot=metrics=>({floors:{eg:{metrics}},plant:{}});

test('enabled influence with unavailable room source is explained without substituting a temperature',()=>{
  const s=snapshot({room_influence:item(true),room_actual:item(null,'unavailable')});
  const help=getHelp('room_influence','eg',s);
  assert.equal(help.current,'Ein');
  assert.ok(help.notes.some(n=>n.includes('kein gültiger Raumfühlerwert')));
  const checks=guideChecks(s,'eg');
  assert.ok(checks.some(c=>c.title==='Raumeinfluss prüfen'));
  assert.equal(checks[0].value,'Kein gültiger Wert geliefert');
});

test('unknown and stale sensor status never claims a confirmed missing sensor',()=>{
  for(const quality of ['pending','stale','error']){
    const s=snapshot({room_influence:item(true),room_actual:item(20,quality)});
    assert.ok(getHelp('room_influence','eg',s).notes.some(n=>n.includes('noch nicht verlässlich')));
    assert.ok(!guideChecks(s,'eg').some(c=>c.title==='Raumeinfluss prüfen'));
  }
});

test('disabled room influence keeps stored factor separate from active correction',()=>{
  const s=snapshot({room_influence:item(false),room_gain:item(4),room_actual:item(20)});
  const h=getHelp('room_gain','eg',s);
  assert.equal(h.current,'4');
  assert.ok(h.notes.some(n=>n.includes('gespeicherter Wert')));
});

test('disabled adaptation is described as disabled in the setup guide',()=>{
  const checks=guideChecks(snapshot({adaptation:item(false)}),'eg');
  const adaptation=checks.find(c=>c.title==='Heizkurvenadaption');
  assert.equal(adaptation.value,'Aus');
  assert.ok(adaptation.note.includes('Aus gemeldet'));
  assert.ok(!adaptation.note.includes('aktivierte'));
});

test('live values preserve units and unavailable values are never displayed as zero',()=>{
  assert.equal(format(item(8,'valid','°C')),'8 °C');
  assert.equal(format(item(null,'unavailable','°C')),'Kein gültiger Wert geliefert');
  assert.equal(format(item(20,'stale','°C')),'Veraltet');
  assert.equal(format(item(false)),'Aus');
});

test('unmapped raw signal help does not claim active demand or decoded attributes',()=>{
  const h=getHelp('forced_producer_raw','eg',snapshot({forced_producer_raw:item('32 00')}));
  assert.ok(h.check.includes('keine gesicherte Aussage'));
  assert.equal(h.current,'32 00');
  assert.ok(getHelp('quick_setback','eg',snapshot({})).check.includes('kein aktiver'));
});

test('help button labels are escaped and keyboard accessible',()=>{
  const html=button('curve','eg','Kurve <img onerror="x">');
  assert.ok(html.includes('type="button"'));
  assert.ok(html.includes('aria-haspopup="dialog"'));
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&lt;img'));
});
