/* Configuración > Facturación electrónica SRI: test against the SRI PRUEBAS environment (nothing is stored). */
function sriTestInstall(){
  const status=document.getElementById('sri-cert-status');
  if(!status||document.getElementById('sri-test-box')||currentUser?.rol!=='admin')return;
  const box=document.createElement('div');box.id='sri-test-box';box.className='mt12';
  box.innerHTML=`<button type="button" class="btn-s" id="sri-test-btn" onclick="sriRunTest()"><i class="ti ti-plug-connected"></i> Probar con el SRI (ambiente de pruebas)</button>
  <div class="text-xs text-muted mt4">Firma y envía una factura de $1,00 al ambiente de pruebas del SRI, sin valor tributario y sin guardarla. Si se autoriza, el RIDE llega al correo de la clínica.</div>
  <div id="sri-test-result" class="mt8"></div>`;
  status.insertAdjacentElement('afterend',box);
}
async function sriRunTest(){
  const btn=document.getElementById('sri-test-btn'),out=document.getElementById('sri-test-result');
  btn.disabled=true;out.innerHTML='<span class="text-muted">Enviando al SRI… puede tardar hasta 30 segundos.</span>';
  try{
    const r=await API.post('/api/sri/test',{});
    const f=r.firma||{};
    const msgs=[...(r.recepcion||[]),...(r.autorizacion||[])].map(m=>`<li>${esc([m.identificador,m.mensaje,m.informacionAdicional].filter(Boolean).join(' · '))}</li>`).join('');
    out.innerHTML=`<div class="alert ${r.ok?'alert-s':'alert-w'}"><div>
      <b>${r.ok?'Autorizada por el SRI (pruebas)':'No autorizada'}</b>${r.estado?` · Estado: ${esc(r.estado)}`:''}${r.error?`<br>${esc(r.error)}`:''}
      ${r.advertencia?`<br><b>Atención:</b> ${esc(r.advertencia)}`:''}
      ${f.titular?`<br>Firma: ${esc(f.titular)} · Vence ${esc(f.vence||'')}${(f.identificaciones||[]).length?' · ID '+esc(f.identificaciones.join(', ')):''}`:''}
      ${r.ruc?`<br>RUC emisor: ${esc(r.ruc)}`:''}${r.claveAcceso?`<br>Clave de acceso: <span style="word-break:break-all">${esc(r.claveAcceso)}</span>`:''}
      ${r.correo?`<br>Correo: ${r.correo.enviado?'enviado a '+esc(r.correo.a):esc(r.correo.error||'no enviado')}`:''}
      ${msgs?`<ul style="margin:6px 0 0 16px">${msgs}</ul>`:''}</div></div>`;
  }catch(e){out.innerHTML=`<div class="alert alert-w">${esc(e.message)}</div>`;}
  finally{btn.disabled=false;}
}
(function(){
  const prev=window.showMod;
  if(typeof prev==='function')window.showMod=function(...a){const r=prev.apply(this,a);try{setTimeout(sriTestInstall,300);}catch(e){}return r;};
})();
