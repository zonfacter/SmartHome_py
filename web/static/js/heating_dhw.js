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
      }catch{if(seq===this.sequence)this.$('dhw-history-note').textContent='Warmwasserverlauf momentan nicht erreichbar; letzter Stand bleibt sichtbar.';}
    }
    chart(data){
      const target=this.$('dhw-history-chart'),rows=data.samples.filter(r=>typeof r.temperature==='number');
      if(rows.length<2){target.innerHTML='<div class="empty-chart"><strong>Der Warmwasserverlauf entsteht mit der Aufzeichnung.</strong><span>Gespeichert wird die gemessene Speichertemperatur.</span></div>';return;}
      const w=Math.max(300,target.clientWidth),h=200,low=Math.floor(data.minimum)-1,high=Math.ceil(data.maximum)+1;
      const first=data.samples[0].ts,last=data.samples.at(-1).ts,span=Math.max(1,last-first);
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
      for(let i=0;i<4;i++){const stamp=first+span*i/3,label=data.days===1?time(stamp).split(', ').at(-1):time(stamp).split(', ')[0];svg+=`<text x="${x(stamp)}" y="190" font-size="10" fill="var(--muted)" text-anchor="${i===0?'start':i===3?'end':'middle'}">${label}</text>`;}
      target.innerHTML=svg+'</svg>';
    }
  }
  return {View};
})();
