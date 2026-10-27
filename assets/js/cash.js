/* Multi-item patient accounts and split payments. All writes go through the cash API. */
let cashDraft={patientId:'',items:[],payments:[]};
let cashAbono={invoiceId:'',payments:[]};
let cashBusy=false;
let cashHistoryPatient=null;
const cashMethods=['Efectivo','Tarjeta débito','Tarjeta crédito','Transferencia'];
function cashPending(){try{return JSON.parse(sessionStorage.getItem('mg_cash_pending')||'null');}catch{return null;}}
function cashMoney(n){return Math.round((Number(n)+Number.EPSILON)*100);}
function cashCanEditPrice(){return ['admin','recepcion','secretaria'].includes(currentUser?.rol);}
function cashUnit(row){const item=getChargeItem(row.key);return row.unitPrice!==undefined?Number(row.unitPrice):item?Math.round(cashMoney(item.precio)*(1-(+item.descuento||0)/100))/100:0;}
function cashTotals(){
  let sub=0;
  cashDraft.items.forEach(row=>{const item=getChargeItem(row.key);if(item)sub+=cashMoney(cashUnit(row))*row.quantity;});
  const rate=0;
  const iva=Math.round(sub*rate/100);
  return {sub:sub/100,iva:iva/100,total:(sub+iva)/100,rate};
}
function cashPaymentRows(type){
 const state=type==='charge'?cashDraft:cashAbono;
 return state.payments.map((p,i)=>`<div class="cash-payment-row">
 <label>Forma de pago<select aria-label="Forma de pago ${i+1}" onchange="cashSetPayment('${type}',${i},'method',this.value)">${cashMethods.map(m=>`<option ${p.method===m?'selected':''}>${m}</option>`).join('')}</select></label>
 <label>Monto recibido ($)<input aria-label="Monto recibido ${i+1}" type="number" min="0.01" step="0.01" value="${esc(p.amount)}" oninput="cashSetPayment('${type}',${i},'amount',this.value)"></label>
 <label>Referencia (opcional)<input aria-label="Referencia ${i+1}" maxlength="120" value="${esc(p.reference)}" oninput="cashSetPayment('${type}',${i},'reference',this.value)"></label>
 <button class="btn-s" aria-label="Quitar pago ${i+1}" onclick="cashRemovePayment('${type}',${i})">Quitar</button></div>`).join('')||'<p class="text-muted">Sin pago inicial: el total quedará pendiente.</p>';
}
function cashSetPayment(type,i,key,value){(type==='charge'?cashDraft:cashAbono).payments[i][key]=value;cashUpdateTotals();}
function cashAddPayment(type){(type==='charge'?cashDraft:cashAbono).payments.push({method:'Efectivo',amount:'',reference:''});cashRenderPayments(type);}
function cashRemovePayment(type,i){(type==='charge'?cashDraft:cashAbono).payments.splice(i,1);cashRenderPayments(type);}
function cashRenderPayments(type){const el=document.getElementById('cash-'+type+'-payments');if(el)el.innerHTML=cashPaymentRows(type);cashUpdateTotals();}
function cashUpdateTotals(){
 const totals=cashTotals();const paid=cashDraft.payments.reduce((sum,p)=>sum+cashMoney(p.amount||0),0)/100;
 const el=document.getElementById('cash-summary');if(el)el.innerHTML=`<span>Subtotal <strong>${fmtMoney(totals.sub)}</strong></span><span>IVA (${totals.rate}%) <strong>${fmtMoney(totals.iva)}</strong></span><span>Total <strong>${fmtMoney(totals.total)}</strong></span><span>Recibido <strong>${fmtMoney(paid)}</strong></span><span>Saldo pendiente <strong>${fmtMoney(totals.total-paid)}</strong></span>`;
 const invoice=(DB.get('facturas')||[]).find(f=>f.id===cashAbono.invoiceId);
 const abono=document.getElementById('cash-abono-summary');if(abono&&invoice){const received=cashAbono.payments.reduce((sum,p)=>sum+cashMoney(p.amount||0),0)/100;abono.textContent=`Saldo actual: ${fmtMoney(invoice.saldo)} · Este abono: ${fmtMoney(received)} · Quedará debiendo: ${fmtMoney(Number(invoice.saldo)-received)}`;}
}
function cashAddItem(){
 const key=document.getElementById('cash-item').value;if(!getChargeItem(key))return;
 const row=cashDraft.items.find(r=>r.key===key);if(row)row.quantity++;else cashDraft.items.push({key,quantity:1});cashRenderItems();
}
function cashRemoveItem(i){cashDraft.items.splice(i,1);cashRenderItems();}
function cashQuantity(i,value){cashDraft.items[i].quantity=Number(value);cashUpdateTotals();}
function cashRenderItems(){const el=document.getElementById('cash-items');if(!el)return;
 el.innerHTML=cashDraft.items.map((row,i)=>{const item=getChargeItem(row.key);return `<div class="cash-item-row"><div><strong>${esc(item?.nombre||'Concepto eliminado')}</strong><div class="text-muted text-sm">${item?.kind==='examen'?'Examen':'Servicio'} · ${fmtMoney(item?chargeItemFinal(item).total:0)} por unidad · IVA 0%</div></div><label>Cantidad<input type="number" min="1" max="1000" step="1" aria-label="Cantidad ${i+1}" value="${row.quantity}" onchange="cashQuantity(${i},this.value)"></label>${cashCanEditPrice()?`<label>Precio ($)<input type="number" min="0" step="0.01" value="${esc(cashUnit(row))}" oninput="cashDraft.items[${i}].unitPrice=this.value;cashUpdateTotals()"></label>`:''}<button class="btn-s" onclick="cashRemoveItem(${i})">Quitar</button></div>`;}).join('')||'<p class="text-muted">Agrega uno o varios servicios y exámenes.</p>';cashUpdateTotals();}
