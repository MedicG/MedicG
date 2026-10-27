/* Vital signs (editable by doctors with history), medical certificates and lab orders.
   All writes go through /api/clinical/docs; the server validates and audits every change. */
const CD_VITALS=[['pa','PA','mmHg','text','120/80'],['fc','FC','lpm','number',''],['fr','FR','rpm','number',''],['temp','T°','°C','number',''],['spo2','SpO₂','%','number',''],['peso','Peso','kg','number',''],['talla','Talla','cm','number',''],['glucosa','Glucosa','mg/dL','number',''],['perimetroAbdominal','P. abd.','cm','number','']];
const CD_CERT_TYPES=['Reposo médico','Asistencia a consulta','Certificado de salud','Otro'];
const CD_ORDER_STATES=['Pendiente','Muestra tomada','Resultados recibidos'];
let cdBusy=false;

function cdIsDoctor(){return currentUser?.rol==='medico'||(currentUser?.rol==='admin'&&!!currentUser?.medicoId);}
function cdCanIssue(){return currentUser?.rol==='medico'||currentUser?.rol==='admin';}
function cdRecords(key,pid){return ((DB.get(key)||{})[pid])||((DB.get(key)||{})[String(pid)])||[];}
function cdDoctorField(){
  if(currentUser?.rol==='medico')return '';
  const meds=(DB.get('medicos')||[]).filter(m=>m.estado!=='inactivo');
  return `<label class="field">Médico que firma<select id="cd-doctor">${meds.map(m=>`<option value="${m.id}" ${String(m.id)===String(currentUser?.medicoId)?'selected':''}>${esc(m.nombre)} · ${esc(m.esp||'')}</option>`).join('')}</select></label>`;
}
function cdModal(id,title,body){
  let el=document.getElementById(id);if(!el){el=document.createElement('div');el.id=id;el.className='modal-bg';document.body.appendChild(el);}
  el.innerHTML=`<section class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}" style="max-width:820px"><div class="card-hdr"><h3 class="card-title">${esc(title)}</h3><button class="btn-s" onclick="closeM('${id}')">Cerrar</button></div><div class="card-body" style="overflow:auto;max-height:78vh">${body}</div></section>`;openM(id);
}
async function cdSend(payload,tab){
  if(cdBusy)return null;cdBusy=true;
  try{
    await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de continuar.');
    const res=await API.post('/api/clinical/docs',payload);
    const store=DB.cache[res.key]&&typeof DB.cache[res.key]==='object'?DB.cache[res.key]:(DB.cache[res.key]={});
    store[res.patientId]=res.records;
    const confirmed=DB.confirmed[res.key]&&typeof DB.confirmed[res.key]==='object'?DB.confirmed[res.key]:(DB.confirmed[res.key]={});
    confirmed[res.patientId]=JSON.parse(JSON.stringify(res.records));
    renderHCE(+payload.patientId);if(tab)cdShowTab(tab);
    return res;
  }catch(e){toast(e.message,'err');return null;}finally{cdBusy=false;}
}
function cdShowTab(panelId){const tab=[...document.querySelectorAll('#hce-detail .tab')].find(t=>t.dataset.panel===panelId);if(tab)swTab(panelId,tab);}
function cdPrintHeader(title){
  const cfg=DB.get('config')||{};
  return `<div class="hdr"><img class="logo" src="${esc(cfg.logo||DEFAULT_LOGO)}"><div><div class="big">${esc(cfg.nombre||'Centro Médico')}</div><div class="muted">RUC: ${esc(cfg.ruc||'---')} · ${esc(cfg.tel||'')} · ${esc(cfg.email||'')}</div><div class="muted">${esc(cfg.dir||'')}</div></div></div><div class="rx-title">${esc(title)}</div>`;
}
function cdSignature(m){return `<div style="margin-top:70px;text-align:center"><div style="border-top:1px solid #111;width:300px;margin:0 auto;padding-top:6px"><b>${esc(m?.nombre||'')}</b><br>${esc(m?.especialidad||'')}<br>${m?.cedula?'C.I. '+esc(m.cedula):''}${m?.registro?' · Reg. SENESCYT '+esc(m.registro):''}</div></div>`;}

