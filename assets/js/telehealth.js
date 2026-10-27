let onlineCall=null;
function onlineEscape(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function showTelehealth(){
 try{
  const data=await API.get('/api/telehealth');
  cashModal('m-online','Consultas online',`<p>Videollamada dentro de Medic G para el médico asignado y su paciente. Entra desde 30 minutos antes de la cita.</p>${data.relayConfigured?'':'<p class="online-notice">La conexión directa está disponible. Algunas redes móviles o empresariales necesitan que la clínica configure su servidor de conexión.</p>'}<button class="btn" onclick="showTelehealth()">Actualizar</button>${data.appointments.length?data.appointments.map(a=>`<article class="online-appointment"><strong>${onlineEscape(a.fecha)} · ${onlineEscape(a.hora)}</strong><p>${onlineEscape(a.paciente)} · ${onlineEscape(a.medico)}</p><span>${onlineEscape(a.estado)}</span> <button class="btn btn-primary" ${a.canJoin?'':'disabled'} onclick="joinOnline(${Number(a.id)},this)">Entrar a consulta</button></article>`).join(''):'<p>No hay consultas online. En Nueva cita selecciona Consulta online.</p>'}`);
 }catch(e){toast(e.message,'err');}
}
async function joinOnline(id,button){
 if(onlineCall){toast('Ya tienes una consulta abierta.','err');return;}
 button.disabled=true;
 const call={id,sid:crypto.randomUUID(),pc:null,stream:null,closed:false,pair:null,remoteSet:false,joined:false,timer:null,lastSuccess:Date.now()};onlineCall=call;
 const panel=document.createElement('section');panel.className='online-room';panel.setAttribute('aria-label','Consulta online');
 panel.innerHTML='<header><strong>Medic G · Consulta online</strong><button data-exit class="btn">Salir</button></header><p data-status role="status" aria-live="polite">Preparando cámara y micrófono…</p><div class="online-videos"><div class="online-remote"><video data-remote autoplay playsinline></video><span>Otro participante</span></div><div class="online-local"><video data-local autoplay muted playsinline></video><span>Tú · Vista previa</span></div></div><footer><button data-mic class="btn" aria-pressed="false">Silenciar micrófono</button><button data-cam class="btn" aria-pressed="false">Apagar cámara</button><button data-reconnect class="btn">Reconectar</button></footer><p class="online-help">Permite cámara y micrófono. La consulta no se graba. Usa auriculares para evitar eco.</p>';
 document.body.append(panel);
 const status=message=>{if(!call.closed)panel.querySelector('[data-status]').textContent=message;};
 const send=(action,extra={})=>API.post('/api/telehealth/session',{appointmentId:id,sessionId:call.sid,action,...extra});
 const cleanup=async(message)=>{
  if(call.closed)return;call.closed=true;clearTimeout(call.timer);call.pc?.close();call.stream?.getTracks().forEach(t=>t.stop());panel.remove();if(onlineCall===call)onlineCall=null;window.removeEventListener('pagehide',onPageHide);button.disabled=false;
  if(call.joined)send('leave').catch(()=>{});
  if(message)toast(message,'err');
 };
 const onPageHide=()=>cleanup();window.addEventListener('pagehide',onPageHide);
 panel.querySelector('[data-exit]').onclick=()=>cleanup();
 panel.querySelector('[data-reconnect]').onclick=async()=>{await cleanup();joinOnline(id,button);};
 for(const [selector,kind,on,off] of [['[data-mic]','audio','Silenciar micrófono','Activar micrófono'],['[data-cam]','video','Apagar cámara','Activar cámara']]){
  panel.querySelector(selector).onclick=e=>{const tracks=call.stream?.getTracks().filter(t=>t.kind===kind)||[];if(!tracks.length)return;const enabled=!tracks[0].enabled;tracks.forEach(t=>t.enabled=enabled);e.target.textContent=enabled?on:off;e.target.setAttribute('aria-pressed',String(!enabled));};
 }
 async function description(type){
  const pc=call.pc;
  await pc.setLocalDescription(type==='offer'?await pc.createOffer():await pc.createAnswer());
  if(pc.iceGatheringState!=='complete')await new Promise((resolve,reject)=>{
   const timeout=setTimeout(()=>done(new Error('No se pudo preparar la conexión. Pulsa Reconectar.')),12000);
   const done=error=>{clearTimeout(timeout);pc.removeEventListener('icegatheringstatechange',check);error?reject(error):resolve();};
   const check=()=>{if(pc.iceGatheringState==='complete')done();};pc.addEventListener('icegatheringstatechange',check);check();
  });
  if(call.closed)return;
  await send('description',{pair:call.pair,description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp}});
 }
 async function update(data){
  if(call.closed)return;
  if(data.pair!==call.pair){
   call.pc?.close();call.pc=null;call.remoteSet=false;call.pair=data.pair;
   panel.querySelector('[data-remote]').srcObject=null;
   if(data.pair){
    const pc=new RTCPeerConnection({iceServers:call.iceServers});call.pc=pc;call.stream.getTracks().forEach(t=>pc.addTrack(t,call.stream));
    pc.ontrack=event=>{panel.querySelector('[data-remote]').srcObject=event.streams[0];panel.querySelector('[data-remote]').play().catch(()=>status('Pulsa el vídeo para escuchar al otro participante.'));};
    pc.onconnectionstatechange=()=>{if(call.pc!==pc||call.closed)return;const states={connected:'Conectados · Consulta en curso',connecting:'Conectando con el otro participante…',disconnected:'Conexión interrumpida. Esperando recuperación…',failed:'No se pudo conectar esta red. Pulsa Reconectar; si persiste, se necesita el servidor de conexión de la clínica.'};if(states[pc.connectionState])status(states[pc.connectionState]);};
    status('Conectando con el otro participante…');
    if(data.role==='doctor')await description('offer');
   }else status('Esperando a que el otro participante entre a la consulta…');
  }
  if(data.description&&call.pc&&!call.remoteSet){
   await call.pc.setRemoteDescription(data.description);call.remoteSet=true;
   if(data.role==='patient')await description('answer');
  }
 }
 panel.querySelector('[data-remote]').onclick=e=>e.target.play().catch(()=>{});
 async function poll(){
  if(call.closed)return;
  try{const data=await send('poll');call.lastSuccess=Date.now();await update(data);}
  catch(e){if(Date.now()-call.lastSuccess>15000){await cleanup('La consulta perdió la conexión con el sistema. Vuelve a entrar.');return;}status(e.message);}
  if(!call.closed)call.timer=setTimeout(poll,2000);
 }
 try{
  if(!navigator.mediaDevices?.getUserMedia||!window.RTCPeerConnection)throw new Error('Este navegador no permite videollamadas. Usa una versión actual de Chrome, Edge, Firefox o Safari con HTTPS.');
  call.stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:{echoCancellation:true,noiseSuppression:true}});
  if(call.closed){call.stream.getTracks().forEach(t=>t.stop());return;}
  panel.querySelector('[data-local]').srcObject=call.stream;
  const data=await send('join');call.joined=true;call.iceServers=data.iceServers||[];call.lastSuccess=Date.now();
  if(call.closed){send('leave').catch(()=>{});return;}
  await update(data);call.timer=setTimeout(poll,1000);
 }catch(e){await cleanup(e.name==='NotAllowedError'?'Permite el acceso a cámara y micrófono para entrar.':e.name==='NotFoundError'?'No se encontró cámara o micrófono. Conecta los dispositivos y vuelve a entrar.':e.message);}
}
