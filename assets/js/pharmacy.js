/* Farmacia: inventory by lot, kardex, electronic prescription (MSP) and dispensing charged in Caja.
   All writes go through /api/pharmacy; the server validates stock, FEFO and the cash account in one transaction. */
const PH_FORMS=['Tableta','Cápsula','Jarabe','Suspensión','Solución oral','Gotas','Inyectable','Crema','Ungüento','Gel','Óvulo','Supositorio','Inhalador','Polvo','Parche','Solución oftálmica','Insumo','Otro'];
const PH_CATEGORIES=['Medicamento','Insumo médico','Dispositivo médico','Suplemento','Otro'];
const PH_ADJUST=['Conteo físico','Corrección de ingreso','Devolución de paciente','Otro'];
const PH_WRITE_OFF=['Caducado','Dañado / roto','Retiro sanitario (ARCSA)','Pérdida','Otro'];
const PH_SOON_DAYS=90;
let phTab='dispensar',phQueue=[],phDraft=null,phBusy=false,phFilter='',phKardexProduct='';

function phProducts(){return DB.get('farmaciaProductos')||[];}
function phLots(){return DB.get('farmaciaLotes')||[];}
function phProduct(id){return phProducts().find(p=>String(p.id)===String(id));}
function phDaysTo(date){return Math.round((new Date(date+'T00:00:00')-new Date(today()+'T00:00:00'))/86400000);}
function phStock(id,usable=true){return phLots().filter(l=>String(l.productoId)===String(id)&&(!usable||l.caducidad>=today())).reduce((s,l)=>s+Number(l.cantidad||0),0);}
function phNextExpiry(id){const l=phLots().filter(x=>String(x.productoId)===String(id)&&Number(x.cantidad)>0&&x.caducidad>=today()).sort((a,b)=>a.caducidad.localeCompare(b.caducidad))[0];return l?l.caducidad:'';}
function phName(p){return [p.nombre,p.concentracion,p.forma].filter(Boolean).join(' ');}
function phCanManage(){return currentUser?.rol==='admin'||hasPerm('farmacia');}
function phApply(res){
  ['farmaciaProductos','farmaciaLotes'].forEach(k=>{if(res[k]){DB.cache[k]=res[k];DB.confirmed[k]=JSON.parse(JSON.stringify(res[k]));}});
}
async function phPost(payload){
  if(phBusy)return null;phBusy=true;
  try{await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de continuar.');const res=await API.post('/api/pharmacy',payload);phApply(res);return res;}
  catch(e){toast(e.message,'err');return null;}finally{phBusy=false;}
}
async function phReload(keys){
  const res=await API.get('/api/data?keys='+keys.join(','));
  keys.forEach(k=>{if(k in res.data){DB.cache[k]=res.data[k];DB.confirmed[k]=JSON.parse(JSON.stringify(res.data[k]));}});
}
function phModal(id,title,body,width=860){
  let el=document.getElementById(id);if(!el){el=document.createElement('div');el.id=id;el.className='modal-bg';document.body.appendChild(el);}
  el.innerHTML=`<section class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}" style="max-width:${width}px"><div class="card-hdr"><h3 class="card-title">${esc(title)}</h3><button class="btn-s" onclick="closeM('${id}')">Cerrar</button></div><div class="card-body" style="overflow:auto;max-height:80vh">${body}</div></section>`;openM(id);
}
function phAlerts(){
  const products=phProducts().filter(p=>p.estado!=='inactivo');
  const low=products.filter(p=>Number(p.stockMinimo)>0&&phStock(p.id)<=Number(p.stockMinimo));
  const lots=phLots().filter(l=>Number(l.cantidad)>0);
  const expired=lots.filter(l=>l.caducidad<today());
  const soon=lots.filter(l=>l.caducidad>=today()&&phDaysTo(l.caducidad)<=PH_SOON_DAYS);
  return {low,expired,soon};
}

/* ------------------------------------------------------------------ module */
function renderFarmacia(){
  const host=document.getElementById('farmacia-content');if(!host)return;
  if(!phCanManage()){host.innerHTML='<div class="alert alert-w">No tienes permiso para farmacia.</div>';return;}
  const a=phAlerts();
  const tabs=[['dispensar','Dispensar / vender'],['recetas','Recetas por dispensar'+(phQueue.length?` (${phQueue.length})`:'')],['inventario','Inventario'],['alertas','Alertas'+((a.low.length+a.expired.length+a.soon.length)?` (${a.low.length+a.expired.length+a.soon.length})`:'')],['kardex','Kardex']];
  host.innerHTML=`<div class="stats-row ph-stats">
    <div class="stat-box"><div class="stat-lbl">Productos activos</div><div class="stat-val">${phProducts().filter(p=>p.estado!=='inactivo').length}</div></div>
    <div class="stat-box"><div class="stat-lbl">Recetas pendientes</div><div class="stat-val">${phQueue.length}</div></div>
    <div class="stat-box"><div class="stat-lbl">Bajo stock mínimo</div><div class="stat-val" style="color:${a.low.length?'var(--red)':'inherit'}">${a.low.length}</div></div>
    <div class="stat-box"><div class="stat-lbl">Lotes por caducar (${PH_SOON_DAYS} días)</div><div class="stat-val" style="color:${a.soon.length?'var(--amber,#b45309)':'inherit'}">${a.soon.length}</div></div>
    <div class="stat-box"><div class="stat-lbl">Lotes caducados con stock</div><div class="stat-val" style="color:${a.expired.length?'var(--red)':'inherit'}">${a.expired.length}</div></div>
  </div>
  <div class="tabs">${tabs.map(([id,l])=>`<div class="tab ${phTab===id?'active':''}" onclick="phTab='${id}';renderFarmacia()">${esc(l)}</div>`).join('')}</div>
  <div id="ph-body" class="mt12"></div>`;
  const body=document.getElementById('ph-body');
  if(phTab==='dispensar')phRenderDispense(body);
  else if(phTab==='recetas')phRenderQueue(body);
  else if(phTab==='inventario')phRenderInventory(body);
  else if(phTab==='alertas')phRenderAlerts(body,a);
  else phRenderKardex(body);
}
async function phLoadQueue(){try{phQueue=(await API.get('/api/pharmacy/queue')).queue||[];}catch(e){phQueue=[];}}
async function openFarmacia(){renderFarmacia();await phLoadQueue();renderFarmacia();}

/* --------------------------------------------------------------- inventory */
function phRenderInventory(body){
  const q=ppNorm(phFilter);
  const rows=phProducts().filter(p=>!q||ppNorm(`${p.nombre} ${p.comercial} ${p.codigo} ${p.registroSanitario}`).includes(q));
  body.innerHTML=`<div class="flex gap8 mb12" style="flex-wrap:wrap;align-items:center"><div class="si" style="flex:1;min-width:220px"><i class="ti ti-search"></i><input id="ph-filter" placeholder="Buscar por nombre, comercial, código o registro sanitario" value="${esc(phFilter)}" oninput="phFilter=this.value;phRenderInventory(document.getElementById('ph-body'));document.getElementById('ph-filter').focus();document.getElementById('ph-filter').setSelectionRange(this.value.length,this.value.length)"></div><button class="btn-p" onclick="phProductForm()"><i class="ti ti-plus"></i> Nuevo producto</button><button class="btn-g" onclick="phReceiveForm()"><i class="ti ti-truck-delivery"></i> Ingresar lote / compra</button></div>
  <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Código</th><th>Producto</th><th>Presentación</th><th>Reg. sanitario</th><th>Stock vigente</th><th>Mínimo</th><th>Próx. caducidad</th><th>P. venta</th><th>IVA</th><th></th></tr></thead><tbody>${rows.map(p=>{const s=phStock(p.id),exp=phNextExpiry(p.id),low=Number(p.stockMinimo)>0&&s<=Number(p.stockMinimo);return `<tr class="${p.estado==='inactivo'?'text-muted':''}"><td>${esc(p.codigo||'')}</td><td><strong>${esc(phName(p))}</strong>${p.comercial?`<div class="text-xs text-muted">${esc(p.comercial)}</div>`:''}${p.controlado?' <span class="badge b-red">Control especial</span>':''}${p.estado==='inactivo'?' <span class="badge">Inactivo</span>':''}</td><td class="text-sm">${esc(p.presentacion||'—')}</td><td class="text-sm">${esc(p.registroSanitario||'—')}</td><td><span class="badge ${s===0?'b-red':low?'b-amber':'b-green'}">${s}</span></td><td>${esc(p.stockMinimo||0)}</td><td>${exp?`${fmtDate(exp)}${phDaysTo(exp)<=PH_SOON_DAYS?` <span class="badge b-amber">${phDaysTo(exp)} d</span>`:''}`:'—'}</td><td>${fmtMoney(p.precioVenta)}</td><td>${esc(p.ivaTarifa||0)}%</td><td class="ph-actions"><button class="btn-s btn-xs" onclick="phProductForm(${p.id})">Editar</button> <button class="btn-s btn-xs" onclick="phLotsModal(${p.id})">Lotes</button> <button class="btn-s btn-xs" onclick="phKardexProduct='${p.id}';phTab='kardex';renderFarmacia()">Kardex</button></td></tr>`;}).join('')||'<tr><td colspan="10" class="text-muted">Sin productos. Registra el primero con "Nuevo producto".</td></tr>'}</tbody></table></div>`;
}
function phProductForm(id){
  const p=id?phProduct(id):{forma:'Tableta',categoria:'Medicamento',ivaTarifa:0,stockMinimo:5,estado:'activo'};
  const opt=(list,v)=>list.map(x=>`<option ${x===v?'selected':''}>${esc(x)}</option>`).join('');
  phModal('m-ph-product',id?'Editar producto':'Nuevo producto',`<div class="form-row"><label class="field" style="flex:2">Nombre genérico (DCI)<input id="ph-p-nombre" maxlength="160" value="${esc(p.nombre||'')}" placeholder="Paracetamol"></label><label class="field" style="flex:2">Nombre comercial<input id="ph-p-comercial" maxlength="160" value="${esc(p.comercial||'')}"></label><label class="field">Código<input id="ph-p-codigo" maxlength="40" value="${esc(p.codigo||'')}" placeholder="Automático"></label></div>
  <div class="form-row"><label class="field">Concentración<input id="ph-p-conc" maxlength="60" value="${esc(p.concentracion||'')}" placeholder="500 mg"></label><label class="field">Forma farmacéutica<select id="ph-p-forma">${opt(PH_FORMS,p.forma)}</select></label><label class="field">Vía<input id="ph-p-via" maxlength="40" value="${esc(p.via||'')}" placeholder="Oral"></label></div>
  <div class="form-row"><label class="field" style="flex:2">Presentación<input id="ph-p-pres" maxlength="120" value="${esc(p.presentacion||'')}" placeholder="Caja x 20 tabletas"></label><label class="field">Registro sanitario ARCSA<input id="ph-p-reg" maxlength="60" value="${esc(p.registroSanitario||'')}"></label><label class="field">Categoría<select id="ph-p-cat" onchange="document.getElementById('ph-p-iva').value=this.value==='Medicamento'?'0':'15'">${opt(PH_CATEGORIES,p.categoria)}</select></label></div>
  <div class="form-row"><label class="field">Precio de venta por unidad ($)<input id="ph-p-precio" type="number" min="0" step="0.01" value="${esc(p.precioVenta??'')}"></label><label class="field">IVA<select id="ph-p-iva"><option value="0" ${+p.ivaTarifa===0?'selected':''}>0% (medicamentos)</option><option value="15" ${+p.ivaTarifa===15?'selected':''}>15%</option></select></label><label class="field">Stock mínimo (unidades)<input id="ph-p-min" type="number" min="0" step="1" value="${esc(p.stockMinimo??0)}"></label><label class="field">Estado<select id="ph-p-estado"><option value="activo">Activo</option><option value="inactivo" ${p.estado==='inactivo'?'selected':''}>Inactivo</option></select></label></div>
  <label class="flex gap8" style="align-items:center"><input type="checkbox" id="ph-p-ctrl" ${p.controlado?'checked':''}> Medicamento de control especial (psicotrópico / estupefaciente): solo se dispensa con receta</label>
  <p class="text-xs text-muted mt8">El stock se controla por unidad mínima de dispensación (tableta, frasco, ampolla…). Los medicamentos tienen IVA 0% en Ecuador; insumos y otros bienes, 15%.</p>
  <button class="btn-p mt8" onclick="phProductSave(${id||0})">Guardar producto</button>`);
}
async function phProductSave(id){
  const v=x=>document.getElementById(x).value;
  const res=await phPost({action:'product_save',id:id||undefined,nombre:v('ph-p-nombre'),comercial:v('ph-p-comercial'),codigo:v('ph-p-codigo'),concentracion:v('ph-p-conc'),forma:v('ph-p-forma'),via:v('ph-p-via'),presentacion:v('ph-p-pres'),registroSanitario:v('ph-p-reg'),categoria:v('ph-p-cat'),precioVenta:v('ph-p-precio'),ivaTarifa:+v('ph-p-iva'),stockMinimo:v('ph-p-min'),estado:v('ph-p-estado'),controlado:document.getElementById('ph-p-ctrl').checked});
  if(res){closeM('m-ph-product');toast('Producto guardado','ok');renderFarmacia();}
}
function phProductOptions(selected){return phProducts().filter(p=>p.estado!=='inactivo').map(p=>`<option value="${p.id}" ${String(p.id)===String(selected)?'selected':''}>${esc(phName(p))}${p.comercial?' ('+esc(p.comercial)+')':''} · stock ${phStock(p.id)}</option>`).join('');}
function phReceiveForm(productId){
  if(!phProducts().length){toast('Primero registra el producto','err');return;}
  phModal('m-ph-receive','Ingreso de lote / compra',`<label class="field">Producto<select id="ph-r-prod">${phProductOptions(productId)}</select></label>
  <div class="form-row"><label class="field">Número de lote<input id="ph-r-lote" maxlength="60"></label><label class="field">Fecha de caducidad<input id="ph-r-cad" type="date" min="${today()}"></label><label class="field">Cantidad (unidades)<input id="ph-r-cant" type="number" min="1" step="1"></label></div>
  <div class="form-row"><label class="field">Costo unitario ($)<input id="ph-r-costo" type="number" min="0" step="0.0001"></label><label class="field" style="flex:2">Proveedor<input id="ph-r-prov" maxlength="160"></label><label class="field">N.º factura de compra<input id="ph-r-doc" maxlength="60"></label></div>
  <button class="btn-g mt8" onclick="phReceiveSave()"><i class="ti ti-check"></i> Registrar ingreso</button>`,760);
}
async function phReceiveSave(){
  const v=x=>document.getElementById(x).value;
  const res=await phPost({action:'lot_receive',productId:v('ph-r-prod'),lote:v('ph-r-lote'),caducidad:v('ph-r-cad'),cantidad:v('ph-r-cant'),costoUnitario:v('ph-r-costo')||0,proveedor:v('ph-r-prov'),documento:v('ph-r-doc')});
  if(res){closeM('m-ph-receive');toast('Ingreso registrado en kardex','ok');renderFarmacia();}
}
function phLotsModal(productId){
  const p=phProduct(productId);if(!p)return;
  const lots=phLots().filter(l=>String(l.productoId)===String(productId)).sort((a,b)=>a.caducidad.localeCompare(b.caducidad));
  phModal('m-ph-lots','Lotes de '+phName(p),`<div class="mb12"><button class="btn-g btn-sm" onclick="closeM('m-ph-lots');phReceiveForm(${p.id})">+ Ingresar lote</button></div><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Lote</th><th>Caducidad</th><th>Existencia</th><th>Costo</th><th>Proveedor / documento</th><th></th></tr></thead><tbody>${lots.map(l=>{const d=phDaysTo(l.caducidad);return `<tr><td>${esc(l.lote)}</td><td>${fmtDate(l.caducidad)} ${d<0?'<span class="badge b-red">Caducado</span>':d<=PH_SOON_DAYS?`<span class="badge b-amber">${d} días</span>`:''}</td><td>${esc(l.cantidad)}</td><td>${fmtMoney(l.costoUnitario||0)}</td><td class="text-sm">${esc(l.proveedor||'—')} ${l.documento?'· '+esc(l.documento):''}</td><td>${Number(l.cantidad)>0||true?`<button class="btn-s btn-xs" onclick="phAdjustForm('${esc(l.id)}',false)">Ajustar</button> ${Number(l.cantidad)>0?`<button class="btn-d btn-xs" onclick="phAdjustForm('${esc(l.id)}',true)">Dar de baja</button>`:''}`:''}</td></tr>`;}).join('')||'<tr><td colspan="6" class="text-muted">Sin lotes.</td></tr>'}</tbody></table></div>`);
}
function phAdjustForm(lotId,writeOff){
  const l=phLots().find(x=>x.id===lotId);if(!l)return;const p=phProduct(l.productoId);
  phModal('m-ph-adjust',writeOff?'Dar de baja unidades':'Ajuste de inventario',`<p><strong>${esc(phName(p||{}))}</strong> · Lote ${esc(l.lote)} · existencia ${esc(l.cantidad)}</p>
  <div class="form-row"><label class="field">${writeOff?'Unidades a dar de baja':'Diferencia (+ suma, − resta)'}<input id="ph-a-cant" type="number" step="1" ${writeOff?`min="1" max="${l.cantidad}" value="${l.caducidad<today()?l.cantidad:''}"`:''}></label><label class="field">Motivo<select id="ph-a-motivo">${(writeOff?PH_WRITE_OFF:PH_ADJUST).map(x=>`<option ${writeOff&&x==='Caducado'&&l.caducidad<today()?'selected':''}>${x}</option>`).join('')}</select></label></div>
  <label class="field">Observación<input id="ph-a-obs" maxlength="500"></label>
  <button class="${writeOff?'btn-d':'btn-p'} mt8" onclick="phAdjustSave('${esc(lotId)}',${writeOff})">${writeOff?'Registrar baja':'Registrar ajuste'}</button>`,620);
}
async function phAdjustSave(lotId,writeOff){
  const res=await phPost({action:writeOff?'lot_write_off':'lot_adjust',lotId,cantidad:document.getElementById('ph-a-cant').value,motivo:document.getElementById('ph-a-motivo').value,observacion:document.getElementById('ph-a-obs').value});
  if(res){closeM('m-ph-adjust');closeM('m-ph-lots');toast(writeOff?'Baja registrada':'Ajuste registrado','ok');renderFarmacia();}
}
function phRenderAlerts(body,a){
  const row=(l,extra)=>{const p=phProduct(l.productoId)||{};return `<tr><td>${esc(phName(p))}</td><td>${esc(l.lote)}</td><td>${fmtDate(l.caducidad)}</td><td>${esc(l.cantidad)}</td><td>${extra}</td></tr>`;};
  body.innerHTML=`<section class="card mb12"><div class="card-hdr"><h3 class="card-title">Caducados con existencia (${a.expired.length})</h3></div><div class="card-body"><p class="text-sm text-muted">No se dispensan. Regístralos como baja para retirarlos del inventario.</p><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Producto</th><th>Lote</th><th>Caducó</th><th>Unidades</th><th></th></tr></thead><tbody>${a.expired.map(l=>row(l,`<button class="btn-d btn-xs" onclick="phAdjustForm('${esc(l.id)}',true)">Dar de baja</button>`)).join('')||'<tr><td colspan="5" class="text-muted">Ninguno.</td></tr>'}</tbody></table></div></div></section>
  <section class="card mb12"><div class="card-hdr"><h3 class="card-title">Por caducar en ${PH_SOON_DAYS} días (${a.soon.length})</h3></div><div class="card-body"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Producto</th><th>Lote</th><th>Caduca</th><th>Unidades</th><th>Días</th></tr></thead><tbody>${a.soon.sort((x,y)=>x.caducidad.localeCompare(y.caducidad)).map(l=>row(l,`<span class="badge b-amber">${phDaysTo(l.caducidad)}</span>`)).join('')||'<tr><td colspan="5" class="text-muted">Ninguno.</td></tr>'}</tbody></table></div></div></section>
  <section class="card"><div class="card-hdr"><h3 class="card-title">Bajo stock mínimo (${a.low.length})</h3></div><div class="card-body"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Producto</th><th>Stock vigente</th><th>Mínimo</th><th></th></tr></thead><tbody>${a.low.map(p=>`<tr><td>${esc(phName(p))}</td><td>${phStock(p.id)}</td><td>${esc(p.stockMinimo)}</td><td><button class="btn-g btn-xs" onclick="phReceiveForm(${p.id})">Ingresar lote</button></td></tr>`).join('')||'<tr><td colspan="4" class="text-muted">Ninguno.</td></tr>'}</tbody></table></div></div></section>`;
}
async function phRenderKardex(body){
  body.innerHTML=`<div class="flex gap8 mb12" style="flex-wrap:wrap;align-items:flex-end"><label class="field" style="flex:1;min-width:260px">Producto<select id="ph-k-prod" onchange="phKardexProduct=this.value;phRenderKardex(document.getElementById('ph-body'))"><option value="">Todos los movimientos recientes</option>${phProducts().map(p=>`<option value="${p.id}" ${String(p.id)===String(phKardexProduct)?'selected':''}>${esc(phName(p))}</option>`).join('')}</select></label><button class="btn-s" onclick="phKardexCsv()"><i class="ti ti-download"></i> Exportar CSV</button></div><div id="ph-k-table" class="text-muted">Cargando kardex…</div>`;
  try{
    const res=await API.get('/api/pharmacy/kardex?limit=500'+(phKardexProduct?'&productId='+encodeURIComponent(phKardexProduct):''));
    window.phKardexRows=res.moves||[];
    document.getElementById('ph-k-table').innerHTML=`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Fecha</th><th>Producto</th><th>Movimiento</th><th>Lote</th><th>Cantidad</th><th>Saldo</th><th>Referencia</th><th>Paciente</th><th>Usuario</th></tr></thead><tbody>${phKardexRows.map(m=>`<tr><td>${esc(String(m.ts).replace('T',' ').slice(0,16))}</td><td>${esc(phName(phProduct(m.product_id)||{nombre:'#'+m.product_id}))}</td><td>${esc(m.kind)}</td><td>${esc(m.lot||'—')}</td><td style="color:${m.qty<0?'var(--red)':'var(--green)'}">${m.qty>0?'+':''}${esc(m.qty)}</td><td>${esc(m.balance)}</td><td class="text-sm">${esc(m.ref||'')}</td><td class="text-sm">${m.patient_id?esc(getPacName(m.patient_id)):''}</td><td class="text-sm">${esc(m.user_name||'')}</td></tr>`).join('')||'<tr><td colspan="9" class="text-muted">Sin movimientos.</td></tr>'}</tbody></table></div>`;
  }catch(e){document.getElementById('ph-k-table').textContent=e.message;}
}
function phKardexCsv(){
  const rows=window.phKardexRows||[];const q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
  const csv=['Fecha,Producto,Movimiento,Lote,Cantidad,Saldo,Referencia,Paciente,Usuario',...rows.map(m=>[m.ts,phName(phProduct(m.product_id)||{nombre:m.product_id}),m.kind,m.lot,m.qty,m.balance,m.ref,m.patient_id?getPacName(m.patient_id):'',m.user_name].map(q).join(','))].join('\n');
  const url=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='kardex-farmacia-'+today()+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

/* ------------------------------------------------------- prescriptions queue */
function phRenderQueue(body){
  body.innerHTML=`<div class="flex gap8 mb12"><button class="btn-s btn-sm" onclick="openFarmacia()"><i class="ti ti-refresh"></i> Actualizar</button></div><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Receta</th><th>Fecha</th><th>Paciente</th><th>Médico</th><th>Medicamentos</th><th>Estado</th><th></th></tr></thead><tbody>${phQueue.map((r,i)=>`<tr><td>${esc(r.numero)}</td><td>${fmtDate(r.fecha)}${r.vencida?' <span class="badge b-red">Vencida</span>':''}</td><td>${esc(r.paciente?.nombre||'')}<div class="text-xs text-muted">${esc(r.paciente?.cedula||'')}</div></td><td class="text-sm">${esc(r.medico||'')}</td><td class="text-sm">${(r.items||[]).map((it,j)=>`${esc(it.nombre)} ${esc(it.concentracion||'')} · ${(r.dispensacion?.lineas?.[j]?.dispensado||0)}/${it.cantidad}${it.productoId?'':' <span class="badge">Fuera de inventario</span>'}`).join('<br>')}</td><td><span class="badge ${r.dispensacion?.estado==='Parcial'?'b-blue':'b-amber'}">${esc(r.dispensacion?.estado||'Pendiente')}</span></td><td>${r.vencida?'':`<button class="btn-g btn-xs" onclick="phLoadRx(${i})">Dispensar</button>`}</td></tr>`).join('')||'<tr><td colspan="7" class="text-muted">No hay recetas electrónicas pendientes.</td></tr>'}</tbody></table></div>`;
}
function phLoadRx(index){
  const r=phQueue[index];if(!r)return;
  phDraft={requestId:crypto.randomUUID(),patientId:r.patientId,rx:r,lines:[],payments:[]};
  (r.items||[]).forEach((it,j)=>{const pending=it.cantidad-(r.dispensacion?.lineas?.[j]?.dispensado||0);if(pending>0&&it.productoId)phDraft.lines.push({productId:String(it.productoId),cantidad:Math.min(pending,phStock(it.productoId)||pending),rxIndex:j});});
  phTab='dispensar';renderFarmacia();
}

/* -------------------------------------------------------------- dispensing */
function phNewDraft(){phDraft={requestId:crypto.randomUUID(),patientId:'',rx:null,lines:[],payments:[]};}
function phLineTotals(){
  let sub0=0,sub15=0,iva=0,units=0;
  phDraft.lines.forEach(l=>{const p=phProduct(l.productId);if(!p)return;const unit=Math.round(Number(l.precio??p.precioVenta)*100);const base=unit*(Number(l.cantidad)||0);units+=Number(l.cantidad)||0;if(+p.ivaTarifa===15){sub15+=base;iva+=Math.round(base*0.15);}else sub0+=base;});
  return {sub0:sub0/100,sub15:sub15/100,iva:iva/100,total:(sub0+sub15+iva)/100,units,count:phDraft.lines.length};
}
function phRenderDispense(body){
  if(!phDraft)phNewDraft();
  const rx=phDraft.rx;
  const patientRx=phQueue.filter(r=>String(r.patientId)===String(phDraft.patientId));
  body.innerHTML=`<div class="cash-layout"><section class="card"><div class="card-hdr"><h3 class="card-title">${rx?'Dispensar receta '+esc(rx.numero):'Dispensar o vender'}</h3>${rx||phDraft.lines.length?'<button class="btn-s btn-sm" onclick="phNewDraft();renderFarmacia()">Nueva operación</button>':''}</div><div class="card-body">
   <label class="field">Paciente<select id="ph-patient" onchange="phDraft.patientId=this.value;if(phDraft.rx&&String(phDraft.rx.patientId)!==this.value){phDraft.rx=null;phDraft.lines=[];}renderFarmacia()"><option value="">Seleccionar paciente</option>${ppPatients().map(p=>`<option value="${p.id}" ${String(p.id)===String(phDraft.patientId)?'selected':''}>${esc(ppLabel(p))}</option>`).join('')}</select></label>
   ${!rx&&patientRx.length?`<div class="alert alert-i mt8"><i class="ti ti-prescription"></i><span>Este paciente tiene ${patientRx.length} receta(s) electrónica(s) pendiente(s). ${patientRx.map(r=>`<button class="btn-g btn-xs" onclick="phLoadRx(${phQueue.indexOf(r)})">${esc(r.numero)}</button>`).join(' ')}</span></div>`:''}
   ${rx?`<div class="box-soft mt8 text-sm"><strong>${esc(rx.medico||'')}</strong> · ${fmtDate(rx.fecha)} · Dx: ${esc(rx.diagnostico||'')} ${rx.cie10?'('+esc(rx.cie10)+')':''}<br>${(rx.items||[]).map((it,j)=>`• ${esc(it.nombre)} ${esc(it.concentracion||'')} ${esc(it.forma||'')} — ${esc(it.posologia||'')} · recetado ${it.cantidad}, entregado ${rx.dispensacion?.lineas?.[j]?.dispensado||0}${it.productoId?'':' <span class="badge">fuera de inventario</span>'}`).join('<br>')}</div>`:''}
   <div class="cash-catalog mt12"><label style="flex:1">Producto<input id="ph-add-q" list="ph-add-list" placeholder="Escribe el nombre, comercial o código…" autocomplete="off"><datalist id="ph-add-list">${phProducts().filter(p=>p.estado!=='inactivo').map(p=>`<option value="${esc(p.codigo)} · ${esc(phName(p))}${p.comercial?' ('+esc(p.comercial)+')':''}">Stock ${phStock(p.id)} · ${fmtMoney(p.precioVenta)}</option>`).join('')}</datalist></label><label style="max-width:110px">Cantidad<input id="ph-add-n" type="number" min="1" step="1" value="1"></label><button class="btn-p" onclick="phAddLine()">Agregar</button></div>
   <div id="ph-lines" class="mt12"></div>
   <h4 class="mt16 mb8">Pago</h4><p class="text-sm text-muted mb8">Cobra ahora (efectivo, tarjeta o transferencia) o deja la cuenta pendiente: aparecerá en Caja en la cuenta del paciente.</p><div id="ph-payments"></div><button class="btn-s mt8" onclick="phDraft.payments.push({method:'Efectivo',amount:'',reference:''});phRenderLines()">+ Agregar forma de pago</button>
   <div id="ph-summary" class="cash-summary" aria-live="polite"></div>
   ${rx?`<label class="flex gap8 mt8" style="align-items:center"><input type="checkbox" id="ph-close-rx"> Cerrar la receta aunque queden unidades sin entregar</label>`:''}
   <button class="btn-g w100 cash-submit" onclick="phDispense()"><i class="ti ti-pill"></i> ${rx?'Dispensar receta y registrar cuenta':'Registrar venta y cuenta'}</button></div></section>
   <section class="card"><div class="card-hdr"><h3 class="card-title">Recetas pendientes</h3></div><div class="card-body">${phQueue.slice(0,12).map((r,i)=>`<div class="ph-queue-item"><div><strong>${esc(r.paciente?.nombre||'')}</strong> · ${esc(r.numero)}<div class="text-xs text-muted">${fmtDate(r.fecha)} · ${esc(r.medico||'')} · ${(r.items||[]).length} medicamento(s)${r.vencida?' · <span style="color:var(--red)">vencida</span>':''}</div></div>${r.vencida?'':`<button class="btn-g btn-xs" onclick="phLoadRx(${i})">Dispensar</button>`}</div>`).join('')||'<p class="text-muted">Sin recetas pendientes.</p>'}</div></section></div>`;
  patientPicker('ph-patient',{onSelect:()=>{}});
  phRenderLines();
  document.getElementById('ph-add-q')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();phAddLine();}});
}
function phAddLine(){
  const q=document.getElementById('ph-add-q').value.trim();if(!q)return;
  const code=q.split(' · ')[0];
  let p=phProducts().find(x=>x.codigo===code&&x.estado!=='inactivo');
  if(!p){const m=phProducts().filter(x=>x.estado!=='inactivo'&&ppNorm(`${x.nombre} ${x.comercial} ${x.codigo}`).includes(ppNorm(q)));if(m.length===1)p=m[0];else{toast(m.length?'Hay varias coincidencias: elige una de la lista':'Producto no encontrado','err');return;}}
  const n=Math.max(1,parseInt(document.getElementById('ph-add-n').value||'1',10));
  const existing=phDraft.lines.find(l=>String(l.productId)===String(p.id)&&l.rxIndex==null);
  if(existing)existing.cantidad+=n;else{
    const rxIndex=phDraft.rx?(phDraft.rx.items||[]).findIndex(it=>String(it.productoId)===String(p.id)):-1;
    phDraft.lines.push({productId:String(p.id),cantidad:n,rxIndex:rxIndex>=0&&!phDraft.lines.some(l=>l.rxIndex===rxIndex)?rxIndex:null});
  }
  document.getElementById('ph-add-q').value='';document.getElementById('ph-add-n').value='1';phRenderLines();document.getElementById('ph-add-q').focus();
}
function phRenderLines(){
  const host=document.getElementById('ph-lines');if(!host)return;
  host.innerHTML=phDraft.lines.length?`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Producto</th><th>Stock</th><th>Cant.</th><th>P. unit.</th><th>IVA</th><th>Subtotal</th><th></th></tr></thead><tbody>${phDraft.lines.map((l,i)=>{const p=phProduct(l.productId)||{};const s=phStock(l.productId);const unit=Number(l.precio??p.precioVenta);return `<tr><td><strong>${esc(phName(p))}</strong>${l.rxIndex!=null?' <span class="badge b-blue">Receta</span>':''}${p.controlado?' <span class="badge b-red">Control</span>':''}</td><td><span class="badge ${s>=l.cantidad?'b-green':'b-red'}">${s}</span></td><td><input type="number" min="1" step="1" style="width:80px" value="${l.cantidad}" oninput="phDraft.lines[${i}].cantidad=Math.max(1,parseInt(this.value||'1',10));phSummary()" aria-label="Cantidad ${i+1}"></td><td>${cashCanEditPrice()?`<input type="number" min="0" step="0.01" style="width:90px" value="${esc(unit)}" oninput="phDraft.lines[${i}].precio=this.value;phSummary()" aria-label="Precio ${i+1}">`:fmtMoney(unit)}</td><td>${esc(p.ivaTarifa||0)}%</td><td id="ph-line-${i}">${fmtMoney(unit*l.cantidad)}</td><td><button class="btn-s" onclick="phDraft.lines.splice(${i},1);phRenderLines()" aria-label="Quitar">×</button></td></tr>`;}).join('')}</tbody></table></div>`:'<p class="text-muted">Agrega productos escribiendo su nombre.</p>';
  const pay=document.getElementById('ph-payments');
  if(pay)pay.innerHTML=phDraft.payments.map((p,i)=>`<div class="cash-payment-row"><label>Forma de pago<select onchange="phDraft.payments[${i}].method=this.value;phSummary()">${cashMethods.map(m=>`<option ${p.method===m?'selected':''}>${m}</option>`).join('')}</select></label><label>Monto ($)<input type="number" min="0.01" step="0.01" value="${esc(p.amount)}" oninput="phDraft.payments[${i}].amount=this.value;phSummary()"></label><label>Referencia<input maxlength="120" value="${esc(p.reference)}" oninput="phDraft.payments[${i}].reference=this.value"></label><button class="btn-s" onclick="phDraft.payments.splice(${i},1);phRenderLines()">Quitar</button></div>`).join('')||'<p class="text-muted text-sm">Sin pago: la cuenta quedará pendiente en Caja.</p>';
  phSummary();
}
function phSummary(){
  phDraft.lines.forEach((l,i)=>{const p=phProduct(l.productId)||{};const el=document.getElementById('ph-line-'+i);if(el)el.textContent=fmtMoney(Number(l.precio??p.precioVenta)*l.cantidad);});
  const t=phLineTotals();const paid=phDraft.payments.reduce((s,p)=>s+Math.round(Number(p.amount||0)*100),0)/100;
  const el=document.getElementById('ph-summary');if(el)el.innerHTML=`<span>${t.count} producto(s) · ${t.units} unidad(es)</span><span>Subtotal 0% <strong>${fmtMoney(t.sub0)}</strong></span><span>Subtotal 15% <strong>${fmtMoney(t.sub15)}</strong></span><span>IVA 15% <strong>${fmtMoney(t.iva)}</strong></span><span>Total <strong>${fmtMoney(t.total)}</strong></span><span>Recibido <strong>${fmtMoney(paid)}</strong></span><span>Pendiente <strong>${fmtMoney(Math.max(0,t.total-paid))}</strong></span>`;
}
async function phDispense(){
  if(!phDraft.patientId){toast('Selecciona el paciente','err');return;}
  if(!phDraft.lines.length){toast('Agrega al menos un producto','err');return;}
  const payload={action:'dispense',requestId:phDraft.requestId,patientId:phDraft.patientId,rxId:phDraft.rx?.rxId,cerrarReceta:!!document.getElementById('ph-close-rx')?.checked,
    lines:phDraft.lines.map(l=>({productId:l.productId,cantidad:l.cantidad,...(l.rxIndex!=null?{rxIndex:l.rxIndex}:{}),...(l.precio!==undefined?{precio:l.precio}:{})})),
    payments:phDraft.payments.filter(p=>Number(p.amount)>0)};
  const res=await phPost(payload);
  if(!res)return;
  await phReload(['facturas','cajas','recetas']);await phLoadQueue();
  const inv=res.invoice;
  phNewDraft();renderFarmacia();
  phModal('m-ph-done','Dispensación registrada',`<p>Cuenta <strong>${esc(inv.id)}</strong> por <strong>${fmtMoney(inv.total)}</strong> · ${esc(inv.estadoPago||'')}${inv.saldo>0?` · pendiente ${fmtMoney(inv.saldo)} en Caja`:''}.</p><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Producto</th><th>Cant.</th><th>Lotes entregados (FEFO)</th></tr></thead><tbody>${(res.lines||[]).map(l=>`<tr><td>${esc(l.nombre)}</td><td>${l.cantidad}</td><td class="text-sm">${l.lotes.map(x=>`${esc(x.lote)} (vence ${fmtDate(x.caducidad)}) × ${x.cantidad}`).join('<br>')}</td></tr>`).join('')}</tbody></table></div><p class="text-sm text-muted">Puedes emitir la factura electrónica al SRI desde Facturación.</p><button class="btn-s" onclick="phPrintTicket('${esc(inv.id)}')"><i class="ti ti-printer"></i> Imprimir comprobante de entrega</button>`,720);
  window.phLastDispense=res;
}
function phPrintTicket(invoiceId){
  const res=window.phLastDispense;if(!res)return;const inv=res.invoice;const cfg=DB.get('config')||{};
  printDoc('Entrega de farmacia',`<div class="hdr"><img class="logo" src="${esc(cfg.logo||DEFAULT_LOGO)}"><div><div class="big">${esc(cfg.nombre||'Centro Médico')}</div><div class="muted">${esc(cfg.dir||'')}</div></div></div><div class="rx-title">COMPROBANTE DE ENTREGA DE MEDICAMENTOS</div><div class="row"><div><div class="label">Cuenta</div>${esc(inv.id)}</div><div><div class="label">Fecha</div>${esc(inv.createdAt.replace('T',' ').slice(0,16))}</div><div><div class="label">Paciente</div>${esc(getPacName(inv.pac))}</div></div>${res.receta?`<p><b>Receta:</b> ${esc(res.receta.numero)} · ${esc(res.receta.medico||'')}</p>`:''}<table width="100%" border="1" cellspacing="0" cellpadding="6"><tr><th>Producto</th><th>Cant.</th><th>Lote / caducidad</th><th>P. unit.</th><th>IVA</th><th>Total</th></tr>${inv.items.map(i=>`<tr><td>${esc(i.nombre)}</td><td>${i.cant}</td><td>${esc((i.lotes||[]).join(', '))}</td><td align="right">${fmtMoney(i.unit)}</td><td>${i.ivaRate}%</td><td align="right">${fmtMoney(i.total+i.iva)}</td></tr>`).join('')}<tr><td colspan="5" align="right"><b>Total</b></td><td align="right"><b>${fmtMoney(inv.total)}</b></td></tr></table><p>Pagado: ${fmtMoney(inv.abonado)} · Pendiente: ${fmtMoney(inv.saldo)}</p><div class="row" style="margin-top:50px"><div style="border-top:1px solid #111;width:40%;text-align:center;padding-top:4px">Entregado por</div><div style="border-top:1px solid #111;width:40%;text-align:center;padding-top:4px">Recibí conforme</div></div>`);
}