/* ---------------------------------------------------------------- vital signs */
function cdVitalsValue(v,key){const x=v?.[key];return x===undefined||x===''||x===null?'—':esc(String(x));}
function cdVitalsPanel(pid){
  const rows=cdRecords('signosVitales',pid);
  const notes=((DB.get('notas')||{})[pid]||[]).filter(n=>!n.clinicalVersion&&['pa','fc','fr','temp','spo2','peso','talla'].some(k=>n[k]));
  const head=`<tr><th>Fecha</th>${CD_VITALS.map(([,l,u])=>`<th>${l}<div class="text-xs text-muted">${u}</div></th>`).join('')}<th>IMC</th><th>Registró</th><th></th></tr>`;
  return `<div class="flex gap8 mb12" style="flex-wrap:wrap"><button class="btn-p btn-sm" onclick="cdVitalsForm(${pid})"><i class="ti ti-heartbeat"></i> Registrar signos vitales</button>${cdIsDoctor()?'':'<span class="text-xs text-muted" style="align-self:center">Solo los médicos pueden corregir registros guardados.</span>'}</div>
  <div class="tbl-wrap"><table class="tbl"><thead>${head}</thead><tbody>${rows.map(r=>`<tr><td>${fmtDate(r.fecha)} ${esc(r.hora||'')}${r.historial?.length?`<div><span class="badge b-amber" title="Corregido ${r.historial.length} vez/veces">Corregido</span></div>`:''}</td>${CD_VITALS.map(([k])=>`<td>${cdVitalsValue(r.valores,k)}</td>`).join('')}<td>${cdVitalsValue(r.valores,'imc')}</td><td class="text-xs">${esc(r.actualizadoPor||r.registradoPor||'')}</td><td>${cdIsDoctor()?`<button class="btn-s btn-xs" onclick="cdVitalsForm(${pid},'${esc(r.id)}')"><i class="ti ti-edit"></i> Editar</button>`:''}${r.historial?.length?` <button class="btn-s btn-xs" onclick="cdVitalsHistory(${pid},'${esc(r.id)}')">Historial</button>`:''}</td></tr>${r.observaciones?`<tr><td></td><td colspan="${CD_VITALS.length+3}" class="text-xs text-muted">${esc(r.observaciones)}</td></tr>`:''}`).join('')||`<tr><td colspan="${CD_VITALS.length+4}" class="text-muted">Sin signos vitales registrados.</td></tr>`}</tbody></table></div>
  ${notes.length?`<h4 class="mt16 mb8">Signos vitales en HCU</h4><div class="tbl-wrap"><table class="tbl"><thead><tr><th>HCU</th><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>SpO₂</th><th>Peso</th><th>Talla</th><th>IMC</th><th></th></tr></thead><tbody>${notes.map(n=>`<tr><td>${fmtDate(n.fecha)} ${esc(n.hora||'')}${n.signosHistorial?.length?' <span class="badge b-amber">Corregido</span>':''}</td>${['pa','fc','fr','temp','spo2','peso','talla','imc'].map(k=>`<td>${esc(n[k]||'—')}</td>`).join('')}<td>${cdIsDoctor()?`<button class="btn-s btn-xs" onclick="cdNoteVitalsForm(${pid},'${esc(String(n.id))}')"><i class="ti ti-edit"></i> Editar</button>`:''}</td></tr>`).join('')}</tbody></table></div>`:''}`;
}
function cdVitalsInputs(values){
  return `<div class="form-row" style="flex-wrap:wrap">${CD_VITALS.map(([k,l,u,t,ph])=>`<label class="field" style="min-width:120px;flex:1">${l} (${u})<input id="cd-v-${k}" type="${t}" ${t==='number'?'step="0.1"':''} placeholder="${ph}" value="${esc(values?.[k]??'')}"></label>`).join('')}</div>`;
}
function cdVitalsCollect(){const out={};CD_VITALS.forEach(([k])=>{out[k]=document.getElementById('cd-v-'+k)?.value??'';});return out;}
function cdVitalsForm(pid,recordId){
  const rec=recordId?cdRecords('signosVitales',pid).find(r=>r.id===recordId):null;
  if(recordId&&!cdIsDoctor()){toast('Solo los médicos pueden editar signos vitales','err');return;}
  cdModal('m-cd-vitals',rec?'Corregir signos vitales':'Registrar signos vitales',`<p class="text-sm"><strong>${esc(getPacName(pid))}</strong></p>
  ${rec?`<p class="text-sm text-muted">Registro del ${fmtDate(rec.fecha)} ${esc(rec.hora||'')}. Los valores anteriores se conservan en el historial.</p>`:`<div class="form-row"><label class="field">Fecha<input id="cd-v-fecha" type="date" value="${today()}" max="${today()}"></label><label class="field">Hora<input id="cd-v-hora" type="time" value="${new Date().toTimeString().slice(0,5)}"></label></div>`}
  ${cdVitalsInputs(rec?.valores)}
  <label class="field">Observaciones<textarea id="cd-v-obs" rows="2" maxlength="1000">${esc(rec?.observaciones||'')}</textarea></label>
  ${rec?'<label class="field">Motivo de la corrección (obligatorio)<input id="cd-v-motivo" maxlength="500" placeholder="Ej: error de digitación en la presión arterial"></label>':''}
  <button class="btn-p mt8" onclick="cdVitalsSave(${pid},'${rec?esc(rec.id):''}')">${rec?'Guardar corrección':'Guardar signos vitales'}</button>`);
}
async function cdVitalsSave(pid,recordId){
  const payload={action:'vitals_save',patientId:pid,...cdVitalsCollect(),observaciones:document.getElementById('cd-v-obs').value};
  if(recordId){payload.id=recordId;payload.motivo=document.getElementById('cd-v-motivo').value;}
  else{payload.fecha=document.getElementById('cd-v-fecha').value;payload.hora=document.getElementById('cd-v-hora').value;}
  if(await cdSend(payload,'t-vitales')){closeM('m-cd-vitals');toast(recordId?'Signos vitales corregidos':'Signos vitales registrados','ok');}
}
function cdVitalsHistory(pid,recordId){
  const r=cdRecords('signosVitales',pid).find(x=>x.id===recordId);if(!r)return;
  cdModal('m-cd-vhist','Historial de correcciones',`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Corregido</th><th>Por</th><th>Motivo</th><th>Valores anteriores</th></tr></thead><tbody>${(r.historial||[]).slice().reverse().map(h=>`<tr><td>${esc((h.editadoEn||'').replace('T',' ').slice(0,16))}</td><td>${esc(h.editadoPor||'')}</td><td>${esc(h.motivo||'')}</td><td class="text-xs">${Object.entries(h.valores||{}).map(([k,v])=>esc(k)+': '+esc(v)).join(' · ')}</td></tr>`).join('')}</tbody></table></div>`);
}
function cdNoteVitalsForm(pid,noteId){
  const n=((DB.get('notas')||{})[pid]||[]).find(x=>String(x.id)===String(noteId));if(!n)return;
  cdModal('m-cd-vitals','Corregir signos vitales de la HCU',`<p class="text-sm"><strong>${esc(getPacName(pid))}</strong> · HCU del ${fmtDate(n.fecha)} ${esc(n.hora||'')}</p>${cdVitalsInputs({pa:n.pa,fc:n.fc,fr:n.fr,temp:n.temp,spo2:n.spo2,peso:n.peso,talla:n.talla})}
  <label class="field">Motivo de la corrección (obligatorio)<input id="cd-v-motivo" maxlength="500"></label>
  <button class="btn-p mt8" onclick="cdNoteVitalsSave(${pid},'${esc(String(noteId))}')">Guardar corrección</button>`);
}
async function cdNoteVitalsSave(pid,noteId){
  const v=cdVitalsCollect();delete v.glucosa;delete v.perimetroAbdominal;
  if(await cdSend({action:'note_vitals',patientId:pid,noteId,...v,motivo:document.getElementById('cd-v-motivo').value},'t-vitales')){closeM('m-cd-vitals');toast('Signos vitales de la HCU corregidos','ok');}
}

