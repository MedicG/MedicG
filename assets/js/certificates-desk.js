/* Medical certificates and exam orders from Reception: reception prepares the document a doctor
   asked for, signed with that doctor's details, without access to the clinical record (server enforced). */
function ctCanUse(){return currentUser?.rol==='admin'||(['recepcion','secretaria'].includes(currentUser?.rol)&&hasPerm('certificados'));}
function otCanUse(){return currentUser?.rol==='admin'||(['recepcion','secretaria'].includes(currentUser?.rol)&&hasPerm('ordenes'));}
function ctStore(key,pid,records){
  for(const bag of [DB.cache,DB.confirmed]){
    if(!bag[key]||typeof bag[key]!=='object')bag[key]={};
    bag[key][String(pid)]=bag===DB.confirmed?JSON.parse(JSON.stringify(records)):records;
  }
}
async function ctCall(payload){
  await DB.tail;
  const res=await API.post('/api/clinical/docs',payload);
  ctStore(res.key,res.patientId,res.records);
  return res;
}
function ctOpen(opts={}){
  if(!ctCanUse()){toast('No tienes permiso para emitir certificados','err');return;}
  const meds=(DB.get('medicos')||[]).filter(m=>m.estado!=='inactivo');
  const pats=ppPatients();
  cdModal('m-cert-desk','Certificado médico',`
  <p class="text-sm text-muted mb12">Emite el certificado que el médico solicitó. Se imprime con los datos y la firma del médico seleccionado y queda registrado quién lo elaboró.</p>
  <div class="form-row"><div class="field" style="flex:1.4"><label class="field-lbl">Paciente <span class="req">*</span></label><select id="ct-pac"><option value="">Seleccionar…</option>${pats.map(p=>`<option value="${p.id}">${esc(ppLabel(p))}</option>`).join('')}</select></div>
  <div class="field"><label class="field-lbl">Médico que solicita y firma <span class="req">*</span></label><select id="ct-med"><option value="">Seleccionar médico…</option>${meds.map(m=>`<option value="${m.id}">${esc(m.nombre)} · ${esc(m.esp||'')}</option>`).join('')}</select></div></div>
  ${cdCertWorkFields(opts.patientId)}
  <div class="form-row"><label class="field">Tipo<select id="cd-c-tipo" onchange="cdCertToggle()">${CD_CERT_TYPES.map(t=>`<option ${t===(opts.tipo||'Asistencia a consulta')?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Fecha de atención<input id="cd-c-fecha" type="date" value="${esc(opts.fecha&&opts.fecha<=today()?opts.fecha:today())}" max="${today()}"></label></div>
  <div class="form-row"><label class="field" style="flex:2">Diagnóstico (lo indica el médico)<input id="cd-c-dx" maxlength="300"></label><label class="field">CIE-10<input id="cd-c-cie" list="cd-cie-list" maxlength="12"><datalist id="cd-cie-list">${cdCieOptions()}</datalist></label></div>
  <div class="form-row" id="cd-c-reposo"><label class="field">Días de reposo<input id="cd-c-dias" type="number" min="1" max="365" value="1"></label><label class="field">Desde<input id="cd-c-desde" type="date" value="${today()}"></label></div>
  <label class="field">Texto del certificado<textarea id="cd-c-texto" rows="3" maxlength="3000" placeholder="Ej: Certifico que el/la paciente se encuentra en buen estado de salud..."></textarea></label>
  <label class="field">Recomendaciones<textarea id="cd-c-rec" rows="2" maxlength="1000"></textarea></label>
  <div class="flex gap8 mt8"><button class="btn-p" id="ct-save" onclick="ctSave()"><i class="ti ti-file-certificate"></i> Emitir e imprimir</button></div>
  <h4 class="mt16 mb8" style="font-size:14px">Certificados del paciente</h4>
  <div id="ct-list" class="text-sm text-muted">Selecciona un paciente para ver sus certificados.</div>`);
  patientPicker('ct-pac',{placeholder:'Escribe nombre, apellido o cédula…'});
  const sel=document.getElementById('ct-pac');
  sel.addEventListener('change',ctLoadList);
  if(opts.patientId){sel.value=String(opts.patientId);}
  if(opts.doctorId)document.getElementById('ct-med').value=String(opts.doctorId);
  else if(meds.length===1)document.getElementById('ct-med').value=String(meds[0].id);
  cdCertToggle();
  if(opts.patientId)ctLoadList();
}
async function ctLoadList(){
  const pid=document.getElementById('ct-pac')?.value;const box=document.getElementById('ct-list');if(!box)return;
  if(!pid){box.textContent='Selecciona un paciente para ver sus certificados.';return;}
  box.textContent='Cargando…';
  try{const res=await ctCall({action:'certificate_list',patientId:pid});ctRenderList(pid,res.records);cdCertFillWork(pid);}
  catch(e){box.textContent=e.message;}
}
function ctCanVoid(c){return c.estado!=='Anulado'&&(currentUser?.rol==='admin'||String(c.emitidoPorId)===String(currentUser?.id));}
function ctRenderList(pid,rows){
  const box=document.getElementById('ct-list');if(!box)return;
  if(!rows.length){box.innerHTML='<span class="text-muted">Sin certificados emitidos.</span>';return;}
  box.innerHTML=`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Número</th><th>Fecha</th><th>Tipo</th><th>Médico</th><th>Elaboró</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map(c=>`<tr><td>${esc(c.numero)}</td><td>${fmtDate(c.fechaEmision)}</td><td>${esc(c.tipo)}${c.reposo?`<div class="text-xs text-muted">${c.reposo.dias} día(s)</div>`:''}</td><td class="text-sm">${esc(c.medico?.nombre||'')}</td><td class="text-sm">${esc(c.emitidoPor||'')}</td><td><span class="badge ${c.estado==='Anulado'?'b-red':'b-green'}">${esc(c.estado)}</span></td><td style="white-space:nowrap"><button class="btn-s btn-xs" onclick="cdCertPrint(${+pid},'${esc(c.id)}')"><i class="ti ti-printer"></i> Imprimir</button>${ctCanVoid(c)?` <button class="btn-d btn-xs" onclick="ctVoid(${+pid},'${esc(c.id)}')">Anular</button>`:''}</td></tr>`).join('')}</tbody></table></div>`;
}
let ctBusy=false;
async function ctSave(){
  if(ctBusy)return;
  const pid=document.getElementById('ct-pac').value,doctorId=document.getElementById('ct-med').value;
  if(!pid){toast('Selecciona el paciente','err');return;}
  if(!doctorId){toast('Selecciona el médico que solicitó el certificado','err');return;}
  const tipo=document.getElementById('cd-c-tipo').value;
  const payload={action:'certificate_create',patientId:pid,doctorId,tipo,fechaAtencion:document.getElementById('cd-c-fecha').value,diagnostico:document.getElementById('cd-c-dx').value,cie10:document.getElementById('cd-c-cie').value,contenido:document.getElementById('cd-c-texto').value,recomendaciones:document.getElementById('cd-c-rec').value,...cdCertWorkPayload()};
  if(tipo==='Reposo médico'){payload.diasReposo=document.getElementById('cd-c-dias').value;payload.desde=document.getElementById('cd-c-desde').value;}
  ctBusy=true;const btn=document.getElementById('ct-save');if(btn)btn.disabled=true;
  try{
    const res=await ctCall(payload);
    ctRenderList(pid,res.records);
    ['cd-c-dx','cd-c-cie','cd-c-texto','cd-c-rec'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});
    toast('Certificado '+res.records[0].numero+' emitido','ok');
    cdCertPrint(+pid,res.records[0].id);
  }catch(e){toast(e.message,'err');}
  finally{ctBusy=false;if(btn)btn.disabled=false;}
}
function ctVoid(pid,id){
  cdModal('m-cd-void','Anular certificado',`<label class="field">Motivo de anulación<input id="cd-void-reason" maxlength="500"></label><button class="btn-d mt8" onclick="ctVoidSave(${pid},'${esc(id)}')">Anular certificado</button>`);
}
async function ctVoidSave(pid,id){
  try{const res=await ctCall({action:'certificate_void',patientId:pid,id,motivo:document.getElementById('cd-void-reason').value});closeM('m-cd-void');ctRenderList(pid,res.records);toast('Certificado anulado','inf');}
  catch(e){toast(e.message,'err');}
}
function ctFromCita(){
  const id=document.getElementById('c-edit-id')?.value;
  const c=(DB.get('citas')||[]).find(x=>String(x.id)===String(id));
  ctOpen(c?{patientId:c.pac,doctorId:c.med,fecha:c.fecha}:{});
}
/* ------------------------------------------------ exam orders from Reception */
function ctDoctorOptions(){return (DB.get('medicos')||[]).filter(m=>m.estado!=='inactivo').map(m=>`<option value="${m.id}">${esc(m.nombre)} · ${esc(m.esp||'')}</option>`).join('');}
function otOpen(opts={}){
  if(!otCanUse()){toast('No tienes permiso para crear órdenes de exámenes','err');return;}
  const meds=(DB.get('medicos')||[]).filter(m=>m.estado!=='inactivo');
  cdModal('m-ord-desk','Orden de exámenes',`
  <p class="text-sm text-muted mb12">Registra los exámenes que el médico solicitó. La orden se imprime con los datos y la firma del médico seleccionado y queda registrado quién la elaboró.</p>
  <div class="form-row"><div class="field" style="flex:1.4"><label class="field-lbl">Paciente <span class="req">*</span></label><select id="ot-pac"><option value="">Seleccionar…</option>${ppPatients().map(p=>`<option value="${p.id}">${esc(ppLabel(p))}</option>`).join('')}</select></div>
  <div class="field"><label class="field-lbl">Médico que solicita y firma <span class="req">*</span></label><select id="ot-med"><option value="">Seleccionar médico…</option>${ctDoctorOptions()}</select></div></div>
  ${cdOrderBody(null)}
  <div class="cd-o-actions"><button class="btn-s" onclick="closeM('m-ord-desk')">Cerrar</button><button class="btn-p" id="ot-save" onclick="otSave()"><i class="ti ti-test-pipe"></i> Crear e imprimir orden</button></div>
  <h4 class="mt16 mb8" style="font-size:14px">Órdenes del paciente</h4>
  <div id="ot-list" class="text-sm text-muted">Selecciona un paciente para ver sus órdenes.</div>`);
  patientPicker('ot-pac',{placeholder:'Escribe nombre, apellido o cédula…'});
  const sel=document.getElementById('ot-pac');sel.addEventListener('change',otLoadList);
  if(opts.patientId)sel.value=String(opts.patientId);
  if(opts.doctorId)document.getElementById('ot-med').value=String(opts.doctorId);
  else if(meds.length===1)document.getElementById('ot-med').value=String(meds[0].id);
  if(opts.patientId)otLoadList();
}
async function otLoadList(){
  const pid=document.getElementById('ot-pac')?.value;const box=document.getElementById('ot-list');if(!box)return;
  if(!pid){box.textContent='Selecciona un paciente para ver sus órdenes.';return;}
  box.textContent='Cargando…';
  try{const res=await ctCall({action:'lab_order_list',patientId:pid});otRenderList(pid,res.records);}
  catch(e){box.textContent=e.message;}
}
function otRenderList(pid,rows){
  const box=document.getElementById('ot-list');if(!box)return;
  if(!rows.length){box.innerHTML='<span class="text-muted">Sin órdenes de exámenes.</span>';return;}
  const canVoid=o=>currentUser?.rol==='admin'||String(o.creadoPorId)===String(currentUser?.id);
  box.innerHTML=`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Número</th><th>Fecha</th><th>Exámenes</th><th>Médico</th><th>Elaboró</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map(o=>`<tr><td>${esc(o.numero)}${o.prioridad==='Urgente'?' <span class="badge b-red">Urgente</span>':''}</td><td>${fmtDate(o.fecha)}</td><td class="text-sm">${esc((o.examenes||[]).map(e=>e.nombre).join(', '))}</td><td class="text-sm">${esc(o.medico?.nombre||'')}</td><td class="text-sm">${esc(o.creadoPor||'')}</td><td><span class="badge ${cdOrderBadge(o.estado)}">${esc(o.estado)}</span></td><td style="white-space:nowrap"><button class="btn-s btn-xs" onclick="cdOrderPrint(${+pid},'${esc(o.id)}')"><i class="ti ti-printer"></i> Imprimir</button>${o.estado!=='Anulada'?` <select class="btn-xs" aria-label="Cambiar estado" onchange="otStatus(${+pid},'${esc(o.id)}',this)"><option value="">Estado…</option>${CD_ORDER_STATES.filter(s=>s!==o.estado).map(s=>`<option>${s}</option>`).join('')}${canVoid(o)?'<option>Anulada</option>':''}</select>`:''}</td></tr>`).join('')}</tbody></table></div>`;
}
let otBusy=false;
async function otSave(){
  if(otBusy)return;
  const pid=document.getElementById('ot-pac').value,doctorId=document.getElementById('ot-med').value;
  if(!pid){toast('Selecciona el paciente','err');return;}
  if(!doctorId){toast('Selecciona el médico que solicitó los exámenes','err');return;}
  const data=cdOrderCollect();
  if(!data.examenes.length){toast('Selecciona o escribe al menos un examen','err');return;}
  otBusy=true;const btn=document.getElementById('ot-save');if(btn)btn.disabled=true;
  try{
    const res=await ctCall({action:'lab_order_create',patientId:pid,doctorId,...data});
    otRenderList(pid,res.records);
    document.querySelectorAll('#m-ord-desk .cd-o-check:checked').forEach(c=>{c.checked=false;});cdOrderCount();
    ['cd-o-otros','cd-o-dx','cd-o-cie','cd-o-ind','cd-o-q'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});cdOrderFilter('');
    toast('Orden '+res.records[0].numero+' creada','ok');
    cdOrderPrint(+pid,res.records[0].id);
  }catch(e){toast(e.message,'err');}
  finally{otBusy=false;if(btn)btn.disabled=false;}
}
async function otStatus(pid,id,select){
  const estado=select.value;if(!estado)return;
  let motivo='';
  if(estado==='Anulada'){motivo=(prompt('Motivo de anulación de la orden:')||'').trim();if(!motivo){select.value='';return;}}
  try{const res=await ctCall({action:'lab_order_status',patientId:pid,id,estado,motivo});otRenderList(pid,res.records);toast('Estado de la orden actualizado','ok');}
  catch(e){toast(e.message,'err');select.value='';}
}
function otFromCita(){
  const id=document.getElementById('c-edit-id')?.value;
  const c=(DB.get('citas')||[]).find(x=>String(x.id)===String(id));
  otOpen(c?{patientId:c.pac,doctorId:c.med}:{});
}
/* Entry points: agenda toolbar and the edit-appointment modal. */
function ctInstallButtons(){
  const rem=document.querySelector('button[onclick="remOpenPanel()"]');
  const send=document.querySelector('#m-cita button[onclick="remSendFromModal()"]');
  if(otCanUse()){
    if(rem&&!document.getElementById('ot-agenda-btn')){
      const b=document.createElement('button');b.id='ot-agenda-btn';b.className='btn-s btn-sm flex gap6';
      b.innerHTML='<i class="ti ti-test-pipe"></i>Orden de exámenes';b.onclick=()=>otOpen();rem.insertAdjacentElement('beforebegin',b);
    }
    if(send&&!document.getElementById('ot-cita-btn')){
      const b=document.createElement('button');b.id='ot-cita-btn';b.className='btn-s cita-edit-only';
      b.innerHTML='<i class="ti ti-test-pipe"></i> Exámenes';b.onclick=otFromCita;b.style.display=send.style.display;send.insertAdjacentElement('beforebegin',b);
    }
  }
  if(!ctCanUse())return;
  if(rem&&!document.getElementById('ct-agenda-btn')){
    const b=document.createElement('button');b.id='ct-agenda-btn';b.className='btn-s btn-sm flex gap6';
    b.innerHTML='<i class="ti ti-file-certificate"></i>Certificado médico';b.onclick=()=>ctOpen();rem.insertAdjacentElement('beforebegin',b);
  }
  if(send&&!document.getElementById('ct-cita-btn')){
    const b=document.createElement('button');b.id='ct-cita-btn';b.className='btn-s cita-edit-only';
    b.innerHTML='<i class="ti ti-file-certificate"></i> Certificado';b.onclick=ctFromCita;b.style.display=send.style.display;send.insertAdjacentElement('beforebegin',b);
  }
}
(function(){
  const prev=window.showMod;
  if(typeof prev==='function')window.showMod=function(...a){const r=prev.apply(this,a);try{ctInstallButtons();}catch(e){}return r;};
  document.addEventListener('DOMContentLoaded',()=>setTimeout(ctInstallButtons,500));
  setTimeout(ctInstallButtons,1500);
})();
