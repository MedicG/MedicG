/* Pediatric growth charts (WHO 2006 standards 0-5 years, WHO 2007 references 5-19 years; adopted by the MSP Ecuador).
   Measurements come from the patient's vital signs and HCU notes (weight, height/length, head circumference).
   z = ((X/M)^L - 1) / (L*S); WHO restricted adjustment beyond ±3 SD for weight and BMI indicators. */
const GROWTH_DATA_URL='assets/js/growth-data.js?v=36fb8b7d65';
const GROWTH_DPM=30.4375;
const GROWTH_PCT=[[3,-1.8808],[15,-1.0364],[50,0],[85,1.0364],[97,1.8808]];
const GROWTH_Z=[-3,-2,-1,0,1,2,3];
const GROWTH_IND={
  wfa:{label:'Peso para la edad',short:'P/E',unit:'kg',field:'peso',x:'age',max:120,restricted:true},
  hfa:{label:'Longitud / Talla para la edad',short:'T/E',unit:'cm',field:'talla',x:'age',max:228},
  bfa:{label:'IMC para la edad',short:'IMC/E',unit:'kg/m²',field:'imc',x:'age',max:228,restricted:true},
  wfh:{label:'Peso para la longitud / talla',short:'P/T',unit:'kg',field:'peso',x:'size',maxAge:60,restricted:true},
  hcfa:{label:'Perímetro cefálico para la edad',short:'PC/E',unit:'cm',field:'perimetroCefalico',x:'age',max:60}
};
let growthState={pid:null,ind:null,mode:'pct',range:null,sex:null};
let growthLoading=null;