/* ---------------------------------------------------------- medical certificates */
function cdCertPanel(pid){
  const rows=cdRecords('certificados',pid);
  return `${cdCanIssue()?`<div class="mb12"><button class="btn-p btn-sm" onclick="cdCertForm(${pid})"><i class="ti ti-file-certificate"></i> Nuevo certificado médico</button></div>`:''}
  <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Número</th><th>Fecha</th><th>Tipo</th><th>Detalle</th><th>Médico</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map(c=>`<tr><td>${esc(c.numero)}</td><td>${fmtDate(c.fechaEmision)}</td><td>${esc(c.tipo)}</td><td class="text-sm">${c.reposo?`${c.reposo.dias} día(s): ${fmtDate(c.reposo.desde)} al ${fmtDate(c.reposo.hasta)}`:esc((c.diagnostico||c.contenido||'').slice(0,80))}</td><td class="text-sm">${esc(c.medico?.nombre||'')}</td><td><span class="badge ${c.estado==='Anulado'?'b-red':'b-green'}">${esc(c.estado)}</span></td><td><button class="btn-s btn-xs" onclick="cdCertPrint(${pid},'${esc(c.id)}')"><i class="ti ti-printer"></i> Imprimir</button>${c.estado!=='Anulado'&&(currentUser?.rol==='admin'||String(c.medico?.id)===String(currentUser?.medicoId))?` <button class="btn-d btn-xs" onclick="cdCertVoid(${pid},'${esc(c.id)}')">Anular</button>`:''}</td></tr>`).join('')||'<tr><td colspan="7" class="text-muted">Sin certificados emitidos.</td></tr>'}</tbody></table></div>`;
}
function cdCieOptions(){return (typeof cie10Catalog==='function'?cie10Catalog():[]).slice(0,4000).map(c=>`<option value="${esc(c.code)}">${esc(c.desc)}</option>`).join('');}
function cdDaysWords(n){n=Math.floor(Number(n)||0);let w=typeof phNumberWords==='function'?phNumberWords(n):String(n);w=w.replace(/uno$/,'un').replace(/veintiuno$/,'veintiún');return `${w.toUpperCase()} (${n}) ${n===1?'día':'días'}`;}
function cdLastCert(pid){return cdRecords('certificados',pid).find(c=>c.empresa||c.cargo||c.domicilio)||{};}
function cdCertWorkFields(pid){
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};const last=cdLastCert(pid);
  return `<div class="form-row"><label class="field" style="flex:2">Dirección de domicilio<input id="cd-c-dom" maxlength="300" value="${esc(p.dir||last.domicilio||'')}" placeholder="Calle, número, ciudad"></label></div>
  <div class="form-row"><label class="field">Empresa donde labora<input id="cd-c-emp" maxlength="200" value="${esc(last.empresa||'')}" placeholder="Opcional"></label><label class="field">Cargo / puesto que desempeña<input id="cd-c-cargo" maxlength="150" value="${esc(last.cargo||'')}" placeholder="Opcional"></label></div>`;
}
function cdCertFillWork(pid){
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};const last=cdLastCert(pid);
  const set=(id,v)=>{const el=document.getElementById(id);if(el)el.value=v||'';};
  set('cd-c-dom',p.dir||last.domicilio);set('cd-c-emp',last.empresa);set('cd-c-cargo',last.cargo);
}
function cdCertWorkPayload(){const v=id=>document.getElementById(id)?.value||'';return {domicilio:v('cd-c-dom'),empresa:v('cd-c-emp'),cargo:v('cd-c-cargo')};}
function cdCertForm(pid){
  if(!cdCanIssue()){toast('Solo médicos o el administrador emiten certificados','err');return;}
  const lastDx=((DB.get('notas')||{})[pid]||[])[0];
  cdModal('m-cd-cert','Nuevo certificado médico',`<p class="text-sm"><strong>${esc(getPacName(pid))}</strong></p>
  ${cdDoctorField()}
  ${cdCertWorkFields(pid)}
  <div class="form-row"><label class="field">Tipo<select id="cd-c-tipo" onchange="cdCertToggle()">${CD_CERT_TYPES.map(t=>`<option>${t}</option>`).join('')}</select></label><label class="field">Fecha de atención<input id="cd-c-fecha" type="date" value="${today()}" max="${today()}"></label></div>
  <div class="form-row"><label class="field" style="flex:2">Diagnóstico<input id="cd-c-dx" maxlength="300" value="${esc(lastDx?.cie10Desc||'')}"></label><label class="field">CIE-10<input id="cd-c-cie" list="cd-cie-list" maxlength="12" value="${esc(lastDx?.cie10Code||'')}"><datalist id="cd-cie-list">${cdCieOptions()}</datalist></label></div>
  <div class="form-row" id="cd-c-reposo"><label class="field">Días de reposo<input id="cd-c-dias" type="number" min="1" max="365" value="1"></label><label class="field">Desde<input id="cd-c-desde" type="date" value="${today()}"></label></div>
  <label class="field">Texto del certificado<textarea id="cd-c-texto" rows="4" maxlength="3000" placeholder="Ej: Certifico que el/la paciente se encuentra en buen estado de salud..."></textarea></label>
  <label class="field">Recomendaciones<textarea id="cd-c-rec" rows="2" maxlength="1000"></textarea></label>
  <button class="btn-p mt8" onclick="cdCertSave(${pid})"><i class="ti ti-file-certificate"></i> Emitir e imprimir</button>`);
  cdCertToggle();
}
function cdCertToggle(){const rest=document.getElementById('cd-c-tipo')?.value==='Reposo médico';const el=document.getElementById('cd-c-reposo');if(el)el.style.display=rest?'':'none';}
async function cdCertSave(pid){
  const tipo=document.getElementById('cd-c-tipo').value;
  const payload={action:'certificate_create',patientId:pid,tipo,fechaAtencion:document.getElementById('cd-c-fecha').value,diagnostico:document.getElementById('cd-c-dx').value,cie10:document.getElementById('cd-c-cie').value,contenido:document.getElementById('cd-c-texto').value,recomendaciones:document.getElementById('cd-c-rec').value,doctorId:document.getElementById('cd-doctor')?.value,...cdCertWorkPayload()};
  if(tipo==='Reposo médico'){payload.diasReposo=document.getElementById('cd-c-dias').value;payload.desde=document.getElementById('cd-c-desde').value;}
  const res=await cdSend(payload,'t-certs');
  if(res){closeM('m-cd-cert');toast('Certificado emitido','ok');cdCertPrint(pid,res.records[0].id);}
}
function cdCertVoid(pid,id){
  cdModal('m-cd-void','Anular certificado',`<label class="field">Motivo de anulación<input id="cd-void-reason" maxlength="500"></label><button class="btn-d mt8" onclick="cdCertVoidSave(${pid},'${esc(id)}')">Anular certificado</button>`);
}
async function cdCertVoidSave(pid,id){if(await cdSend({action:'certificate_void',patientId:pid,id,motivo:document.getElementById('cd-void-reason').value},'t-certs')){closeM('m-cd-void');toast('Certificado anulado','inf');}}
function cdCertPrint(pid,id){
  const c=cdRecords('certificados',pid).find(x=>x.id===id);if(!c)return;
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};
  const age=typeof patientAge==='function'?patientAge(p):'';
  let body;
  const who=`el/la paciente <b>${esc(c.paciente?.nombre)}</b>, con documento de identidad <b>${esc(c.paciente?.cedula||'—')}</b>${age&&age!=='—'?`, de ${esc(age)} años de edad`:''}${c.domicilio?`, con domicilio en <b>${esc(c.domicilio)}</b>`:''}${c.empresa?`, quien labora en <b>${esc(c.empresa)}</b>${c.cargo?` desempeñando el cargo de <b>${esc(c.cargo)}</b>`:''}`:(c.cargo?`, quien desempeña el cargo de <b>${esc(c.cargo)}</b>`:'')}`;
  const dx=c.diagnostico?` con diagnóstico de <b>${esc(c.diagnostico)}</b>${c.cie10?` (CIE-10 ${esc(c.cie10)})`:''}`:'';
  if(c.tipo==='Reposo médico')body=`Certifico que ${who}, fue atendido/a en esta casa de salud el <b>${fmtDate(c.fechaAtencion)}</b>${dx}, por lo que requiere <b>${cdDaysWords(c.reposo.dias)} de reposo</b> desde el <b>${fmtDate(c.reposo.desde)}</b> hasta el <b>${fmtDate(c.reposo.hasta)}</b> inclusive.`;
  else if(c.tipo==='Asistencia a consulta')body=`Certifico que ${who}, acudió a consulta médica en esta casa de salud el <b>${fmtDate(c.fechaAtencion)}</b>${dx}.`;
  else body=`Paciente: <b>${esc(c.paciente?.nombre)}</b> · Documento: <b>${esc(c.paciente?.cedula||'—')}</b> · Fecha de atención: <b>${fmtDate(c.fechaAtencion)}</b>${c.domicilio?`<br>Domicilio: <b>${esc(c.domicilio)}</b>`:''}${c.empresa?`<br>Empresa: <b>${esc(c.empresa)}</b>`:''}${c.cargo?` · Cargo: <b>${esc(c.cargo)}</b>`:''}${c.diagnostico?`<br>Diagnóstico: <b>${esc(c.diagnostico)}</b>${c.cie10?` (CIE-10 ${esc(c.cie10)})`:''}`:''}`;
  printDoc('Certificado '+c.numero,`${cdPrintHeader('CERTIFICADO MÉDICO')}${c.estado==='Anulado'?'<div class="box" style="color:#b00;font-weight:bold;text-align:center">DOCUMENTO ANULADO</div>':''}
  <div class="row"><div><div class="label">Número</div>${esc(c.numero)}</div><div><div class="label">Tipo</div>${esc(c.tipo)}</div><div><div class="label">Fecha de emisión</div>${fmtDate(c.fechaEmision)}</div></div>
  <p style="line-height:1.7;margin-top:18px;text-align:justify">${body}</p>
  ${c.contenido?`<p style="line-height:1.7;text-align:justify;white-space:pre-wrap">${esc(c.contenido)}</p>`:''}
  ${c.recomendaciones?`<div class="box"><div class="label">Recomendaciones</div><pre>${esc(c.recomendaciones)}</pre></div>`:''}
  <p>Se extiende el presente certificado a petición del interesado/a para los fines que estime conveniente.</p>${cdSignature(c.medico)}`);
}

