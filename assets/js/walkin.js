let walkinDraft=null;
function openWalkin(){
 if(currentUser?.rol==='medico'||!hasPerm('agenda'))return;
 walkinDraft={requestId:crypto.randomUUID(),items:[]};
 const doctors=(DB.get('medicos')||[]).filter(m=>m.estado!=='inactivo'&&(currentUser.rol!=='medico'||String(m.id)===String(currentUser.medicoId)));
 cashModal('m-walkin','Registrar consulta sin cita previa',`<p>Registra al paciente que llega directamente. Selecciona la fecha y los servicios de la atención.</p><div class="wi-patient-row"><label class="field">Paciente<select id="wi-patient"><option value="">Seleccionar paciente</option>${(DB.get('pacientes')||[]).map(p=>`<option value="${p.id}">${esc(p.nombres+' '+p.apellidos)}</option>`).join('')}</select></label><button class="btn-s" onclick="walkinNewPatient()">+ Nuevo paciente</button></div><div class="wi-details"><label class="field">Médico<select id="wi-doctor" onchange="walkinSpecialties()">${doctors.map(m=>`<option value="${m.id}">${esc(m.nombre)}</option>`).join('')}</select></label><label class="field">Fecha de atención<input id="wi-date" type="date" value="${today()}" required></label><label class="field">Hora de atención<input id="wi-time" type="time" value="${new Intl.DateTimeFormat('en-GB',{timeZone:'America/Guayaquil',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date())}" required></label></div><label class="field">Especialidad de la atención<select id="wi-specialty"></select></label><label class="field">Motivo de consulta<textarea rows="2" id="wi-reason" maxlength="2000"></textarea></label><div class="wi-catalog"><label class="field">Servicio o examen<select id="wi-item">${chargeOptionsHtml()}</select></label><button class="btn-p" onclick="walkinAdd()">Agregar</button></div><div id="wi-items" class="mt12"></div><p>Servicios médicos y exámenes · IVA 0%. El cobro se registra en caja.</p><button class="btn-g mt12" id="wi-save" onclick="saveWalkin()">Registrar consulta</button>`);
 walkinSpecialties();
}
function walkinAdd(){const key=document.getElementById('wi-item').value;if(!getChargeItem(key))return;const row=walkinDraft.items.find(i=>i.key===key);if(row)row.quantity++;else walkinDraft.items.push({key,quantity:1});walkinRender();}
function walkinRender(){
 document.getElementById('wi-items').innerHTML=walkinDraft.items.length?`<div class="wi-table-wrap"><table class="wi-table"><thead><tr><th>Servicio o examen</th><th>Cant.</th><th>Precio ($)</th><th>Total</th><th></th></tr></thead><tbody>${walkinDraft.items.map((i,n)=>`<tr><td>${esc(getChargeItem(i.key)?.nombre||'Concepto')}</td><td><input aria-label="Cantidad ${n+1}" type="number" min="1" max="1000" value="${i.quantity}" oninput="walkinDraft.items[${n}].quantity=Number(this.value);walkinTotal(${n})"></td><td>${cashCanEditPrice()?`<input aria-label="Precio ${n+1}" type="number" min="0" step="0.01" value="${esc(cashUnit(i))}" oninput="walkinDraft.items[${n}].unitPrice=this.value;walkinTotal(${n})">`:fmtMoney(cashUnit(i))}</td><td id="wi-total-${n}">${fmtMoney(cashUnit(i)*i.quantity)}</td><td><button class="btn-s" aria-label="Quitar concepto ${n+1}" onclick="walkinDraft.items.splice(${n},1);walkinRender()">×</button></td></tr>`).join('')}</tbody></table></div>`:'';
}
function walkinTotal(n){document.getElementById('wi-total-'+n).textContent=fmtMoney(cashUnit(walkinDraft.items[n])*walkinDraft.items[n].quantity);}
async function saveWalkin(){
 const button=document.getElementById('wi-save');if(button.disabled)return;button.disabled=true;
 try{
  await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de registrar.');
  const result=await API.post('/api/consultations/walkin',{requestId:walkinDraft.requestId,date:document.getElementById('wi-date').value,time:document.getElementById('wi-time').value,patientId:document.getElementById('wi-patient').value,doctorId:document.getElementById('wi-doctor').value,specialty:document.getElementById('wi-specialty').value,reason:document.getElementById('wi-reason').value,items:walkinDraft.items.map(i=>{const [kind,id]=i.key.split(':');return {kind,id,quantity:i.quantity,...(i.unitPrice!==undefined?{unitPrice:i.unitPrice}:{})};})});
  DB.cache.citas=result.appointments;DB.confirmed.citas=JSON.parse(JSON.stringify(result.appointments));if(result.nextIds){DB.cache.nextIds=result.nextIds;DB.confirmed.nextIds=JSON.parse(JSON.stringify(result.nextIds));}
  closeM('m-walkin');renderWeek();initDashboard();
  const a=result.appointment;
  cashModal('m-walkin-saved','Consulta registrada',`<p>Consulta #${a.id} registrada sin cita previa, con ${a.serviciosSolicitados.length} conceptos.</p><p>La atención está pendiente en la agenda. Todavía no se ha registrado ningún cobro.</p>${hasPerm('caja')?'<button class="btn-g" id="wi-cash">Llevar servicios a caja</button>':''}`);
  document.getElementById('wi-cash')?.addEventListener('click',()=>{if(cashDraft.items.length||cashDraft.payments.length){toast('Hay un cobro en preparación en caja. Termínalo antes de cargar esta consulta.','err');return;}cashDraft={patientId:String(a.pac),items:a.serviciosSolicitados.map(i=>({key:i.kind+':'+i.id,quantity:i.quantity,...(i.unitPrice!==undefined?{unitPrice:i.unitPrice}:{})})),payments:[]};closeM('m-walkin-saved');showMod('caja',document.querySelector('[data-module=caja]'));});
 }catch(e){toast(e.message,'err');}finally{button.disabled=false;}
}

let returnToWalkinAfterPac=false;
function walkinNewPatient(){
 openPacFromCita();returnToCitaAfterPac=false;returnToWalkinAfterPac=true;
 document.getElementById('m-pac').style.zIndex='10002';
 document.getElementById('m-pac-title').textContent='Nuevo paciente para consulta sin cita';
}
function walkinPatientSaved(id){
 returnToWalkinAfterPac=false;
 const select=document.getElementById('wi-patient');if(!select)return;
 select.innerHTML='<option value="">Seleccionar paciente</option>'+(DB.get('pacientes')||[]).map(p=>`<option value="${p.id}">${esc(p.nombres+' '+p.apellidos)}</option>`).join('');select.value=id;
}

function walkinSpecialties(){const m=(DB.get('medicos')||[]).find(m=>String(m.id)===document.getElementById('wi-doctor').value);document.getElementById('wi-specialty').innerHTML=(m?doctorSpecialties(m):[]).map(s=>`<option>${esc(s)}</option>`).join('');}
