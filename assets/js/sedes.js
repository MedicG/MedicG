/* Establishments (sedes): Configuración card, patient form, patient filter and user assignment.
   The server enforces what a sede-limited user can read and write (medicg/sedes.py). */
function sedesList(){const c=DB.get('config')||{};return (Array.isArray(c.sedes)?c.sedes:[]).filter(s=>s&&s.id);}
function sedesActive(){return sedesList().filter(s=>s.estado!=='inactivo');}
function sedeMainId(){const l=sedesList();return String((l.find(s=>s.principal)||l[0]||{}).id||'');}
function sedeName(id){return (sedesList().find(s=>String(s.id)===String(id))||{}).nombre||'';}
/* mySede: sede the user is LIMITED to ('' = sees all). homeSede: sede where the user works. */
function mySede(){return currentUser&&currentUser.rol!=='admin'&&currentUser.sede&&currentUser.sedeSolo!==false?String(currentUser.sede):'';}
function homeSede(){const s=String(currentUser?.sede||'');return sedesList().some(x=>String(x.id)===s)?s:sedeMainId();}
function patientSedeId(p){return String(p?.sede||sedeMainId());}
function sedesEnabled(){return sedesList().length>1;}
function sedeBadge(p){if(!sedesEnabled()||mySede())return '';const n=sedeName(patientSedeId(p));return n?`<span class="badge sede-badge" title="Establecimiento">${esc(n)}</span> `:'';}
function sedePatientValue(){const sel=document.getElementById('p-sede');if(!sedesList().length||!sel)return {};return {sede:mySede()||sel.value||sedeMainId()};}
function sedeOptions(selected,withAll){return (withAll?`<option value="">${esc(withAll)}</option>`:'')+sedesActive().map(s=>`<option value="${esc(s.id)}" ${String(s.id)===String(selected)?'selected':''}>${esc(s.nombre)}${s.principal?' (principal)':''}</option>`).join('');}
function sedeAccessOptions(solo){return `<option value="solo" ${solo?'selected':''}>Solo pacientes de su sede</option><option value="todas" ${!solo?'selected':''}>Pacientes de todas las sedes</option>`;}
function sedeUserSelect(u){
  if(!sedesEnabled())return '';
  const admin=u.rol==='admin';
  return `<div class="mt8"><label class="field-lbl" for="edit-u-sede-${u.id}">Sede de trabajo</label><select id="edit-u-sede-${u.id}" ${admin?'disabled title="El administrador ve todos los establecimientos"':''} onchange="document.getElementById('edit-u-sedeacc-${u.id}').disabled=!this.value">${sedeOptions(u.sede||'','Sin sede fija (todas)')}</select>
  <label class="field-lbl mt8" for="edit-u-sedeacc-${u.id}">Acceso a pacientes</label><select id="edit-u-sedeacc-${u.id}" ${admin||!u.sede?'disabled':''}>${sedeAccessOptions(u.sede&&u.sedeSolo!==false)}</select></div>`;
}
function sedeUserLabel(u){if(!sedesEnabled()||u.rol==='admin'||u.rol==='paciente')return '';return `<div class="text-xs mt4">${u.sede?`<span class="badge sede-badge">${esc(sedeName(u.sede)||u.sede)}</span> ${u.sedeSolo!==false?'solo su sede':'ve todas las sedes'}`:'<span class="text-muted">Todas las sedes</span>'}</div>`;}
/* ---------- cash box per sede ---------- */
function cashSedeId(){if(!sedesEnabled())return '';const mine=mySede();if(mine)return mine;let v='';try{v=localStorage.getItem('mg_cash_sede')||'';}catch(e){}return sedesActive().some(s=>String(s.id)===v)?v:homeSede();}
function sedeBoxMatch(box){return !sedesEnabled()||String(box?.sede||sedeMainId())===cashSedeId();}
function cashCurrentBox(boxes){return (boxes||DB.get('cajas')||[]).find(c=>c.estado==='abierta'&&sedeBoxMatch(c));}
function cashSedeBar(){
  if(!sedesEnabled())return '';
  const mine=mySede(),cur=cashSedeId();
  return `<div class="caja-sede-bar"><i class="ti ti-building-hospital"></i> ${mine?`Caja de <b>${esc(sedeName(mine))}</b>`:`<label for="cash-sede-sel">Caja de</label> <select id="cash-sede-sel" onchange="cashSedeChange(this.value)">${sedeOptions(cur)}</select>`}<span class="text-xs text-muted">Cada sede abre, cobra y cierra su propia caja.</span></div>`;
}
function cashSedeChange(v){try{localStorage.setItem('mg_cash_sede',v);}catch(e){}if(typeof renderCaja==='function')renderCaja();}
function sedesPublicFill(list){
  const wrap=document.getElementById('pub-sede-wrap'),sel=document.getElementById('pub-sede');if(!wrap||!sel)return;
  const items=(list||[]).filter(s=>s&&s.id);wrap.hidden=items.length<2;if(wrap.hidden)return;
  sel.innerHTML='<option value="">Elige la sede…</option>'+items.map(s=>`<option value="${esc(s.id)}">${esc(s.nombre)}</option>`).join('');
  const dir=document.getElementById('pub-sede-dir');sel.onchange=()=>{const s=items.find(x=>String(x.id)===sel.value);if(dir)dir.textContent=s?.dir||'';};
}
function sedeFillCitaForm(){
  const wrap=document.getElementById('c-sede-wrap'),sel=document.getElementById('c-sede');if(!wrap||!sel)return;
  wrap.hidden=!sedesEnabled();if(wrap.hidden)return;
  const id=+(document.getElementById('c-edit-id')?.value||0);const cita=(DB.get('citas')||[]).find(c=>+c.id===id);
  const pac=(DB.get('pacientes')||[]).find(p=>String(p.id)===String(document.getElementById('c-pac')?.value));
  const mine=mySede();const value=mine||cita?.sede||(pac?patientSedeId(pac):homeSede());
  sel.innerHTML=sedeOptions(value);sel.value=value;sel.disabled=!!mine;
}
/* ---------- patient form ---------- */
function sedeFillPatientForm(p){
  const row=document.getElementById('p-sede-row'),sel=document.getElementById('p-sede'),hint=document.getElementById('p-sede-hint');if(!row||!sel)return;
  row.hidden=!sedesEnabled();if(row.hidden)return;
  const mine=mySede();const value=p?patientSedeId(p):(mine||homeSede());
  sel.innerHTML=sedeOptions(value);sel.value=value;sel.disabled=!!mine;
  if(hint)hint.textContent=mine?`Tu usuario registra pacientes en ${sedeName(mine)}.`:'Sede donde se atiende el paciente.';
}
(function(){
  // Every cash-desk request (and pharmacy charges, which go to the box) carries the selected sede.
  if(window.API&&typeof API.post==='function'){const post=API.post.bind(API);API.post=function(path,payload){if(sedesEnabled()&&payload&&typeof payload==='object'&&!payload.sede&&(/^\/api\/cash\/(open|close|charge|payment|expense|expense-void)$/.test(path)||(path==='/api/pharmacy'&&/dispense|sell|venta|cobr/.test(String(payload.action||'')))))payload={...payload,sede:cashSedeId()};return post(path,payload);};}
  for(const name of ['openNewCita','editCita']){const fn=window[name];if(typeof fn==='function')window[name]=function(){const r=fn.apply(this,arguments);setTimeout(()=>{try{sedeFillCitaForm();}catch(e){}},120);return r;};}
  document.addEventListener('change',e=>{if(e.target&&e.target.id==='c-pac'&&!(+(document.getElementById('c-edit-id')?.value||0)))try{sedeFillCitaForm();}catch(_){}});
  const rc=window.renderCaja;if(typeof rc==='function')window.renderCaja=function(){const r=rc.apply(this,arguments);try{const el=document.getElementById('caja-content');if(el&&sedesEnabled()&&!el.querySelector('.caja-sede-bar'))el.insertAdjacentHTML('afterbegin',cashSedeBar());}catch(e){}return r;};
  const fill=window.fillPacModalSelects;
  if(typeof fill==='function')window.fillPacModalSelects=function(){const r=fill.apply(this,arguments);try{sedeFillPatientForm(null);}catch(e){}return r;};
  const edit=window.editPacModal;
  if(typeof edit==='function')window.editPacModal=function(id){const r=edit.apply(this,arguments);setTimeout(()=>{try{sedeFillPatientForm((DB.get('pacientes')||[]).find(x=>x.id===+id));}catch(e){}},80);return r;};
})();
/* ---------- patients filter, user form, header ---------- */
function sedesInstall(){
  const enabled=sedesEnabled(),mine=mySede();
  const espF=document.getElementById('pac-esp-f');
  if(espF&&enabled&&!mine&&!document.getElementById('pac-sede-f')){
    const s=document.createElement('select');s.id='pac-sede-f';s.setAttribute('aria-label','Filtrar por establecimiento');s.className=espF.className;s.style.cssText=espF.style.cssText;
    s.innerHTML=sedeOptions('','Todos los establecimientos');s.onchange=()=>{if(typeof renderPacs==='function')renderPacs();};
    espF.insertAdjacentElement('afterend',s);
  }
  const uw=document.getElementById('u-sede-wrap'),us=document.getElementById('u-sede');
  if(uw&&us){uw.hidden=!enabled;if(enabled&&!us.options.length)us.innerHTML=sedeOptions('','Sin sede fija (todas)');}
  const who=document.getElementById('sb-urole');
  if(who&&currentUser){const base=(typeof ROLE_LABELS!=='undefined'&&ROLE_LABELS[userRoleKey(currentUser)])||currentUser.rol;const work=enabled&&currentUser.rol!=='admin'&&currentUser.sede?sedeName(currentUser.sede):'';who.textContent=work?base+' · '+work:base;}
  sedesConfigCard();
}
/* ---------- Configuración: establishments ---------- */
let sedesDraft=null;
function sedesSlug(name){const base=String(name||'sede').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,24)||'sede';let id=base,i=2;const used=new Set((sedesDraft||[]).map(s=>s.id));while(used.has(id))id=base+'-'+(i++);return id;}
function sedesConfigCard(){
  const mod=document.getElementById('mod-config');if(!mod||currentUser?.rol!=='admin')return;
  let card=document.getElementById('sedes-card');
  if(!card){card=document.createElement('section');card.className='card mb16';card.id='sedes-card';const sri=[...mod.querySelectorAll('section.card')].find(c=>/Facturaci[oó]n electr[oó]nica SRI/.test(c.textContent));(sri||mod.firstElementChild)?.insertAdjacentElement('beforebegin',card);if(!card.parentElement)mod.prepend(card);}
  if(!sedesDraft)sedesDraft=JSON.parse(JSON.stringify(sedesList()));
  const counts={};(DB.get('pacientes')||[]).forEach(p=>{const k=patientSedeId(p);counts[k]=(counts[k]||0)+1;});
  const users={};(DB.get('users')||[]).forEach(u=>{if(u.sede)users[u.sede]=(users[u.sede]||0)+1;});
  card.innerHTML=`<div class="card-hdr"><h2 class="card-title"><i class="ti ti-building-hospital"></i> Establecimientos (sedes)</h2></div><div class="card-body">
  <p class="text-sm text-muted mb12">Cada paciente pertenece a un establecimiento. A cada usuario puedes asignarle una sede en "Usuarios": solo verá y registrará pacientes de esa sede. Los pacientes sin sede pertenecen al establecimiento principal.</p>
  <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Principal</th><th>Nombre</th><th>Dirección</th><th>Teléfono</th><th>Pacientes</th><th>Estado</th></tr></thead><tbody>
  ${sedesDraft.map((s,i)=>`<tr><td><input type="radio" name="sede-main" aria-label="Establecimiento principal" ${s.principal?'checked':''} onchange="sedesDraftMain(${i})"></td>
  <td><input aria-label="Nombre del establecimiento" value="${esc(s.nombre||'')}" maxlength="60" oninput="sedesDraft[${i}].nombre=this.value"></td>
  <td><input aria-label="Dirección" value="${esc(s.dir||'')}" maxlength="200" oninput="sedesDraft[${i}].dir=this.value"></td>
  <td><input aria-label="Teléfono" value="${esc(s.tel||'')}" maxlength="30" oninput="sedesDraft[${i}].tel=this.value" style="max-width:130px"></td>
  <td>${counts[s.id]||0}${users[s.id]?` · ${users[s.id]} usuario(s)`:''}</td>
  <td><select aria-label="Estado" onchange="sedesDraft[${i}].estado=this.value"><option value="activo" ${s.estado!=='inactivo'?'selected':''}>Activo</option><option value="inactivo" ${s.estado==='inactivo'?'selected':''}>Inactivo</option></select></td></tr>`).join('')||'<tr><td colspan="6" class="text-muted">Aún no hay establecimientos. Agrega el principal y los demás.</td></tr>'}
  </tbody></table></div>
  <div class="flex gap8 mt12" style="flex-wrap:wrap"><button class="btn-s" onclick="sedesDraftAdd()"><i class="ti ti-plus"></i> Agregar establecimiento</button><button class="btn-p" onclick="sedesSave()"><i class="ti ti-device-floppy"></i> Guardar establecimientos</button></div></div>`;
}
function sedesDraftAdd(){sedesDraft.push({id:'',nombre:'',dir:'',tel:'',estado:'activo',principal:!sedesDraft.length});sedesConfigCard();const inputs=document.querySelectorAll('#sedes-card tbody tr:last-child input');inputs[1]?.focus();}
function sedesDraftMain(i){sedesDraft.forEach((s,j)=>{s.principal=j===i;});}
async function sedesSave(){
  const rows=sedesDraft.map(s=>({...s,nombre:String(s.nombre||'').trim()}));
  if(rows.some(s=>s.nombre.length<2)){toast('Escribe el nombre de cada establecimiento.','err');return;}
  const names=rows.map(s=>s.nombre.toLowerCase());if(new Set(names).size!==names.length){toast('Hay establecimientos con el mismo nombre.','err');return;}
  rows.forEach(s=>{if(!s.id)s.id=sedesSlug(s.nombre);});
  if(rows.length&&!rows.some(s=>s.principal))rows[0].principal=true;
  const main=rows.find(s=>s.principal);if(main&&main.estado==='inactivo'){toast('El establecimiento principal debe estar activo.','err');return;}
  const cfg={...(DB.get('config')||{}),sedes:rows};
  DB.set('config',cfg);sedesDraft=JSON.parse(JSON.stringify(rows));
  try{await DB.tail;}catch(e){}
  if(DB.failures&&DB.failures.size){toast('No se pudo guardar. Revisa la conexión e intenta otra vez.','err');return;}
  toast('Establecimientos guardados','ok');sedesConfigCard();sedesInstall();
}
(function(){
  const prev=window.showMod;
  if(typeof prev==='function')window.showMod=function(id){const r=prev.apply(this,arguments);try{if(id==='config')sedesDraft=null;setTimeout(sedesInstall,250);}catch(e){}return r;};
  document.addEventListener('DOMContentLoaded',()=>setTimeout(sedesInstall,800));
})();