/* ------------------------------------------------------------- laboratory orders */
function cdOrderBadge(s){return s==='Anulada'?'b-red':s==='Resultados recibidos'?'b-green':s==='Muestra tomada'?'b-blue':'b-amber';}
function cdOrdersPanel(pid){
  const rows=cdRecords('ordenesLab',pid);
  return `${cdCanIssue()?`<div class="mb12"><button class="btn-p btn-sm" onclick="cdOrderForm(${pid})"><i class="ti ti-test-pipe"></i> Nueva orden de laboratorio</button></div>`:''}
  <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Número</th><th>Fecha</th><th>Exámenes</th><th>Prioridad</th><th>Médico</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map(o=>`<tr><td>${esc(o.numero)}</td><td>${fmtDate(o.fecha)}</td><td class="text-sm">${esc((o.examenes||[]).map(e=>e.nombre).join(', '))}</td><td>${o.prioridad==='Urgente'?'<span class="badge b-red">Urgente</span>':'Rutina'}</td><td class="text-sm">${esc(o.medico?.nombre||'')}</td><td><span class="badge ${cdOrderBadge(o.estado)}">${esc(o.estado)}</span></td><td><button class="btn-s btn-xs" onclick="cdOrderPrint(${pid},'${esc(o.id)}')"><i class="ti ti-printer"></i> Imprimir</button>${o.estado!=='Anulada'?` <select class="btn-xs" aria-label="Cambiar estado" onchange="cdOrderStatus(${pid},'${esc(o.id)}',this.value)"><option value="">Cambiar estado…</option>${CD_ORDER_STATES.filter(s=>s!==o.estado).map(s=>`<option>${s}</option>`).join('')}${cdCanIssue()?'<option>Anulada</option>':''}</select>`:''}</td></tr>`).join('')||'<tr><td colspan="7" class="text-muted">Sin órdenes de laboratorio.</td></tr>'}</tbody></table></div>`;
}
function cdTitle(v){const s=String(v||'').trim();return s&&s===s.toUpperCase()&&s.length>3?s.charAt(0)+s.slice(1).toLowerCase():s;}
function cdOrderForm(pid){
  if(!cdCanIssue()){toast('Solo médicos o el administrador crean órdenes','err');return;}
  const groups={};
  (DB.get('examenes')||[]).forEach(e=>{const g=cdTitle(e.categoria)||'Otros';(groups[g]=groups[g]||[]).push(e);});
  const ordered=Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0],'es')).map(([g,l])=>[g,l.sort((x,y)=>String(x.nombre).localeCompare(String(y.nombre),'es'))]);
  const lastDx=((DB.get('notas')||{})[pid]||[])[0];
  cdModal('m-cd-order','Nueva orden de laboratorio',`<div class="cd-o-patient"><i class="ti ti-user"></i> <strong>${esc(getPacName(pid))}</strong></div>${cdDoctorField()}
  <div class="cd-o-toolbar"><div class="si" style="flex:1"><i class="ti ti-search"></i><input id="cd-o-q" placeholder="Buscar examen: hemograma, glucosa, TSH…" oninput="cdOrderFilter(this.value)" autocomplete="off"></div><span class="cd-o-count" id="cd-o-count">0 seleccionados</span></div>
  <div id="cd-o-selected" class="cd-o-selected"></div>
  <div id="cd-o-list" class="cd-o-list">${ordered.map(([g,list],gi)=>`<section class="cd-o-group" data-group="${gi}"><header><span>${esc(g)} <em>${list.length}</em></span><button type="button" class="btn-s btn-xs" onclick="cdOrderToggleGroup(${gi})">Seleccionar todo</button></header><div class="cd-o-grid">${list.map(e=>`<label class="cd-o-item" data-name="${esc(proNormSafe(e.nombre+' '+g))}"><input type="checkbox" class="cd-o-check" value="${esc(String(e.id))}" data-label="${esc(e.nombre)}" onchange="cdOrderCount()"><span>${esc(e.nombre)}</span></label>`).join('')}</div></section>`).join('')||'<p class="text-muted">No hay exámenes en el catálogo. Escríbelos abajo.</p>'}</div>
  <label class="field mt12">Otros exámenes no listados (uno por línea)<textarea id="cd-o-otros" rows="2" maxlength="2000"></textarea></label>
  <div class="form-row"><label class="field" style="flex:2">Diagnóstico presuntivo<input id="cd-o-dx" maxlength="300" value="${esc(lastDx?.cie10Desc||'')}"></label><label class="field">CIE-10<input id="cd-o-cie" list="cd-cie-list2" maxlength="12" value="${esc(lastDx?.cie10Code||'')}"><datalist id="cd-cie-list2">${cdCieOptions()}</datalist></label><label class="field">Prioridad<select id="cd-o-prio"><option>Rutina</option><option>Urgente</option></select></label></div>
  <label class="field">Indicaciones para el paciente<textarea id="cd-o-ind" rows="2" maxlength="1000" placeholder="Ej: Ayuno de 8 a 12 horas"></textarea></label>
  <div class="cd-o-actions"><button class="btn-s" onclick="closeM('m-cd-order')">Cancelar</button><button class="btn-p" onclick="cdOrderSave(${pid})"><i class="ti ti-test-pipe"></i> Crear e imprimir orden</button></div>`);
  setTimeout(()=>document.getElementById('cd-o-q')?.focus(),50);
}
function proNormSafe(v){return String(v??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();}
function cdOrderFilter(q){
  q=proNormSafe(q).trim();
  document.querySelectorAll('#cd-o-list .cd-o-group').forEach(g=>{let visible=0;g.querySelectorAll('.cd-o-item').forEach(el=>{const show=!q||el.dataset.name.includes(q);el.style.display=show?'':'none';if(show)visible++;});g.style.display=visible?'':'none';});
}
function cdOrderToggleGroup(i){
  const boxes=[...document.querySelectorAll(`#cd-o-list .cd-o-group[data-group="${i}"] .cd-o-item`)].filter(el=>el.style.display!=='none').map(el=>el.querySelector('input'));
  const all=boxes.every(b=>b.checked);boxes.forEach(b=>{b.checked=!all;});cdOrderCount();
}
function cdOrderCount(){
  const checked=[...document.querySelectorAll('.cd-o-check:checked')];
  const c=document.getElementById('cd-o-count');if(c)c.textContent=`${checked.length} seleccionado${checked.length===1?'':'s'}`;
  const sel=document.getElementById('cd-o-selected');
  if(sel)sel.innerHTML=checked.map(b=>`<button type="button" class="cd-o-chip" onclick="document.querySelector('.cd-o-check[value=&quot;${esc(b.value)}&quot;]').checked=false;cdOrderCount()">${esc(b.dataset.label)} <i class="ti ti-x"></i></button>`).join('');
}
async function cdOrderSave(pid){
  const examenes=[...document.querySelectorAll('.cd-o-check:checked')].map(c=>({id:c.value}));
  document.getElementById('cd-o-otros').value.split('\n').map(x=>x.trim()).filter(Boolean).forEach(nombre=>examenes.push({nombre}));
  if(!examenes.length){toast('Selecciona o escribe al menos un examen','err');return;}
  const res=await cdSend({action:'lab_order_create',patientId:pid,examenes,diagnostico:document.getElementById('cd-o-dx').value,cie10:document.getElementById('cd-o-cie').value,prioridad:document.getElementById('cd-o-prio').value,indicaciones:document.getElementById('cd-o-ind').value,doctorId:document.getElementById('cd-doctor')?.value},'t-labs');
  if(res){closeM('m-cd-order');toast('Orden de laboratorio creada','ok');cdOrderPrint(pid,res.records[0].id);}
}
async function cdOrderStatus(pid,id,estado){
  if(!estado)return;
  let motivo='';
  if(estado==='Anulada'){motivo=prompt('Motivo de anulación de la orden:')||'';if(!motivo.trim()){renderHCE(+pid);cdShowTab('t-labs');return;}}
  if(await cdSend({action:'lab_order_status',patientId:pid,id,estado,motivo},'t-labs'))toast('Estado de la orden actualizado','ok');
}
function cdOrderPrint(pid,id){
  const o=cdRecords('ordenesLab',pid).find(x=>x.id===id);if(!o)return;
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};
  const groups={};(o.examenes||[]).forEach(e=>{(groups[e.categoria||'Otros']=groups[e.categoria||'Otros']||[]).push(e.nombre);});
  printDoc('Orden '+o.numero,`${cdPrintHeader('ORDEN DE LABORATORIO')}${o.estado==='Anulada'?'<div class="box" style="color:#b00;font-weight:bold;text-align:center">ORDEN ANULADA</div>':''}
  <div class="row"><div><div class="label">Número</div>${esc(o.numero)}</div><div><div class="label">Fecha</div>${fmtDate(o.fecha)}</div><div><div class="label">Prioridad</div>${esc(o.prioridad)}</div></div>
  <table width="100%" border="1" cellspacing="0" cellpadding="6"><tr><td><b>Paciente:</b> ${esc(o.paciente?.nombre)}</td><td><b>Documento:</b> ${esc(o.paciente?.cedula||'—')}</td><td><b>Edad:</b> ${esc(typeof patientAge==='function'?patientAge(p):'')}${p.genero?' · '+esc(p.genero):''}</td></tr>${o.diagnostico?`<tr><td colspan="3"><b>Diagnóstico presuntivo:</b> ${esc(o.diagnostico)}${o.cie10?` (CIE-10 ${esc(o.cie10)})`:''}</td></tr>`:''}</table>
  <div class="box"><div class="label">Exámenes solicitados</div>${Object.entries(groups).map(([g,list])=>`<div style="margin-top:8px"><b>${esc(g)}</b><ul style="margin:4px 0 0 4px;columns:2;list-style:none;padding:0">${list.map(n=>`<li>☐ ${esc(n)}</li>`).join('')}</ul></div>`).join('')}</div>
  ${o.indicaciones?`<div class="box"><div class="label">Indicaciones para el paciente</div><pre>${esc(o.indicaciones)}</pre></div>`:''}${cdSignature(o.medico)}`);
}