function cashSelectPatient(value){cashDraft.patientId=value;const el=document.getElementById('cash-patient-account');if(el)el.innerHTML=cashAccountHtml(value);}
function cashAccountHtml(patientId){
 if(!patientId)return '<p class="text-muted">Selecciona un paciente para ver sus cuentas y abonos.</p>';
 const invoices=(DB.get('facturas')||[]).filter(f=>String(f.pac)===String(patientId));
 const current=invoices.filter(f=>f.cobroVersion===1&&f.estado!=='Anulado');
 const total=current.reduce((s,f)=>s+Number(f.total||0),0),paid=current.reduce((s,f)=>s+Number(f.abonado||0),0),balance=current.reduce((s,f)=>s+Number(f.saldo||0),0);
 return `<div class="cash-summary"><span>Total de cuentas nuevas <strong>${fmtMoney(total)}</strong></span><span>Pagado <strong>${fmtMoney(paid)}</strong></span><span>Pendiente <strong>${fmtMoney(balance)}</strong></span></div>`+invoices.map(f=>`<article class="cash-account"><div class="flex gap8"><strong>${esc(f.id)}</strong><span>${esc(f.fecha)}</span><span class="badge ${f.saldo>0?'b-amber':'b-green'}">${esc(f.estadoPago||f.estado||'Registro anterior')}</span></div><p>${esc(f.serv||'')}</p>
 ${f.cobroVersion===1?`<ul>${(f.items||[]).map(i=>`<li>${i.cantidad} × ${esc(i.nombre)} — ${fmtMoney(i.total)} antes de IVA</li>`).join('')}</ul><p>Total: <strong>${fmtMoney(f.total)}</strong> · Abonado: <strong>${fmtMoney(f.abonado)}</strong> · Debe: <strong>${fmtMoney(f.saldo)}</strong></p>
 <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fecha del pago</th><th>Forma</th><th>Recibido</th><th>Referencia</th><th>Registrado por</th></tr></thead><tbody>${(f.pagos||[]).map(p=>`<tr><td>${esc(p.fecha.replace('T',' '))}</td><td>${esc(p.metodo)}</td><td>${fmtMoney(p.monto)}</td><td>${esc(p.referencia||'—')}</td><td>${esc(p.registradoPor||'—')}</td></tr>`).join('')||'<tr><td colspan="5">Sin pagos registrados</td></tr>'}</tbody></table></div>
 ${hasPerm('caja')&&f.saldo>0&&f.estado!=='Anulado'?`<button class="btn-g mt12" data-invoice="${esc(f.id)}" onclick="cashOpenAbono(this.dataset.invoice)">Registrar abono</button>`:''}`:`<p>Total histórico: ${fmtMoney(f.total)} · ${esc(f.pago||'Sin método')}</p><p class="text-sm text-muted">Registro anterior; no se ha inferido un saldo ni un desglose de abonos.</p>`}</article>`).join('')||'<p>Sin cuentas registradas.</p>';
}
function renderCaja(){
 if(!hasPerm('caja'))return;
 const boxes=DB.get('cajas')||[],box=boxes.find(c=>c.estado==='abierta');
 if(!box){renderCajaLegacy();return;}
 const movs=(box.movimientos||[]).filter(m=>m.pago!=='Pendiente');
 const sum=filter=>movs.filter(filter).reduce((s,m)=>s+Number(m.monto||0),0);
 const totals=[['Total recibido en esta caja',sum(()=>true)],['Efectivo',sum(m=>m.pago==='Efectivo')],['Tarjeta',sum(m=>String(m.pago).startsWith('Tarjeta'))],['Transferencia',sum(m=>m.pago==='Transferencia')],['Seguros (registros anteriores)',sum(m=>m.pago==='IESS'||m.pago==='Seguro privado')]];
 document.getElementById('caja-content').innerHTML=`<div class="caja-status-bar caja-open"><strong>Caja abierta</strong> · ${esc(box.fecha)} · ${esc(box.cajero||'')}</div>
 ${cashPending()?'<div class="alert alert-w">Hay una operación pendiente de confirmar. <button class="btn-p" onclick="cashRetry()">Reintentar la misma operación</button></div>':''}
 <div class="stats-row">${totals.map(([name,total])=>`<div class="stat-box"><div class="stat-lbl">${name}</div><div class="stat-val">${fmtMoney(total)}</div></div>`).join('')}</div>
 <div class="cash-layout"><section class="card"><div class="card-hdr"><h3 class="card-title">Cobrar servicios y exámenes</h3></div><div class="card-body">
 <label class="field">Paciente<select id="cash-patient" onchange="cashSelectPatient(this.value)"><option value="">Seleccionar paciente...</option>${(DB.get('pacientes')||[]).map(p=>`<option value="${p.id}" ${String(p.id)===String(cashDraft.patientId)?'selected':''}>${esc(p.nombres+' '+p.apellidos)}</option>`).join('')}</select></label>
 <div class="cash-catalog"><label>Servicio o examen<select id="cash-item">${chargeOptionsHtml()}</select></label><button class="btn-p" onclick="cashAddItem()">Agregar concepto</button></div><div id="cash-items" class="mt12"></div>
 <h4 class="mt16 mb8">Pago o adelanto</h4><p class="text-sm text-muted mb8">Puedes combinar efectivo, tarjeta y transferencia. Si no recibe dinero ahora, guarda la cuenta sin agregar pagos.</p><div id="cash-charge-payments"></div><button class="btn-s mt8" onclick="cashAddPayment('charge')">+ Agregar forma de pago</button>
 <div id="cash-summary" class="cash-summary" aria-live="polite"></div><button class="btn-g w100 cash-submit" onclick="cashCharge()">Guardar cobro y saldo</button></div></section>
 <section class="card"><div class="card-hdr"><h3 class="card-title">Cuenta del paciente</h3><button class="btn-s btn-sm" onclick="cashRefresh()">Actualizar</button></div><div class="card-body" id="cash-patient-account">${cashAccountHtml(cashDraft.patientId)}</div></section></div>
 <section class="card mt16"><div class="card-hdr"><h3 class="card-title">Movimientos recibidos</h3><span class="text-muted">Los saldos pendientes no se suman como ingresos</span></div><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fecha / hora</th><th>Paciente</th><th>Concepto</th><th>Recibido</th><th>Forma</th><th>Referencia</th>${currentUser?.rol==='admin'?'<th>Acciones</th>':''}</tr></thead><tbody>${movs.map(m=>`<tr><td>${esc(m.fecha||box.fecha)} ${esc(m.hora||'')}</td><td>${esc(m.pac||'')}</td><td>${esc(m.concepto||'')}</td><td>${fmtMoney(m.monto)}</td><td>${esc(m.pago||'')}</td><td>${esc(m.referencia||'—')}</td>${currentUser?.rol==='admin'?`<td><button class="btn-d btn-sm" onclick="cashDeleteDialog(${boxes.indexOf(box)},${box.movimientos.indexOf(m)})">Eliminar</button></td>`:''}</tr>`).join('')||'<tr><td colspan="6">Sin pagos recibidos</td></tr>'}</tbody></table></div></section>
 ${currentUser?.rol==='admin'?'<div class="mt12 text-r"><button class="btn-d" onclick="cerrarCaja()">Cerrar caja</button></div>':''}`;
 cashRenderItems();cashRenderPayments('charge');
}
function cashModal(id,title,body){
 let el=document.getElementById(id);if(!el){el=document.createElement('div');el.id=id;el.className='modal-bg';document.body.appendChild(el);}
 el.innerHTML=`<section class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}" style="max-width:1000px"><div class="card-hdr"><h3 class="card-title">${esc(title)}</h3><button class="btn-s" onclick="closeM('${id}')">Cerrar</button></div><div class="card-body" style="overflow:auto">${body}</div></section>`;openM(id);
}
function openPatientAccount(id){if(currentUser?.rol==='medico')return;cashHistoryPatient=id;cashModal('m-patient-account','Cuenta de '+getPacName(+id),cashAccountHtml(id));}
function cashOpenAbono(id){
 if(!(DB.get('cajas')||[]).some(c=>c.estado==='abierta')){toast('Abre caja antes de registrar un abono.','err');return;}
 cashAbono={invoiceId:id,payments:[]};const invoice=(DB.get('facturas')||[]).find(f=>f.id===id);if(!invoice)return;
 cashModal('m-cash-abono','Registrar abono · '+getPacName(invoice.pac),`<p>${esc(id)} · ${esc(invoice.serv)}</p><div id="cash-abono-summary" class="cash-summary"></div><div id="cash-abono-payments"></div><button class="btn-s mt8" onclick="cashAddPayment('abono')">+ Agregar forma de pago</button><button class="btn-g w100 mt16 cash-submit" onclick="cashPay()">Guardar abono</button>`);cashAddPayment('abono');
}
async function cashRefresh(){await DB.tail;if(DB.failures.size){toast('Hay cambios sin guardar. Resuelve el error antes de actualizar.','err');return false;}const loaded=await API.get('/api/data');DB.load(loaded.data);renderCaja();if(document.getElementById('m-patient-account')?.classList.contains('open'))openPatientAccount(cashHistoryPatient);return true;}
function cashValidPayments(rows){if(rows.some(p=>!Number.isFinite(Number(p.amount))||Number(p.amount)<=0)){toast('Ingresa un monto mayor a cero para cada pago.','err');return false;}return true;}
async function cashCharge(){
 if(cashPending()){await cashRetry();return;}
 if(!cashDraft.patientId||!cashDraft.items.length){toast('Selecciona paciente y agrega conceptos.','err');return;}
 if(cashDraft.items.some(i=>!Number.isInteger(i.quantity)||i.quantity<1||i.quantity>1000)){toast('Revisa las cantidades.','err');return;}
 if(!cashValidPayments(cashDraft.payments))return;
 const payload={requestId:crypto.randomUUID(),patientId:cashDraft.patientId,items:cashDraft.items.map(i=>{const [kind,id]=i.key.split(':');return {kind,id,quantity:i.quantity,...(i.unitPrice!==undefined?{unitPrice:i.unitPrice}:{})};}),payments:cashDraft.payments,expectedTotal:cashTotals().total};
 await cashSend('/api/cash/charge',payload);
}
async function cashPay(){
 if(cashPending()){await cashRetry();return;}
 const invoice=(DB.get('facturas')||[]).find(f=>f.id===cashAbono.invoiceId);
 if(!invoice||!cashAbono.payments.length||!cashValidPayments(cashAbono.payments))return;
 await cashSend('/api/cash/payment',{requestId:crypto.randomUUID(),invoiceId:invoice.id,expectedBalance:invoice.saldo,payments:cashAbono.payments});
}
async function cashRetry(){const pending=cashPending();if(pending)await cashSend(pending.path,pending.payload);}
async function cashSend(path,payload){
 if(cashBusy)return;cashBusy=true;document.querySelectorAll('.cash-submit').forEach(b=>b.disabled=true);
 try{
  await DB.tail;if(DB.failures.size)throw new Error('Hay cambios sin guardar. Resuelve esos errores antes de cobrar.');
  sessionStorage.setItem('mg_cash_pending',JSON.stringify({path,payload}));
  const response=await fetch(API.base+path,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+API.token},body:JSON.stringify(payload)});
  const result=await response.json();
  if(!response.ok){if(response.status<500)sessionStorage.removeItem('mg_cash_pending');throw new Error(result.error||'No se pudo guardar.');}
  sessionStorage.removeItem('mg_cash_pending');
  cashDraft={patientId:String(result.invoice.pac),items:[],payments:[]};if(document.getElementById('m-cash-abono'))closeM('m-cash-abono');
  toast(`Guardado. Abonado: ${fmtMoney(result.invoice.abonado)} · Saldo: ${fmtMoney(result.invoice.saldo)}`,'ok');
  try{await cashRefresh();}catch{toast('El pago quedó guardado. Recarga la página para actualizar los datos.','inf');}
 }catch(err){toast(err.message+(cashPending()?' Reintenta la misma operación para confirmar sin duplicar el cobro.':''),'err');}
 finally{cashBusy=false;document.querySelectorAll('.cash-submit').forEach(b=>b.disabled=false);}
}
function openCobroModal(){showMod('caja',document.querySelector('[data-module=caja]'));document.getElementById('cash-patient')?.focus();}
function procesarCobroInline(){return cashCharge();}
function procesarCobro(){return cashCharge();}
let cashDeleteTarget=null;
function cashDeleteDialog(boxIndex,index){
 if(currentUser?.rol!=='admin')return;
 const box=(DB.get('cajas')||[])[boxIndex],movement=box?.movimientos?.[index];if(!movement)return;
 cashDeleteTarget={boxId:box.id,index,base:JSON.parse(JSON.stringify(movement))};
 cashModal('m-cash-delete','Eliminar movimiento recibido',`<p><strong>${esc(movement.pac||'Sin paciente')}</strong> · ${fmtMoney(movement.monto)} · ${esc(movement.pago)}</p><p>${esc(movement.concepto||'')}</p><p>Se quitará de los ingresos de caja.${movement.factura?' El importe volverá al saldo pendiente de la cuenta vinculada.':''} El motivo y el registro original quedarán en auditoría.</p><label class="field">Motivo<input id="cash-delete-reason" maxlength="500" placeholder="Ejemplo: registro de prueba" /></label><button class="btn-d mt12" onclick="cashDeleteMovement(this)">Eliminar movimiento</button>`);
}
async function cashDeleteMovement(button){
 if(!cashDeleteTarget||cashBusy)return;
 const reason=document.getElementById('cash-delete-reason').value.trim();if(reason.length<5){toast('Indica el motivo de eliminación.','err');return;}
 cashBusy=true;button.disabled=true;
 try{await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de eliminar.');await API.post('/api/cash/delete-movement',{...cashDeleteTarget,reason});closeM('m-cash-delete');cashDeleteTarget=null;await cashRefresh();toast('Movimiento eliminado; caja y saldo actualizados.','ok');}
 catch(e){toast(e.message,'err');}finally{cashBusy=false;button.disabled=false;}
}