/* ------------------------------------- electronic prescription (MSP format) */
let rxDraft=null;
function phNumberWords(n){
  n=Math.floor(Number(n)||0);if(n===0)return 'cero';
  const u=['','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve','diez','once','doce','trece','catorce','quince','dieciséis','diecisiete','dieciocho','diecinueve','veinte','veintiuno','veintidós','veintitrés','veinticuatro','veinticinco','veintiséis','veintisiete','veintiocho','veintinueve'];
  const d=['','','','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa'];
  const c=['','ciento','doscientos','trescientos','cuatrocientos','quinientos','seiscientos','setecientos','ochocientos','novecientos'];
  const under100=x=>x<30?u[x]:d[Math.floor(x/10)]+(x%10?' y '+u[x%10]:'');
  const under1000=x=>x===100?'cien':(x>=100?c[Math.floor(x/100)]+(x%100?' '+under100(x%100):''):under100(x));
  if(n<1000)return under1000(n);
  const th=Math.floor(n/1000),rest=n%1000;
  return (th===1?'mil':under1000(th)+' mil')+(rest?' '+under1000(rest):'');
}
function openRecetaModal(pacId){
  if(!hasPerm('hce')){toast('No tienes permiso para generar recetas','err');return;}
  if(!(currentUser?.rol==='medico'||currentUser?.rol==='admin')){toast('Solo los médicos emiten recetas','err');return;}
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pacId))||{};
  const latest=((DB.get('notas')||{})[pacId]||[])[0]||{};
  rxDraft={pacId,items:[]};
  phModal('m-rx-e','Receta médica electrónica',`<p class="text-sm"><strong>${esc(ppLabel(p))}</strong> · C.I. ${esc(p.cedula||'—')} · ${esc(typeof patientAge==='function'?patientAge(p):'')} años</p>
  ${typeof cdDoctorField==='function'?cdDoctorField():''}
  <div class="form-row"><label class="field" style="flex:2">Diagnóstico<input id="rx-e-dx" maxlength="300" value="${esc(latest.cie10Desc||latest.dx||'')}"></label><label class="field">CIE-10<input id="rx-e-cie" list="rx-e-cie-list" maxlength="12" value="${esc(latest.cie10Code||'')}"><datalist id="rx-e-cie-list">${typeof cdCieOptions==='function'?cdCieOptions():''}</datalist></label></div>
  <label class="field">Alergias<input id="rx-e-alergias" maxlength="300" value="${esc(p.alergias||'No refiere')}"></label>
  <div class="cash-catalog mt8"><label style="flex:1">Medicamento del inventario<input id="rx-e-q" list="rx-e-list" autocomplete="off" placeholder="Escribe el nombre genérico o comercial…"><datalist id="rx-e-list">${phProducts().filter(x=>x.estado!=='inactivo').map(x=>`<option value="${esc(x.codigo)} · ${esc(phName(x))}${x.comercial?' ('+esc(x.comercial)+')':''}">Disponible: ${phStock(x.id)}</option>`).join('')}</datalist></label><button class="btn-p" onclick="rxAddItem()">Agregar</button><button class="btn-s" onclick="rxAddItem(true)" title="Medicamento que no está en el inventario de farmacia">Fuera de inventario</button></div>
  <div id="rx-e-items" class="mt12"></div>
  <div class="form-row mt8"><label class="field" style="flex:3">Indicaciones generales y signos de alarma<textarea id="rx-e-ind" rows="2" maxlength="1500"></textarea></label><label class="field">Validez (días)<input id="rx-e-val" type="number" min="1" max="180" value="30"></label></div>
  <button class="btn-g mt8" onclick="rxSave()"><i class="ti ti-prescription"></i> Emitir receta e imprimir</button>`,980);
  document.getElementById('rx-e-q').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();rxAddItem();}});
  rxRenderItems();
}
function rxAddItem(free){
  const q=document.getElementById('rx-e-q').value.trim();
  if(free){rxDraft.items.push({productoId:null,nombre:q,concentracion:'',forma:'',cantidad:1,posologia:'',duracion:'',via:''});document.getElementById('rx-e-q').value='';rxRenderItems();return;}
  if(!q)return;
  const code=q.split(' · ')[0];
  let p=phProducts().find(x=>x.codigo===code);
  if(!p){const m=phProducts().filter(x=>x.estado!=='inactivo'&&ppNorm(`${x.nombre} ${x.comercial} ${x.codigo}`).includes(ppNorm(q)));if(m.length===1)p=m[0];else{toast(m.length?'Elige una opción de la lista':'No está en el inventario. Usa "Fuera de inventario".','err');return;}}
  rxDraft.items.push({productoId:p.id,nombre:p.nombre,concentracion:p.concentracion,forma:p.forma,cantidad:1,posologia:'',duracion:'',via:p.via||''});
  document.getElementById('rx-e-q').value='';rxRenderItems();
}
function rxRenderItems(){
  const host=document.getElementById('rx-e-items');if(!host)return;
  host.innerHTML=rxDraft.items.length?rxDraft.items.map((it,i)=>{const stock=it.productoId?phStock(it.productoId):null;return `<div class="rx-line"><div class="rx-line-head"><strong>${i+1}.</strong> ${it.productoId?`<strong>${esc([it.nombre,it.concentracion,it.forma].filter(Boolean).join(' '))}</strong> <span class="badge ${stock>=it.cantidad?'b-green':'b-amber'}">Farmacia: ${stock}</span>`:`<input placeholder="Nombre genérico" value="${esc(it.nombre)}" oninput="rxDraft.items[${i}].nombre=this.value" style="flex:2"><input placeholder="Concentración" value="${esc(it.concentracion)}" oninput="rxDraft.items[${i}].concentracion=this.value" style="width:120px"><input placeholder="Forma" value="${esc(it.forma)}" oninput="rxDraft.items[${i}].forma=this.value" style="width:120px"> <span class="badge">Fuera de inventario</span>`}<button class="btn-s btn-xs" style="margin-left:auto" onclick="rxDraft.items.splice(${i},1);rxRenderItems()">Quitar</button></div>
  <div class="form-row"><label class="field" style="max-width:120px">Cantidad total<input type="number" min="1" step="1" value="${it.cantidad}" oninput="rxDraft.items[${i}].cantidad=Math.max(1,parseInt(this.value||'1',10))"></label><label class="field" style="flex:3">Posología (dosis, frecuencia)<input maxlength="300" value="${esc(it.posologia)}" placeholder="1 tableta cada 8 horas" oninput="rxDraft.items[${i}].posologia=this.value"></label><label class="field">Duración<input maxlength="80" value="${esc(it.duracion)}" placeholder="5 días" oninput="rxDraft.items[${i}].duracion=this.value"></label><label class="field">Vía<input maxlength="40" value="${esc(it.via)}" placeholder="Oral" oninput="rxDraft.items[${i}].via=this.value"></label></div></div>`;}).join(''):'<p class="text-muted">Agrega los medicamentos. Los del inventario se descuentan al dispensar en Farmacia.</p>';
}
async function rxSave(){
  if(!rxDraft.items.length){toast('Agrega al menos un medicamento','err');return;}
  if(phBusy)return;phBusy=true;
  try{
    await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de continuar.');
    const res=await API.post('/api/pharmacy',{action:'rx_create',patientId:rxDraft.pacId,doctorId:document.getElementById('cd-doctor')?.value,diagnostico:document.getElementById('rx-e-dx').value,cie10:document.getElementById('rx-e-cie').value,alergias:document.getElementById('rx-e-alergias').value,indicaciones:document.getElementById('rx-e-ind').value,validezDias:document.getElementById('rx-e-val').value,items:rxDraft.items});
    phApply(res);
    const store=DB.cache.recetas&&typeof DB.cache.recetas==='object'?DB.cache.recetas:(DB.cache.recetas={});store[res.patientId]=res.records;
    const conf=DB.confirmed.recetas&&typeof DB.confirmed.recetas==='object'?DB.confirmed.recetas:(DB.confirmed.recetas={});conf[res.patientId]=JSON.parse(JSON.stringify(res.records));
    closeM('m-rx-e');toast('Receta emitida. Farmacia ya puede dispensarla.','ok');
    if(typeof renderHCE==='function'&&document.getElementById('hce-detail'))renderHCE(+rxDraft.pacId);
    printReceta(+rxDraft.pacId,res.receta.id);
  }catch(e){toast(e.message,'err');}finally{phBusy=false;}
}
(function(){
  if(typeof printReceta==='function'){
    const legacy=printReceta;
    printReceta=function(pacId,recetaId){
      const r=((DB.get('recetas')||{})[pacId]||[]).find(x=>x.id===recetaId);
      if(!r||!r.rxVersion)return legacy(pacId,recetaId);
      const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pacId))||{};const cfg=DB.get('config')||{};const m=r.medicoInfo||{};
      const head=`<div class="hdr"><img class="logo" src="${esc(cfg.logo||DEFAULT_LOGO)}"><div><div class="big">${esc(cfg.nombre||'Centro Médico')}</div><div class="muted">RUC: ${esc(cfg.ruc||'---')} · ${esc(cfg.tel||'')}</div><div class="muted">${esc(cfg.dir||'')}</div></div><div style="margin-left:auto;text-align:right"><div class="label">Receta N.º</div><b>${esc(r.numero)}</b><div class="muted">${fmtDate(r.fecha)} ${esc(r.hora||'')}</div></div></div>`;
      const patient=`<table width="100%" border="1" cellspacing="0" cellpadding="5"><tr><td><b>Paciente:</b> ${esc(r.paciente?.nombre||ppLabel(p))}</td><td><b>C.I.:</b> ${esc(r.paciente?.cedula||p.cedula||'—')}</td><td><b>Edad:</b> ${esc(typeof patientAge==='function'?patientAge(p):'')} · <b>Sexo:</b> ${esc(p.genero||'—')}</td></tr><tr><td colspan="2"><b>Diagnóstico:</b> ${esc(r.diagnostico||'')}${r.cie10?` · <b>CIE-10:</b> ${esc(r.cie10)}`:''}</td><td><b>Alergias:</b> ${esc(r.alergias||'—')}</td></tr></table>`;
      const sign=`<div style="margin-top:46px;text-align:center"><div style="border-top:1px solid #111;width:280px;margin:0 auto;padding-top:5px"><b>${esc(m.nombre||r.medico||'')}</b><br>${esc(m.especialidad||'')}<br>${m.cedula?'C.I. '+esc(m.cedula):''}${(m.registro||r.registro)?' · Reg. '+esc(m.registro||r.registro):''}</div></div><p class="muted" style="text-align:center">Válida hasta el ${fmtDate(r.vence)} · Documento generado electrónicamente</p>`;
      const rp=r.items.map((it,i)=>`<li style="margin-bottom:10px"><b>${esc(it.nombre)}</b> ${esc(it.concentracion||'')} ${esc(it.forma||'')}${it.via?' · vía '+esc(it.via):''}<br>Cantidad: <b>#${it.cantidad}</b> (${esc(phNumberWords(it.cantidad))})${it.controlado?' <b>— control especial</b>':''}</li>`).join('');
      const ind=r.items.map((it,i)=>`<li style="margin-bottom:10px"><b>${esc(it.nombre)}</b>: ${esc(it.posologia||'')}${it.duracion?' por '+esc(it.duracion):''}${it.indicacion?'. '+esc(it.indicacion):''}</li>`).join('');
      printDoc('Receta '+r.numero,`<style>.rx-cols{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid #111;margin-top:12px}.rx-cols>div{padding:12px;min-height:300px}.rx-cols>div:first-child{border-right:1px dashed #111}.rx-cols h4{margin:0 0 8px}</style>${head}<div class="rx-title">RECETA MÉDICA</div>${patient}<div class="rx-cols"><div><h4>Rp.</h4><ol>${rp}</ol>${sign}</div><div><h4>Indicaciones</h4><ol>${ind}</ol>${r.indicaciones?`<p style="white-space:pre-wrap">${esc(r.indicaciones)}</p>`:''}${sign}</div></div>`);
    };
  }
  if(typeof renderRecetaCard==='function'){
    const legacy=renderRecetaCard;
    renderRecetaCard=function(r,pacId){
      const html=legacy(r,pacId);
      if(!r.rxVersion)return html;
      const st=r.dispensacion?.estado||'Pendiente';
      return html.replace('</div><button',` · <span class="badge ${st==='Dispensada'?'b-green':st==='Parcial'?'b-blue':'b-amber'}">Farmacia: ${esc(st)}</span></div><button`);
    };
  }
  if(typeof showMod==='function'){
    const base=showMod;
    showMod=function(id,el){
      base(id,el);
      if(id==='farmacia'&&hasPerm('farmacia')){const t=document.getElementById('tb-title');if(t)t.textContent='Farmacia e inventario';openFarmacia();}
    };
  }
})();