function growthLoad(){
  if(window.WHO_GROWTH)return Promise.resolve(window.WHO_GROWTH);
  if(growthLoading)return growthLoading;
  growthLoading=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=GROWTH_DATA_URL;s.onload=()=>resolve(window.WHO_GROWTH);s.onerror=()=>{growthLoading=null;reject(new Error('No se pudieron cargar las tablas de la OMS.'));};document.head.appendChild(s);});
  return growthLoading;
}
function growthSex(p){const g=String(p?.genero||p?.sexo||'').toLowerCase();return g.startsWith('m')&&!g.startsWith('mu')?'m':(g.startsWith('f')||g.startsWith('mu'))?'f':null;}
function growthAgeMonths(fnac,fecha){const a=new Date(fnac+'T00:00:00'),b=new Date(String(fecha).slice(0,10)+'T00:00:00');return (b-a)/86400000/GROWTH_DPM;}
function growthAgeText(months){if(months<0)return '—';const days=Math.round(months*GROWTH_DPM);if(days<31)return days+' d';const y=Math.floor(months/12),m=Math.floor(months%12);return (y?y+' a ':'')+m+' m';}
function growthLmsAt(table,x){
  if(x<0||x>table.length-1)return null;
  const i=Math.floor(x),f=x-i,a=table[i],b=table[Math.min(i+1,table.length-1)];
  return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f];
}
function growthValueAt(lms,z){const [L,M,S]=lms;return Math.abs(L)<1e-6?M*Math.exp(S*z):M*Math.pow(1+L*S*z,1/L);}
function growthZ(lms,X,restricted){
  const [L,M,S]=lms;let z=Math.abs(L)<1e-6?Math.log(X/M)/S:(Math.pow(X/M,L)-1)/(L*S);
  if(restricted&&Math.abs(z)>3){
    const sd3=growthValueAt(lms,3*Math.sign(z)),sd2=growthValueAt(lms,2*Math.sign(z));
    z=3*Math.sign(z)+(X-sd3)/Math.abs(sd3-sd2);
  }
  return z;
}
function growthPercentile(z){ // standard normal CDF
  const t=1/(1+0.2316419*Math.abs(z)),d=0.3989423*Math.exp(-z*z/2);
  let p=d*t*(0.3193815+t*(-0.3565638+t*(1.781478+t*(-1.821256+t*1.330274))));
  return z>0?(1-p)*100:p*100;
}
/* Table for an indicator: age tables by month; weight-for-length (<24 m) / weight-for-height (24-60 m) by size. */
/* Age table; under 24 months length/BMI use recumbent length (WHO switches to standing height at 24 months). */
function growthAgeTable(ind,sex,lying){
  const A=window.WHO_GROWTH.age[sex];const t=A[ind];
  if(lying&&A.len24&&A.len24[ind]){const c=t.slice();c[24]=A.len24[ind];return c;}
  return t;
}
function growthTable(ind,sex,ageMonths){
  const D=window.WHO_GROWTH;if(!D)return null;
  if(GROWTH_IND[ind].x==='age')return {t:growthAgeTable(ind,sex,ageMonths!=null&&ageMonths<24),start:0,step:1};
  const key=ageMonths!=null&&ageMonths<24?'wfl':'wfh';const s=D.size[sex][key];return {t:s.lms,start:s.start,step:s.step,key};
}
function growthLmsFor(ind,sex,point){
  const def=GROWTH_IND[ind];
  if(def.x==='age'){if(point.age>def.max+0.5)return null;return growthLmsAt(growthTable(ind,sex,point.age).t,Math.min(point.age,def.max));}
  if(point.age>def.maxAge+0.5||!point.talla)return null;
  const tb=growthTable(ind,sex,point.age);return growthLmsAt(tb.t,(point.talla-tb.start)/tb.step);
}
function growthClassify(ind,z,age){
  if(z==null||!isFinite(z))return {txt:'—',cls:''};
  const r=(t,c)=>({txt:t,cls:c});
  if(ind==='hfa')return z<-3?r('Talla baja severa','b-red'):z<-2?r('Talla baja','b-amber'):z>3?r('Talla muy alta','b-amber'):r('Talla normal','b-green');
  if(ind==='wfa')return z<-3?r('Bajo peso severo','b-red'):z<-2?r('Bajo peso','b-amber'):z>2?r('Evaluar con P/T o IMC','b-amber'):r('Peso adecuado','b-green');
  if(ind==='hcfa')return z<-2?r('Microcefalia (< −2 DE)','b-red'):z>2?r('Macrocefalia (> +2 DE)','b-red'):r('Normal','b-green');
  if(ind==='bfa'&&age>=60)return z<-3?r('Delgadez severa','b-red'):z<-2?r('Delgadez','b-amber'):z>2?r('Obesidad','b-red'):z>1?r('Sobrepeso','b-amber'):r('IMC normal','b-green');
  // weight-for-length/height and BMI under 5 years
  return z<-3?r('Desnutrición aguda severa','b-red'):z<-2?r('Desnutrición aguda moderada','b-amber'):z>3?r('Obesidad','b-red'):z>2?r('Sobrepeso','b-amber'):z>1?r('Riesgo de sobrepeso','b-blue'):r('Normal','b-green');
}
/* Measurements of the patient from vital signs and HCU notes, one per date (latest wins). */
function growthPoints(pid){
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid));if(!p?.fnac)return [];
  const raw=[];
  (((DB.get('signosVitales')||{})[pid])||((DB.get('signosVitales')||{})[String(pid)])||[]).forEach(r=>{const v=r.valores||{};raw.push({fecha:r.fecha,hora:r.hora||'',peso:+v.peso||null,talla:+v.talla||null,perimetroCefalico:+v.perimetroCefalico||null,src:'Signos vitales'});});
  (((DB.get('notas')||{})[pid])||((DB.get('notas')||{})[String(pid)])||[]).forEach(n=>{if(n.peso||n.talla)raw.push({fecha:String(n.fecha||'').slice(0,10),hora:'',peso:+n.peso||null,talla:+n.talla||null,perimetroCefalico:+n.perimetroCefalico||null,src:'HCU'});});
  const byDate={};
  raw.filter(r=>r.fecha&&(r.peso||r.talla||r.perimetroCefalico)).sort((a,b)=>(a.fecha+a.hora).localeCompare(b.fecha+b.hora)).forEach(r=>{const d=byDate[r.fecha]||(byDate[r.fecha]={fecha:r.fecha});for(const k of ['peso','talla','perimetroCefalico'])if(r[k])d[k]=r[k];d.src=r.src;});
  return Object.values(byDate).map(d=>({...d,age:growthAgeMonths(p.fnac,d.fecha),imc:d.peso&&d.talla?Math.round(d.peso/((d.talla/100)**2)*10)/10:null})).filter(d=>d.age>=0&&d.age<=230).sort((a,b)=>a.fecha.localeCompare(b.fecha));
}
function growthEval(ind,sex,point){
  const v=point[GROWTH_IND[ind].field];if(!v)return null;
  const lms=growthLmsFor(ind,sex,point);if(!lms)return null;
  const z=growthZ(lms,v,GROWTH_IND[ind].restricted);return {z,p:growthPercentile(z),c:growthClassify(ind,z,point.age)};
}
function growthRanges(ind){
  if(ind==='wfh')return [['wfl','0–2 años (longitud)'],['wfh','2–5 años (talla)']];
  if(ind==='hcfa')return [['0-24','0–2 años'],['0-60','0–5 años']];
  if(ind==='wfa')return [['0-24','0–2 años'],['24-60','2–5 años'],['0-60','0–5 años'],['60-120','5–10 años']];
  return [['0-24','0–2 años'],['24-60','2–5 años'],['0-60','0–5 años'],['60-228','5–19 años']];
}
function growthDefaultRange(ind,age,firstAge){
  const rs=growthRanges(ind).map(r=>r[0]);
  if(ind==='wfh')return age<24?'wfl':'wfh';
  if(age>24&&age<=60&&firstAge!=null&&firstAge<24&&rs.includes('0-60'))return '0-60';
  for(const r of rs){const [a,b]=r.split('-').map(Number);if(age>=a&&age<=b)return r;}
  return rs[rs.length-1];
}
/* ---------- SVG chart ---------- */
function growthChartSvg(ind,sex,range,mode,points,opts={}){
  const D=window.WHO_GROWTH,def=GROWTH_IND[ind];
  const W=opts.width||820,H=opts.height||470,ml=52,mr=54,mt=16,mb=44,pw=W-ml-mr,ph=H-mt-mb;
  let xs=[],x0,x1,xlabel,curveAt,pointX;
  if(ind==='wfh'){
    const s=D.size[sex][range];x0=s.start;x1=s.start+s.step*(s.lms.length-1);xlabel=range==='wfl'?'Longitud (cm)':'Talla (cm)';
    for(let i=0;i<s.lms.length;i++)xs.push([s.start+i*s.step,s.lms[i]]);
    pointX=p=>p.talla;points=points.filter(p=>p.talla&&p.peso&&(range==='wfl'?p.age<24:p.age>=24&&p.age<=60.5));
  }else{
    [x0,x1]=range.split('-').map(Number);const t=growthAgeTable(ind,sex,x1<=24);x1=Math.min(x1,t.length-1);
    for(let m=x0;m<=x1;m++)xs.push([m,t[m]]);
    xlabel=x1>60?'Edad (años)':'Edad (meses)';pointX=p=>p.age;
    points=points.filter(p=>p[def.field]&&p.age>=x0-0.5&&p.age<=x1+0.5);
  }
  const lines=(mode==='z'?GROWTH_Z.map(z=>[z,z>0?'+'+z:String(z)]):GROWTH_PCT.map(([p,z])=>[z,'P'+p]));
  const ext=mode==='z'?3:1.8808;
  let y0=Infinity,y1=-Infinity;
  xs.forEach(([,l])=>{y0=Math.min(y0,growthValueAt(l,-ext));y1=Math.max(y1,growthValueAt(l,ext));});
  points.forEach(p=>{const v=p[def.field];y0=Math.min(y0,v);y1=Math.max(y1,v);});
  const span=y1-y0;y0=Math.max(0,y0-span*0.04);y1=y1+span*0.04;
  const X=x=>ml+(x-x0)/(x1-x0)*pw,Y=y=>mt+ph-(y-y0)/(y1-y0)*ph;
  const path=z=>xs.map(([x,l],i)=>(i?'L':'M')+X(x).toFixed(1)+' '+Y(growthValueAt(l,z)).toFixed(1)).join('');
  const band=(za,zb,color)=>`<path d="${path(za)}${xs.slice().reverse().map(([x,l])=>'L'+X(x).toFixed(1)+' '+Y(growthValueAt(l,zb)).toFixed(1)).join('')}Z" fill="${color}"/>`;
  const sexColor=sex==='m'?'#1d6fb8':'#c2417a';
  let g='';
  // bands: normal (green), alert (yellow), outside drawn by background
  if(mode==='z'){g+=band(-3,-2,'#fde2e2')+band(-2,-1,'#fff4c2')+band(-1,1,'#dcf3e4')+band(1,2,'#fff4c2')+band(2,3,'#fde2e2');}
  else{g+=band(-1.8808,-1.0364,'#fff4c2')+band(-1.0364,1.0364,'#dcf3e4')+band(1.0364,1.8808,'#fff4c2');}
  // grid
  const yStep=growthNiceStep((y1-y0)/8),xStep=ind==='wfh'?5:(x1-x0)>60?12:(x1-x0)>24?6:2;
  for(let v=Math.ceil(y0/yStep)*yStep;v<=y1;v+=yStep)g+=`<line x1="${ml}" x2="${ml+pw}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e5e7eb"/><text x="${ml-6}" y="${Y(v)+4}" text-anchor="end" font-size="11" fill="#475569">${+v.toFixed(1)}</text>`;
  for(let v=Math.ceil(x0/xStep)*xStep;v<=x1;v+=xStep){const lbl=ind!=='wfh'&&x1>60?(v/12).toFixed(v%12?1:0):v;g+=`<line y1="${mt}" y2="${mt+ph}" x1="${X(v)}" x2="${X(v)}" stroke="#e5e7eb"/><text y="${mt+ph+16}" x="${X(v)}" text-anchor="middle" font-size="11" fill="#475569">${lbl}</text>`;}
  // reference curves
  lines.forEach(([z,lbl])=>{const main=z===0;const red=mode==='z'&&Math.abs(z)>=2,amber=mode==='z'&&Math.abs(z)===1;
    g+=`<path d="${path(z)}" fill="none" stroke="${main?'#15803d':red?(Math.abs(z)===3?'#111827':'#dc2626'):amber?'#ca8a04':'#64748b'}" stroke-width="${main?2.2:1.3}"${mode==='pct'&&!main?' stroke-dasharray="0"':''}/>`;
    const last=xs[xs.length-1];g+=`<text x="${ml+pw+4}" y="${Y(growthValueAt(last[1],z))+4}" font-size="11" font-weight="600" fill="${main?'#15803d':'#334155'}">${lbl}</text>`;});
  // patient
  if(points.length){
    g+=`<path d="${points.map((p,i)=>(i?'L':'M')+X(pointX(p)).toFixed(1)+' '+Y(p[def.field]).toFixed(1)).join('')}" fill="none" stroke="${sexColor}" stroke-width="2"/>`;
    points.forEach(p=>{const e=growthEval(ind,sex,p);g+=`<circle cx="${X(pointX(p)).toFixed(1)}" cy="${Y(p[def.field]).toFixed(1)}" r="4.5" fill="${sexColor}" stroke="#fff" stroke-width="1.5"><title>${fmtDate(p.fecha)} · ${growthAgeText(p.age)} · ${p[def.field]} ${def.unit}${e?` · P${e.p.toFixed(0)} · z ${e.z.toFixed(2)} · ${e.c.txt}`:''}</title></circle>`;});
  }
  g+=`<rect x="${ml}" y="${mt}" width="${pw}" height="${ph}" fill="none" stroke="#94a3b8"/>`;
  g+=`<text x="${ml+pw/2}" y="${H-6}" text-anchor="middle" font-size="12" fill="#1e293b">${xlabel}</text><text transform="translate(13 ${mt+ph/2}) rotate(-90)" text-anchor="middle" font-size="12" fill="#1e293b">${def.label.split(' para ')[0]} (${def.unit})</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(def.label)} · ${sex==='m'?'niños':'niñas'} · OMS" style="max-width:${W}px;font-family:Inter,Arial,sans-serif;background:#fff">${g}</svg>`;
}
function growthNiceStep(raw){const p=Math.pow(10,Math.floor(Math.log10(raw)));const n=raw/p;return (n<1.5?1:n<3?2:n<7?5:10)*p;}
/* ---------- panel ---------- */
function growthPanelHtml(pid){return `<div id="growth-panel" data-pid="${pid}"><p class="text-muted">Cargando curvas de crecimiento OMS…</p></div>`;}
async function growthRender(pid){
  const box=document.getElementById('growth-panel');if(!box)return;
  try{await growthLoad();}catch(e){box.innerHTML=`<div class="alert alert-w">${esc(e.message)}</div>`;return;}
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};
  if(!p.fnac){box.innerHTML='<div class="alert alert-w"><i class="ti ti-alert-triangle"></i><span>Registra la <b>fecha de nacimiento</b> del paciente (botón Editar) para calcular las curvas de crecimiento.</span></div>';return;}
  if(growthState.pid!==pid)growthState={pid,ind:null,mode:'pct',range:null,sex:growthSex(p)};
  const sex=growthState.sex;
  const ageNow=growthAgeMonths(p.fnac,new Date().toISOString().slice(0,10));
  const pts=growthPoints(pid);
  if(!growthState.ind)growthState.ind=ageNow<=60?'wfa':'bfa';
  const ind=growthState.ind;
  if(!growthState.range||!growthRanges(ind).some(r=>r[0]===growthState.range))growthState.range=growthDefaultRange(ind,pts.length?pts[pts.length-1].age:ageNow,pts.length?pts[0].age:null);
  const canAdd=hasPerm('hce');
  const sexPicker=`<div class="growth-seg" role="group" aria-label="Sexo">${[['m','Niño'],['f','Niña']].map(([k,l])=>`<button type="button" class="${sex===k?'on':''}" onclick="growthSet('sex','${k}')">${l}</button>`).join('')}</div>`;
  if(!sex){box.innerHTML=`<div class="alert alert-w"><span>El sexo del paciente no está registrado como masculino o femenino. Elige la curva:</span> ${sexPicker}</div>`;return;}
  const last=pts[pts.length-1];
  const summary=last?Object.keys(GROWTH_IND).map(k=>{const e=growthEval(k,sex,last);return e?`<div class="growth-kpi"><div class="text-xs text-muted">${GROWTH_IND[k].short} · ${esc(GROWTH_IND[k].label)}</div><div class="fw7">${(k==='wfh'?last.peso:last[GROWTH_IND[k].field])} ${GROWTH_IND[k].unit} · P${e.p<1?'<1':e.p>99?'>99':e.p.toFixed(0)} · z ${e.z>0?'+':''}${e.z.toFixed(2)}</div><span class="badge ${e.c.cls}">${esc(e.c.txt)}</span></div>`:'';}).join(''):'';
  box.innerHTML=`<div class="growth-head">
    <div><div class="fw7">Curvas de crecimiento OMS · ${sex==='m'?'Niños':'Niñas'}</div><div class="text-xs text-muted">Edad actual: ${growthAgeText(ageNow)} · Fecha de nacimiento ${fmtDate(p.fnac)} · Patrones OMS 2006 (0–5 años) y referencia OMS 2007 (5–19 años), adoptados por el MSP del Ecuador.</div></div>
    <div class="flex gap8" style="flex-wrap:wrap">${canAdd?`<button class="btn-p btn-sm" onclick="cdVitalsForm(${pid})"><i class="ti ti-plus"></i> Registrar medición</button>`:''}<button class="btn-s btn-sm" onclick="growthPrint(${pid})"><i class="ti ti-printer"></i> Imprimir curva</button></div></div>
    ${last?`<div class="text-xs text-muted mt8">Última medición: ${fmtDate(last.fecha)} (${growthAgeText(last.age)})</div><div class="growth-kpis">${summary}</div>`:`<div class="alert alert-i mt8"><i class="ti ti-info-circle"></i><span>Aún no hay mediciones. Registra peso, talla y perímetro cefálico con "Registrar medición" (se guardan en Signos vitales). Puedes poner la fecha en que se tomaron para cargar controles anteriores.</span></div>`}
    <div class="growth-tools">
      <div class="growth-seg" role="group" aria-label="Indicador">${Object.entries(GROWTH_IND).filter(([k])=>!(k==='hcfa'&&ageNow>66&&!pts.some(x=>x.perimetroCefalico))).map(([k,d])=>`<button type="button" class="${ind===k?'on':''}" onclick="growthSet('ind','${k}')">${esc(d.label)}</button>`).join('')}</div>
      <div class="flex gap8" style="flex-wrap:wrap"><div class="growth-seg" role="group" aria-label="Rango">${growthRanges(ind).map(([k,l])=>`<button type="button" class="${growthState.range===k?'on':''}" onclick="growthSet('range','${k}')">${l}</button>`).join('')}</div>
      <div class="growth-seg" role="group" aria-label="Escala"><button type="button" class="${growthState.mode==='pct'?'on':''}" onclick="growthSet('mode','pct')">Percentiles</button><button type="button" class="${growthState.mode==='z'?'on':''}" onclick="growthSet('mode','z')">Puntuación Z</button></div>${sexPicker}</div>
    </div>
    <div class="growth-chart">${growthChartSvg(ind,sex,growthState.range,growthState.mode,pts)}</div>
    <div class="text-xs text-muted">${growthState.mode==='pct'?'Líneas: percentiles 3, 15, 50, 85 y 97. Verde: entre P15 y P85; amarillo: P3–P15 y P85–P97.':'Líneas: puntuación Z −3 a +3 (desviaciones estándar). Verde ±1; amarillo ±1 a ±2; rojo ±2 a ±3.'} Pasa el cursor sobre un punto para ver el detalle.</div>
    <h4 class="mt16 mb8" style="font-size:14px">Mediciones (${pts.length})</h4>
    ${growthTableHtml(sex,pts)}`;
}
function growthFmtEval(e){return e?`<div>P${e.p<1?'<1':e.p>99?'>99':e.p.toFixed(0)} · z ${e.z>0?'+':''}${e.z.toFixed(2)}</div><span class="badge ${e.c.cls}">${esc(e.c.txt)}</span>`:'<span class="text-muted">—</span>';}
function growthTableHtml(sex,pts){
  if(!pts.length)return '<p class="text-muted text-sm">Sin mediciones.</p>';
  return `<div class="tbl-wrap"><table class="tbl growth-tbl"><thead><tr><th>Fecha</th><th>Edad</th><th>Peso</th><th>Talla</th><th>IMC</th><th>PC</th><th>Peso/edad</th><th>Talla/edad</th><th>Peso/talla</th><th>IMC/edad</th><th>PC/edad</th></tr></thead><tbody>${pts.slice().reverse().map(p=>`<tr><td>${fmtDate(p.fecha)}</td><td>${growthAgeText(p.age)}</td><td>${p.peso?p.peso+' kg':'—'}</td><td>${p.talla?p.talla+' cm':'—'}</td><td>${p.imc??'—'}</td><td>${p.perimetroCefalico?p.perimetroCefalico+' cm':'—'}</td>${['wfa','hfa','wfh','bfa','hcfa'].map(k=>`<td class="text-xs">${growthFmtEval(growthEval(k,sex,p))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function growthSet(key,value){growthState[key]=value;if(key==='ind')growthState.range=null;growthRender(growthState.pid);}
async function growthPrint(pid){
  await growthLoad();
  const p=(DB.get('pacientes')||[]).find(x=>String(x.id)===String(pid))||{};const sex=growthState.sex||growthSex(p);if(!sex)return;
  const pts=growthPoints(pid);const ind=growthState.ind||'wfa';const def=GROWTH_IND[ind];
  const cfg=DB.get('config')||{};
  printDoc('Curva de crecimiento',`<div class="hdr"><img class="logo" src="${esc(cfg.logo||DEFAULT_LOGO)}"><div><div class="big">${esc(cfg.nombre||'Centro Médico')}</div><div class="muted">${esc(cfg.dir||'')}</div></div></div>
  <div class="rx-title">CURVA DE CRECIMIENTO · ${esc(def.label.toUpperCase())}</div>
  <div class="row"><div><div class="label">Paciente</div>${esc((p.nombres||'')+' '+(p.apellidos||''))}</div><div><div class="label">Cédula</div>${esc(p.cedula||'—')}</div><div><div class="label">Fecha de nacimiento</div>${fmtDate(p.fnac)}</div><div><div class="label">Sexo</div>${sex==='m'?'Masculino':'Femenino'}</div></div>
  ${growthChartSvg(ind,sex,growthState.range||growthDefaultRange(ind,pts.length?pts[pts.length-1].age:0),growthState.mode,pts,{width:760,height:430})}
  <p style="font-size:10px;color:#555">${growthState.mode==='pct'?'Percentiles 3, 15, 50, 85 y 97':'Puntuación Z −3 a +3'} · Patrones de crecimiento OMS 2006 (0–5 años) y referencia OMS 2007 (5–19 años), adoptados por el MSP del Ecuador.</p>
  <table width="100%" border="1" cellspacing="0" cellpadding="4" style="font-size:11px"><tr><th>Fecha</th><th>Edad</th><th>Peso</th><th>Talla</th><th>IMC</th><th>PC</th><th>${esc(def.short)} percentil</th><th>z</th><th>Clasificación</th></tr>
  ${pts.map(x=>{const e=growthEval(ind,sex,x);return `<tr><td>${fmtDate(x.fecha)}</td><td>${growthAgeText(x.age)}</td><td>${x.peso||'—'}</td><td>${x.talla||'—'}</td><td>${x.imc||'—'}</td><td>${x.perimetroCefalico||'—'}</td><td>${e?'P'+e.p.toFixed(0):'—'}</td><td>${e?e.z.toFixed(2):'—'}</td><td>${e?esc(e.c.txt):'—'}</td></tr>`;}).join('')}</table>`);
}
/* ---------- integration with the HCE ---------- */
function growthApplies(p){
  if(!p)return false;
  if(p.fnac){const age=growthAgeMonths(p.fnac,new Date().toISOString().slice(0,10));return age>=0&&age<=228;}
  return /pediatr|neonat/i.test((typeof patientEsps==='function'?patientEsps(p):[p.esp]).join(' '));
}
(function(){
  if(typeof renderHCE!=='function')return;
  const base=renderHCE;
  renderHCE=function(id){
    base(id);
    if(!hasPerm('hce'))return;
    const p=(DB.get('pacientes')||[]).find(x=>x.id===+id);if(!growthApplies(p))return;
    const tabs=document.querySelector('#hce-detail .tabs');const body=document.getElementById('t-evo')?.parentElement;if(!tabs||!body)return;
    const t=document.createElement('div');t.className='tab';t.dataset.panel='t-growth';t.innerHTML='<i class="ti ti-chart-bar"></i> Curvas de crecimiento';
    t.onclick=function(){swTab('t-growth',this);growthRender(+id);};
    const vit=tabs.querySelector('[data-panel="t-vitales"]');(vit?vit.nextSibling:null)?tabs.insertBefore(t,vit.nextSibling):tabs.appendChild(t);
    const d=document.createElement('div');d.id='t-growth';d.className='tab-panel';d.innerHTML=growthPanelHtml(+id);body.appendChild(d);
  };
  // After saving a measurement from the growth tab, come back to it.
  if(typeof cdVitalsSave==='function'){const save=cdVitalsSave;cdVitalsSave=async function(pid,recordId){growthState.reopen=!!document.getElementById('t-growth')?.classList.contains('active');try{return await save.apply(this,arguments);}finally{growthState.reopen=false;}};}
  if(typeof cdShowTab==='function'){const show=cdShowTab;cdShowTab=function(panel){if(panel==='t-vitales'&&growthState.reopen&&document.getElementById('t-growth')){const t=document.querySelector('#hce-detail .tab[data-panel="t-growth"]');if(t){swTab('t-growth',t);growthRender(growthState.pid);return;}}return show.apply(this,arguments);};}
})();
