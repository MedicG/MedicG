// Runs growth.js formulas in Node against WHO published reference values.
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'..');
const ctx={window:{},console,document:{getElementById:()=>null,querySelector:()=>null,head:{appendChild(){}}},esc:s=>String(s),fmtDate:s=>s,hasPerm:()=>true,DB:{get:k=>ctx.__db[k]},__db:{}};
ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(root+'/assets/js/growth-data.js','utf8'),ctx);
vm.runInContext(fs.readFileSync(root+'/assets/js/growth.js','utf8'),ctx);
const R=vm.runInContext('({growthEval,growthZ,growthLmsFor,growthValueAt,growthPercentile,growthPoints,growthClassify,growthChartSvg})',ctx);
const ok=(c,m)=>{if(!c){console.error('FAIL',m);process.exit(1);}};
const near=(a,b,t,m)=>ok(Math.abs(a-b)<=t,`${m}: ${a} vs ${b}`);
// WHO weight-for-age boys (kg): 12 months median 9.6, -2 SD 7.7, +2 SD 12.0 ; girls 24 months median 11.5
near(R.growthEval('wfa','m',{age:12,peso:9.6}).z,0,0.05,'boy 12 m 9.6 kg z≈0');
near(R.growthEval('wfa','m',{age:12,peso:7.7}).z,-2,0.06,'boy 12 m 7.7 kg z≈-2');
near(R.growthEval('wfa','m',{age:12,peso:12.0}).z,2,0.06,'boy 12 m 12.0 kg z≈+2');
near(R.growthEval('wfa','f',{age:24,peso:11.5}).z,0,0.05,'girl 24 m 11.5 kg z≈0');
// Length 0-2 (girls 24 m median 86.4 cm lying) vs height 2-5 (85.7 cm standing)
near(R.growthEval('hfa','f',{age:23.99,talla:86.4}).z,0,0.05,'girl just under 24 m, length');
near(R.growthEval('hfa','f',{age:24,talla:85.7}).z,0,0.05,'girl 24 m, height');
// Head circumference boys at birth median 34.5 cm; percentiles
near(R.growthEval('hcfa','m',{age:0,perimetroCefalico:34.46}).p,50,1,'HC boy birth P50');
near(R.growthPercentile(1.8808),97,0.1,'P97');near(R.growthPercentile(-1.0364),15,0.1,'P15');
// Weight-for-length (0-2): boy 75 cm median 9.5 kg ; weight-for-height (2-5): girl 100 cm median 15.2 kg, +2 SD 18.4
near(R.growthEval('wfh','m',{age:12,peso:9.5,talla:75}).z,0,0.1,'WFL boy 75 cm');
near(R.growthEval('wfh','f',{age:40,peso:15.2246,talla:100}).z,0,0.01,'WFH girl 100 cm');near(R.growthEval('wfh','f',{age:40,peso:18.4,talla:100}).z,2,0.05,'WFH girl 100 cm +2');
// BMI-for-age 5-19 (WHO 2007): uses references after 60 months; obesity > +2
const e=R.growthEval('bfa','m',{age:120,imc:24});ok(e&&e.z>2&&e.c.txt==='Obesidad','BMI boy 10 y 24 -> obesidad');
ok(R.growthEval('bfa','f',{age:200,imc:14}).c.txt.startsWith('Delgadez'),'BMI girl 16 y 14 -> delgadez');
// Restricted z beyond +3 (WHO): z grows linearly with the SD distance
const l=R.growthLmsFor('wfa','m',{age:12});const sd3=R.growthValueAt(l,3),sd2=R.growthValueAt(l,2);
near(R.growthZ(l,sd3+(sd3-sd2),true),4,1e-6,'restricted z = 4');
ok(R.growthEval('wfa','m',{age:121,peso:30})===null,'no weight-for-age after 10 years');
ok(R.growthEval('hcfa','m',{age:61,perimetroCefalico:50})===null,'no HC after 5 years');
ok(R.growthClassify('wfh',-3.2,30).txt==='Desnutrición aguda severa','wasting severe');
ok(R.growthClassify('wfh',1.5,30).txt==='Riesgo de sobrepeso','risk overweight');
ok(R.growthClassify('hfa',-2.5,30).txt==='Talla baja','stunting');
// Points from vital signs + HCU, one per date, BMI computed
ctx.__db={pacientes:[{id:7,fnac:'2024-01-15',genero:'Femenino'}],signosVitales:{7:[{fecha:'2025-01-15',valores:{peso:8.9,talla:74}},{fecha:'2024-07-15',valores:{peso:7.3}}]},notas:{7:[{fecha:'2024-07-15',talla:65.7}]}};
const pts=R.growthPoints(7);ok(pts.length===2&&pts[0].peso===7.3&&pts[0].talla===65.7&&Math.abs(pts[1].age-12)<0.1&&pts[1].imc===16.3,'points '+JSON.stringify(pts));
const svg=R.growthChartSvg('wfa','f','0-24','pct',pts);ok(svg.startsWith('<svg')&&(svg.match(/<circle/g)||[]).length===2&&svg.includes('P97'),'chart svg');
ok(R.growthChartSvg('bfa','m','60-228','z',[]).includes('+3'),'z chart 5-19');
console.log('PASS growth: WHO z-scores and percentiles (0-5 standards, 5-19 references, length/height switch, WFL/WFH, restricted z), classification, points and charts');
