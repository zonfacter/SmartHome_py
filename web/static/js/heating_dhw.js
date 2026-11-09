'use strict';
window.HeatingDhwView=(()=>{
  const number=v=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-DE',{maximumFractionDigits:1,minimumFractionDigits:1}):'—';
  const time=ts=>new Date(ts*1000).toLocaleString('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
  class View{
    constructor(container){
      this.container=container;this.days=1;this.sequence=0;this.$=id=>container.querySelector('#'+id);
      container.querySelectorAll('[data-dhw-days]').forEach(button=>button.addEventListener('click',()=>{
        this.days=Number(button.dataset.dhwDays);container.querySelectorAll('[data-dhw-days]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});this.load();
      }));
    }
    async load(){
      const seq=++this.sequence,days=this.days;
      try{
        const response=await fetch('/api/heating/observer/dhw-history?days='+days,{cache:'no-store'});
        if(!response.ok)throw Error();
        const data=await response.json();if(seq!==this.sequence)return;
        this.$('dhw-history-latest').textContent=number(data.latest?.temperature)+' °C';
        this.$('dhw-history-min').textContent=number(data.minimum)+' °C';this.$('dhw-history-max').textContent=number(data.maximum)+' °C';
        this.$('dhw-history-note').textContent=data.first_sample?`${data.valid_samples.toLocaleString('de-DE')} gültige Messungen · verfügbar ${time(data.first_sample)} bis ${time(data.last_sample)}. Bis 90 Tage lokal gespeichert; Zeiträume füllen sich mit der Aufzeichnung. Lücken werden nicht überbrückt.`:'Noch keine gespeicherten Warmwassermessungen. Der Verlauf füllt sich mit der Aufzeichnung.';
        this.chart(data);
        this.pumps(data);
      }catch{if(seq===this.sequence)this.$('dhw-history-note').textContent='Warmwasserverlauf momentan nicht erreichbar; letzter Stand bleibt sichtbar.';}
    }
    pumps(data){
      const target=this.$('dhw-pump-chart'),eventsTarget=this.$('dhw-pump-events');
      const tracks=data.pumps||[],first=data.first_sample,last=data.last_sample;
      if(!tracks.length||!first||last<=first){target.innerHTML='<p class="diagnostic-note">Noch keine aufgezeichneten Pumpenkontakte.</p>';eventsTarget.textContent='Noch keine Schaltwechsel aufgezeichnet.';return;}
      const w=Math.max(300,this.$('dhw-history-chart').clientWidth),span=last-first,x=t=>38+(t-first)/span*(w-52);
      const labels={eg:'EG · Heizkreispumpe',og:'OG · Heizkreispumpe',dhw:'Warmwasser · Ladepumpe'};
      let svg=`<svg viewBox="0 0 ${w} 150" role="img" aria-label="Pumpenrelais im zeitlichen Verlauf"><defs><pattern id="pump-history-unknown" patternUnits="userSpaceOnUse" width="6" height="6"><path d="M0 6L6 0" stroke="var(--muted)" stroke-opacity=".4"/></pattern></defs>`;
      let events=[];
      tracks.forEach((track,i)=>{
        const label=labels[track.key];if(!label)return;
        const y=14+i*48,current=track.state===true?'Ein':track.state===false?'Aus':'Unbekannt';
        svg+=`<text x="38" y="${y}" font-size="11" fill="var(--muted)">${label} · zuletzt ${current}</text>`;
        for(const b of track.buckets){
          const mixed=(b.on_seconds>0&&b.off_seconds>0)||b.switches>0,unknown=b.unknown_seconds>0;
          const fill=mixed?'#ca8a26':unknown?'url(#pump-history-unknown)':b.on_seconds>0?'#269274':'var(--line)';
          svg+=`<rect x="${x(b.from)}" y="${y+7}" width="${Math.max(0,x(b.to)-x(b.from))}" height="18" fill="${fill}"><title>${label}: ${time(b.from)} – ${time(b.to)}; Ein ${b.on_seconds} s, Aus ${b.off_seconds} s, unbekannt/Wechselintervall ${b.unknown_seconds} s; ${b.switches} Wechsel</title></rect>`;
        }
        events.push(...track.events.map(e=>({...e,label})));
      });
      target.innerHTML=svg+'</svg>';
      events.sort((a,b)=>b.to-a.to);
      eventsTarget.innerHTML=events.length?'<table class="pump-switch-table"><thead><tr><th>Pumpe</th><th>Wechsel zwischen</th><th>Danach</th></tr></thead><tbody>'+events.map(e=>`<tr><td>${e.label}</td><td>${time(e.from)} – ${time(e.to)}</td><td>${e.state?'Ein':'Aus'}</td></tr>`).join('')+'</tbody></table>':'<p class="diagnostic-note">Keine sicher beobachteten Schaltwechsel im gewählten Zeitraum.</p>';
    }
    chart(data){
      const target=this.$('dhw-history-chart'),rows=data.samples.filter(r=>typeof r.temperature==='number');
      if(rows.length<2){target.innerHTML='<div class="empty-chart"><strong>Der Warmwasserverlauf entsteht mit der Aufzeichnung.</strong><span>Gespeichert wird die gemessene Speichertemperatur.</span></div>';return;}
      const w=Math.max(300,target.clientWidth),h=200,low=Math.floor(data.minimum)-1,high=Math.ceil(data.maximum)+1;
      const first=data.first_sample,last=data.last_sample,span=Math.max(1,last-first);
      const x=t=>38+(t-first)/span*(w-52),y=v=>165-(v-low)/(high-low)*145;
      let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Warmwassertemperatur über ${data.days} Tage, mit Minimum und Maximum je Zeitabschnitt">`;
      for(let i=0;i<4;i++){const value=low+(high-low)*i/3;svg+=`<line x1="38" x2="${w-14}" y1="${y(value)}" y2="${y(value)}" stroke="var(--line)"/><text x="0" y="${y(value)+3}" font-size="10" fill="var(--muted)">${number(value)}°</text>`;}
      let path='',previous=null;
      for(const row of data.samples){
        if(typeof row.temperature!=='number'){previous=null;continue;}
        path+=`${!previous||row.break_before?'M':'L'}${x(row.ts).toFixed(1)},${y(row.temperature).toFixed(1)} `;previous=row;
        svg+=`<g><title>${time(row.from)} – ${time(row.to)}: Mittel ${number(row.temperature)} °C, Minimum ${number(row.minimum)} °C, Maximum ${number(row.maximum)} °C (${row.count} Messungen)</title><line x1="${x(row.ts)}" x2="${x(row.ts)}" y1="${y(row.minimum)}" y2="${y(row.maximum)}" stroke="#269274" stroke-opacity=".3" stroke-width="3"/><circle cx="${x(row.ts)}" cy="${y(row.temperature)}" r="2" fill="#269274"/></g>`;
      }
      svg+=`<path d="${path}" fill="none" stroke="#269274" stroke-width="2"/>`;
      for(let i=0;i<4;i++){const stamp=first+span*i/3,label=span<36*3600?time(stamp).split(', ').at(-1):time(stamp).split(', ')[0];svg+=`<text x="${x(stamp)}" y="190" font-size="10" fill="var(--muted)" text-anchor="${i===0?'start':i===3?'end':'middle'}">${label}</text>`;}
      target.innerHTML=svg+'</svg>';
    }
  }
  return {View};
})();
