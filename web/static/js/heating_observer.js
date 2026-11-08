'use strict';
window.HeatingObserverView=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-DE',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
  const time=ts=>ts?new Date(ts*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
  const state={collecting:'Sammelt Daten',validated:'Modell geprüft',partly_validated:'Teilweise geprüft',not_validated:'Weitere Beobachtung nötig',record_only:'Nur Aufzeichnung'};
  class View{
    constructor(container){
      this.container=container;this.data=null;this.samples=[];this.sequence=0;this.hours=24;
      this.$=id=>container.querySelector('#'+id);
      this.$('observer-area').addEventListener('change',()=>{this.rooms();this.chart();});
      this.$('observer-room').addEventListener('change',()=>this.chart());
      container.querySelectorAll('[data-observer-hours]').forEach(b=>b.addEventListener('click',()=>{this.hours=Number(b.dataset.observerHours);container.querySelectorAll('[data-observer-hours]').forEach(x=>x.classList.toggle('selected',x===b));this.load();}));
    }
    setView(view){if(view==='eg'||view==='og'){this.$('observer-area').value=view;this.rooms();this.chart();}}
    async load(){
      const seq=++this.sequence;
      try{
        const responses=await Promise.all([fetch('/api/heating/observer?hours='+this.hours,{cache:'no-store'}),fetch('/api/heating/observer/history?hours='+this.hours,{cache:'no-store'})]);
        if(responses.some(r=>!r.ok))throw Error();
        const [data,history]=await Promise.all(responses.map(r=>r.json()));if(seq!==this.sequence)return;
        this.data=data;this.samples=history.samples;this.render();
      }catch{if(seq===this.sequence)this.$('observer-note').textContent='Beobachtungsdaten sind momentan nicht erreichbar; letzter Stand bleibt sichtbar.';}
    }
    render(){
      const d=this.data,energy=d.energy_reference;
      this.$('observer-state').textContent=d.enabled?'Beobachtungsmodus aktiv':'Noch nicht eingerichtet';
      this.$('observer-count').textContent=number(d.sample_count,0);
      this.$('observer-span').textContent=number(d.span_hours)+' h';
      this.$('observer-last').textContent='Letzte Aufzeichnung '+time(d.last_sample);
      this.$('observer-runtime').textContent=number(energy.relay_minutes)+' min';
      this.$('observer-energy').textContent=number(energy.rated_input_reference_kwh_hi,2)+' kWh (Hi)';
      this.$('observer-gas').textContent=number(energy.gas_equivalent_nm3,3)+' Nm³';
      this.$('observer-energy-note').textContent=`Nur im beobachteten Abschnitt: ${number(energy.coverage_percent)} % Abdeckung des ${this.hours}-h-Fensters. Nennleistungsrechnung, nicht gemessener Verbrauch. Keine Hochrechnung für Datenlücken.`;
      const reference=d.assumptions||{};
      this.$('observer-reference').textContent=`${reference.model||'Kesseltyp nicht hinterlegt'} · Belastung ${number(reference.rated_input_hi_kw)} kW (Hi), Wärmeleistung ${number(reference.rated_output_kw)} kW. Beispiel-Heizwert ${number(reference.assumed_hi_kwh_per_nm3)} kWh/Nm³, aktuelles Gas nicht vermessen. Volle Nennbelastung während jeder erfassten Relaisminute angenommen; Stufenleistung unbestätigt. Normvolumen, kein Gaszähler-/Abrechnungswert. Abgasverlust wird nicht als Nutzungsgrad verwendet.`;
      const note=!d.enabled?'Die Aufzeichnung ist deaktiviert.':d.error?'Aufzeichnung oder Lernen meldet '+d.error+'. Bestehende Reglerprogramme werden weiterhin eigenständig ausgeführt.':'Die VM zeichnet nach Dienststart auch ohne geöffneten Browser auf. Modelle werten frühestens drei Tage und 48 gültige Zeitfenster mit Heiz- und Abkühlphasen aus. Heizzeiten und Einstellungen werden nicht verändert.';
      this.$('observer-note').textContent=note;
      this.$('observer-models').innerHTML=['eg','og','dhw'].map(area=>{
        const m=d.models[area],rooms=m.rooms||[];
        const title=area==='eg'?'EG · Fußbodenheizung':area==='og'?'OG · Heizkörper':'Warmwasser · '+(m.tank_litres||'—')+' Liter';
        return `<article class="observer-model"><div class="diagnostic-heading"><h3>${title}</h3><span class="diagnostic-status ${m.state==='validated'?'ok':''}">${state[m.state]||'Sammelt Daten'}</span></div><p>${esc(m.input_note||'')}</p>${rooms.length?rooms.map(r=>`<div class="observer-model-row"><strong>${esc(r.name)}</strong><span>${state[r.state]||'Sammelt Daten'}${r.pairs!==undefined?' · '+r.pairs+' Zeitfenster':''}</span><small>${esc(r.reason||'')}${r.validation_mae_c!==undefined?' Prüfabweichung: '+number(r.validation_mae_c,3)+' °C; Vergleich: '+number(r.persistence_mae_c,3)+' °C.':''}</small></div>`).join(''):`<div class="observer-model-row"><strong>${number(m.pairs||0,0)} gültige Zeitfenster</strong><small>${esc(m.reason||'Raumdaten werden gesammelt.')}${m.validation_mae_c!==undefined?' Prüfabweichung: '+number(m.validation_mae_c,3)+' °C.':''}</small></div>`}</article>`;
      }).join('');
      this.rooms();this.chart();
    }
    rooms(){
      const area=this.$('observer-area').value,select=this.$('observer-room');
      select.parentElement.hidden=area==='dhw';if(area==='dhw')return;
      const rooms=(this.data?.rooms||[]).filter(r=>r.floor===area),signature=JSON.stringify(rooms.map(r=>[r.id,r.name]));
      if(signature===this.roomSignature)return;this.roomSignature=signature;
      const selected=select.value;
      select.innerHTML=rooms.map(r=>`<option value="${esc(r.id)}">${esc(r.name)}${r.type==='AIR_CONDITIONING'?' · Klima-Sensor':''}</option>`).join('');
      if(rooms.some(r=>r.id===selected))select.value=selected;
    }
    chart(){
      const area=this.$('observer-area').value,id=this.$('observer-room').value;
      const rows=this.samples.map(s=>{
        if(area==='dhw')return {ts:s.ts,a:s.plant.dhw.q==='valid'?s.plant.dhw.v:null,b:s.plant.dhw_setpoint.q==='valid'?s.plant.dhw_setpoint.v:null};
        const room=s.rooms.find(r=>r.id===id);
        return {ts:s.ts,a:room?.quality.temperature==='valid'?room.temperature:null,b:room?.quality.setpoint==='valid'?room.setpoint:null};
      });
      this.$('observer-legend').textContent=area==='dhw'?'Speichertemperatur · Nennvorgabe (nicht zwingend aktiver Sollwert)':'Raumtemperatur · Tado-Sollvorgabe';
      const nums=rows.flatMap(r=>[r.a,r.b]).filter(n=>typeof n==='number'&&Number.isFinite(n));
      if(rows.length<2||!nums.length){this.$('observer-chart').innerHTML='<div class="empty-chart"><strong>Der Verlauf entsteht ab jetzt.</strong><span>Keine Tado-Vergangenheit wird erfunden oder rückwirkend ergänzt.</span></div>';return;}
      const w=Math.max(300,this.$('observer-chart').clientWidth),h=170,lo=Math.floor(Math.min(...nums))-1,hi=Math.ceil(Math.max(...nums))+1;
      const first=rows[0].ts,span=Math.max(1,rows.at(-1).ts-first),x=t=>35+(t-first)/span*(w-47),y=v=>140-(v-lo)/(hi-lo)*125;
      let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Aufgezeichnete Temperaturen und Sollvorgaben">`;
      for(let i=0;i<4;i++){const v=lo+(hi-lo)*i/3;svg+=`<line x1="35" x2="${w-12}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="0" y="${y(v)+3}" font-size="9" fill="var(--muted)">${number(v)}°</text>`;}
      for(const [key,color,dash] of [['a','#269274',''],['b','#dda56e','5 4']]){
        let path='',last=null;
        for(const row of rows){if(typeof row[key]!=='number'){last=null;continue;}path+=`${last===null||row.ts-last>Math.max(180,this.hours*3600/180)?'M':'L'}${x(row.ts).toFixed(1)},${y(row[key]).toFixed(1)} `;last=row.ts;}
        svg+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="${dash}"/>`;
      }
      for(let i=0;i<4;i++)svg+=`<text x="${x(first+span*i/3)}" y="164" font-size="9" fill="var(--muted)" text-anchor="${i===0?'start':i===3?'end':'middle'}">${time(first+span*i/3).split(', ').at(-1)}</text>`;
      this.$('observer-chart').innerHTML=svg+'</svg>';
    }
  }
  return {View};
})();
