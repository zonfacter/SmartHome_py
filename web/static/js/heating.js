'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const numeric = value => typeof value === 'number' && Number.isFinite(value);
  const number = (value, digits = 1) => numeric(value) ? value.toLocaleString('de-DE', {minimumFractionDigits: digits, maximumFractionDigits: digits}) : '—';
  const valid = metric => metric && metric.quality === 'valid';
  const value = metric => valid(metric) ? metric.value : null;
  const text = metric => !valid(metric) ? '—' : typeof metric.value === 'boolean' ? (metric.value ? 'Ein' : 'Aus') : numeric(metric.value) ? number(metric.value, ['curve','gain','minutes','counter'].includes(metric.kind) && metric.kind !== 'curve' ? 0 : 1) : metric.value;
  const formatTime = ts => new Intl.DateTimeFormat('de-DE', {hour:'2-digit', minute:'2-digit', timeZone:'Europe/Berlin'}).format(new Date(ts * 1000));
  let snapshot = null, view = 'overview', hours = 6, historySequence = 0, inFlight = false, expanded = new Set();
  let theme = localStorage.getItem('heating-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.body.dataset.theme = theme;
  const initialView = new URLSearchParams(location.search).get('etage');
  if (['eg','og'].includes(initialView)) view = initialView;

  function stat(id, metric, unit = '°C') {
    const el = $(id); el.innerHTML = escape(text(metric)) + (unit ? `<small>${escape(unit)}</small>` : '');
    el.classList.toggle('is-stale', metric?.quality === 'stale');
    el.title = metric?.quality === 'stale' ? 'Letzter Messwert ist veraltet' : metric?.quality === 'unavailable' ? 'Kein gültiger Messwert vom Regler' : '';
  }
  function setting(label, metric) {
    return `<div class="setting"><span>${escape(label)}</span><strong>${escape(text(metric))}${valid(metric) && metric.unit ? ' ' + escape(metric.unit) : ''}</strong></div>`;
  }
  function floorCard(area) {
    const floor = snapshot.floors[area], m = floor.metrics, eg = area === 'eg';
    const current = eg ? m.flow_actual : m.room_setpoint;
    const target = eg ? m.flow_setpoint : snapshot.plant.boiler;
    const pump = value(m.pump), open = value(m.mixer_open), close = value(m.mixer_close);
    const mixerText = open === true && close === true ? 'Mischermeldung prüfen' : open === true ? 'Mischer öffnet' : close === true ? 'Mischer schließt' : open === false && close === false ? 'Mischerantrieb aus' : 'Mischer nicht verfügbar';
    const low = value(m.flow_min), high = value(m.flow_max), actual = value(m.flow_actual);
    const position = numeric(low) && numeric(high) && numeric(actual) && high > low ? Math.min(100, Math.max(0, (actual - low) / (high - low) * 100)) : null;
    const basic = [setting('Heizkurve', m.curve),setting('Raumeinfluss', m.room_influence),setting('Komfortsollwert',m.nominal),setting('Adaption',m.adaptation)].join('');
    const detail = ['parallel','room_gain','differential','summer','reduced','frost','boost','overrun','flow_min','flow_max'].filter(k=>m[k]).map(k=>setting(m[k].label,m[k])).join('');
    return `<article class="floor-card ${area} ${expanded.has(area) ? 'expanded' : ''}"><div class="floor-header"><div class="floor-avatar">${area.toUpperCase()}</div><div><h3>${escape(floor.name)}</h3><p>${eg ? 'Fußbodenheizung · gemischter Heizkreis' : 'Heizkörper · eigener Heizkreis'}</p></div><span class="floor-controller">${escape(floor.controller)}</span></div>
      <div class="floor-body"><div class="floor-reading"><div><div class="reading-caption">${eg ? 'Vorlauftemperatur' : 'Aktueller Raumsollwert'}</div><div class="reading-number">${escape(text(current))}<small>°C</small></div></div><div class="target">${eg ? 'Vorlaufsollwert' : 'Kesseltemperatur'}<br><strong>${escape(text(target))}</strong> °C</div></div>
      <div class="status-pills"><span class="pill ${pump === true ? 'on' : ''}">${pump === true ? 'Pumpe ein' : pump === false ? 'Pumpe aus' : 'Pumpe unbekannt'}</span><span class="pill ${value(m.mode) === 'Automatik' ? 'on' : ''}">${escape(text(m.mode))}</span>${eg ? `<span class="pill ${open || close ? 'on' : ''}">${mixerText}</span>` : ''}</div>
      ${eg ? `<div class="temperature-range"><div class="range-track">${position !== null ? `<i class="range-marker" style="left:calc(${position.toFixed(1)}% - 5px)"></i>` : ''}</div><div class="range-labels"><span>Min. ${escape(text(m.flow_min))} °C</span><span>Max. ${escape(text(m.flow_max))} °C</span></div></div>` : '<p class="sensor-note" style="margin-bottom:20px">Der Raumsollwert ist die Vorgabe des Reglers. Gemessene Raumtemperaturen findest du weiter unten bei Tado.</p>'}
      <div class="settings">${basic}<div class="detail-settings">${detail}</div></div>
      ${eg && m.room_actual?.quality === 'unavailable' ? '<div class="sensor-note">Am Regler liegt aktuell kein gültiger Raumfühlerwert vor.</div>' : ''}</div>
      <div class="floor-footer"><span>${area.toUpperCase()} · ${escape(floor.controller)} · LPB</span><button data-details="${area}" aria-expanded="${expanded.has(area)}">${expanded.has(area) ? 'Weniger Details −' : 'Alle Einstellungen +'}</button></div></article>`;
  }
  function renderFloors() {
    if (!snapshot) return;
    const focusedDetails = document.activeElement?.dataset.details;
    $('floor-grid').innerHTML = ['eg','og'].filter(f=>view === 'overview' || view === f).map(floorCard).join('');
    $('floor-grid').style.gridTemplateColumns = view === 'overview' ? '' : 'minmax(0,1fr)';
    document.querySelectorAll('[data-details]').forEach(button=>button.addEventListener('click',()=>{const area=button.dataset.details; expanded.has(area) ? expanded.delete(area) : expanded.add(area); renderFloors();}));
    if (focusedDetails) document.querySelector(`[data-details="${focusedDetails}"]`)?.focus({preventScroll:true});
  }
  function renderRooms() {
    if (!snapshot) return;
    const rooms = snapshot.rooms.filter(r=>view === 'overview' || r.floor === view);
    $('rooms-grid').innerHTML = rooms.length ? rooms.map(room=>`<article class="room-card ${room.stale ? 'stale' : ''}"><div class="room-top"><span>${escape(room.name)}</span><span class="room-floor">${room.floor === 'eg' ? 'Erdgeschoss' : room.floor === 'og' ? 'Obergeschoss' : room.floor === 'kg' ? 'Keller' : 'Etage offen'}</span></div><div class="room-temp">${number(room.temperature)}<small>°C</small></div><div class="room-bottom"><span>${numeric(room.setpoint) ? 'Soll ' + number(room.setpoint) + ' °C' : 'Kein Raumsollwert'}</span><span>${room.stale ? 'Veraltet' : numeric(room.humidity) ? number(room.humidity,0) + ' % Feuchte' : 'Tado'}</span></div></article>`).join('') : '<div class="panel empty-rooms">'+ (snapshot.iobroker.connected ? (view === 'overview' ? 'Keine Tado-Raumtemperaturen verfügbar.' : 'Dieser Etage sind noch keine Tado-Räume zugeordnet.') : 'Raumtemperaturen sind verfügbar, sobald ioBroker verbunden ist.') + '</div>';
    const connected = snapshot.iobroker.tado_connected;
    $('tado-status').textContent = connected ? '● Über ioBroker verbunden' : 'Tado nicht verbunden';
    $('tado-status').classList.toggle('online',!!connected);
  }
  const scheduleView = new HeatingSchedules.View($('schedule-table'), $('schedule-editor'), localStorage);
  function renderSchedule() { scheduleView.render(snapshot, view); }
  const diagnostics=new HeatingDiagnostics.View($('diagnostics'));
  function render() {
    const p = snapshot.plant, connected = snapshot.connection.connected;
    stat('boiler',p.boiler); stat('dhw',p.dhw); stat('outside',snapshot.floors.eg.metrics.outside); stat('burner',p.burner,'');
    $('burner').textContent = !valid(p.burner) || !valid(p.burner_stage2) ? '—' : p.burner.value && p.burner_stage2.value ? 'Stufe 1 + 2' : p.burner.value ? 'Stufe 1' : p.burner_stage2.value ? 'Stufe 2' : 'Aus';
    $('burner').title = 'Gemeldete Relaiskontakte K4/K5, keine Flammenmessung';
    $('dhw-target').textContent = 'Soll ' + text(p.dhw_setpoint) + ' °C' + (valid(p.dhw_pump) ? ' · Ladepumpe ' + (p.dhw_pump.value ? 'ein' : 'aus') : '');
    $('burner-starts').textContent = valid(p.starts) ? number(p.starts.value,0) + ' Brennerstarts' : 'Kein Zählerwert verfügbar';
    $('live-tag').classList.toggle('online',connected); $('live-tag').querySelector('span').textContent = connected ? 'Heizung verbunden' : 'Heizung offline';
    $('nav-light').classList.toggle('online',connected); $('nav-status').textContent = connected ? 'K und M verbunden' : 'Verbindung unterbrochen';
    $('connection-note').hidden = connected;
    $('connection-note').textContent = !snapshot.enabled ? 'Die Heizungsanbindung ist noch nicht eingerichtet.' : (snapshot.connection.message + '. Vorhandene Werte werden nach Ablauf ihrer Gültigkeit als veraltet markiert.');
    const io = snapshot.iobroker.connected;
    $('io-light').classList.toggle('online',io); $('io-status').textContent = io ? 'ioBroker verbunden · Heizungswerte synchronisiert' : 'ioBroker nicht verbunden';
    $('updated').textContent = snapshot.connection.last_success ? 'Letzte Heizungsabfrage ' + formatTime(snapshot.connection.last_success) : 'Warte auf Heizungsdaten';
    renderFloors(); renderRooms(); renderSchedule(); diagnostics.render(snapshot,view);
  }
  async function load() {
    if (inFlight) return;
    inFlight=true; $('refresh').disabled=true;
    try { const response=await fetch('/api/heating/state',{cache:'no-store'}); if(!response.ok) throw Error(); snapshot=await response.json(); render(); }
    catch { $('connection-note').hidden=false; $('connection-note').textContent='Die SmartHome-VM ist gerade nicht erreichbar. Anzeige wird automatisch erneut geladen.'; $('live-tag').classList.remove('online'); $('live-tag').querySelector('span').textContent='Anzeige offline'; }
    finally { inFlight=false; $('refresh').disabled=false; }
  }
  async function history() {
    const sequence=++historySequence;
    try {
      const response=await fetch('/api/heating/history?hours='+hours,{cache:'no-store'}); if(!response.ok) throw Error();
      const data=await response.json(), samples=data.samples;
      if(sequence!==historySequence)return;
      const weather=$('history-series').value==='weather',area=view==='og'?'og':'eg';
      const series=weather?[[area+'.outside','#269274','Aktuell'],[area+'.outside_attenuated','#dda56e','Gedämpft'],[area+'.outside_composite','#7c89bb','Gemischt']]:[['eg.flow_actual','#269274','EG · Vorlauf'],['anlage.boiler','#dda56e','Kesseltemperatur']];
      $('history-description').textContent=weather?'Außentemperatur · '+area.toUpperCase():'Vorlauf im Erdgeschoss und Kesseltemperatur';
      $('history-legend').innerHTML=series.map(([,color,label])=>'<span><i style="background:'+color+'"></i>'+label+'</span>').join('');
      if(samples.length<2) return;
      const w=Math.max(320,$('history-chart').clientWidth),h=178,left=37,right=12,top=13,bottom=24;
      const values=samples.flatMap(s=>series.map(([key])=>s[key])).filter(numeric); if(!values.length){$('history-chart').innerHTML='<div class="empty-chart"><strong>Für diese Größen entsteht der Verlauf ab jetzt.</strong><span>Fehlende historische Werte werden nicht ergänzt.</span></div>';return;}
      const low=Math.floor(Math.min(...values)/10)*10-5,high=Math.ceil(Math.max(...values)/10)*10+5;
      const first=samples[0].ts,last=samples.at(-1).ts,span=Math.max(1,last-first);
      const x=t=>left+(t-first)/span*(w-left-right), y=v=>h-bottom-(v-low)/(high-low)*(h-top-bottom);
      let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${weather?'Außentemperaturen':'Vorlauf und Kesseltemperatur'} in Grad Celsius">`;
      for(let i=0;i<4;i++){const v=low+(high-low)*i/3, py=y(v);svg+=`<line x1="${left}" x2="${w-right}" y1="${py}" y2="${py}" stroke="var(--line)" stroke-width="1"/><text x="0" y="${py+3}" fill="var(--muted)" font-size="9">${number(v,0)}°</text>`;}
      for(const [key,color] of series){
        let path='',previous=null;
        for(const sample of samples){const v=sample[key];if(!numeric(v)){previous=null;continue;}const move=previous===null||sample.ts-previous>Math.max(120,hours*3600/180);path+=`${move?'M':'L'}${x(sample.ts).toFixed(1)},${y(v).toFixed(1)} `;previous=sample.ts;}
        svg+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>`;
      }
      for(let i=0;i<5;i++){const ts=first+span*i/4;svg+=`<text x="${x(ts)}" y="${h-3}" fill="var(--muted)" font-size="9" text-anchor="${i===0?'start':i===4?'end':'middle'}">${formatTime(ts)}</text>`;}
      $('history-chart').innerHTML=svg+'</svg>';
    } catch { /* Keep the last visible history when the VM is briefly unavailable. */ }
  }
  function selectView(next) {
    view=next;
    document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
    $('page-title').innerHTML=(view==='eg'?'Erdgeschoss':view==='og'?'Obergeschoss':'Heizungsübersicht')+'<span>.</span>';
    $('page-subtitle').textContent=view==='eg'?'Fußbodenheizung · Eurocontrol M':view==='og'?'Heizkörper · Eurocontrol K':'Fußbodenheizung im EG. Heizkörper im OG. Alles an einem Ort.';
    const url=new URL(location); view==='overview'?url.searchParams.delete('etage'):url.searchParams.set('etage',view); window.history.replaceState(null,'',url);
    renderFloors();renderRooms();renderSchedule();diagnostics.render(snapshot,view);history();
    window.scrollTo(0,0);
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>selectView(b.dataset.view)));
  document.querySelectorAll('[data-hours]').forEach(b=>b.addEventListener('click',()=>{hours=Number(b.dataset.hours);document.querySelectorAll('[data-hours]').forEach(c=>c.classList.toggle('selected',c.dataset.hours===b.dataset.hours));history();diagnostics.load(hours);}));
  $('refresh').addEventListener('click',()=>{load();diagnostics.load(hours);});
  $('history-series').addEventListener('change',history);
  document.addEventListener('heating-schedules-updated',load);
  $('theme').addEventListener('click',()=>{theme=theme==='dark'?'light':'dark';document.body.dataset.theme=theme;localStorage.setItem('heating-theme',theme);});
  selectView(view); load(); history();diagnostics.load(hours); setInterval(()=>{if(!document.hidden)load();},5000); setInterval(()=>{if(!document.hidden){history();diagnostics.load(hours);}},30000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){load();history();diagnostics.load(hours);}});
})();
