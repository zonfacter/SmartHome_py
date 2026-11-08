'use strict';
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.HeatingSchedules = api;
})(typeof window === 'object' ? window : this, function () {
  const DAYS = ['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag'];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clone = value => JSON.parse(JSON.stringify(value));
  const format = minute => `${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`;
  function parse(value) {
    if (!/^\d{2}:\d{2}$/.test(value)) throw Error('Bitte Zeiten als HH:MM eingeben, zum Beispiel 06:30.');
    const [h,m] = value.split(':').map(Number);
    if (h>24 || m>59 || (h===24 && m!==0)) throw Error('Die Uhrzeit muss zwischen 00:00 und 24:00 liegen.');
    return h*60+m;
  }
  function validate(periods, quarterHours = false) {
    if (!Array.isArray(periods) || periods.length>3) throw Error('Pro Tag sind höchstens drei Komfortphasen möglich.');
    let previous=0;
    return periods.map((p,i) => {
      const start=parse(p.start), end=parse(p.end);
      if (start>=1440 || end<=start) throw Error('Das Ende muss nach dem Beginn liegen. Für Mitternacht bitte 24:00 verwenden.');
      if (i && start<previous) throw Error('Die Zeitfenster müssen aufsteigend sein und dürfen sich nicht überschneiden.');
      if (quarterHours && (start%15 || end%15)) throw Error('Bitte Viertelstunden verwenden: :00, :15, :30 oder :45.');
      previous=end;
      return {start:format(start),end:format(end),start_minute:start,end_minute:end};
    });
  }
  function targetDays(day, scope) {
    if (scope==='weekdays') return [0,1,2,3,4];
    if (scope==='weekend') return [5,6];
    if (scope==='week') return [0,1,2,3,4,5,6];
    if (scope==='day' && Number.isInteger(day) && day>=0 && day<7) return [day];
    throw Error('Ungültige Tagesauswahl.');
  }
  function validDraft(value) {
    if (!value || value.version!==1 || !['eg','og'].includes(value.area) || !Array.isArray(value.days) || value.days.length!==7 || typeof value.base!=='string') return null;
    try { return {...value,days:value.days.map(day=>validate(day))}; } catch { return null; }
  }
  const times = periods => periods.length ? periods.map(p=>`${p.start}–${p.end}`).join(' · ') : 'Keine Komfortphase';
  const signature = days => JSON.stringify(days.map(d=>d.periods));

  class View {
    constructor(container, dialog, storage) {
      this.container=container; this.dialog=dialog; this.storage=storage;
      this.mode='grid'; this.drafts={}; this.showDraft={}; this.discarded={}; this.key=''; this.view='overview';
      for (const area of ['eg','og']) {
        try {
          const draft=validDraft(JSON.parse(storage.getItem(this.storageKey(area))));
          if (draft?.area===area) { this.drafts[area]=draft; this.showDraft[area]=true; }
        } catch { /* A blocked browser store must not prevent reading the controller. */ }
      }
      document.querySelectorAll('[data-schedule-mode]').forEach(button=>button.addEventListener('click',()=>{
        this.mode=button.dataset.scheduleMode; this.key=''; this.render(this.snapshot,this.view);
      }));
      container.addEventListener('click',event=>{
        const button=event.target.closest('button[data-schedule-action]');
        if (!button) return;
        const area=button.dataset.area;
        if (button.dataset.scheduleAction==='edit') this.edit(area,Number(button.dataset.day || 0));
        if (button.dataset.scheduleAction==='compare') { this.showDraft[area]=!this.showDraft[area]; this.key=''; this.render(this.snapshot,this.view); }
        if (button.dataset.scheduleAction==='discard') {
          try { this.storage.removeItem(this.storageKey(area)); }
          catch { document.getElementById('schedule-message').textContent='Der Browser kann den gespeicherten Entwurf nicht entfernen.'; return; }
          this.discarded[area]=this.drafts[area]; delete this.drafts[area]; this.showDraft[area]=false;
          this.key=''; this.render(this.snapshot,this.view);
        }
        if (button.dataset.scheduleAction==='undo' && this.discarded[area]) {
          try { this.storage.setItem(this.storageKey(area),JSON.stringify(this.discarded[area])); }
          catch { document.getElementById('schedule-message').textContent='Der Browser kann den Entwurf nicht wiederherstellen.'; return; }
          this.drafts[area]=this.discarded[area]; delete this.discarded[area]; this.showDraft[area]=true;
          this.key=''; this.render(this.snapshot,this.view);
        }
      });
      this.form=dialog.querySelector('form');
      this.form.addEventListener('submit',event=>{ event.preventDefault(); this.apply(); });
      this.form.querySelector('[name=day]').addEventListener('change',()=>{
        const next=Number(this.form.elements.day.value);
        try { this.working[this.editorDay]=this.readPeriods(); this.fillDay(next); }
        catch (e) { this.form.elements.day.value=String(this.editorDay); this.form.querySelector('[data-editor-error]').textContent=e.message; }
      });
      this.form.querySelectorAll('[data-period-enabled]').forEach(input=>input.addEventListener('change',()=>this.enableFields()));
      dialog.querySelector('[data-close-editor]').addEventListener('click',()=>dialog.close());
    }
    storageKey(area) { return 'heating-schedule-draft-v1-'+area; }
    render(snapshot, view) {
      if (!snapshot?.schedules) return;
      this.snapshot=snapshot; this.view=view;
      const key=JSON.stringify([snapshot.schedules,view,this.mode,this.showDraft,this.drafts]);
      if (key===this.key) return;
      this.key=key;
      const focus=document.activeElement?.closest('[data-schedule-action]');
      const focusId=focus ? [focus.dataset.scheduleAction,focus.dataset.area,focus.dataset.day || ''] : null;
      document.querySelectorAll('[data-schedule-mode]').forEach(b=>{
        b.classList.toggle('selected',b.dataset.scheduleMode===this.mode);
        b.setAttribute('aria-pressed',String(b.dataset.scheduleMode===this.mode));
      });
      this.container.innerHTML=['eg','og'].filter(a=>view==='overview'||view===a).map(area=>this.board(area)).join('');
      if (focusId) this.container.querySelector(`[data-schedule-action="${focusId[0]}"][data-area="${focusId[1]}"][data-day="${focusId[2]}"]`)?.focus({preventScroll:true});
    }
    board(area) {
      const days=this.snapshot.schedules[area], draft=this.drafts[area], planned=!!draft && this.showDraft[area];
      const ready=days.every(d=>d.quality==='valid');
      const today=new Intl.DateTimeFormat('en-GB',{weekday:'long',timeZone:'Europe/Berlin'}).format(new Date()).toLowerCase();
      const oldBase=!!draft && draft.base!==signature(days);
      const rows=days.map((d,i)=>{
        const good=planned || d.quality==='valid', periods=planned ? draft.days[i] : (d.periods || []);
        const text=good ? times(periods) : d.quality==='pending' ? 'Wird gelesen …' : d.quality==='stale' ? 'Stand veraltet' : 'Nicht verfügbar';
        const label=`${DAYS[i]} planen · ${text}`;
        return `<div class="week-row ${d.day===today?'today':''}"><span class="week-day">${DAYS[i].slice(0,2)}${d.day===today?'<small>Heute</small>':''}</span><button type="button" class="week-track ${good?'':'unavailable'}" data-schedule-action="edit" data-area="${area}" data-day="${i}" aria-label="${esc(label)}" title="${esc(label)}" ${!ready?'disabled':''}>${good ? periods.map(p=>`<i class="week-period" style="left:${p.start_minute/14.4}%;width:${(p.end_minute-p.start_minute)/14.4}%"></i>`).join('') : '<span>—</span>'}</button><span class="week-times">${esc(text)}</span></div>`;
      }).join('');
      return `<article class="week-board ${area} ${planned?'is-draft':''} ${this.mode==='list'?'list-view':''}"><div class="week-heading"><div><h3>${area.toUpperCase()} <span>· ${area==='eg'?'Fußbodenheizung':'Heizkörper'}</span></h3><p>${esc(this.snapshot.floors[area].controller)} · ${planned?'Lokaler Entwurf · nicht übertragen':'Gelesener Reglerstand'}</p></div><div class="week-actions">${draft?`<button type="button" class="schedule-button quiet" data-schedule-action="compare" data-area="${area}" data-day="">${planned?'Reglerstand anzeigen':'Entwurf anzeigen'}</button><button type="button" class="schedule-button quiet" data-schedule-action="discard" data-area="${area}" data-day="">Entwurf verwerfen</button>`:this.discarded[area]?`<button type="button" class="schedule-button quiet" data-schedule-action="undo" data-area="${area}" data-day="">Verwerfen rückgängig</button>`:''}<button type="button" class="schedule-button" data-schedule-action="edit" data-area="${area}" data-day="0" ${!ready?'disabled':''}>${draft?'Entwurf bearbeiten':'Zeiten entwerfen'}</button></div></div>${oldBase?'<p class="draft-warning">Der Reglerstand hat sich seit dem Entwurf geändert. Bitte die Zeiten vor einer späteren Übernahme vergleichen.</p>':''}<div class="week-scroll" tabindex="0" aria-label="${area.toUpperCase()} Wochenprogramm, bei Bedarf horizontal scrollen"><div class="week-grid"><div class="week-axis"><span>Tag</span><div>${Array.from({length:9},(_,i)=>`<span style="left:${i*12.5}%">${String(i*3).padStart(2,'0')}</span>`).join('')}</div><span>Zeitfenster</span></div>${rows}</div></div><div class="week-legend"><span><i class="comfort-key"></i>Komfortphase</span><span><i class="reduced-key"></i>Absenkphase in Automatik</span>${planned?'<strong>Entwurf · nur in diesem Browser gespeichert</strong>':'<span class="week-hint">Tag anklicken, um einen Entwurf zu planen.</span>'}</div></article>`;
    }
    edit(area, day) {
      if (!['eg','og'].includes(area) || !this.snapshot.schedules[area].every(d=>d.quality==='valid')) return;
      this.editArea=area;
      this.working=clone(this.drafts[area]?.days || this.snapshot.schedules[area].map(d=>d.periods));
      this.base=this.drafts[area]?.base || signature(this.snapshot.schedules[area]);
      this.dialog.querySelector('#schedule-editor-title').textContent=`Zeiten planen · ${area.toUpperCase()}`;
      this.form.elements.day.value=String(day);
      this.form.elements.scope.value='day';
      this.fillDay(day); this.dialog.showModal(); this.form.elements.day.focus();
    }
    fillDay(day) {
      this.editorDay=day;
      const periods=this.working[day];
      for (let i=0;i<3;i++) {
        this.form.elements['enabled'+i].checked=!!periods[i];
        this.form.elements['start'+i].value=periods[i]?.start || '';
        this.form.elements['end'+i].value=periods[i]?.end || '';
      }
      this.form.querySelector('[data-editor-error]').textContent='';
      this.enableFields();
    }
    enableFields() {
      for (let i=0;i<3;i++) for (const name of ['start','end']) this.form.elements[name+i].disabled=!this.form.elements['enabled'+i].checked;
    }
    readPeriods() {
      const input=[];
      for (let i=0;i<3;i++) if (this.form.elements['enabled'+i].checked) input.push({start:this.form.elements['start'+i].value.trim(),end:this.form.elements['end'+i].value.trim()});
      return validate(input,true);
    }
    apply() {
      const error=this.form.querySelector('[data-editor-error]');
      try {
        const periods=this.readPeriods(), day=Number(this.form.elements.day.value);
        const days=clone(this.working);
        for (const i of targetDays(day,this.form.elements.scope.value)) days[i]=clone(periods);
        const draft={version:1,area:this.editArea,base:this.base,days,saved_at:Date.now()};
        // Persist before changing the visible state, so storage failures are explicit.
        try { this.storage.setItem(this.storageKey(this.editArea),JSON.stringify(draft)); }
        catch { throw Error('Der Browser kann den Entwurf nicht speichern. Bitte lokalen Speicher für diese Seite erlauben.'); }
        this.drafts[this.editArea]=draft; this.showDraft[this.editArea]=true;
        this.key=''; this.render(this.snapshot,this.view); this.dialog.close();
        document.getElementById('schedule-message').textContent=`${this.editArea.toUpperCase()}: Entwurf lokal gespeichert. Keine Zeiten an die Heizung gesendet.`;
      } catch (e) { error.textContent=e.message; }
    }
  }
  return {View,parse,validate,targetDays,validDraft};
});