/* ----------------------------------------------------- integration with the HCE */
(function(){
  if(typeof renderHCE!=='function')return;
  const baseRenderHCE=renderHCE;
  renderHCE=function(id){
    baseRenderHCE(id);
    if(!hasPerm('hce'))return;
    const tabs=document.querySelector('#hce-detail .tabs');const body=document.getElementById('t-evo')?.parentElement;
    if(!tabs||!body)return;
    document.querySelectorAll('#hce-detail .tab').forEach(t=>{const m=(t.getAttribute('onclick')||'').match(/swTab\('([^']+)'/);if(m)t.dataset.panel=m[1];});
    const add=(panel,label,html)=>{const t=document.createElement('div');t.className='tab';t.dataset.panel=panel;t.textContent=label;t.onclick=function(){swTab(panel,this);};tabs.appendChild(t);const d=document.createElement('div');d.id=panel;d.className='tab-panel';d.innerHTML=html;body.appendChild(d);};
    add('t-vitales','Signos vitales ('+cdRecords('signosVitales',id).length+')',cdVitalsPanel(id));
    add('t-certs','Certificados ('+cdRecords('certificados',id).length+')',cdCertPanel(id));
    add('t-labs','Órdenes de laboratorio ('+cdRecords('ordenesLab',id).length+')',cdOrdersPanel(id));
  };
})();
