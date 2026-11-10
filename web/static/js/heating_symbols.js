'use strict';
(() => {
  const types={boiler:'Heizkessel',tank:'Warmwasserspeicher · Heizwendel',pump:'Heizungs-/Ladepumpe',circulation_pump:'Trinkwasser-Zirkulationspumpe',valve:'Absperrventil',check_valve:'Rückschlagventil',mixer:'Dreiwegemischer',radiator:'Heizkörper / Heizkreis',floor_heating:'Fußboden-Heizkreis',manifold:'Verteiler / Sammler',junction:'Rohrabzweig · verbunden',sensor:'Temperaturfühler',label:'Beschriftung',expansion_vessel:'Membran-Ausdehnungsgefäß',heat_exchanger:'Plattenwärmetauscher',supply_connection:'Vorlaufanschluss · VL',return_connection:'Rücklaufanschluss · RL',safety_valve:'Sicherheitsventil',air_vent:'Automatischer Entlüfter',drain:'Füllen / Entleeren'};
  // Ports describe schematic functions, never physical positions on a particular product.
  const p=(id,label,x,y,dx,dy,medium='neutral')=>({id,label,x,y,dx,dy,medium});
  const through=()=>[p('in','Ein',-50,0,-1,0),p('out','Aus',50,0,1,0)];
  const specs={
    boiler:{w:140,h:120,ports:[p('flow','VL',80,-30,1,0,'hot'),p('return','RL',80,30,1,0,'cold')]},
    tank:{w:140,h:220,ports:[p('dhw','WW',-90,-80,-1,0,'dhw'),p('circulation','Z',-90,-15,-1,0,'dhw_circulation'),p('cold','KW',-90,80,-1,0,'cold_water'),p('coil_flow','Lade-VL',90,15,1,0,'hot'),p('coil_return','Lade-RL',90,70,1,0,'cold')]},
    pump:{w:80,h:80,ports:through()},circulation_pump:{w:80,h:80,ports:through()},
    valve:{w:80,h:80,ports:through()},check_valve:{w:80,h:60,ports:through()},
    mixer:{w:90,h:90,ports:[p('a','A',-60,0,-1,0),p('b','B',0,60,0,1),p('ab','AB',60,0,1,0)]},
    radiator:{w:130,h:80,ports:[p('flow','VL',-80,-20,-1,0,'hot'),p('return','RL',80,20,1,0,'cold')]},
    floor_heating:{w:130,h:90,ports:[p('flow','VL',-80,-25,-1,0,'hot'),p('return','RL',80,25,1,0,'cold')]},
    manifold:{w:140,h:70,ports:[p('in','Ein',-90,0,-1,0),p('out','Aus',90,0,1,0),p('branch_1','1',-40,50,0,1),p('branch_2','2',0,50,0,1),p('branch_3','3',40,50,0,1)]},
    junction:{w:20,h:20,ports:[p('n','',0,-10,0,-1),p('e','',10,0,1,0),p('s','',0,10,0,1),p('w','',-10,0,-1,0)]},
    sensor:{w:54,h:60,ports:[p('probe','Messpunkt',0,40,0,1)]},label:{w:140,h:38,ports:[]},
    expansion_vessel:{w:90,h:100,ports:[p('connection','Anschluss',0,60,0,1)]},
    heat_exchanger:{w:100,h:110,ports:[p('primary_flow','P-VL',-70,-30,-1,0,'hot'),p('primary_return','P-RL',-70,30,-1,0,'cold'),p('secondary_flow','S-VL',70,-30,1,0,'hot'),p('secondary_return','S-RL',70,30,1,0,'cold')]},
    supply_connection:{w:80,h:50,ports:[p('flow','VL',50,0,1,0,'hot')]},
    return_connection:{w:80,h:50,ports:[p('return','RL',50,0,1,0,'cold')]},
    safety_valve:{w:90,h:100,ports:[p('in','Druckseite',0,60,0,1),p('discharge','Abblaseleitung',60,0,1,0)]},
    air_vent:{w:60,h:90,ports:[p('connection','Anschluss',0,55,0,1)]},
    drain:{w:80,h:80,ports:[p('connection','Anschluss',-50,0,-1,0),p('drain','Ablauf',0,50,0,1)]}
  };
  const media={hot:{label:'Heizung · Vorlauf',color:'#d45440',dash:''},cold:{label:'Heizung · Rücklauf',color:'#397fae',dash:'9 5'},dhw:{label:'Trinkwarmwasser · WW',color:'#c6771d',dash:''},dhw_circulation:{label:'Trinkwasser-Zirkulation · Z',color:'#c6771d',dash:'9 5'},cold_water:{label:'Trinkkaltwasser · KW',color:'#288c77',dash:''},potable:{label:'Trinkwasser · bisherige Zuordnung',color:'#8e6abe',dash:''},neutral:{label:'Neutral / noch ungeklärt',color:'#85938e',dash:''}};
  function size(n){if(n.port_layout!=='hydronic')return n.type==='junction'?[22,22]:n.type==='sensor'?[66,44]:n.type==='tank'?[104,142]:n.type==='label'?[140,38]:[110,72];const s=specs[n.type];return [s.w,s.h];}
  function ports(n){if(n.port_layout==='hydronic')return specs[n.type].ports;const [w,h]=size(n);return [p('n','N',0,-h/2,0,-1),p('e','O',w/2,0,1,0),p('s','S',0,h/2,0,1),p('w','W',-w/2,0,-1,0)];}
  const round=v=>Math.round(v*1e8)/1e8||0;
  function rotate(x,y,angle){const a=angle*Math.PI/180;return {x:round(x*Math.cos(a)-y*Math.sin(a)),y:round(x*Math.sin(a)+y*Math.cos(a))};}
  function anchor(n,id){const pt=ports(n).find(p=>p.id===id);if(!pt)throw Error('Unbekannter Anschluss: '+id);const xy=rotate(pt.x,pt.y,n.rotation||0);return {x:n.x+xy.x,y:n.y+xy.y};}
  function normal(n,id){const pt=ports(n).find(p=>p.id===id);if(!pt)throw Error('Unbekannter Anschluss');return rotate(pt.dx,pt.dy,n.rotation||0);}
  function bounds(n){const a=(n.rotation||0)%180, [w,h]=size(n);const pp=ports(n).map(p=>anchor(n,p.id));return {left:Math.min(n.x-(a?h:w)/2,...pp.map(p=>p.x)),right:Math.max(n.x+(a?h:w)/2,...pp.map(p=>p.x)),top:Math.min(n.y-(a?w:h)/2,...pp.map(p=>p.y)),bottom:Math.max(n.y+(a?w:h)/2,...pp.map(p=>p.y))};}
  function symbol(n){const legacy=n.port_layout!=='hydronic',s=specs[n.type],scale=legacy?Math.min(size(n)[0]/s.w,size(n)[1]/s.h):1;
    let shape='';switch(n.type){
      case 'boiler':shape='<rect x="-60" y="-50" width="120" height="100" rx="5"/><path d="M60-30H80M60 30H80M-42 28H42M-10-27C-37 1-17 18 0 16C30 12 23-15 9-28C12-9 2-5-10-27Z"/>';break;
      case 'tank':shape='<rect x="-60" y="-100" width="120" height="200" rx="35"/><path d="M-60-80H-90M-60-15H-90M-60 80H-90M-60-65H60M-60 65H-28M90 15H25C-28 15-28 30 12 30S52 45 12 45S-28 60 12 60H25V70H90"/>';break;
      case 'pump':case 'circulation_pump':shape='<path d="M-50 0H-30M30 0H50"/><circle r="30"/><path class="symbol-solid" d="M-13-17L20 0-13 17Z"/>'+(n.type==='circulation_pump'?'<text class="symbol-letter" x="0" y="-39" text-anchor="middle">Z</text>':'');break;
      case 'valve':shape='<path d="M-50 0H-25M25 0H50M-25-18L25 18V-18L-25 18ZM0 0V-31M-15-31H15"/>';break;
      case 'check_valve':shape='<path d="M-50 0H-25M25 0H50M-25-19L14 0-25 19ZM22-23V23"/>';break;
      case 'mixer':shape='<path d="M-60 0H-27M27 0H60M0 27V60M-27-18L0 0-27 18ZM27-18L0 0 27 18ZM-18 27L0 0 18 27ZM0-18V-35"/><rect x="-12" y="-54" width="24" height="20"/><text class="symbol-letter" y="-39" text-anchor="middle">M</text>';break;
      case 'radiator':shape='<rect x="-60" y="-32" width="120" height="64" rx="4"/><path d="M-80-20H-60M60 20H80M-42-32V32M-21-32V32M0-32V32M21-32V32M42-32V32"/>';break;
      case 'floor_heating':shape='<path d="M-80-25H45Q65-25 45-8H-40Q-60-8-40 9H45Q65 9 45 25H-40Q-60 25-40 37H60V25H80"/><path d="M-60 44H60"/>';break;
      case 'manifold':shape='<rect x="-65" y="-15" width="130" height="30"/><path d="M-90 0H-65M65 0H90M-40 15V50M0 15V50M40 15V50"/>';break;
      case 'junction':shape='<circle class="symbol-solid" r="7"/><path d="M-10 0H10M0-10V10"/>';break;
      case 'sensor':shape='<circle cy="-7" r="21"/><text class="symbol-letter" y="-2" text-anchor="middle">T</text><path d="M0 14V40"/>';break;
      case 'expansion_vessel':shape='<ellipse cy="-5" rx="35" ry="40"/><path d="M-35-5H35M0 35V60"/>';break;
      case 'heat_exchanger':shape='<rect x="-45" y="-48" width="90" height="96"/><path d="M-70-30H-45M-70 30H-45M45-30H70M45 30H70M-30-48L0 48M-5-48L25 48M20-48L45 30"/>';break;
      case 'supply_connection':shape='<path d="M-40-17H10L35 0 10 17H-40ZM35 0H50"/><text class="symbol-letter" x="-10" y="5" text-anchor="middle">VL</text>';break;
      case 'return_connection':shape='<path d="M-40 0L-15-17H35V17H-15ZM35 0H50"/><text class="symbol-letter" x="4" y="5" text-anchor="middle">RL</text>';break;
      case 'safety_valve':shape='<path d="M0 60V19M-18 19L0-12 18 19ZM0 0H60M0-12V-20L-9-25 9-31-9-37 9-43H0V-51M-15-51H15"/>';break;
      case 'air_vent':shape='<path d="M0 55V25M-20 25V-24Q-20-32 0-32T20-24V25ZM0-32V-44H15M-14 2H14"/>';break;
      case 'drain':shape='<path d="M-50 0H-25M-25-18L25 18V-18L-25 18ZM25 0H38M0 0V50M0-18V-31M-14-31H14"/>';break;
    }
    return `<g transform="scale(${scale})">${shape}</g>`;
  }
  const api={types,specs,media,size,ports,anchor,normal,bounds,symbol};
  if(typeof module!=='undefined')module.exports=api;
  if(typeof window!=='undefined')window.HeatingSymbols=api;
})();
