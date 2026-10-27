/* Searchable patient selector: type a name, surname or ID number instead of scrolling a long list.
   Enhances an existing <select>; the select stays (hidden) so existing code keeps reading its value. */
function ppNorm(v){return String(v??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().trim();}
function ppPatients(){return (DB.get('pacientes')||[]).filter(p=>!p.deletedAt);}
function ppLabel(p){return `${p.nombres||''} ${p.apellidos||''}`.trim();}
function ppMatches(q,limit=8){
  const terms=ppNorm(q).split(/\s+/).filter(Boolean);
  if(!terms.length)return [];
  const out=[];
  for(const p of ppPatients()){
    const hay=ppNorm(`${ppLabel(p)} ${p.cedula||''} ${p.tel||''} ${p.email||''}`);
    if(terms.every(t=>hay.includes(t))){out.push(p);if(out.length>=limit)break;}
  }
  return out;
}
function patientPicker(selectId,opts={}){
  const sel=document.getElementById(selectId);if(!sel||sel.dataset.picker)return;
  sel.dataset.picker='1';sel.style.display='none';
  const wrap=document.createElement('div');wrap.className='pp-wrap';
  wrap.innerHTML=`<div class="pp-box"><i class="ti ti-search pp-icon"></i><input type="search" class="pp-input" autocomplete="off" placeholder="${esc(opts.placeholder||'Escribe nombre, apellido o cédula del paciente…')}" aria-label="Buscar paciente" role="combobox" aria-expanded="false"></div><div class="pp-list" role="listbox" hidden></div><div class="pp-selected text-xs text-muted"></div>`;
  sel.insertAdjacentElement('afterend',wrap);
  const input=wrap.querySelector('.pp-input'),list=wrap.querySelector('.pp-list'),info=wrap.querySelector('.pp-selected');
  let items=[],active=-1;
  const showInfo=()=>{const p=ppPatients().find(x=>String(x.id)===String(sel.value));info.textContent=p?`Seleccionado: ${ppLabel(p)}${p.cedula?' · C.I. '+p.cedula:''}`:'';if(document.activeElement!==input)input.value=p?ppLabel(p):'';sel.dispatchEvent(new Event('ppsync'));};
  // Keep the search box in sync when other code sets the select's value programmatically.
  const desc=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value');
  Object.defineProperty(sel,'value',{configurable:true,get(){return desc.get.call(this);},set(v){desc.set.call(this,v);setTimeout(showInfo,0);}});
  const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');active=-1;};
  const choose=p=>{sel.value=String(p.id);if(sel.value!==String(p.id)){const o=document.createElement('option');o.value=p.id;o.textContent=ppLabel(p);sel.appendChild(o);sel.value=String(p.id);}input.value=ppLabel(p);close();showInfo();sel.dispatchEvent(new Event('change',{bubbles:true}));opts.onSelect?.(p);};
  const render=()=>{
    items=ppMatches(input.value,opts.limit||8);
    if(!input.value.trim()){close();return;}
    list.innerHTML=items.length?items.map((p,i)=>`<div class="pp-item${i===active?' active':''}" role="option" data-i="${i}"><strong>${esc(ppLabel(p))}</strong><span>${esc(p.cedula?'C.I. '+p.cedula:'Sin cédula')}${p.tel?' · '+esc(p.tel):''}</span></div>`).join(''):`<div class="pp-empty">Sin coincidencias.${opts.onNew?' <button type="button" class="btn-s btn-xs pp-new">+ Registrar paciente nuevo</button>':''}</div>`;
    list.hidden=false;input.setAttribute('aria-expanded','true');
  };
  input.addEventListener('input',()=>{active=-1;if(!input.value.trim()){sel.value='';showInfo();sel.dispatchEvent(new Event('change',{bubbles:true}));}render();});
  input.addEventListener('focus',()=>{if(input.value.trim()&&!sel.value)render();});
  input.addEventListener('keydown',e=>{
    if(list.hidden&&e.key==='ArrowDown'){render();return;}
    if(e.key==='ArrowDown'){active=Math.min(items.length-1,active+1);render();e.preventDefault();}
    else if(e.key==='ArrowUp'){active=Math.max(0,active-1);render();e.preventDefault();}
    else if(e.key==='Enter'){const p=items[active>=0?active:0];if(p&&!list.hidden){choose(p);e.preventDefault();}}
    else if(e.key==='Escape')close();
  });
  list.addEventListener('mousedown',e=>{const el=e.target.closest('.pp-item');if(el){e.preventDefault();choose(items[+el.dataset.i]);}else if(e.target.closest('.pp-new')){e.preventDefault();close();opts.onNew?.();}});
  input.addEventListener('blur',()=>setTimeout(close,150));
  sel.ppSync=showInfo;showInfo();
  if(opts.autofocus)setTimeout(()=>input.focus(),50);
  return wrap;
}
function patientPickerSync(selectId){document.getElementById(selectId)?.ppSync?.();}

/* ---- Walk-in consultation: patient search + running count and total */
(function(){
  if(typeof openWalkin==='function'){
    const base=openWalkin;
    openWalkin=function(){base();patientPicker('wi-patient',{autofocus:true,onNew:()=>walkinNewPatient()});};
  }
  if(typeof walkinPatientSaved==='function'){
    const base=walkinPatientSaved;
    walkinPatientSaved=function(id){base(id);patientPickerSync('wi-patient');};
  }
  if(typeof walkinRender==='function'){
    const base=walkinRender;
    walkinRender=function(){base();walkinSummary();};
  }
  if(typeof walkinTotal==='function'){
    const base=walkinTotal;
    walkinTotal=function(n){base(n);walkinSummary();};
  }
  if(typeof renderCaja==='function'){
    const base=renderCaja;
    renderCaja=function(){base();patientPicker('cash-patient');};
  }
})();
function walkinSummary(){
  const host=document.getElementById('wi-items');if(!host||!walkinDraft)return;
  let el=document.getElementById('wi-summary');
  if(!walkinDraft.items.length){if(el)el.remove();return;}
  const cents=walkinDraft.items.reduce((s,i)=>s+Math.round(cashUnit(i)*100)*(Number(i.quantity)||0),0);
  const units=walkinDraft.items.reduce((s,i)=>s+(Number(i.quantity)||0),0);
  if(!el){el=document.createElement('div');el.id='wi-summary';el.className='wi-summary';el.setAttribute('aria-live','polite');host.appendChild(el);}
  el.innerHTML=`<span><strong>${walkinDraft.items.length}</strong> ${walkinDraft.items.length===1?'concepto':'conceptos'}</span><span><strong>${units}</strong> ${units===1?'unidad':'unidades'}</span><span class="wi-summary-total">Total a pagar <strong>${fmtMoney(cents/100)}</strong></span>`;
}
