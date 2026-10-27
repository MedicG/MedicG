/* Professional reports (cash basis, revenue by specialty/doctor/concept, real export),
   organised service and exam catalogues. */

/* ------------------------------------------------------------- helpers */
function proNorm(v){return String(v??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/\s+/g,' ').trim();}
function proTitle(v){const s=String(v||'').trim();if(!s)return '';return s===s.toUpperCase()&&s.length>3?s.charAt(0)+s.slice(1).toLowerCase():s;}
function proDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function proPeriod(){
  const p=document.getElementById('rep-per')?.value||'mes';const now=new Date(today()+'T12:00:00');let s=new Date(now),e=new Date(now);
  if(p==='ayer'){s.setDate(s.getDate()-1);e=new Date(s);}
  else if(p==='semana')s.setDate(s.getDate()-((s.getDay()+6)%7));
  else if(p==='mes')s.setDate(1);
  else if(p==='mes_anterior'){s=new Date(now.getFullYear(),now.getMonth()-1,1,12);e=new Date(now.getFullYear(),now.getMonth(),0,12);}
  else if(p==='año'){s=new Date(now.getFullYear(),0,1,12);}
  else if(p==='rango'){return {start:document.getElementById('rep-from')?.value||today(),end:document.getElementById('rep-to')?.value||today(),label:'Rango personalizado'};}
  const labels={hoy:'Hoy',ayer:'Ayer',semana:'Esta semana',mes:'Este mes',mes_anterior:'Mes anterior',año:'Este año'};
  return {start:proDate(s),end:proDate(e),label:labels[p]||p};
}
function proSpecialtyMatcher(){
  const esps=(DB.get('especialidades')||[]).filter(e=>e.nombre);
  const list=esps.map(e=>({name:e.nombre,key:proNorm(e.nombre),color:e.color}));
  return text=>{
    const n=proNorm(text);if(!n||n.length<3)return null;
    let hit=list.find(e=>e.key===n);if(hit)return hit.name;
    hit=list.filter(e=>e.key.length>=4&&(e.key.includes(n)||n.includes(e.key))).sort((a,b)=>b.key.length-a.key.length)[0];
    return hit?hit.name:null;
  };
}

