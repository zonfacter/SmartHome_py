'use strict';
window.HeatingPumps=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number=v=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-DE',{maximumFractionDigits:2}):'—';
  const time=ts=>ts?new Intl.DateTimeFormat('de-DE',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'Europe/Berlin'}).format(new Date(ts*1000)):'—';
  const read=(metrics,key)=>metrics[key]?.quality==='valid'?metrics[key].value:null;
  const contact=v=>v===true?'Ein':v===false?'Aus':'Unbekannt';
  const requestAttr=m=>{const raw=read(m,'space_request_raw');return typeof raw==='string'?raw.split(' ').slice(2).join(' '):'—';};
  function field(s){
    if(s.quality!=='valid')return s.quality==='stale'?'Veraltet':'Nicht verfügbar';
    if('producer_present' in s)return s.producer_present?'Erzeuger vorhanden · Statusfeld':'Kein Erzeuger bestätigt · Statusfeld';
    if('temperature_field' in s)return number(s.temperature_field)+' °C · Temperaturfeld';
    if('percent_field' in s)return s.percent_field===null?'Wertbyte '+number(s.value_field)+' · außerhalb 0–100 %':number(s.percent_field)+' % · Wertfeld';
    return 'Wertfeld '+number(s.value_field);
  }
  function signalHtml(s){
    const bits=s.attribute_bits||[],unknown=s.unknown_attribute_bits||[];
    const state='producer_present' in s?('Erzeuger vorhanden: '+(s.producer_present?'ja':'nicht bestätigt')):
      ('Gültigkeitsbit: '+(s.protocol_valid?'gesetzt':'nicht gesetzt'));
    return `<div class="pump-signal"><strong>${esc(s.label)}</strong><span>${esc(field(s))}</span><code>${esc(s.raw||'—')}</code><small>Attribute ${esc(s.attributes_hex||'—')} · Bits ${bits.length?bits.join(', '):'keine gesetzt'}${s.priority_field!==undefined?' · Prioritätsfeld '+s.priority_field:''}</small><p>${esc(s.interpretation)}</p>${s.definition_source?`<small>${esc(state)} · Weitere gesetzte Bits: ${unknown.length?unknown.join(', '):'keine'}<br><a href="${esc(s.definition_source.url)}" target="_blank" rel="noopener noreferrer">Herstellerdefinition · LPB ${s.lpb_object}</a>. ${esc(s.definition_source.scope)}</small>`:''}</div>`;
  }
  function assessmentHtml(d){
    if(!d.assessment)return `<p class="pump-cause">${esc(d.cause)}</p>`;
    const a=d.assessment;
    const labels={consistent:'Messwerte passen zusammen',observed:'Beobachteter Zustand',indication:'Hinweis aus dem Reglerstatus',insufficient:'Datenlage unvollständig',unresolved:'Einordnung offen'};
    return `<h4>Einordnung · ${esc(labels[a.status]||'offen')}</h4><p class="pump-cause">${esc(a.summary)}</p><p class="diagnostic-note">${esc(a.limit)}${a.read_skew_seconds!==null?' Zeitversatz der dafür verwendeten Werte: '+number(a.read_skew_seconds)+' s.':''}</p>`;
  }
  class View{
    constructor(container){this.container=container;this.events={};this.failed=false;this.sequence=0;}
    render(snapshot,view){
      if(!snapshot)return;
      this.snapshot=snapshot;this.view=view;
      const open=new Set([...this.container.querySelectorAll('details[open]')].map(e=>e.dataset.pumpDetail));
      const focused=document.activeElement?.closest('details')?.dataset.pumpDetail;
      HeatingLive.update(this.container,['eg','og'].filter(a=>view==='overview'||view===a).map(area=>{
        const floor=snapshot.floors[area],d=floor.pump_diagnosis;
        if(!d)return '';
        const events=this.events[area]||[];
        return `<article class="diagnostic-card pump-card"><div class="diagnostic-heading"><h3>${area.toUpperCase()} · ${esc(floor.controller)}</h3><span class="diagnostic-status ${d.pump_contact===true?'ok':''}">${esc(d.summary)}</span></div>${assessmentHtml(d)}<div class="pump-facts">${d.facts.map(s=>`<p>${esc(s)}</p>`).join('')}</div>${d.hints.length?`<div class="pump-hints"><h4>Mögliche Einflüsse · nicht bestätigt</h4>${d.hints.map(s=>`<p>${esc(s)}</p>`).join('')}</div>`:''}<p class="diagnostic-note">Kontaktstand ${time(d.observed_at)}${d.read_skew_seconds>15?' · Zeitversatz der gelesenen Signale: '+number(d.read_skew_seconds)+' s':''}. ${esc(d.limits)}</p><details data-pump-detail="${area}-signals" ${open.has(area+'-signals')?'open':''}><summary>Signalwerte & Attribute</summary><p>Anforderungen, Reduktions-/Nachlaufanforderung und Erzeugerstatus sind teilweise nach Herstellerdefinition eingeordnet. Nicht zugeordnete Bits und die genaue Wirkung auf die alten Regler bleiben offen.</p>${d.signals.map(signalHtml).join('')}</details><details data-pump-detail="${area}-events" ${open.has(area+'-events')?'open':''}><summary>Lokaler Mitschnitt · letzte Änderungen</summary><p>Die letzten acht aufgezeichneten Änderungen. Q1 und Signale werden nacheinander abgefragt; Gleichzeitigkeit und Ursachen sind damit nicht bewiesen.</p>${this.failed?'<p>Der Mitschnitt ist momentan nicht erreichbar; letzter Stand wird angezeigt.</p>':''}${events.length?`<div class="pump-event-scroll"><table class="pump-event-table"><thead><tr><th>Zeit</th><th>Q1</th><th>Raumsoll</th><th>Anf.-Attr.</th></tr></thead><tbody>${events.slice(0,8).map(e=>`<tr><td>${time(e.ts)}</td><td>${contact(read(e.metrics,'pump'))}</td><td>${number(read(e.metrics,'room_setpoint'))} °C</td><td><code>${esc(requestAttr(e.metrics))}</code></td></tr>`).join('')}</tbody></table></div>`:'<p>Mit den nächsten Heizungsabfragen entsteht hier ein Mitschnitt. Frühere Zustände werden nicht rückwirkend ergänzt.</p>'}</details></article>`;
      }).join(''));
      if(focused)this.container.querySelector(`details[data-pump-detail="${focused}"] summary`)?.focus({preventScroll:true});
    }
    async load(hours){
      const sequence=++this.sequence;
      try{
        const r=await fetch('/api/heating/pumps?hours='+hours,{cache:'no-store'});
        if(!r.ok)throw Error();
        const d=await r.json();if(sequence!==this.sequence)return;
        this.events=d.events;this.failed=false;
      }catch{if(sequence!==this.sequence)return;this.failed=true;}
      this.render(this.snapshot,this.view);
    }
  }
  return {View};
})();
