(() => {
 let checking=false;
 async function checkVersion(){
  if(checking||document.hidden||document.getElementById('app-update-notice'))return;
  checking=true;
  try{
   const response=await fetch('/?version-check='+Date.now(),{cache:'no-store'});
   if(!response.ok)return;
   const html=await response.text();const version=html.match(/window\.APP_BUILD\s*=\s*"([^"]+)"/)?.[1];
   if(!version||version===window.APP_BUILD)return;
   const notice=document.createElement('div');notice.id='app-update-notice';notice.setAttribute('role','status');
   notice.style.cssText='position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:30000;background:#fff;color:#173d36;border:1px solid #0d7a6b;border-radius:10px;padding:12px 16px;box-shadow:0 4px 20px #0002;max-width:90vw;display:flex;align-items:center;gap:12px';
   const label=document.createElement('span');label.textContent='Hay una versión nueva. Guarda o termina lo que estás llenando antes de actualizar.';
   const button=document.createElement('button');button.className='btn-p';button.textContent='Actualizar';
   button.onclick=()=>{if(typeof DB!=='undefined'&&(DB.failures?.size||DB.pending)){toast('Revisa los cambios pendientes antes de actualizar.','err');return;}if(!confirm('¿Terminaste de guardar los formularios abiertos? Se actualizará la página.'))return;const url=new URL(location.href);url.searchParams.set('v',version);location.replace(url.href);};
   notice.append(label,button);document.body.appendChild(notice);
  }catch(e){}finally{checking=false;}
 }
 window.addEventListener('focus',checkVersion);document.addEventListener('visibilitychange',checkVersion);setInterval(checkVersion,60000);setTimeout(checkVersion,5000);
})();
