'use strict';
window.HeatingDiagnostics=(()=>{
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number=(v,d=1)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
  const time=ts=>new Intl.DateTimeFormat('de-DE',{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Berlin'}).format(new Date(ts*1000));
  const value=item=>item?.quality==='valid'?item.value:null;
  function display(item){
    const v=value(item);
    if(v===null)return item?.quality==='unavailable'?'Nicht vorhanden':item?.quality==='stale'?'Veraltet':'—';
    if(item.kind==='error_code')return v===0?'0 · Keine Fehlermeldung':'Fehlercode '+v;
    if(typeof v==='boolean')return v?'Ein':'Aus';
    if(typeof v==='string')return v;
    return number(v,['counter','burner_hours','minutes','error_priority','gain'].includes(item.kind)?0:1)+(item.unit?' '+item.unit:'');
  }
  function rows(metrics,keys){
    return keys.filter(k=>metrics[k]).map(k=>`<div class="diagnostic-row"><span>${esc(metrics[k].label)}</span><strong class="${metrics[k].quality==='valid'?'':'muted'}">${esc(display(metrics[k]))}</strong></div>`).join('');
  }
  class View{
    constructor(container){this.container=container;this.stats=null;this.failed=false;this.sequence=0;}
    render(snapshot,view){
      if(!snapshot)return;
      this.snapshot=snapshot;
      const open=new Set([...this.container.querySelectorAll('details[open]')].map(d=>d.dataset.diagnostic));
      const focused=document.activeElement?.closest('details')?.dataset.diagnostic;
      const p=snapshot.plant;
      let html='<div class="diagnostic-grid">';
      html+=`<article class="diagnostic-card"><h3>Kessel & Brenner</h3><p>Eurocontrol K · gemeldete Regelparameter</p>${rows(p,['boiler_min','boiler_max','boiler_differential','burner_min_run','burner_on_threshold','burner_off_threshold'])}</article>`;
      html+=`<article class="diagnostic-card"><h3>Warmwasser</h3><p>Betriebsart und Ladeeinstellungen</p>${rows(p,['dhw_enabled','dhw_reduced','dhw_max','dhw_differential','dhw_boost','dhw_program','dhw_priority','dhw_charging'])}</article>`;
      html+='</div><div class="diagnostic-grid floor-diagnostics">';
      for(const area of ['eg','og'].filter(a=>view==='overview'||view===a)){
        const floor=snapshot.floors[area],m=floor.metrics,error=value(m.error_code);
        const status=error===0?'Keine Fehlermeldung':error===null?'Fehlerstatus unbekannt':'Fehlercode '+error;
        html+=`<article class="diagnostic-card ${area}"><div class="diagnostic-heading"><h3>${area.toUpperCase()} · ${esc(floor.controller)}</h3><span class="diagnostic-status ${error===0?'ok':error>0?'alert':''}">${esc(status)}</span></div>${rows(m,['clock','error_code','error_priority','relay_test','lpb_power','plant_frost','building','changeover_source','overrun','pump_function'])}<h4>Wetter & Fühler</h4>${rows(m,['outside','outside_local','outside_attenuated','outside_composite','room_actual'])}<p class="diagnostic-note">Der lokale Außenfühler kann fehlen, obwohl die Außentemperatur über LPB verfügbar ist. Der Speisungsstatus ist keine Spannungsmessung.</p><details data-diagnostic="${area}" ${open.has(area)?'open':''}><summary>LPB-Rohdiagnose · Zuordnung offen</summary><p>Werte und Zusatzkennzeichen sind hier unverändert dargestellt. Daraus wird keine aktive Sperre oder Ursache für einen Pumpenstopp abgeleitet.</p>${rows(m,Object.keys(m).filter(k=>k.endsWith('_raw')))}</details></article>`;
      }
      this.container.innerHTML=html+'</div>';
      if(focused)this.container.querySelector(`details[data-diagnostic="${focused}"] summary`)?.focus({preventScroll:true});
      document.getElementById('burner-hours').textContent=display(p.burner_hours);
      document.getElementById('lifetime-starts').textContent='Startzähler aktuell: '+display(p.starts);
    }
    async load(hours){
      const sequence=++this.sequence;
      try{
        const response=await fetch('/api/heating/statistics?hours='+hours,{cache:'no-store'});
        if(!response.ok)throw Error();
        const data=await response.json();if(sequence!==this.sequence)return;
        this.stats=data;this.failed=false;this.renderStats();
      }catch{if(sequence===this.sequence){this.failed=true;this.renderStats();}}
    }
    renderStats(){
      const data=this.stats,note=document.getElementById('cycle-note');
      if(!data){note.textContent=this.failed?'Statistik ist momentan nicht erreichbar.':'Eine Datenbasis entsteht mit den nächsten Messungen.';return;}
      document.getElementById('observed-starts').textContent=number(data.starts,0);
      document.getElementById('starts-per-hour').textContent=number(data.starts_per_hour,1);
      document.getElementById('minutes-per-start').textContent=number(data.relay_minutes_per_start,1);
      document.getElementById('cycle-coverage').textContent=`${number(data.coverage_seconds/60,0)} min von ${data.hours} h beobachtet · ${number(data.coverage_percent,1)} % Datenabdeckung`;
      document.getElementById('cycle-meter').style.width=Math.min(100,data.coverage_percent)+'%';
      const max=Math.max(1,...data.bins.map(b=>b.starts||0));
      document.getElementById('cycle-chart').innerHTML=data.bins.map(b=>`<div class="cycle-bin ${b.starts===null?'unknown':''}" title="${time(b.ts)}: ${b.starts===null?'Keine vollständigen Messintervalle':b.starts+' Starts; '+number(b.coverage_seconds/60,0)+' min beobachtet'}"><span>${b.starts===null?'—':b.starts}</span><i style="height:${b.starts===null?12:Math.max(3,b.starts/max*74)}px"></i><small>${time(b.ts)}</small></div>`).join('');
      note.textContent=(this.failed?'Statistikabruf fehlgeschlagen; letzter Stand wird angezeigt. ':'')+`Beobachtete Relaislaufzeit: ${number(data.relay_runtime_minutes,1)} min. `+(data.counter_resets?`${data.counter_resets} Zählerrücksetzung(en) ausgelassen. `:'')+'Starts und Laufzeit beziehen sich nur auf gemeinsam gültige Messintervalle. Relaiskontakte messen keine Flamme; Relaisminuten/Start sind keine vollständigen Brennerzyklen.';
    }
  }
  return {View};
})();
