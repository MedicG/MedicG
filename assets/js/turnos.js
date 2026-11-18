/* Turn system (staff side): give numbered turns per area, call them to a room/window, open the waiting-room screen.
   The server numbers turns per day, sede and area (medicg/turnos.py); the screen is /turnos.html. */
let turnosState={data:null,timer:null,busy:false,filter:'activos'};
function turnosCanUse(user=currentUser){if(!user)return false;if(user.rol==='admin')return true;const p=typeof userPerms==='function'?userPerms(user):(user.permissions||[]);return ['agenda','caja','hce'].some(x=>p.includes(x));}
function turnosLS(k,v){try{if(v===undefined)return localStorage.getItem('mg_turnos_'+k);localStorage.setItem('mg_turnos_'+k,v);}catch(e){return null;}}
function turnosSede(){
  if(typeof sedesEnabled!=='function'||!sedesEnabled())return '';
  const mine=typeof mySede==='function'?mySede():'';if(mine)return mine;
  const v=turnosLS('sede')||'';return sedesActive().some(s=>String(s.id)===v)?v:homeSede();
}
async function turnosLoad(){
  const sede=turnosSede();
  const res=await API.get('/api/turnos'+(sede?'?sede='+encodeURIComponent(sede):''));
  turnosState.data=res;return res;
}
function turnosAreaName(letra){return (turnosState.data?.areas||[]).find(a=>a.letra===letra)?.nombre||letra;}
function turnosMyAreas(){const saved=(turnosLS('areas')||'').split(',').filter(Boolean);const all=(turnosState.data?.areas||[]).map(a=>a.letra);const mine=saved.filter(a=>all.includes(a));return mine.length?mine:all;}
function turnosTime(iso){return iso?String(iso).slice(11,16):'';}
function turnosBadge(st){return {espera:'<span class="badge b-amber">En espera</span>',llamado:'<span class="badge b-blue">Llamado</span>',atendido:'<span class="badge b-green">Atendido</span>',ausente:'<span class="badge b-red">No se presentó</span>',cancelado:'<span class="badge">Cancelado</span>'}[st]||esc(st);}
async function openTurnos(){
  const box=document.getElementById('turnos-content');if(!box)return;
  if(!turnosState.data)box.innerHTML='<p class="text-muted">Cargando turnos…</p>';
  try{await turnosLoad();}catch(e){box.innerHTML=`<div class="alert alert-w">${esc(e.message)}</div>`;return;}
  turnosRender();turnosStartTimer();
}
function turnosStartTimer(){clearInterval(turnosState.timer);turnosState.timer=setInterval(async()=>{if(!document.getElementById('mod-turnos')?.classList.contains('active')||document.hidden){clearInterval(turnosState.timer);return;}if(turnosState.busy||document.querySelector('#turnos-content input:focus,#turnos-content select:focus'))return;try{await turnosLoad();turnosRenderLists();}catch(e){}},5000);}
function turnosRender(){
  const box=document.getElementById('turnos-content');const d=turnosState.data;if(!box||!d)return;
  const areas=d.areas||[];const mine=turnosMyAreas();const sedeBar=(typeof sedesEnabled==='function'&&sedesEnabled())?(mySede()?`<span class="badge sede-badge">${esc(sedeName(mySede()))}</span>`:`<label class="text-sm" for="tn-sede">Sede</label> <select id="tn-sede" onchange="turnosLS('sede',this.value);openTurnos()">${sedeOptions(turnosSede())}</select>`):'';
  box.innerHTML=`<div class="turnos-top"><div class="flex gap8" style="align-items:center;flex-wrap:wrap">${sedeBar}<span class="text-sm text-muted">Turnos de hoy · ${fmtDate(d.fecha)}</span></div>
   <div class="flex gap8" style="flex-wrap:wrap"><button class="btn-p btn-sm" onclick="turnosOpenScreen()"><i class="ti ti-device-heart-monitor"></i> Abrir pantalla de turnos</button>${currentUser?.rol==='admin'?'<button class="btn-s btn-sm" onclick="turnosConfig()"><i class="ti ti-settings"></i> Configurar</button>':''}</div></div>
  <div id="tn-counters" class="turnos-counters"></div>
  <div class="turnos-grid">
   <section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-receipt"></i> Dar turno</h3></div><div class="card-body">
    <div class="field"><label class="field-lbl" for="tn-pac">Paciente (opcional)</label><select id="tn-pac"><option value="">Sin paciente registrado</option>${(DB.get('pacientes')||[]).map(p=>`<option value="${p.id}">${esc(p.nombres+' '+p.apellidos)}</option>`).join('')}</select></div>
    <div class="field"><label class="field-lbl" for="tn-nombre">Nombre (si no está registrado)</label><input id="tn-nombre" maxlength="80" placeholder="Opcional"></div>
    <label class="tn-pref"><input type="checkbox" id="tn-pref"> Atención preferencial <span class="text-xs text-muted">(adulto mayor, embarazada, discapacidad)</span></label>
    <label class="tn-pref"><input type="checkbox" id="tn-print" ${turnosLS('print')!=='0'?'checked':''} onchange="turnosLS('print',this.checked?'1':'0')"> Imprimir ticket</label>
    <div class="turnos-areas">${areas.map(a=>`<button class="tn-area" onclick="turnosCreate('${esc(a.letra)}')"><span class="tn-letter">${esc(a.letra)}</span><span>${esc(a.nombre)}</span></button>`).join('')}</div>
   </div></section>
   <section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-bell-ringing"></i> Llamar turnos</h3></div><div class="card-body">
    <div class="field"><label class="field-lbl" for="tn-destino">Llamar a</label><input id="tn-destino" maxlength="40" value="${esc(turnosLS('destino')||'')}" placeholder="Ej: Consultorio 2, Ventanilla 1, Laboratorio" onchange="turnosLS('destino',this.value.trim())"></div>
    <div class="field"><span class="field-lbl">Áreas que atiendo</span><div class="flex gap8" style="flex-wrap:wrap">${areas.map(a=>`<label class="tn-chk"><input type="checkbox" value="${esc(a.letra)}" ${mine.includes(a.letra)?'checked':''} onchange="turnosSaveAreas()"> ${esc(a.letra)} · ${esc(a.nombre)}</label>`).join('')}</div></div>
    <button class="btn-g w100 tn-next" onclick="turnosCallNext()"><i class="ti ti-player-play"></i> Llamar siguiente turno</button>
    <div id="tn-last" class="tn-last"></div>
   </div></section>
  </div>
  <section class="card mt16"><div class="card-hdr"><h3 class="card-title">Turnos del día</h3><select id="tn-filter" aria-label="Filtrar turnos" onchange="turnosState.filter=this.value;turnosRenderLists()"><option value="activos" ${turnosState.filter==='activos'?'selected':''}>En espera y llamados</option><option value="todos" ${turnosState.filter==='todos'?'selected':''}>Todos</option></select></div><div class="tbl-wrap" id="tn-list"></div></section>`;
  patientPicker?.('tn-pac',{placeholder:'Buscar paciente por nombre o cédula (opcional)…'});
  turnosRenderLists();
}
function turnosRenderLists(){
  const d=turnosState.data;if(!d)return;const rows=d.turnos||[];
  const counters=document.getElementById('tn-counters');
  if(counters)counters.innerHTML=(d.areas||[]).map(a=>{const w=rows.filter(t=>t.area===a.letra&&t.estado==='espera').length;const last=rows.filter(t=>t.area===a.letra&&t.llamado_en).sort((x,y)=>y.llamado_en-x.llamado_en)[0];return `<div class="tn-counter"><div class="tn-letter">${esc(a.letra)}</div><div><div class="fw6">${esc(a.nombre)}</div><div class="text-xs text-muted">${w} en espera${last?` · último: ${esc(last.codigo)}`:''}</div></div></div>`;}).join('');
  const list=document.getElementById('tn-list');
  if(list){const shown=turnosState.filter==='todos'?rows:rows.filter(t=>t.estado==='espera'||t.estado==='llamado');
    const ordered=shown.slice().sort((a,b)=>(a.estado==='llamado'?0:1)-(b.estado==='llamado'?0:1)||(b.prioridad-a.prioridad)||String(a.creado_en).localeCompare(String(b.creado_en)));
    list.innerHTML=`<table class="tbl"><thead><tr><th>Turno</th><th>Área</th><th>Paciente</th><th>Llegada</th><th>Estado</th><th>Llamado a</th><th></th></tr></thead><tbody>${ordered.map(t=>`<tr><td class="fw7" style="font-size:16px">${esc(t.codigo)}${t.prioridad?' <span class="badge b-red" title="Atención preferencial">P</span>':''}</td><td>${esc(turnosAreaName(t.area))}</td><td>${esc(t.nombre||'—')}</td><td>${turnosTime(t.creado_en)}</td><td>${turnosBadge(t.estado)}${t.llamadas>1?` <span class="text-xs text-muted">${t.llamadas} llamadas</span>`:''}</td><td>${esc(t.destino||'—')}</td>
    <td style="white-space:nowrap">${t.estado==='espera'?`<button class="btn-p btn-xs" onclick="turnosCall('${t.id}')">Llamar</button> `:''}${t.estado==='llamado'?`<button class="btn-s btn-xs" onclick="turnosCall('${t.id}')">Volver a llamar</button> <button class="btn-g btn-xs" onclick="turnosSetState('${t.id}','atendido')">Atendido</button> <button class="btn-s btn-xs" onclick="turnosSetState('${t.id}','ausente')">No se presentó</button> `:''}${t.estado==='espera'?`<button class="btn-s btn-xs" onclick="turnosSetState('${t.id}','cancelado')">Cancelar</button>`:''}${['ausente','cancelado'].includes(t.estado)?`<button class="btn-s btn-xs" onclick="turnosSetState('${t.id}','espera')">Volver a la fila</button>`:''}</td></tr>`).join('')||'<tr><td colspan="7" class="text-muted">No hay turnos.</td></tr>'}</tbody></table>`;}
  const last=document.getElementById('tn-last');const mineLast=rows.filter(t=>t.llamado_por&&t.llamado_por===((currentUser?.name||'')+' '+(currentUser?.last||'')).trim()&&t.estado==='llamado').sort((a,b)=>b.llamado_en-a.llamado_en)[0];
  if(last)last.innerHTML=mineLast?`<div class="text-xs text-muted">Llamaste a</div><div class="tn-big">${esc(mineLast.codigo)}</div><div class="text-sm">${esc(mineLast.nombre||'')} → ${esc(mineLast.destino)}</div><div class="flex gap8 mt8" style="justify-content:center;flex-wrap:wrap"><button class="btn-s btn-sm" onclick="turnosCall('${mineLast.id}')"><i class="ti ti-refresh"></i> Volver a llamar</button><button class="btn-g btn-sm" onclick="turnosSetState('${mineLast.id}','atendido')"><i class="ti ti-check"></i> Atendido</button><button class="btn-s btn-sm" onclick="turnosSetState('${mineLast.id}','ausente')">No se presentó</button></div>`:'';
}
function turnosSaveAreas(){turnosLS('areas',[...document.querySelectorAll('#turnos-content .tn-chk input:checked')].map(i=>i.value).join(','));}
async function turnosPost(payload){
  if(turnosState.busy)return null;turnosState.busy=true;
  try{const sede=turnosSede();const res=await API.post('/api/turnos',{...payload,...(sede?{sede}:{})});await turnosLoad();turnosRenderLists();return res;}
  catch(e){toast(e.message,'err');return null;}finally{turnosState.busy=false;}
}
async function turnosCreate(area){
  const pac=document.getElementById('tn-pac')?.value||'',nombre=document.getElementById('tn-nombre')?.value.trim()||'';
  const res=await turnosPost({action:'crear',area,pacienteId:pac||undefined,nombre:pac?undefined:nombre,prioridad:document.getElementById('tn-pref')?.checked});
  if(!res)return;
  const t=res.turno;toast(`Turno ${t.codigo} entregado`,'ok');
  const sel=document.getElementById('tn-pac');if(sel){sel.value='';}const n=document.getElementById('tn-nombre');if(n)n.value='';const pref=document.getElementById('tn-pref');if(pref)pref.checked=false;
  if(document.getElementById('tn-print')?.checked)turnosPrintTicket(t);
}
function turnosDestino(){const v=(document.getElementById('tn-destino')?.value||turnosLS('destino')||'').trim();if(!v){toast('Escribe a dónde llamas (ej: Consultorio 2).','err');document.getElementById('tn-destino')?.focus();return '';}turnosLS('destino',v);return v;}
async function turnosCallNext(){const destino=turnosDestino();if(!destino)return;const areas=turnosMyAreas();const res=await turnosPost({action:'llamar',areas,destino});if(res)toast(`Llamando ${res.turno.codigo} a ${destino}`,'ok');}
async function turnosCall(id){const destino=turnosDestino();if(!destino)return;const res=await turnosPost({action:'llamar',id,destino});if(res)toast(`Llamando ${res.turno.codigo} a ${destino}`,'ok');}
async function turnosSetState(id,estado){await turnosPost({action:'estado',id,estado});}
function turnosScreenUrl(){const d=turnosState.data||{};const p=new URLSearchParams();const s=turnosSede();if(s)p.set('sede',s);if(d.displayKey)p.set('k',d.displayKey);return location.origin+'/turnos.html'+(p.toString()?'?'+p:'');}
async function turnosOpenScreen(){
  const d=turnosState.data||{};
  if(!d.displayKey&&currentUser?.rol==='admin'){await turnosSaveConfig(d.areas||[],!!d.mostrarNombre,d.voz!==false,false,true);}
  const url=turnosScreenUrl();window.open(url,'medicg-turnos');
  cashModal?.('m-turnos-link','Pantalla de turnos',`<p class="text-sm">Se abrió la pantalla en otra ventana. Para la TV de la sala de espera, abre este enlace en su navegador y presiona <b>F11</b> (pantalla completa). Toca la pantalla una vez para activar el sonido.</p><div class="flex gap8" style="flex-wrap:wrap"><input readonly value="${esc(url)}" id="tn-url" style="flex:1;min-width:240px" aria-label="Enlace de la pantalla"><button class="btn-s" onclick="navigator.clipboard?.writeText(document.getElementById('tn-url').value).then(()=>toast('Enlace copiado','ok'))">Copiar</button></div>${d.displayKey?'':'<p class="text-xs text-muted mt8">Pide al administrador que abra la pantalla una vez para generar el enlace para la TV.</p>'}`);
}
function turnosPrintTicket(t){
  const cfg=DB.get('config')||{};const sede=typeof sedeName==='function'&&t.sede?sedeName(t.sede):'';
  const w=window.open('','ticket','width=360,height=520');if(!w){toast('Permite ventanas emergentes para imprimir el ticket.','err');return;}
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Turno ${esc(t.codigo)}</title><style>@page{size:80mm auto;margin:4mm}body{font-family:Arial,sans-serif;text-align:center;margin:0;padding:6px;width:72mm}h1{font-size:15px;margin:4px 0}.code{font-size:54px;font-weight:800;letter-spacing:2px;margin:10px 0}.muted{color:#444;font-size:12px}.box{border-top:1px dashed #000;border-bottom:1px dashed #000;padding:6px 0;margin:8px 0}</style></head><body>
  <h1>${esc(cfg.nombre||'Centro médico')}</h1>${sede?`<div class="muted">Sede ${esc(sede)}</div>`:''}<div class="box"><div class="muted">${esc(turnosAreaName(t.area))}${t.prioridad?' · PREFERENCIAL':''}</div><div class="code">${esc(t.codigo)}</div>${t.nombre?`<div class="muted">${esc(t.nombre)}</div>`:''}</div>
  <div class="muted">${new Date().toLocaleString('es-EC')}</div><p class="muted">Espere a ser llamado en la pantalla.</p><script>window.onload=()=>{window.print();setTimeout(()=>window.close(),500);}<\/script></body></html>`);
  w.document.close();
}
function turnosConfig(){
  const d=turnosState.data||{};const areas=(d.areas||[]).map(a=>({...a}));window.__tnAreas=areas;
  const render=()=>`<p class="text-sm text-muted">Cada área tiene una letra: los turnos salen como C-001, L-001… y la numeración empieza cada día.</p><div id="tn-cfg-areas">${window.__tnAreas.map((a,i)=>`<div class="flex gap8 mb8"><input aria-label="Letra" maxlength="2" value="${esc(a.letra)}" style="width:70px;text-transform:uppercase" oninput="__tnAreas[${i}].letra=this.value.toUpperCase()"><input aria-label="Nombre del área" maxlength="40" value="${esc(a.nombre)}" style="flex:1" oninput="__tnAreas[${i}].nombre=this.value"><button class="btn-s btn-sm" aria-label="Quitar área" onclick="__tnAreas.splice(${i},1);document.getElementById('m-turnos-cfg').querySelector('.card-body').innerHTML=window.__tnRender()">×</button></div>`).join('')}</div>
  <button class="btn-s btn-sm" onclick="__tnAreas.push({letra:'',nombre:''});document.getElementById('m-turnos-cfg').querySelector('.card-body').innerHTML=window.__tnRender()">+ Agregar área</button>
  <label class="tn-pref mt12"><input type="checkbox" id="tn-cfg-nombre" ${d.mostrarNombre?'checked':''}> Mostrar el nombre corto del paciente en la pantalla (ej. "María P.")</label>
  <label class="tn-pref"><input type="checkbox" id="tn-cfg-voz" ${d.voz!==false?'checked':''}> Anunciar el turno con voz además del timbre</label>
  <label class="tn-pref"><input type="checkbox" id="tn-cfg-key"> Generar un enlace nuevo para la pantalla (el anterior deja de funcionar)</label>
  <button class="btn-p mt12" onclick="turnosSaveConfig(__tnAreas,document.getElementById('tn-cfg-nombre').checked,document.getElementById('tn-cfg-voz').checked,document.getElementById('tn-cfg-key').checked)">Guardar</button>`;
  window.__tnRender=render;cashModal('m-turnos-cfg','Configurar turnos',render());
}
async function turnosSaveConfig(areas,mostrarNombre,voz,nuevaClave,silent){
  try{await API.post('/api/turnos',{action:'config',areas:areas.map(a=>({letra:String(a.letra||'').trim(),nombre:String(a.nombre||'').trim()})),mostrarNombre,voz,nuevaClave});await turnosLoad();if(!silent){closeM('m-turnos-cfg');toast('Turnos configurados','ok');}turnosRender();}
  catch(e){toast(e.message,'err');}
}
(function(){
  const hp=window.hasPerm;
  if(typeof hp==='function')window.hasPerm=function(id,user){if(id==='turnos')return turnosCanUse(user||currentUser);return hp.apply(this,arguments);};
  const sm=window.showMod;
  if(typeof sm==='function')window.showMod=function(id,el){const r=sm.apply(this,arguments);if(id==='turnos'&&turnosCanUse()){const t=document.getElementById('tb-title');if(t)t.textContent='Sistema de turnos';openTurnos();}return r;};
  const ap=window.applyPermissionUI;
  if(typeof ap==='function')window.applyPermissionUI=function(){const r=ap.apply(this,arguments);const n=document.querySelector('.nav-item[data-module="turnos"]');if(n)n.style.display=turnosCanUse()?'flex':'none';return r;};
  document.addEventListener('DOMContentLoaded',()=>{const n=document.querySelector('.nav-item[data-module="turnos"]');if(n&&currentUser)n.style.display=turnosCanUse()?'flex':'none';});
})();