/* ------------------------------------------------------------- reports */
function proBuildReport(period){
  const {start,end,label}=period||proPeriod();
  const inP=v=>{const d=String(v||'').slice(0,10);return d>=start&&d<=end;};
  const match=proSpecialtyMatcher();
  const espNames=new Map((DB.get('especialidades')||[]).map(e=>[proNorm(e.nombre),e.nombre]));
  const exact=v=>espNames.get(proNorm(v))||null;
  const services=new Map((DB.get('servicios')||[]).map(s=>['servicio:'+s.id,s]));
  const exams=new Map((DB.get('examenes')||[]).map(s=>['examen:'+s.id,s]));
  const patients=new Map((DB.get('pacientes')||[]).map(p=>[String(p.id),p]));
  const citas=(DB.get('citas')||[]).filter(c=>!['cancelada','cancelado','anulada'].includes(proNorm(c.estado)));
  const byPatient={};citas.forEach(c=>{(byPatient[String(c.pac)]=byPatient[String(c.pac)]||[]).push(c);});
  Object.values(byPatient).forEach(l=>l.sort((a,b)=>String(b.fecha).localeCompare(String(a.fecha))));
  const visitFor=(pac,date,itemKeys)=>{
    const list=byPatient[String(pac)]||[];
    const walk=list.find(c=>(c.serviciosSolicitados||[]).some(i=>itemKeys.has(i.kind+':'+i.id))&&String(c.fecha)<=date);
    if(walk)return walk;
    return list.find(c=>String(c.fecha)<=date&&(new Date(date)-new Date(c.fecha))/864e5<=60)||null;
  };
  const rows=[];
  (DB.get('facturas')||[]).forEach(f=>{
    if(f.estado==='Anulado'||f.demo||f.isDemo)return;
    let receipts=[];
    if(Array.isArray(f.pagos)&&f.cobroVersion===1)receipts=f.pagos.filter(p=>inP(p.fecha)).map(p=>({fecha:String(p.fecha).slice(0,10),monto:Number(p.monto)||0,metodo:p.metodo||'—'}));
    else if(['Pagado','Autorizado SRI'].includes(f.estado)&&inP(f.fecha))receipts=[{fecha:f.fecha,monto:Number(f.total)||0,metodo:f.pago||'—'}];
    if(!receipts.length)return;
    const items=(f.items&&f.items.length?f.items:[{nombre:f.serv||'Servicios',total:Number(f.total)||0}]).map(i=>({...i,gross:(Number(i.total)||0)+(Number(i.iva)||0)}));
    const grossTotal=items.reduce((s,i)=>s+i.gross,0)||1;
    const keys=new Set(items.filter(i=>i.kind&&i.id!=null).map(i=>i.kind+':'+i.id));
    const visit=visitFor(f.pac,String(f.fecha||'').slice(0,10),keys);
    const patient=patients.get(String(f.pac))||{};
    receipts.forEach(r=>items.forEach(i=>{
      const catalog=services.get(i.kind+':'+i.id)||exams.get(i.kind+':'+i.id);
      let esp=i.kind==='medicamento'?'Farmacia':(catalog&&match(catalog.categoria))||(visit&&match(visit.esp))||exact(f.esp)||match(patient.esp)||'Sin especialidad asignada';
      rows.push({fecha:r.fecha,comprobante:f.id,pac:f.pac,paciente:`${patient.nombres||''} ${patient.apellidos||''}`.trim()||'—',concepto:i.nombre||i.desc||'Servicio',tipo:i.kind==='medicamento'?'Farmacia':i.kind==='examen'?'Examen':i.kind==='servicio'?'Servicio':'Otro',especialidad:esp,medico:visit?getMedName(visit.med):'—',metodo:r.metodo,monto:Math.round(r.monto*i.gross/grossTotal*100)/100});
    }));
  });
  const sum=(arr,key)=>{const o={};arr.forEach(r=>{o[r[key]]=(o[r[key]]||0)+r.monto;});return Object.entries(o).map(([k,v])=>[k,Math.round(v*100)/100]).sort((a,b)=>b[1]-a[1]);};
  const total=Math.round(rows.reduce((s,r)=>s+r.monto,0)*100)/100;
  const attended=(DB.get('citas')||[]).filter(c=>inP(c.fecha)&&['atendida','atendido','completada','realizada','finalizada'].includes(proNorm(c.estado)));
  const paying=new Set(rows.map(r=>String(r.pac)));
  const people=new Set([...paying,...attended.map(c=>String(c.pac))]);
  const receivable=(DB.get('facturas')||[]).filter(f=>f.cobroVersion===1&&f.estado!=='Anulado'&&Number(f.saldo)>0);
  return {start,end,label,rows,total,bySpecialty:sum(rows,'especialidad'),byMethod:sum(rows,'metodo'),byDoctor:sum(rows.filter(r=>r.medico!=='—'),'medico'),byConcept:sum(rows,'concepto').slice(0,12),byType:sum(rows,'tipo'),
    attended:attended.length,patients:people.size,ticket:paying.size?total/paying.size:0,receivable:receivable.reduce((s,f)=>s+Number(f.saldo||0),0),receivableCount:receivable.length,invoices:new Set(rows.map(r=>r.comprobante)).size};
}
function proBars(list,total,colorFor){
  if(!list.length)return '<p class="text-muted text-sm">Sin ingresos en el período.</p>';
  const max=Math.max(...list.map(x=>x[1]),1);
  return list.map(([k,v],i)=>`<div class="pro-bar"><div class="pro-bar-head"><span>${esc(k)}</span><strong>${fmtMoney(v)} <em>${total?Math.round(v/total*100):0}%</em></strong></div><div class="progress"><div class="prog-fill" style="width:${Math.max(2,Math.round(v/max*100))}%;background:${colorFor(k,i)}"></div></div></div>`).join('');
}
const PRO_COLORS=['#0D7A6B','#1B4F8A','#C47A0A','#7C3AED','#B83232','#2A7A3B','#0E7490','#9D174D','#5A5A6A'];
let proLastReport=null;
function renderReportes(){
  const mod=document.getElementById('mod-reportes');if(!mod)return;
  if(!document.getElementById('pro-reports')){
    mod.innerHTML=`<div id="pro-reports"><div class="pro-toolbar"><div class="pro-toolbar-left"><select id="rep-per" onchange="document.getElementById('rep-range').hidden=this.value!=='rango';renderReportes()"><option value="hoy">Hoy</option><option value="ayer">Ayer</option><option value="semana">Esta semana</option><option value="mes" selected>Este mes</option><option value="mes_anterior">Mes anterior</option><option value="año">Este año</option><option value="rango">Rango de fechas…</option></select><span id="rep-range" hidden><input type="date" id="rep-from" onchange="renderReportes()"> a <input type="date" id="rep-to" onchange="renderReportes()"></span><span id="rep-label" class="text-muted text-sm"></span></div><div class="pro-toolbar-right"><button class="btn-s btn-sm" onclick="proPrintReport()"><i class="ti ti-printer"></i> Imprimir</button><button class="btn-g btn-sm" onclick="proExportReport()"><i class="ti ti-file-spreadsheet"></i> Exportar Excel</button></div></div>
    <div class="stats-row pro-kpis" id="rep-stats"></div>
    <div class="grid2 mt16"><section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-chart-bar"></i> Ingresos por especialidad</h3></div><div class="card-body" id="rep-esp"></div></section><section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-credit-card"></i> Formas de pago</h3></div><div class="card-body" id="rep-pago"></div><div class="card-hdr"><h3 class="card-title"><i class="ti ti-category"></i> Por tipo de ingreso</h3></div><div class="card-body" id="rep-type"></div></section></div>
    <div class="grid2 mt16"><section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-stethoscope"></i> Ingresos por médico</h3></div><div class="card-body" id="rep-doc"></div></section><section class="card"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-list-numbers"></i> Servicios y exámenes más vendidos</h3></div><div class="card-body" id="rep-top"></div></section></div>
    <section class="card mt16"><div class="card-hdr"><h3 class="card-title"><i class="ti ti-receipt"></i> Detalle de ingresos</h3><span class="text-muted text-sm" id="rep-detail-count"></span></div><div class="tbl-wrap" id="rep-detail"></div></section></div>`;
    document.getElementById('rep-from').value=today().slice(0,8)+'01';document.getElementById('rep-to').value=today();
  }
  const r=proBuildReport();proLastReport=r;
  const espColor=Object.fromEntries((DB.get('especialidades')||[]).map(e=>[e.nombre,e.color]));
  document.getElementById('rep-label').textContent=`${r.label}: ${fmtDate(r.start)} – ${fmtDate(r.end)}`;
  document.getElementById('rep-stats').innerHTML=`
    <div class="stat-box"><div class="stat-lbl">Ingresos cobrados</div><div class="stat-val" style="color:var(--green)">${fmtMoney(r.total)}</div><div class="stat-sub">${r.invoices} comprobante(s) con pagos</div></div>
    <div class="stat-box"><div class="stat-lbl">Cuentas por cobrar</div><div class="stat-val" style="color:${r.receivable?'var(--amber,#b45309)':'inherit'}">${fmtMoney(r.receivable)}</div><div class="stat-sub">${r.receivableCount} cuenta(s) con saldo, a la fecha</div></div>
    <div class="stat-box"><div class="stat-lbl">Pacientes atendidos</div><div class="stat-val">${r.patients}</div><div class="stat-sub">Con pago o cita atendida</div></div>
    <div class="stat-box"><div class="stat-lbl">Ticket promedio</div><div class="stat-val">${fmtMoney(r.ticket)}</div><div class="stat-sub">Por paciente que pagó</div></div>
    <div class="stat-box"><div class="stat-lbl">Citas atendidas</div><div class="stat-val">${r.attended}</div><div class="stat-sub">Marcadas como atendidas</div></div>`;
  document.getElementById('rep-esp').innerHTML=proBars(r.bySpecialty,r.total,(k,i)=>espColor[k]||(k==='Farmacia'?'#7C3AED':k.startsWith('Sin')?'#9CA3AF':PRO_COLORS[i%PRO_COLORS.length]));
  document.getElementById('rep-pago').innerHTML=proBars(r.byMethod,r.total,(k,i)=>PRO_COLORS[i%PRO_COLORS.length]);
  document.getElementById('rep-type').innerHTML=proBars(r.byType,r.total,(k,i)=>PRO_COLORS[(i+2)%PRO_COLORS.length]);
  document.getElementById('rep-doc').innerHTML=r.byDoctor.length?proBars(r.byDoctor,r.total,(k,i)=>PRO_COLORS[(i+1)%PRO_COLORS.length])+'<p class="text-xs text-muted mt8">Según la cita o consulta vinculada al cobro.</p>':'<p class="text-muted text-sm">Sin cobros vinculados a citas en el período.</p>';
  document.getElementById('rep-top').innerHTML=r.byConcept.length?`<table class="tbl"><tbody>${r.byConcept.map(([k,v],i)=>`<tr><td class="text-muted" style="width:28px">${i+1}</td><td>${esc(k)}</td><td class="text-r fw6">${fmtMoney(v)}</td></tr>`).join('')}</tbody></table>`:'<p class="text-muted text-sm">Sin ingresos en el período.</p>';
  const detail=r.rows.slice().sort((a,b)=>b.fecha.localeCompare(a.fecha));
  document.getElementById('rep-detail-count').textContent=`${detail.length} línea(s)${detail.length>200?' · se muestran 200, exporta para ver todo':''}`;
  document.getElementById('rep-detail').innerHTML=`<table class="tbl"><thead><tr><th>Fecha</th><th>Comprobante</th><th>Paciente</th><th>Concepto</th><th>Especialidad</th><th>Médico</th><th>Forma de pago</th><th class="text-r">Monto</th></tr></thead><tbody>${detail.slice(0,200).map(x=>`<tr><td>${fmtDate(x.fecha)}</td><td class="text-sm">${esc(x.comprobante)}</td><td>${esc(x.paciente)}</td><td class="text-sm">${esc(x.concepto)}</td><td><span class="badge" style="background:${(espColor[x.especialidad]||'#6B7280')}1f;color:${espColor[x.especialidad]||'#374151'}">${esc(x.especialidad)}</span></td><td class="text-sm">${esc(x.medico)}</td><td class="text-sm">${esc(x.metodo)}</td><td class="text-r fw6">${fmtMoney(x.monto)}</td></tr>`).join('')||'<tr><td colspan="8" class="text-muted">Sin ingresos en el período.</td></tr>'}</tbody></table>`;
}
function proExportReport(){
  const r=proLastReport||proBuildReport();const q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const n=v=>String((Math.round(Number(v)*100)/100).toFixed(2)).replace('.',',');
  const lines=[`Reporte de ingresos;${r.label};${r.start};${r.end}`,'',
    'Resumen',`Ingresos cobrados;${n(r.total)}`,`Cuentas por cobrar;${n(r.receivable)}`,`Pacientes atendidos;${r.patients}`,`Citas atendidas;${r.attended}`,'',
    'Ingresos por especialidad;Monto',...r.bySpecialty.map(([k,v])=>`${q(k)};${n(v)}`),'',
    'Formas de pago;Monto',...r.byMethod.map(([k,v])=>`${q(k)};${n(v)}`),'',
    'Ingresos por médico;Monto',...r.byDoctor.map(([k,v])=>`${q(k)};${n(v)}`),'',
    'Fecha;Comprobante;Paciente;Concepto;Tipo;Especialidad;Médico;Forma de pago;Monto',
    ...r.rows.map(x=>[x.fecha,x.comprobante,x.paciente,x.concepto,x.tipo,x.especialidad,x.medico,x.metodo].map(q).join(';')+';'+n(x.monto))];
  const url=URL.createObjectURL(new Blob(['﻿'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`reporte-ingresos-${r.start}-a-${r.end}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast('Reporte exportado (se abre en Excel)','ok');
}
function proPrintReport(){
  const r=proLastReport||proBuildReport();const cfg=DB.get('config')||{};
  const table=(title,list)=>`<h3 style="margin:16px 0 6px">${title}</h3><table width="100%" border="1" cellspacing="0" cellpadding="5">${list.map(([k,v])=>`<tr><td>${esc(k)}</td><td align="right">${fmtMoney(v)}</td><td align="right">${r.total?Math.round(v/r.total*100):0}%</td></tr>`).join('')||'<tr><td>Sin datos</td></tr>'}</table>`;
  printDoc('Reporte de ingresos',`<div class="hdr"><img class="logo" src="${esc(cfg.logo||DEFAULT_LOGO)}"><div><div class="big">${esc(cfg.nombre||'Centro Médico')}</div><div class="muted">Reporte de ingresos · ${esc(r.label)}: ${fmtDate(r.start)} – ${fmtDate(r.end)}</div></div></div>
  <div class="row"><div><div class="label">Ingresos cobrados</div><div class="big">${fmtMoney(r.total)}</div></div><div><div class="label">Por cobrar</div><div class="big">${fmtMoney(r.receivable)}</div></div><div><div class="label">Pacientes</div><div class="big">${r.patients}</div></div><div><div class="label">Citas atendidas</div><div class="big">${r.attended}</div></div></div>
  ${table('Ingresos por especialidad',r.bySpecialty)}${table('Formas de pago',r.byMethod)}${table('Ingresos por médico',r.byDoctor)}${table('Servicios y exámenes más vendidos',r.byConcept)}`);
}

/* ------------------------------------------------- organised catalogues */
function proChargeGroups(){
  const groups={};
  allChargeItems().forEach(i=>{const g=(i.kind==='examen'?'Exámenes · ':'Servicios · ')+(proTitle(i.categoria)||'General');(groups[g]=groups[g]||[]).push(i);});
  return Object.entries(groups).sort((a,b)=>a[0].localeCompare(b[0],'es')).map(([g,items])=>[g,items.sort((a,b)=>String(a.nombre).localeCompare(String(b.nombre),'es'))]);
}
function chargeOptionsHtml(){
  return proChargeGroups().map(([g,items])=>`<optgroup label="${esc(g)}">${items.map(i=>`<option value="${chargeItemKey(i)}">${esc(i.nombre)} — ${fmtMoney(chargeItemFinal(i).total)}</option>`).join('')}</optgroup>`).join('');
}
let proExamFilter='',proExamCat='';
(function(){
  if(typeof renderExamenes!=='function')return;
  const base=renderExamenes;
  renderExamenes=function(){
    base();
    const body=document.getElementById('ex-tbody');if(!body)return;
    const table=body.closest('.tbl-wrap');
    if(table&&!document.getElementById('ex-pro-filter')){
      const bar=document.createElement('div');bar.className='pro-toolbar mb8';bar.id='ex-pro-filter';
      bar.innerHTML=`<div class="pro-toolbar-left"><div class="si" style="min-width:240px"><i class="ti ti-search"></i><input id="ex-pro-q" placeholder="Buscar examen…" oninput="proExamFilter=this.value;renderExamenes()"></div><select id="ex-pro-cat" onchange="proExamCat=this.value;renderExamenes()"></select></div><span class="text-muted text-sm" id="ex-pro-count"></span>`;
      table.parentNode.insertBefore(bar,table);
    }
    const rows=[...body.querySelectorAll('tr')];
    const exams=DB.get('examenes')||[];
    if(rows.length!==exams.length)return;
    const cats=[...new Set(exams.map(e=>proTitle(e.categoria)||'Examen'))].sort((a,b)=>a.localeCompare(b,'es'));
    const sel=document.getElementById('ex-pro-cat');if(sel){sel.innerHTML=`<option value="">Todas las categorías (${exams.length})</option>`+cats.map(c=>`<option ${c===proExamCat?'selected':''}>${esc(c)}</option>`).join('');}
    const q=proNorm(proExamFilter);
    const items=exams.map((e,i)=>({e,row:rows[i],cat:proTitle(e.categoria)||'Examen'})).filter(x=>(!proExamCat||x.cat===proExamCat)&&(!q||proNorm(x.e.nombre+' '+x.cat).includes(q)))
      .sort((a,b)=>a.cat.localeCompare(b.cat,'es')||String(a.e.nombre).localeCompare(String(b.e.nombre),'es'));
    body.innerHTML='';let last=null;
    items.forEach(x=>{if(x.cat!==last){last=x.cat;const h=document.createElement('tr');h.className='pro-group-row';h.innerHTML=`<td colspan="6">${esc(x.cat)} <span>${items.filter(y=>y.cat===x.cat).length}</span></td>`;body.appendChild(h);}body.appendChild(x.row);});
    if(!items.length)body.innerHTML='<tr><td colspan="6" class="text-muted">Sin exámenes que coincidan.</td></tr>';
    const count=document.getElementById('ex-pro-count');if(count)count.textContent=`${items.length} de ${exams.length} exámenes`;
  };
})();

/* Dashboard: revenue by specialty of the current month, same rules as Reports */
(function(){
  if(typeof initDashboard!=='function')return;
  const base=initDashboard;
  initDashboard=function(){
    base();
    const el=document.getElementById('dash-chart');if(!el)return;
    try{
      const r=proBuildReport({start:today().slice(0,8)+'01',end:today(),label:'Este mes'});
      const espColor=Object.fromEntries((DB.get('especialidades')||[]).map(e=>[e.nombre,e.color]));
      el.innerHTML=`<p class="text-xs text-muted mb8">Cobrado este mes: <strong>${fmtMoney(r.total)}</strong></p>`+proBars(r.bySpecialty,r.total,(k,i)=>espColor[k]||(k==='Farmacia'?'#7C3AED':k.startsWith('Sin')?'#9CA3AF':PRO_COLORS[i%PRO_COLORS.length]));
    }catch(e){}
  };
})();
