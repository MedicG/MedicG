/* Accessibility helpers for forms and buttons built at runtime:
   - associates each visible field label with its control (for=/aria-label)
   - gives icon-only buttons and links an accessible name from their title
   - names dialogs after their title. */
(function(){
  let seq=0;
  function labelText(label){return (label.textContent||'').replace(/\*/g,'').replace(/\s+/g,' ').trim();}
  function fix(root){
    (root.querySelectorAll?root:document).querySelectorAll('label.field-lbl:not([for]),label.field-lbl[for=""]').forEach(label=>{
      const field=label.closest('.field')||label.parentElement;if(!field)return;
      const control=field.querySelector('input:not([type=hidden]),select,textarea');if(!control||control.closest('label')===label)return;
      if(!control.id)control.id='a11y-f'+(++seq);
      label.setAttribute('for',control.id);
    });
    (root.querySelectorAll?root:document).querySelectorAll('input:not([type=hidden]):not([aria-label]),select:not([aria-label]),textarea:not([aria-label])').forEach(control=>{
      if(control.labels&&control.labels.length)return;
      const hint=control.getAttribute('title')||control.getAttribute('placeholder');
      if(hint)control.setAttribute('aria-label',hint.trim());
    });
    (root.querySelectorAll?root:document).querySelectorAll('button:not([aria-label]),a[href]:not([aria-label])').forEach(el=>{
      if((el.textContent||'').trim())return;
      const t=el.getAttribute('title')||el.querySelector('img[alt]')?.getAttribute('alt');
      if(t)el.setAttribute('aria-label',t.trim());
      else{const icon=el.querySelector('i[class*="ti-"]');if(icon){const n=(icon.className.match(/ti-([a-z0-9-]+)/)||[])[1];const names={x:'Cerrar',trash:'Eliminar',printer:'Imprimir',edit:'Editar',pencil:'Editar',eye:'Ver',download:'Descargar',refresh:'Actualizar',plus:'Agregar',search:'Buscar','chevron-left':'Anterior','chevron-right':'Siguiente',menu:'Menú','menu-2':'Menú',send:'Enviar',mail:'Enviar correo',file:'Ver archivo'};if(n&&names[n])el.setAttribute('aria-label',names[n]);}}
    });
    (root.querySelectorAll?root:document).querySelectorAll('.modal-bg .modal:not([aria-label]):not([aria-labelledby])').forEach(m=>{
      const t=m.querySelector('.modal-title,.card-title');if(!t)return;
      if(!t.id)t.id='a11y-t'+(++seq);
      m.setAttribute('role','dialog');m.setAttribute('aria-modal','true');m.setAttribute('aria-labelledby',t.id);
    });
  }
  let pending=false;
  function schedule(){if(pending)return;pending=true;(window.requestIdleCallback||setTimeout)(()=>{pending=false;try{fix(document);}catch(e){}},{timeout:400});}
  if(document.readyState!=='loading')fix(document);else document.addEventListener('DOMContentLoaded',()=>fix(document));
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
})();
