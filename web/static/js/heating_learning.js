'use strict';
(()=>{
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
  const time=ts=>new Date(ts*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
  let theme=localStorage.getItem('heating-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.body.dataset.theme=theme;
  $('theme').addEventListener('click',()=>{theme=theme==='dark'?'light':'dark';document.body.dataset.theme=theme;localStorage.setItem('heating-theme',theme);});
  const observer=new HeatingObserverView.View($('beobachtung'));
  $('beobachtung').addEventListener('heating-observer-updated',event=>{
    const data=event.detail,labels={eg:'EG · Fußbodenheizung',og:'OG · Heizkörper',dhw:'Warmwasser · 200 Liter'};
    $('learning-live').classList.toggle('online',data.enabled&&!data.error);
    $('nav-light').classList.toggle('online',data.enabled&&!data.error);
    $('nav-status').textContent=data.error?'Aufzeichnung prüfen':data.last_sample?'Letzte Aufzeichnung '+time(data.last_sample):'Wartet auf Messwerte';
    $('learning-summary').innerHTML=['eg','og','dhw'].map(area=>{
      const model=data.models[area],eligible=(model.rooms||[model]).filter(r=>r.state!=='record_only');
      const validated=eligible.filter(r=>r.state==='validated').length,progress=eligible.length?Math.round(eligible.reduce((total,r)=>total+HeatingObserverView.progress(r),0)/eligible.length):0;
      const pairs=eligible.reduce((total,r)=>total+(r.pairs||0),0);
      const status=!data.enabled?'Aufzeichnung deaktiviert':model.state==='validated'?'Modelle geprüft':model.state==='partly_validated'?'Teilweise geprüft':eligible.some(r=>r.state==='not_validated')?'Weitere Beobachtung nötig':'Sammelt Daten';
      return `<article class="panel learning-card"><span class="eyebrow">${area==='dhw'?'SPEICHERMODELL':'GETRENNTE RAUMMODELLE'}</span><h2>${labels[area]}</h2><strong class="learning-card-state">${status}</strong><progress max="100" value="${progress}" aria-label="${labels[area]} Datengrundlage ${progress} Prozent"></progress><p>${progress} % Datengrundlage · ${validated}/${eligible.length} Modelle geprüft</p><p>${pairs} gültige Zeitfenster${area==='dhw'?'':' über '+eligible.length+(eligible.length===1?' Heizungsraum':' Heizungsräume')}<span class="learning-fit-time"><br>Letzte Auswertung: ${data.trained_at?time(data.trained_at):'noch ausstehend'}</span></p><a href="#beobachtung">Details & Messverläufe ↓</a></article>`;
    }).join('');
  });
  const parts=Object.fromEntries(new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).map(p=>[p.type,p.value]));
  $('meter-date').value=`${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
  let meterSequence=0;
  async function loadMeter(){
    const seq=++meterSequence;
    try{
      const response=await fetch('/api/heating/gas-readings',{cache:'no-store'});if(!response.ok)throw Error();
      const data=await response.json();if(seq!==meterSequence)return;
      $('meter-latest').textContent=data.latest?data.latest.volume_text+' m³':'—';$('meter-last-time').textContent=data.latest?time(data.latest.ts):'Noch kein Stützwert';$('meter-count').textContent=number(data.count,0);
      const interval=data.latest_interval;
      $('meter-delta').textContent=interval?number(interval.measured_m3,3)+' m³':'—';
      $('meter-interval').textContent=interval?`${time(interval.from)} bis ${time(interval.to)}`:'Ab zwei Stützwerten verfügbar';
      $('meter-readings').innerHTML=data.readings.length?data.readings.map((r,i)=>`<tr><td>${time(r.ts)}</td><td>${esc(r.volume_text)} m³</td><td>${data.readings[i+1]?number(r.volume_m3-data.readings[i+1].volume_m3,3)+' m³':data.count>data.readings.length?'Älterer Stützwert außerhalb dieser Liste':'Ausgangsstand'}</td></tr>`).join(''):'<tr><td colspan="3">Noch keine Ablesung gespeichert.</td></tr>';
      if(interval){
        const reference=interval.relay_reference;
        $('meter-comparison').textContent=`Gemessen: ${number(interval.measured_m3,3)} m³ in ${number(interval.hours)} Stunden. Brennerrelais: ${number(reference.relay_minutes)} Minuten bei ${number(reference.coverage_percent)} % Datenabdeckung. Beispielrechnung auf Nennleistung/angenommenem Heizwert: ${number(reference.gas_equivalent_nm3,3)} Nm³ – Normvolumen, daher nicht direkt mit den Zähler-m³ gleichzusetzen. Nur Abgleich; keine automatische Kalibrierung oder Veränderung der Heizung.`;
      }else $('meter-comparison').textContent='Der erste Stützwert bildet die Ausgangsbasis. Erst eine weitere Ablesung ergibt einen gemessenen Verbrauch. Keine Zwischenstände werden interpoliert, kein Gasverbrauch wird einem einzelnen Heizkreis zugeschrieben.';
    }catch{if(seq===meterSequence)$('meter-feedback').textContent='Zählerstände sind momentan nicht erreichbar; letzter Stand bleibt sichtbar.';}
  }
  $('gas-meter-form').addEventListener('submit',async event=>{
    event.preventDefault();$('meter-save').disabled=true;$('meter-feedback').textContent='Stützwert wird gespeichert …';
    try{
      const response=await fetch('/api/heating/gas-readings',{method:'POST',headers:{'Content-Type':'application/json','X-Heating-Meter':'1'},body:JSON.stringify({measured_at:$('meter-date').value,volume_m3:$('meter-volume').value})});
      const result=await response.json();if(!response.ok)throw Error(result.message||'Speichern fehlgeschlagen.');
      $('meter-feedback').textContent=result.inserted?'Stützwert gespeichert. Heizungsregelung unverändert.':'Dieser Stützwert ist bereits gespeichert.';
      $('meter-volume').value='';await loadMeter();
    }catch(error){$('meter-feedback').textContent=error.message||'Speichern fehlgeschlagen.';}
    finally{$('meter-save').disabled=false;}
  });
  async function refresh(){$('learning-refresh').disabled=true;try{await Promise.all([observer.load(),loadMeter()]);}finally{$('learning-refresh').disabled=false;}}
  $('learning-refresh').addEventListener('click',refresh);refresh();
  setInterval(()=>{if(!document.hidden)refresh();},30000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
})();
