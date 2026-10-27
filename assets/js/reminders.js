/* Appointment form improvements and patient reminders (e-mail and WhatsApp). */
function remPlan(notif){
  const t=String(notif||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  if(!t||t.includes('sin recordatorio'))return [];
  const ch=[];if(t.includes('whatsapp'))ch.push('whatsapp');if(t.includes('correo')||t.includes('email'))ch.push('email');return ch;
}
function remPatient(id){return (DB.get('pacientes')||[]).find(p=>String(p.id)===String(id));}
function remPhoneOk(tel){const d=String(tel||'').replace(/\D/g,'');return d.length>=9;}
function remCanUse(){return currentUser&&currentUser.rol!=='medico'&&hasPerm('agenda');}

/* --------------------------------------------------- appointment form */
function remContactHint(){
  const host=document.getElementById('c-contact-hint');if(!host)return;
  const p=remPatient(document.getElementById('c-pac')?.value);const ch=remPlan(document.getElementById('c-notif')?.value);
  if(!p){host.innerHTML='';return;}
  const tel=p.tel?`<span class="${remPhoneOk(p.tel)?'':'rem-warn'}"><i class="ti ti-brand-whatsapp"></i> ${esc(p.tel)}</span>`:'<span class="rem-warn"><i class="ti ti-brand-whatsapp"></i> Sin celular</span>';
  const mail=p.email?`<span><i class="ti ti-mail"></i> ${esc(p.email)}</span>`:'<span class="rem-warn"><i class="ti ti-mail"></i> Sin correo</span>';
  const missing=(ch.includes('whatsapp')&&!remPhoneOk(p.tel))||(ch.includes('email')&&!p.email);
  host.innerHTML=`${tel}${mail}${missing?' <span class="rem-warn">· Completa el contacto en la ficha del paciente para que reciba los recordatorios.</span>':''}`;
}
function remPrepareModal(isEdit){
  if(!document.getElementById('c-contact-hint')){
    const sel=document.getElementById('c-pac');
    const hint=document.createElement('div');hint.id='c-contact-hint';hint.className='rem-contact text-xs';
    sel?.closest('.field')?.appendChild(hint);
    sel?.addEventListener('change',remContactHint);sel?.addEventListener('ppsync',remContactHint);
  }
  patientPicker('c-pac',{onNew:()=>document.querySelector('#m-cita button[onclick*="openPacFromCita"]')?.click()});
  patientPickerSync('c-pac');
  document.querySelectorAll('#m-cita .cita-edit-only').forEach(b=>{b.style.display=isEdit?'':'none';});
  const wrap=document.getElementById('c-confirm-wrap');if(wrap)wrap.style.display=isEdit?'none':'';
  const box=document.getElementById('c-confirm-send');if(box)box.checked=!isEdit;
  remContactHint();
}
(function(){
  if(typeof openNewCita==='function'){
    const base=openNewCita;
    openNewCita=async function(fecha,hora){const r=base(fecha,hora);remPrepareModal(false);await r;return r;};
  }
  if(typeof editCita==='function'){
    const base=editCita;
    editCita=async function(id){
      const c=(DB.get('citas')||[]).find(x=>x.id===+id);
      const sel=document.getElementById('c-notif');
      if(c&&c.notif&&sel&&![...sel.options].some(o=>o.value===c.notif)){const o=document.createElement('option');o.textContent=c.notif;sel.appendChild(o);}
      const r=base(id);remPrepareModal(true);await r;remContactHint();return r;
    };
  }
  if(typeof saveCita==='function'){
    const base=saveCita;
    saveCita=async function(){
      const isNew=!+(document.getElementById('c-edit-id').value||0);
      const wantConfirm=isNew&&document.getElementById('c-confirm-send')?.checked;
      const notif=document.getElementById('c-notif').value;const pac=document.getElementById('c-pac').value;
      const before=new Set((DB.get('citas')||[]).map(c=>c.id));
      await base();
      if(!wantConfirm)return;
      const created=(DB.get('citas')||[]).find(c=>!before.has(c.id)&&String(c.pac)===String(pac));
      const channels=remPlan(notif);
      if(created&&channels.length)remSend(created.id,channels,'confirmacion');
    };
  }
})();
async function remSendFromModal(){
  const id=+(document.getElementById('c-edit-id').value||0);if(!id)return;
  let channels=remPlan(document.getElementById('c-notif').value);if(!channels.length)channels=['whatsapp','email'];
  remSend(id,channels,'manual');
}
async function remSend(citaId,channels,kind){
  try{
    const res=await API.post('/api/reminders/send',{citaId,channels,kind});
    const r=res.results||{};const msgs=[];let link=null;
    if(r.email)msgs.push(`Correo: ${r.email.status==='sent'?'enviado':r.email.detail}`);
    if(r.whatsapp){if(r.whatsapp.status==='sent')msgs.push('WhatsApp: enviado');else if(r.whatsapp.waLink)link=r.whatsapp.waLink;else msgs.push('WhatsApp: '+r.whatsapp.detail);}
    if(msgs.length)toast(msgs.join(' · '),Object.values(r).some(x=>x.status==='error')?'err':'ok');
    if(link)remWhatsAppPrompt(citaId,link,kind);
    if(document.getElementById('m-rem-panel')?.classList.contains('open'))remRenderPanel();
  }catch(e){toast(e.message,'err');}
}
function remWhatsAppPrompt(citaId,link,kind){
  const c=(DB.get('citas')||[]).find(x=>x.id===+citaId)||{};const p=remPatient(c.pac)||{};
  const text=decodeURIComponent(link.split('?text=')[1]||'');
  cashModal('m-rem-wa','Enviar por WhatsApp',`<p class="text-sm">Mensaje preparado para <strong>${esc((p.nombres||'')+' '+(p.apellidos||''))}</strong> (${esc(p.tel||'')}):</p><pre class="rem-preview">${esc(text)}</pre><div class="flex gap8 mt12" style="flex-wrap:wrap"><a class="btn-g" href="${esc(link)}" target="_blank" rel="noopener" onclick="remMark(${+citaId},'${esc(kind)}');closeM('m-rem-wa')"><i class="ti ti-brand-whatsapp"></i> Abrir WhatsApp y enviar</a><button class="btn-s" onclick="navigator.clipboard?.writeText(${esc(JSON.stringify(text))}).then(()=>toast('Mensaje copiado','ok'))">Copiar mensaje</button></div><p class="text-xs text-muted mt12">Para enviar automáticamente sin abrir WhatsApp, configura WhatsApp Business en Configuración → Recordatorios.</p>`);
}
async function remMark(citaId,kind){try{await API.post('/api/reminders/mark',{citaId,kind});if(document.getElementById('m-rem-panel')?.classList.contains('open'))setTimeout(remRenderPanel,500);}catch(e){}}

/* --------------------------------------------------- reminders panel */
let remPanelHours=48;
async function remOpenPanel(){
  if(!remCanUse()){toast('No tienes permiso de agenda','err');return;}
  cashModal('m-rem-panel','Recordatorios de citas',`<div class="pro-toolbar"><div class="pro-toolbar-left"><select id="rem-range" onchange="remPanelHours=+this.value;remRenderPanel()"><option value="24">Próximas 24 horas</option><option value="48" selected>Próximas 48 horas</option><option value="168">Próximos 7 días</option></select><span class="text-sm text-muted" id="rem-auto"></span></div><div class="pro-toolbar-right"><button class="btn-s btn-sm" onclick="remRunNow()"><i class="ti ti-player-play"></i> Procesar envíos automáticos</button></div></div><div id="rem-panel-body" class="text-muted">Cargando…</div>`);
  remRenderPanel();
}
async function remRenderPanel(){
  const host=document.getElementById('rem-panel-body');if(!host)return;
  const now=new Date(),limit=new Date(now.getTime()+remPanelHours*3600e3);
  const citas=(DB.get('citas')||[]).filter(c=>{if(!c.fecha||!c.hora)return false;const t=new Date(`${c.fecha}T${c.hora}:00-05:00`);return t>now&&t<=limit&&!['cancelada','atendida'].includes(String(c.estado||'').toLowerCase());}).sort((a,b)=>(a.fecha+a.hora).localeCompare(b.fecha+b.hora));
  let status={};
  try{if(citas.length)status=(await API.get('/api/reminders/status?ids='+citas.map(c=>c.id).join(','))).status||{};}catch(e){}
  const badge=(log,channel)=>{const rows=(log||[]).filter(x=>x.channel===channel);const last=rows[rows.length-1];if(!last)return '<span class="badge">Pendiente</span>';const map={sent:['b-green','Enviado'],manual:['b-green','Enviado (manual)'],error:['b-red','Error'],skipped:['b-amber','Sin contacto']};const [cls,label]=map[last.status]||['','—'];return `<span class="badge ${cls}" title="${esc((last.detail||'')+' · '+String(last.ts).replace('T',' ').slice(0,16)+' · '+(last.user_name||''))}">${label}</span>`;};
  host.innerHTML=citas.length?`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Cita</th><th>Paciente</th><th>Contacto</th><th>Recordatorio</th><th>Correo</th><th>WhatsApp</th><th></th></tr></thead><tbody>${citas.map(c=>{const p=remPatient(c.pac)||{};const ch=remPlan(c.notif);return `<tr><td><strong>${fmtDate(c.fecha)} ${esc(c.hora)}</strong><div class="text-xs text-muted">${esc(getMedName(c.med))} · ${esc(c.esp||'')}</div></td><td>${esc((p.nombres||'')+' '+(p.apellidos||''))}<div class="text-xs"><span class="badge ${c.estado==='Confirmada'?'b-green':'b-amber'}">${esc(c.estado||'')}</span></div></td><td class="text-xs">${p.tel?esc(p.tel):'<span class="rem-warn">Sin celular</span>'}<br>${p.email?esc(p.email):'<span class="rem-warn">Sin correo</span>'}</td><td class="text-xs">${esc(c.notif||'—')}</td><td>${ch.includes('email')?badge(status[c.id],'email'):'<span class="text-muted text-xs">No aplica</span>'}</td><td>${ch.includes('whatsapp')?badge(status[c.id],'whatsapp'):'<span class="text-muted text-xs">No aplica</span>'}</td><td class="ph-actions"><button class="btn-s btn-xs" onclick="remSend(${c.id},['email'],'manual')" ${p.email?'':'disabled'}><i class="ti ti-mail"></i> Correo</button> <button class="btn-g btn-xs" onclick="remSend(${c.id},['whatsapp'],'manual')" ${remPhoneOk(p.tel)?'':'disabled'}><i class="ti ti-brand-whatsapp"></i> WhatsApp</button></td></tr>`;}).join('')}</tbody></table></div>`:'<p class="text-muted">No hay citas activas en este período.</p>';
}
async function remRunNow(){
  try{const r=await API.post('/api/reminders/run',{force:true});toast(r.throttled?'Ya se procesó hace unos minutos.':r.disabled?'Los recordatorios automáticos están desactivados.':`Envíos automáticos: ${r.sent} enviado(s)${r.errors?.length?`, ${r.errors.length} con error`:''}.`,r.errors?.length?'err':'ok');remRenderPanel();}
  catch(e){toast(e.message,'err');}
}
/* Automatic processing while staff have the app open (e-mail and WhatsApp Business). */
setInterval(()=>{if(API.token&&remCanUse()&&!document.hidden)API.post('/api/reminders/run',{}).catch(()=>{});},10*60*1000);
setTimeout(()=>{if(API.token&&remCanUse())API.post('/api/reminders/run',{}).catch(()=>{});},20000);

/* --------------------------------------------------- settings (admin) */
async function remRenderSettings(){
  const cfgMod=document.getElementById('mod-config');if(!cfgMod||currentUser?.rol!=='admin')return;
  let card=document.getElementById('rem-settings-card');
  if(!card){card=document.createElement('section');card.className='card mb16';card.id='rem-settings-card';const mail=document.getElementById('email-settings-card');mail?mail.insertAdjacentElement('afterend',card):cfgMod.prepend(card);}
  card.innerHTML='<div class="card-hdr"><h2 class="card-title">Recordatorios de citas (correo y WhatsApp)</h2></div><div class="card-body text-muted">Cargando…</div>';
  try{
    const s=(await API.get('/api/reminders/settings')).settings;
    card.querySelector('.card-body').outerHTML=`<div class="card-body">
     <div class="rem-status"><span class="badge ${s.emailConfigured?'b-green':'b-amber'}">Correo: ${s.emailConfigured?'listo ('+esc(s.emailFrom)+')':'configura el correo saliente arriba'}</span><span class="badge ${s.whatsappAutomatic?'b-green':'b-blue'}">WhatsApp: ${s.whatsappAutomatic?'envío automático (WhatsApp Business)':'envío asistido con un clic'}</span></div>
     <label class="flex gap8 mt12" style="align-items:center"><input type="checkbox" id="rem-enabled" ${s.enabled?'checked':''}> Enviar recordatorios automáticos según la opción elegida en cada cita (24 h y/o 2 h antes)</label>
     <div class="form-row mt12"><label class="field">WhatsApp<select id="rem-mode" onchange="document.getElementById('rem-cloud').hidden=this.value!=='cloud'"><option value="manual" ${s.whatsappMode!=='cloud'?'selected':''}>Asistido: el sistema prepara el mensaje y recepción lo envía con un clic</option><option value="cloud" ${s.whatsappMode==='cloud'?'selected':''}>Automático: WhatsApp Business Cloud API (Meta)</option></select></label></div>
     <div id="rem-cloud" ${s.whatsappMode==='cloud'?'':'hidden'}>
      <div class="form-row"><label class="field">Phone Number ID<input id="rem-phone-id" value="${esc(s.phoneNumberId||'')}" placeholder="123456789012345"></label><label class="field">Token de acceso permanente<input id="rem-token" type="password" placeholder="${s.hasToken?'Guardado (déjalo vacío para mantenerlo)':'EAAG…'}"></label></div>
      <div class="form-row"><label class="field">Nombre de la plantilla aprobada<input id="rem-template" value="${esc(s.templateName||'')}" placeholder="recordatorio_cita"></label><label class="field">Idioma de la plantilla<input id="rem-lang" value="${esc(s.templateLang||'es')}" placeholder="es"></label></div>
      <div class="alert alert-i text-sm"><i class="ti ti-info-circle"></i><span>En Meta Business crea una plantilla de categoría <b>Utilidad</b> con 5 variables en este orden: {{1}} paciente, {{2}} fecha, {{3}} hora, {{4}} médico, {{5}} centro. Ejemplo: "Hola {{1}}, le recordamos su cita el {{2}} a las {{3}} con {{4}} en {{5}}. Si no puede asistir, responda este mensaje."</span></div>
     </div>
     <p class="text-xs text-muted">El envío automático se procesa cada 10 minutos mientras el sistema está abierto y una vez al día (07:00) aunque nadie esté conectado. Cada mensaje se envía una sola vez y queda registrado.</p>
     <button class="btn-p mt8" onclick="remSaveSettings()">Guardar recordatorios</button></div>`;
  }catch(e){card.querySelector('.card-body').textContent=e.message;}
}
async function remSaveSettings(){
  try{
    await API.post('/api/reminders/settings',{enabled:document.getElementById('rem-enabled').checked,whatsappMode:document.getElementById('rem-mode').value,phoneNumberId:document.getElementById('rem-phone-id')?.value||'',token:document.getElementById('rem-token')?.value||'',templateName:document.getElementById('rem-template')?.value||'',templateLang:document.getElementById('rem-lang')?.value||'es'});
    toast('Recordatorios guardados','ok');remRenderSettings();
  }catch(e){toast(e.message,'err');}
}
(function(){
  if(typeof showMod!=='function')return;
  const base=showMod;
  showMod=function(id,el){base(id,el);if(id==='config')remRenderSettings();};
})();
