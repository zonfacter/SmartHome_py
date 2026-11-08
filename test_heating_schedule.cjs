'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {parse,validate,targetDays,validDraft}=require('./web/static/js/heating_schedule.js');
test('midnight and ten-minute ranges retain exact minutes',()=>{
  assert.equal(parse('24:00'),1440);
  assert.deepEqual(validate([{start:'05:10',end:'06:30'},{start:'15:00',end:'24:00'}],true),[
    {start:'05:10',end:'06:30',start_minute:310,end_minute:390},
    {start:'15:00',end:'24:00',start_minute:900,end_minute:1440}]);
  assert.deepEqual(validate([],true),[]);
});
test('invalid, reversed, overlapping and too many phases are rejected',()=>{
  for (const value of ['6:00','25:00','24:01','12:60','-1:00','06:00<script>']) assert.throws(()=>parse(value));
  for (const phases of [
    [{start:'24:00',end:'24:00'}], [{start:'06:00',end:'06:00'}],
    [{start:'20:00',end:'06:00'}], [{start:'06:00',end:'08:00'},{start:'07:45',end:'09:00'}],
    Array.from({length:4},()=>({start:'06:00',end:'07:00'})), [{start:'06:01',end:'08:00'}], [{start:'06:15',end:'08:00'}]
  ]) assert.throws(()=>validate(phases,true));
  assert.equal(validate([{start:'06:01',end:'08:02'}])[0].start_minute,361);
});
test('day copies affect exactly the selected set',()=>{
  assert.deepEqual(targetDays(3,'day'),[3]);
  assert.deepEqual(targetDays(2,'weekdays'),[0,1,2,3,4]);
  assert.deepEqual(targetDays(0,'weekend'),[5,6]);
  assert.equal(targetDays(0,'week').length,7);
  assert.throws(()=>targetDays(7,'day')); assert.throws(()=>targetDays(0,'other'));
});
test('persisted drafts must match the schema and contain seven valid days',()=>{
  const draft={version:1,area:'eg',base:'source',days:Array.from({length:7},()=>[{start:'06:00',end:'20:00'}])};
  assert.equal(validDraft(draft).days[6][0].end_minute,1200);
  for (const value of [null,{}, {...draft,area:'plant'}, {...draft,version:2}, {...draft,days:[]},
    {...draft,days:[...draft.days.slice(0,6),[{start:'22:00',end:'06:00'}]]}]) assert.equal(validDraft(value),null);
});
