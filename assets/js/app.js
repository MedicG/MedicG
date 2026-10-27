function doctorSpecialties(m){return [...new Set([m.esp,m.esp2,m.esp3,m.esp4].filter(Boolean))];}








// =========================================================







// DATABASE (SQLite via local API)







// =========================================================







const DEFAULT_LOGO = 'assets/medicg-logo.jpg';







const API = {







  base:(window.MEDICG_API_BASE || '').replace(/\/$/,''),







  requireBackend: window.MEDICG_REQUIRE_BACKEND !== false,







  token: localStorage.getItem('mg_token') || '',







  get missingBackend(){return !this.base && this.requireBackend && (location.hostname.endsWith('github.io') || location.protocol === 'file:');},







  async req(path, opts={}){







    if(this.missingBackend && path.startsWith('/api/')){







      throw new Error('Servidor de base de datos no configurado. Configura MEDICG_API_BASE en config.js.');







    }







    const headers = {'Content-Type':'application/json'};







    if(this.token) headers.Authorization = 'Bearer '+this.token;







    try{







      const res = await fetch(this.base+path,{...opts,headers:{...headers,...(opts.headers||{})}});







      const data = await res.json().catch(()=>({}));







      if(!res.ok) throw new Error(data.error || 'Error de servidor');







      return data;







    }catch(err){







      throw new Error(err.message || 'No se pudo conectar con el servidor');







    }







  },







  get(path){return this.req(path);},







  post(path, body){return this.req(path,{method:'POST',body:JSON.stringify(body||{})});}







};















function repairMojibakeText(){







  const fix=s=>fixMojibakeString(s);







  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);







  let node; while((node=walker.nextNode())) node.nodeValue=fix(node.nodeValue);







  document.querySelectorAll('input,textarea,option').forEach(el=>{







    if(el.placeholder) el.placeholder=fix(el.placeholder);







    if(el.value) el.value=fix(el.value);







    if(el.textContent) el.textContent=fix(el.textContent);







  });







}















function fixMojibakeString(s){
  if(typeof s!=='string') return s;
  const map=[["\u00e2\u20ac\u20ac", "\u2000"], ["\u00e2\u0080\u0080", "\u2000"], ["\u00e2\u20ac\u0081", "\u2001"], ["\u00e2\u0080\u0081", "\u2001"], ["\u00e2\u20ac\u201a", "\u2002"], ["\u00e2\u0080\u0082", "\u2002"], ["\u00e2\u20ac\u0192", "\u2003"], ["\u00e2\u0080\u0083", "\u2003"], ["\u00e2\u20ac\u201e", "\u2004"], ["\u00e2\u0080\u0084", "\u2004"], ["\u00e2\u20ac\u2026", "\u2005"], ["\u00e2\u0080\u0085", "\u2005"], ["\u00e2\u20ac\u2020", "\u2006"], ["\u00e2\u0080\u0086", "\u2006"], ["\u00e2\u20ac\u2021", "\u2007"], ["\u00e2\u0080\u0087", "\u2007"], ["\u00e2\u20ac\u02c6", "\u2008"], ["\u00e2\u0080\u0088", "\u2008"], ["\u00e2\u20ac\u2030", "\u2009"], ["\u00e2\u0080\u0089", "\u2009"], ["\u00e2\u20ac\u0160", "\u200a"], ["\u00e2\u0080\u008a", "\u200a"], ["\u00e2\u20ac\u2039", "\u200b"], ["\u00e2\u0080\u008b", "\u200b"], ["\u00e2\u20ac\u0152", "\u200c"], ["\u00e2\u0080\u008c", "\u200c"], ["\u00e2\u20ac\u008d", "\u200d"], ["\u00e2\u0080\u008d", "\u200d"], ["\u00e2\u20ac\u017d", "\u200e"], ["\u00e2\u0080\u008e", "\u200e"], ["\u00e2\u20ac\u008f", "\u200f"], ["\u00e2\u0080\u008f", "\u200f"], ["\u00e2\u20ac\u0090", "\u2010"], ["\u00e2\u0080\u0090", "\u2010"], ["\u00e2\u20ac\u2018", "\u2011"], ["\u00e2\u0080\u0091", "\u2011"], ["\u00e2\u20ac\u2019", "\u2012"], ["\u00e2\u0080\u0092", "\u2012"], ["\u00e2\u20ac\u201c", "\u2013"], ["\u00e2\u0080\u0093", "\u2013"], ["\u00e2\u20ac\u201d", "\u2014"], ["\u00e2\u0080\u0094", "\u2014"], ["\u00e2\u20ac\u2022", "\u2015"], ["\u00e2\u0080\u0095", "\u2015"], ["\u00e2\u20ac\u2013", "\u2016"], ["\u00e2\u0080\u0096", "\u2016"], ["\u00e2\u20ac\u2014", "\u2017"], ["\u00e2\u0080\u0097", "\u2017"], ["\u00e2\u20ac\u02dc", "\u2018"], ["\u00e2\u0080\u0098", "\u2018"], ["\u00e2\u20ac\u2122", "\u2019"], ["\u00e2\u0080\u0099", "\u2019"], ["\u00e2\u20ac\u0161", "\u201a"], ["\u00e2\u0080\u009a", "\u201a"], ["\u00e2\u20ac\u203a", "\u201b"], ["\u00e2\u0080\u009b", "\u201b"], ["\u00e2\u20ac\u0153", "\u201c"], ["\u00e2\u0080\u009c", "\u201c"], ["\u00e2\u20ac\u009d", "\u201d"], ["\u00e2\u0080\u009d", "\u201d"], ["\u00e2\u20ac\u017e", "\u201e"], ["\u00e2\u0080\u009e", "\u201e"], ["\u00e2\u20ac\u0178", "\u201f"], ["\u00e2\u0080\u009f", "\u201f"], ["\u00e2\u20ac\u00a0", "\u2020"], ["\u00e2\u0080\u00a0", "\u2020"], ["\u00e2\u20ac\u00a1", "\u2021"], ["\u00e2\u0080\u00a1", "\u2021"], ["\u00e2\u20ac\u00a2", "\u2022"], ["\u00e2\u0080\u00a2", "\u2022"], ["\u00e2\u20ac\u00a3", "\u2023"], ["\u00e2\u0080\u00a3", "\u2023"], ["\u00e2\u20ac\u00a4", "\u2024"], ["\u00e2\u0080\u00a4", "\u2024"], ["\u00e2\u20ac\u00a5", "\u2025"], ["\u00e2\u0080\u00a5", "\u2025"], ["\u00e2\u20ac\u00a6", "\u2026"], ["\u00e2\u0080\u00a6", "\u2026"], ["\u00e2\u20ac\u00a7", "\u2027"], ["\u00e2\u0080\u00a7", "\u2027"], ["\u00e2\u20ac\u00a8", "\u2028"], ["\u00e2\u0080\u00a8", "\u2028"], ["\u00e2\u20ac\u00a9", "\u2029"], ["\u00e2\u0080\u00a9", "\u2029"], ["\u00e2\u20ac\u00aa", "\u202a"], ["\u00e2\u0080\u00aa", "\u202a"], ["\u00e2\u20ac\u00ab", "\u202b"], ["\u00e2\u0080\u00ab", "\u202b"], ["\u00e2\u20ac\u00ac", "\u202c"], ["\u00e2\u0080\u00ac", "\u202c"], ["\u00e2\u20ac\u00ad", "\u202d"], ["\u00e2\u0080\u00ad", "\u202d"], ["\u00e2\u20ac\u00ae", "\u202e"], ["\u00e2\u0080\u00ae", "\u202e"], ["\u00e2\u20ac\u00af", "\u202f"], ["\u00e2\u0080\u00af", "\u202f"], ["\u00e2\u20ac\u00b0", "\u2030"], ["\u00e2\u0080\u00b0", "\u2030"], ["\u00e2\u20ac\u00b1", "\u2031"], ["\u00e2\u0080\u00b1", "\u2031"], ["\u00e2\u20ac\u00b2", "\u2032"], ["\u00e2\u0080\u00b2", "\u2032"], ["\u00e2\u20ac\u00b3", "\u2033"], ["\u00e2\u0080\u00b3", "\u2033"], ["\u00e2\u20ac\u00b4", "\u2034"], ["\u00e2\u0080\u00b4", "\u2034"], ["\u00e2\u20ac\u00b5", "\u2035"], ["\u00e2\u0080\u00b5", "\u2035"], ["\u00e2\u20ac\u00b6", "\u2036"], ["\u00e2\u0080\u00b6", "\u2036"], ["\u00e2\u20ac\u00b7", "\u2037"], ["\u00e2\u0080\u00b7", "\u2037"], ["\u00e2\u20ac\u00b8", "\u2038"], ["\u00e2\u0080\u00b8", "\u2038"], ["\u00e2\u20ac\u00b9", "\u2039"], ["\u00e2\u0080\u00b9", "\u2039"], ["\u00e2\u20ac\u00ba", "\u203a"], ["\u00e2\u0080\u00ba", "\u203a"], ["\u00e2\u20ac\u00bb", "\u203b"], ["\u00e2\u0080\u00bb", "\u203b"], ["\u00e2\u20ac\u00bc", "\u203c"], ["\u00e2\u0080\u00bc", "\u203c"], ["\u00e2\u20ac\u00bd", "\u203d"], ["\u00e2\u0080\u00bd", "\u203d"], ["\u00e2\u20ac\u00be", "\u203e"], ["\u00e2\u0080\u00be", "\u203e"], ["\u00e2\u20ac\u00bf", "\u203f"], ["\u00e2\u0080\u00bf", "\u203f"], ["\u00e2\u0081\u20ac", "\u2040"], ["\u00e2\u0081\u0080", "\u2040"], ["\u00e2\u0081\u0081", "\u2041"], ["\u00e2\u0081\u201a", "\u2042"], ["\u00e2\u0081\u0082", "\u2042"], ["\u00e2\u0081\u0192", "\u2043"], ["\u00e2\u0081\u0083", "\u2043"], ["\u00e2\u0081\u201e", "\u2044"], ["\u00e2\u0081\u0084", "\u2044"], ["\u00e2\u0081\u2026", "\u2045"], ["\u00e2\u0081\u0085", "\u2045"], ["\u00e2\u0081\u2020", "\u2046"], ["\u00e2\u0081\u0086", "\u2046"], ["\u00e2\u0081\u2021", "\u2047"], ["\u00e2\u0081\u0087", "\u2047"], ["\u00e2\u0081\u02c6", "\u2048"], ["\u00e2\u0081\u0088", "\u2048"], ["\u00e2\u0081\u2030", "\u2049"], ["\u00e2\u0081\u0089", "\u2049"], ["\u00e2\u0081\u0160", "\u204a"], ["\u00e2\u0081\u008a", "\u204a"], ["\u00e2\u0081\u2039", "\u204b"], ["\u00e2\u0081\u008b", "\u204b"], ["\u00e2\u0081\u0152", "\u204c"], ["\u00e2\u0081\u008c", "\u204c"], ["\u00e2\u0081\u008d", "\u204d"], ["\u00e2\u0081\u017d", "\u204e"], ["\u00e2\u0081\u008e", "\u204e"], ["\u00e2\u0081\u008f", "\u204f"], ["\u00e2\u0081\u0090", "\u2050"], ["\u00e2\u0081\u2018", "\u2051"], ["\u00e2\u0081\u0091", "\u2051"], ["\u00e2\u0081\u2019", "\u2052"], ["\u00e2\u0081\u0092", "\u2052"], ["\u00e2\u0081\u201c", "\u2053"], ["\u00e2\u0081\u0093", "\u2053"], ["\u00e2\u0081\u201d", "\u2054"], ["\u00e2\u0081\u0094", "\u2054"], ["\u00e2\u0081\u2022", "\u2055"], ["\u00e2\u0081\u0095", "\u2055"], ["\u00e2\u0081\u2013", "\u2056"], ["\u00e2\u0081\u0096", "\u2056"], ["\u00e2\u0081\u2014", "\u2057"], ["\u00e2\u0081\u0097", "\u2057"], ["\u00e2\u0081\u02dc", "\u2058"], ["\u00e2\u0081\u0098", "\u2058"], ["\u00e2\u0081\u2122", "\u2059"], ["\u00e2\u0081\u0099", "\u2059"], ["\u00e2\u0081\u0161", "\u205a"], ["\u00e2\u0081\u009a", "\u205a"], ["\u00e2\u0081\u203a", "\u205b"], ["\u00e2\u0081\u009b", "\u205b"], ["\u00e2\u0081\u0153", "\u205c"], ["\u00e2\u0081\u009c", "\u205c"], ["\u00e2\u0081\u009d", "\u205d"], ["\u00e2\u0081\u017e", "\u205e"], ["\u00e2\u0081\u009e", "\u205e"], ["\u00e2\u0081\u0178", "\u205f"], ["\u00e2\u0081\u009f", "\u205f"], ["\u00e2\u0081\u00a0", "\u2060"], ["\u00e2\u0081\u00a1", "\u2061"], ["\u00e2\u0081\u00a2", "\u2062"], ["\u00e2\u0081\u00a3", "\u2063"], ["\u00e2\u0081\u00a4", "\u2064"], ["\u00e2\u0081\u00a5", "\u2065"], ["\u00e2\u0081\u00a6", "\u2066"], ["\u00e2\u0081\u00a7", "\u2067"], ["\u00e2\u0081\u00a8", "\u2068"], ["\u00e2\u0081\u00a9", "\u2069"], ["\u00e2\u0081\u00aa", "\u206a"], ["\u00e2\u0081\u00ab", "\u206b"], ["\u00e2\u0081\u00ac", "\u206c"], ["\u00e2\u0081\u00ad", "\u206d"], ["\u00e2\u0081\u00ae", "\u206e"], ["\u00e2\u0081\u00af", "\u206f"], ["\u00e2\u201a\u00ac", "\u20ac"], ["\u00e2\u0082\u00ac", "\u20ac"], ["\u00c2\u00a0", "\u00a0"], ["\u00c2\u00a1", "\u00a1"], ["\u00c2\u00a2", "\u00a2"], ["\u00c2\u00a3", "\u00a3"], ["\u00c2\u00a4", "\u00a4"], ["\u00c2\u00a5", "\u00a5"], ["\u00c2\u00a6", "\u00a6"], ["\u00c2\u00a7", "\u00a7"], ["\u00c2\u00a8", "\u00a8"], ["\u00c2\u00a9", "\u00a9"], ["\u00c2\u00aa", "\u00aa"], ["\u00c2\u00ab", "\u00ab"], ["\u00c2\u00ac", "\u00ac"], ["\u00c2\u00ad", "\u00ad"], ["\u00c2\u00ae", "\u00ae"], ["\u00c2\u00af", "\u00af"], ["\u00c2\u00b0", "\u00b0"], ["\u00c2\u00b1", "\u00b1"], ["\u00c2\u00b2", "\u00b2"], ["\u00c2\u00b3", "\u00b3"], ["\u00c2\u00b4", "\u00b4"], ["\u00c2\u00b5", "\u00b5"], ["\u00c2\u00b6", "\u00b6"], ["\u00c2\u00b7", "\u00b7"], ["\u00c2\u00b8", "\u00b8"], ["\u00c2\u00b9", "\u00b9"], ["\u00c2\u00ba", "\u00ba"], ["\u00c2\u00bb", "\u00bb"], ["\u00c2\u00bc", "\u00bc"], ["\u00c2\u00bd", "\u00bd"], ["\u00c2\u00be", "\u00be"], ["\u00c2\u00bf", "\u00bf"], ["\u00c3\u20ac", "\u00c0"], ["\u00c3\u0080", "\u00c0"], ["\u00c3\u0081", "\u00c1"], ["\u00c3\u201a", "\u00c2"], ["\u00c3\u0082", "\u00c2"], ["\u00c3\u0192", "\u00c3"], ["\u00c3\u0083", "\u00c3"], ["\u00c3\u201e", "\u00c4"], ["\u00c3\u0084", "\u00c4"], ["\u00c3\u2026", "\u00c5"], ["\u00c3\u0085", "\u00c5"], ["\u00c3\u2020", "\u00c6"], ["\u00c3\u0086", "\u00c6"], ["\u00c3\u2021", "\u00c7"], ["\u00c3\u0087", "\u00c7"], ["\u00c3\u02c6", "\u00c8"], ["\u00c3\u0088", "\u00c8"], ["\u00c3\u2030", "\u00c9"], ["\u00c3\u0089", "\u00c9"], ["\u00c3\u0160", "\u00ca"], ["\u00c3\u008a", "\u00ca"], ["\u00c3\u2039", "\u00cb"], ["\u00c3\u008b", "\u00cb"], ["\u00c3\u0152", "\u00cc"], ["\u00c3\u008c", "\u00cc"], ["\u00c3\u008d", "\u00cd"], ["\u00c3\u017d", "\u00ce"], ["\u00c3\u008e", "\u00ce"], ["\u00c3\u008f", "\u00cf"], ["\u00c3\u0090", "\u00d0"], ["\u00c3\u2018", "\u00d1"], ["\u00c3\u0091", "\u00d1"], ["\u00c3\u2019", "\u00d2"], ["\u00c3\u0092", "\u00d2"], ["\u00c3\u201c", "\u00d3"], ["\u00c3\u0093", "\u00d3"], ["\u00c3\u201d", "\u00d4"], ["\u00c3\u0094", "\u00d4"], ["\u00c3\u2022", "\u00d5"], ["\u00c3\u0095", "\u00d5"], ["\u00c3\u2013", "\u00d6"], ["\u00c3\u0096", "\u00d6"], ["\u00c3\u2014", "\u00d7"], ["\u00c3\u0097", "\u00d7"], ["\u00c3\u02dc", "\u00d8"], ["\u00c3\u0098", "\u00d8"], ["\u00c3\u2122", "\u00d9"], ["\u00c3\u0099", "\u00d9"], ["\u00c3\u0161", "\u00da"], ["\u00c3\u009a", "\u00da"], ["\u00c3\u203a", "\u00db"], ["\u00c3\u009b", "\u00db"], ["\u00c3\u0153", "\u00dc"], ["\u00c3\u009c", "\u00dc"], ["\u00c3\u009d", "\u00dd"], ["\u00c3\u017e", "\u00de"], ["\u00c3\u009e", "\u00de"], ["\u00c3\u0178", "\u00df"], ["\u00c3\u009f", "\u00df"], ["\u00c3\u00a0", "\u00e0"], ["\u00c3\u00a1", "\u00e1"], ["\u00c3\u00a2", "\u00e2"], ["\u00c3\u00a3", "\u00e3"], ["\u00c3\u00a4", "\u00e4"], ["\u00c3\u00a5", "\u00e5"], ["\u00c3\u00a6", "\u00e6"], ["\u00c3\u00a7", "\u00e7"], ["\u00c3\u00a8", "\u00e8"], ["\u00c3\u00a9", "\u00e9"], ["\u00c3\u00aa", "\u00ea"], ["\u00c3\u00ab", "\u00eb"], ["\u00c3\u00ac", "\u00ec"], ["\u00c3\u00ad", "\u00ed"], ["\u00c3\u00ae", "\u00ee"], ["\u00c3\u00af", "\u00ef"], ["\u00c3\u00b0", "\u00f0"], ["\u00c3\u00b1", "\u00f1"], ["\u00c3\u00b2", "\u00f2"], ["\u00c3\u00b3", "\u00f3"], ["\u00c3\u00b4", "\u00f4"], ["\u00c3\u00b5", "\u00f5"], ["\u00c3\u00b6", "\u00f6"], ["\u00c3\u00b7", "\u00f7"], ["\u00c3\u00b8", "\u00f8"], ["\u00c3\u00b9", "\u00f9"], ["\u00c3\u00ba", "\u00fa"], ["\u00c3\u00bb", "\u00fb"], ["\u00c3\u00bc", "\u00fc"], ["\u00c3\u00bd", "\u00fd"], ["\u00c3\u00be", "\u00fe"], ["\u00c3\u00bf", "\u00ff"], ["\u00c4\u20ac", "\u0100"], ["\u00c4\u0080", "\u0100"], ["\u00c4\u0081", "\u0101"], ["\u00c4\u201a", "\u0102"], ["\u00c4\u0082", "\u0102"], ["\u00c4\u0192", "\u0103"], ["\u00c4\u0083", "\u0103"], ["\u00c4\u201e", "\u0104"], ["\u00c4\u0084", "\u0104"], ["\u00c4\u2026", "\u0105"], ["\u00c4\u0085", "\u0105"], ["\u00c4\u2020", "\u0106"], ["\u00c4\u0086", "\u0106"], ["\u00c4\u2021", "\u0107"], ["\u00c4\u0087", "\u0107"], ["\u00c4\u02c6", "\u0108"], ["\u00c4\u0088", "\u0108"], ["\u00c4\u2030", "\u0109"], ["\u00c4\u0089", "\u0109"], ["\u00c4\u0160", "\u010a"], ["\u00c4\u008a", "\u010a"], ["\u00c4\u2039", "\u010b"], ["\u00c4\u008b", "\u010b"], ["\u00c4\u0152", "\u010c"], ["\u00c4\u008c", "\u010c"], ["\u00c4\u008d", "\u010d"], ["\u00c4\u017d", "\u010e"], ["\u00c4\u008e", "\u010e"], ["\u00c4\u008f", "\u010f"], ["\u00c4\u0090", "\u0110"], ["\u00c4\u2018", "\u0111"], ["\u00c4\u0091", "\u0111"], ["\u00c4\u2019", "\u0112"], ["\u00c4\u0092", "\u0112"], ["\u00c4\u201c", "\u0113"], ["\u00c4\u0093", "\u0113"], ["\u00c4\u201d", "\u0114"], ["\u00c4\u0094", "\u0114"], ["\u00c4\u2022", "\u0115"], ["\u00c4\u0095", "\u0115"], ["\u00c4\u2013", "\u0116"], ["\u00c4\u0096", "\u0116"], ["\u00c4\u2014", "\u0117"], ["\u00c4\u0097", "\u0117"], ["\u00c4\u02dc", "\u0118"], ["\u00c4\u0098", "\u0118"], ["\u00c4\u2122", "\u0119"], ["\u00c4\u0099", "\u0119"], ["\u00c4\u0161", "\u011a"], ["\u00c4\u009a", "\u011a"], ["\u00c4\u203a", "\u011b"], ["\u00c4\u009b", "\u011b"], ["\u00c4\u0153", "\u011c"], ["\u00c4\u009c", "\u011c"], ["\u00c4\u009d", "\u011d"], ["\u00c4\u017e", "\u011e"], ["\u00c4\u009e", "\u011e"], ["\u00c4\u0178", "\u011f"], ["\u00c4\u009f", "\u011f"], ["\u00c4\u00a0", "\u0120"], ["\u00c4\u00a1", "\u0121"], ["\u00c4\u00a2", "\u0122"], ["\u00c4\u00a3", "\u0123"], ["\u00c4\u00a4", "\u0124"], ["\u00c4\u00a5", "\u0125"], ["\u00c4\u00a6", "\u0126"], ["\u00c4\u00a7", "\u0127"], ["\u00c4\u00a8", "\u0128"], ["\u00c4\u00a9", "\u0129"], ["\u00c4\u00aa", "\u012a"], ["\u00c4\u00ab", "\u012b"], ["\u00c4\u00ac", "\u012c"], ["\u00c4\u00ad", "\u012d"], ["\u00c4\u00ae", "\u012e"], ["\u00c4\u00af", "\u012f"], ["\u00c4\u00b0", "\u0130"], ["\u00c4\u00b1", "\u0131"], ["\u00c4\u00b2", "\u0132"], ["\u00c4\u00b3", "\u0133"], ["\u00c4\u00b4", "\u0134"], ["\u00c4\u00b5", "\u0135"], ["\u00c4\u00b6", "\u0136"], ["\u00c4\u00b7", "\u0137"], ["\u00c4\u00b8", "\u0138"], ["\u00c4\u00b9", "\u0139"], ["\u00c4\u00ba", "\u013a"], ["\u00c4\u00bb", "\u013b"], ["\u00c4\u00bc", "\u013c"], ["\u00c4\u00bd", "\u013d"], ["\u00c4\u00be", "\u013e"], ["\u00c4\u00bf", "\u013f"], ["\u00c5\u20ac", "\u0140"], ["\u00c5\u0080", "\u0140"], ["\u00c5\u0081", "\u0141"], ["\u00c5\u201a", "\u0142"], ["\u00c5\u0082", "\u0142"], ["\u00c5\u0192", "\u0143"], ["\u00c5\u0083", "\u0143"], ["\u00c5\u201e", "\u0144"], ["\u00c5\u0084", "\u0144"], ["\u00c5\u2026", "\u0145"], ["\u00c5\u0085", "\u0145"], ["\u00c5\u2020", "\u0146"], ["\u00c5\u0086", "\u0146"], ["\u00c5\u2021", "\u0147"], ["\u00c5\u0087", "\u0147"], ["\u00c5\u02c6", "\u0148"], ["\u00c5\u0088", "\u0148"], ["\u00c5\u2030", "\u0149"], ["\u00c5\u0089", "\u0149"], ["\u00c5\u0160", "\u014a"], ["\u00c5\u008a", "\u014a"], ["\u00c5\u2039", "\u014b"], ["\u00c5\u008b", "\u014b"], ["\u00c5\u0152", "\u014c"], ["\u00c5\u008c", "\u014c"], ["\u00c5\u008d", "\u014d"], ["\u00c5\u017d", "\u014e"], ["\u00c5\u008e", "\u014e"], ["\u00c5\u008f", "\u014f"], ["\u00c5\u0090", "\u0150"], ["\u00c5\u2018", "\u0151"], ["\u00c5\u0091", "\u0151"], ["\u00c5\u2019", "\u0152"], ["\u00c5\u0092", "\u0152"], ["\u00c5\u201c", "\u0153"], ["\u00c5\u0093", "\u0153"], ["\u00c5\u201d", "\u0154"], ["\u00c5\u0094", "\u0154"], ["\u00c5\u2022", "\u0155"], ["\u00c5\u0095", "\u0155"], ["\u00c5\u2013", "\u0156"], ["\u00c5\u0096", "\u0156"], ["\u00c5\u2014", "\u0157"], ["\u00c5\u0097", "\u0157"], ["\u00c5\u02dc", "\u0158"], ["\u00c5\u0098", "\u0158"], ["\u00c5\u2122", "\u0159"], ["\u00c5\u0099", "\u0159"], ["\u00c5\u0161", "\u015a"], ["\u00c5\u009a", "\u015a"], ["\u00c5\u203a", "\u015b"], ["\u00c5\u009b", "\u015b"], ["\u00c5\u0153", "\u015c"], ["\u00c5\u009c", "\u015c"], ["\u00c5\u009d", "\u015d"], ["\u00c5\u017e", "\u015e"], ["\u00c5\u009e", "\u015e"], ["\u00c5\u0178", "\u015f"], ["\u00c5\u009f", "\u015f"], ["\u00c5\u00a0", "\u0160"], ["\u00c5\u00a1", "\u0161"], ["\u00c5\u00a2", "\u0162"], ["\u00c5\u00a3", "\u0163"], ["\u00c5\u00a4", "\u0164"], ["\u00c5\u00a5", "\u0165"], ["\u00c5\u00a6", "\u0166"], ["\u00c5\u00a7", "\u0167"], ["\u00c5\u00a8", "\u0168"], ["\u00c5\u00a9", "\u0169"], ["\u00c5\u00aa", "\u016a"], ["\u00c5\u00ab", "\u016b"], ["\u00c5\u00ac", "\u016c"], ["\u00c5\u00ad", "\u016d"], ["\u00c5\u00ae", "\u016e"], ["\u00c5\u00af", "\u016f"], ["\u00c5\u00b0", "\u0170"], ["\u00c5\u00b1", "\u0171"], ["\u00c5\u00b2", "\u0172"], ["\u00c5\u00b3", "\u0173"], ["\u00c5\u00b4", "\u0174"], ["\u00c5\u00b5", "\u0175"], ["\u00c5\u00b6", "\u0176"], ["\u00c5\u00b7", "\u0177"], ["\u00c5\u00b8", "\u0178"], ["\u00c5\u00b9", "\u0179"], ["\u00c5\u00ba", "\u017a"], ["\u00c5\u00bb", "\u017b"], ["\u00c5\u00bc", "\u017c"], ["\u00c5\u00bd", "\u017d"], ["\u00c5\u00be", "\u017e"], ["\u00c5\u00bf", "\u017f"]];
  for(let pass=0;pass<3;pass++) for(const [bad,good] of map) s=s.split(bad).join(good);
  return s;
}















function normalizeData(value){







  if(typeof value==='string') return fixMojibakeString(value);







  if(Array.isArray(value)) return value.map(normalizeData);







  if(value && typeof value==='object'){







    Object.keys(value).forEach(k=>{value[k]=normalizeData(value[k]);});







  }







  return value;







}















const CIE10_SEED = [







  {code:'A09',desc:'Diarrea y gastroenteritis de presunto origen infeccioso',chapter:'Enfermedades infecciosas'},







  {code:'B34.9',desc:'Infección viral, no especificada',chapter:'Enfermedades infecciosas'},







  {code:'D64.9',desc:'Anemia, no especificada',chapter:'Sangre y órganos hematopoyéticos'},







  {code:'E03.9',desc:'Hipotiroidismo, no especificado',chapter:'Endocrino y metabólico'},







  {code:'E10',desc:'Diabetes mellitus insulinodependiente',chapter:'Endocrino y metabólico'},







  {code:'E11',desc:'Diabetes mellitus no insulinodependiente',chapter:'Endocrino y metabólico'},







  {code:'E66.9',desc:'Obesidad, no especificada',chapter:'Endocrino y metabólico'},







  {code:'F32.9',desc:'Episodio depresivo, no especificado',chapter:'Salud mental'},







  {code:'F41.1',desc:'Trastorno de ansiedad generalizada',chapter:'Salud mental'},







  {code:'G40.9',desc:'Epilepsia, no especificada',chapter:'Neurología'},







  {code:'G43.9',desc:'Migraña, no especificada',chapter:'Neurología'},







  {code:'H10.9',desc:'Conjuntivitis, no especificada',chapter:'Oftalmología'},







  {code:'H52.1',desc:'Miopía',chapter:'Oftalmología'},







  {code:'I10',desc:'Hipertensión esencial primaria',chapter:'Cardiología'},







  {code:'I20.9',desc:'Angina de pecho, no especificada',chapter:'Cardiología'},







  {code:'I25.1',desc:'Enfermedad aterosclerótica del corazón',chapter:'Cardiología'},







  {code:'I50.9',desc:'Insuficiencia cardíaca, no especificada',chapter:'Cardiología'},







  {code:'J00',desc:'Rinofaringitis aguda, resfriado común',chapter:'Respiratorio'},







  {code:'J02.9',desc:'Faringitis aguda, no especificada',chapter:'Respiratorio'},







  {code:'J03.9',desc:'Amigdalitis aguda, no especificada',chapter:'Respiratorio'},







  {code:'J06.9',desc:'Infección aguda de vías respiratorias superiores, no especificada',chapter:'Respiratorio'},







  {code:'J18.9',desc:'Neumonía, no especificada',chapter:'Respiratorio'},







  {code:'J30.4',desc:'Rinitis alérgica, no especificada',chapter:'Respiratorio'},







  {code:'J45.9',desc:'Asma, no especificada',chapter:'Respiratorio'},







  {code:'K21.9',desc:'Enfermedad por reflujo gastroesofágico sin esofagitis',chapter:'Gastroenterología'},







  {code:'K29.7',desc:'Gastritis, no especificada',chapter:'Gastroenterología'},







  {code:'K35.9',desc:'Apendicitis aguda, no especificada',chapter:'Gastroenterología'},







  {code:'K52.9',desc:'Gastroenteritis y colitis no infecciosas, no especificadas',chapter:'Gastroenterología'},







  {code:'L20.9',desc:'Dermatitis atópica, no especificada',chapter:'Dermatología'},







  {code:'L30.9',desc:'Dermatitis, no especificada',chapter:'Dermatología'},







  {code:'M25.5',desc:'Dolor en articulación',chapter:'Traumatología'},







  {code:'M54.5',desc:'Lumbago',chapter:'Traumatología'},







  {code:'N39.0',desc:'Infección de vías urinarias, sitio no especificado',chapter:'Urología'},







  {code:'O80',desc:'Parto único espontáneo',chapter:'Ginecología y obstetricia'},







  {code:'R05',desc:'Tos',chapter:'Síntomas y signos'},







  {code:'R10.4',desc:'Otros dolores abdominales y los no especificados',chapter:'Síntomas y signos'},







  {code:'R50.9',desc:'Fiebre, no especificada',chapter:'Síntomas y signos'},







  {code:'R51',desc:'Cefalea',chapter:'Síntomas y signos'},







  {code:'S00.9',desc:'Traumatismo superficial de la cabeza, parte no especificada',chapter:'Lesiones'},







  {code:'T14.9',desc:'Traumatismo, no especificado',chapter:'Lesiones'},







  {code:'Z00.0',desc:'Examen médico general',chapter:'Factores de contacto con servicios de salud'},







  {code:'Z34.9',desc:'Supervisión de embarazo normal, no especificado',chapter:'Ginecología y obstetricia'}







];















const MODULE_PERMS = [







  {id:'dashboard',label:'Dashboard'},







  {id:'agenda',label:'Agenda'},







  {id:'hce',label:'Historia clínica y evoluciones'},







  {id:'facturacion',label:'Facturación'},







  {id:'reportes',label:'Reportes'},







  {id:'pacientes',label:'Pacientes'},







  {id:'medicos',label:'Médicos'},







  {id:'especialidades',label:'Especialidades'},







  {id:'seguros',label:'Seguros'},







  {id:'quirofanos',label:'Quirófanos'},







  {id:'servicios',label:'Servicios'},







  {id:'examenes',label:'Exámenes y cotizador'},







  {id:'caja',label:'Caja / cobranza'},
  {id:'farmacia',label:'Farmacia e inventario'},
  {id:'certificados',label:'Certificados médicos (sin historia clínica)'},
  {id:'ordenes',label:'Órdenes de exámenes (sin historia clínica)'},







  {id:'config',label:'Configuración'}







];







function userRoleKey(u){return u?.rol==='admin'&&u?.superadminMedico?'medico_superadmin':u?.rol;}
const ROLE_LABELS={admin:'Dueño / Administrador',medico_superadmin:'Médico superadmin',recepcion:'Recepción',secretaria:'Secretaria',asistente:'Asistente clínico',medico:'Médico',paciente:'Paciente',pendiente:'Pendiente de permisos'};







const ROLE_DEFAULT_PERMS={







  admin:MODULE_PERMS.map(p=>p.id),







  recepcion:['dashboard','agenda','caja','servicios','examenes','certificados','ordenes'],







  secretaria:['dashboard','agenda','caja','servicios','examenes','certificados','ordenes'],







  asistente:['agenda','caja'],







  medico:['dashboard','agenda','hce'],







  paciente:[],







  pendiente:[]







};















// Scalable saves: send only the records that changed (server merges by id).
function saveIndex(list){
  if(!Array.isArray(list))return null;
  const index=new Map();
  for(const item of list){
    if(!item||typeof item!=='object'||item.id==null||item.id===''||typeof item.id==='object'||typeof item.id==='boolean')return null;
    const id=String(item.id);if(index.has(id))return null;index.set(id,item);
  }
  return index;
}
function buildSaveDelta(key,base,value){
  try{
    if(Array.isArray(value)){
      const before=saveIndex(base==null?[]:base),after=saveIndex(value);
      if(!before||!after)return null;
      const upsert=[],remove=[],baseOut={},positions={};
      value.forEach((item,idx)=>{const id=String(item.id);const old=before.get(id);if(!old)positions[id]=idx;if(!old||JSON.stringify(old)!==JSON.stringify(item)){upsert.push(item);baseOut[id]=old??null;}});
      for(const [id,old] of before){if(!after.has(id)){remove.push(id);baseOut[id]=old;}}
      return {type:'list',upsert,remove,base:baseOut,positions};
    }
    if(value&&typeof value==='object'){
      const before=(base&&typeof base==='object'&&!Array.isArray(base))?base:{};
      const set={},remove=[],baseOut={};
      Object.keys(value).forEach(k=>{if(!(k in before)||JSON.stringify(before[k])!==JSON.stringify(value[k])){set[k]=value[k];baseOut[k]=before[k]??null;}});
      Object.keys(before).forEach(k=>{if(!(k in value)){remove.push(k);baseOut[k]=before[k];}});
      return {type:'map',set,remove,base:baseOut};
    }
  }catch(e){}
  return null;
}
// Clinical file contents are downloaded on demand instead of with every page load.
const CLINICAL_FILE_DATA={};
function clinicalFileKey(pacId,id){return String(pacId)+':'+String(id);}
function stashClinicalFileData(map){
  if(!map||typeof map!=='object')return;
  Object.entries(map).forEach(([pid,list])=>{(Array.isArray(list)?list:[]).forEach(a=>{if(a&&a.dataUrl){CLINICAL_FILE_DATA[clinicalFileKey(pid,a.id)]=a.dataUrl;delete a.dataUrl;a.hasFile=true;}});});
}
async function clinicalFileData(pacId,a){
  if(!a)throw new Error('Archivo no encontrado');
  if(a.dataUrl)return a.dataUrl;
  const k=clinicalFileKey(pacId,a.id);
  if(CLINICAL_FILE_DATA[k])return CLINICAL_FILE_DATA[k];
  const res=await API.post('/api/clinical/file',{patientId:pacId,fileId:a.id});
  if(!res||!res.dataUrl)throw new Error('Archivo no disponible');
  CLINICAL_FILE_DATA[k]=res.dataUrl;
  return res.dataUrl;
}
const DB = {







  cache:{},







  saveTimers:{},







  get(k){return this.cache[k] ?? null;},







  confirmed:{},
  tail:Promise.resolve(),
  pending:0,
  failures:new Set(),
  failureDetails:{},
  set(k,v){
    const value=JSON.parse(JSON.stringify(normalizeData(v)));
    this.cache[k]=value;
    this.pending++;this.saveStatus();
    const task=this.tail.then(async()=>{
      try{
        if(!API.token) throw new Error('No hay sesión activa. Inicia sesión antes de guardar.');
        const base=this.confirmed[k]??null;
        const delta=k==='cie10'?null:buildSaveDelta(k,base,value);
        await API.post('/api/data',delta?{key:k,delta}:{key:k,value,baseValue:base});
        if(k==='archivosClinicos'){stashClinicalFileData(value);if(this.cache[k]!==value)stashClinicalFileData(this.cache[k]);}
        this.confirmed[k]=JSON.parse(JSON.stringify(value));
        this.failures.delete(k);
        delete this.failureDetails[k];
        return true;
      }catch(err){
        this.failures.add(k);
        this.failureDetails[k]=err.message;
        toast('No se guardó '+k+': '+err.message,'err');
        return false;
      }finally{this.pending--;this.saveStatus(true);}
    });
    this.tail=task;
    return task;
  },
  saveStatus(completed=false){
    clearTimeout(this.saveStatusTimer);
    let el=document.getElementById('save-status');
    if(!this.pending&&!this.failures.size&&!completed){if(el)el.hidden=true;return;}
    if(!el){el=document.createElement('div');el.id='save-status';el.setAttribute('role','status');el.style.cssText='position:fixed;bottom:12px;right:12px;z-index:9999;background:white;padding:10px;border:1px solid #ccc;border-radius:8px;max-width:380px';document.body.appendChild(el);}
    el.hidden=false;
    el.style.pointerEvents='none';
    el.textContent=this.pending?'Guardando información…':this.failures.size?'Hay cambios SIN GUARDAR. Revisa el error antes de salir.':'Información guardada';
    if(this.failures.size){el.textContent='Sin guardar: '+[...this.failures].map(k=>k+' — '+(this.failureDetails[k]||'Error de conexión')).join('; ');}
    el.style.color=this.failures.size?'#b83232':'#0d7a6b';
    if(!this.pending&&!this.failures.size)this.saveStatusTimer=setTimeout(()=>{el.hidden=true;},2500);
  },
  load(data){this.cache=normalizeData(data||{});this.confirmed=JSON.parse(JSON.stringify(this.cache));this.failures.clear();this.failureDetails={};this.saveStatus();},
  init(){
    // Initial UI defaults never create demonstration records or issue writes on login.
    const arrays=['users','especialidades','seguros','pacientes','medicos','citas','facturas','cajas','quirofanos','equipos','stockQx','servicios','examenes','cotizaciones'];
    arrays.forEach(k=>{if(this.cache[k]==null)this.cache[k]=[];});
    ['notas','recetas','archivosClinicos'].forEach(k=>{if(this.cache[k]==null)this.cache[k]={};});
    this.cache.config ??= {nombre:'Medic G'};
    this.cache.cie10 ??= CIE10_SEED;
    this.cache.nextIds ??= {};
  },
  nextId(k){const ids=this.get('nextIds');const n=ids[k]||1;ids[k]=n+1;this.set('nextIds',ids);return n;},







};















function now(){return new Date().toISOString();}







function today(){return new Date().toISOString().split('T')[0];}







function fmtDate(d){if(!d)return'—';const[y,mo,da]=d.split('-');const ms=['','Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];return`${da} ${ms[+mo]} ${y}`;}







function fmtMoney(n){return'$'+(+n||0).toFixed(2);}







function fmtBytes(bytes){const n=+bytes||0;if(n<1024)return n+' B';if(n<1048576)return(n/1024).toFixed(1)+' KB';return(n/1048576).toFixed(1)+' MB';}







function esc(value){return String(value??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));}







function defaultPermsForRole(role){return [...(ROLE_DEFAULT_PERMS[role]||ROLE_DEFAULT_PERMS.recepcion)];}







function cleanPermissions(perms,role){







  if(role==='admin') return defaultPermsForRole('admin');







  const allowed=MODULE_PERMS.map(p=>p.id).filter(p=>p!=='config');







  const base=Array.isArray(perms)&&perms.length?perms:defaultPermsForRole(role);







  const catalogPerms=['recepcion','secretaria'].includes(role)?['servicios','examenes','certificados','ordenes']:[];

  return [...new Set([...base,...catalogPerms].filter(p=>allowed.includes(p)))];







}







function userPerms(user=currentUser){return cleanPermissions(user?.permissions,user?.rol||'recepcion');}







function hasPerm(moduleId,user=currentUser){if(user?.rol==='medico'&&!['dashboard','agenda','hce','pacientes'].includes(moduleId))return false;return user?.rol==='admin'||userPerms(user).includes(moduleId);}







function canEditCatalog(moduleId){return ['admin','recepcion','secretaria'].includes(currentUser?.rol)&&hasPerm(moduleId);}

function firstAllowedModule(){return MODULE_PERMS.find(p=>!['certificados','ordenes'].includes(p.id)&&hasPerm(p.id))?.id||null;}







const MAX_CLINICAL_FILE_BYTES=8*1024*1024;







const CLINICAL_FILE_EXTS=['pdf','jpg','jpeg','png','webp','gif','txt','doc','docx','xls','xlsx'];







const CLINICAL_FILE_MIMES=['application/pdf','image/jpeg','image/png','image/webp','image/gif','text/plain','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];







function isAllowedClinicalFile(file){







  const ext=(file.name.split('.').pop()||'').toLowerCase();







  return CLINICAL_FILE_EXTS.includes(ext) || CLINICAL_FILE_MIMES.includes(file.type);







}







function patientAge(p){return p.fnac?calcEdad(p.fnac):(Number.isInteger(p.edadDeclarada)?p.edadDeclarada:'—');}
function syncPatientAge(){const date=document.getElementById('p-fnac').value;const input=document.getElementById('p-edad');input.disabled=!!date;if(date)input.value=calcEdad(date);document.getElementById('p-edad-help').textContent=date?'La edad se calcula con la fecha de nacimiento.':'Edad declarada por el paciente; no se inventará una fecha de nacimiento.';}
function calcEdad(fnac){if(!fnac)return'—';const diff=Date.now()-new Date(fnac).getTime();return Math.floor(diff/31557600000);}







function getPacName(id){const p=(DB.get('pacientes')||[]).find(x=>x.id===+id);return p?p.nombres+' '+p.apellidos:'—';}







function getMedName(id){const m=(DB.get('medicos')||[]).find(x=>x.id===+id);return m?m.nombre:'---';}







function normalizeLookup(value){return String(value||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'');}







function linkedDoctorForUser(user=currentUser){







  const meds=DB.get('medicos')||[];







  if(!user)return null;







  if(user.medicoId){const direct=meds.find(m=>String(m.id)===String(user.medicoId));if(direct)return direct;}







  const email=(user.email||'').trim().toLowerCase();







  if(email){const byEmail=meds.find(m=>(m.email||'').trim().toLowerCase()===email);if(byEmail)return byEmail;}







  const wanted=normalizeLookup(`${user.name||''} ${user.last||''}`);







  if(wanted){







    const byName=meds.find(m=>{const key=normalizeLookup(m.nombre||'');return key.includes(wanted)||wanted.includes(key);});







    if(byName)return byName;







  }







  return null;







}







function doctorProfileLabel(m){return m?`${m.nombre||'Medico'}${m.esp?' - '+m.esp:''}${m.email?' - '+m.email:''}`:'Sin perfil medico';}







function renderMedicoLinkOptions(selected=''){







  const meds=DB.get('medicos')||[];







  if(!meds.length)return '<option value="">Primero registra medicos en el modulo Medicos</option>';







  return '<option value="">Seleccionar perfil medico...</option>'+meds.map(m=>`<option value="${m.id}" ${String(m.id)===String(selected||'')?'selected':''}>${esc(doctorProfileLabel(m))}</option>`).join('');







}







function currentDoctorId(){const med=linkedDoctorForUser();return currentUser?.rol==='medico'&&med?+med.id:0;}







function getEspColor(name){const e=(DB.get('especialidades')||[]).find(x=>x.nombre===name);return e?e.color:'#5A5A6A';}















// =========================================================







// AUTH







// =========================================================







let currentUser = null;







let patientPortalData = null;







let publicOptions = {especialidades:[],medicos:[],servicios:[],config:{}};







const PUBLIC_HOURS=['07:00','07:30','08:00','08:30','09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','14:00','14:30','15:00','15:30','16:00','16:30','17:00'];







const PUBLIC_FALLBACK={







  config:{nombre:'Medic G',tel:'',wa:'',email:'',dir:'',color:'#1B4F8A',logo:DEFAULT_LOGO},







  especialidades:[







    {id:1,nombre:'Cardiología',color:'#1B4F8A',estado:'activo'},







    {id:2,nombre:'Pediatría',color:'#0D7A6B',estado:'activo'},







    {id:3,nombre:'Dermatología',color:'#C47A0A',estado:'activo'},







    {id:4,nombre:'Ginecología',color:'#2A7A3B',estado:'activo'},







  ],







  medicos:[],







  servicios:[]







};















async function initPublicLanding(){







  document.getElementById('pub-fecha').value=today();







  renderAvailableHourOptions('pub-hora', PUBLIC_HOURS.map(h=>({hora:h})));







  try{







    publicOptions=await API.get('/api/public/options');







  }catch(err){







    publicOptions=PUBLIC_FALLBACK;







  }







  publicOptions.config=publicOptions.config||{};







  const cfg=publicOptions.config;







  const brand=cfg.nombre||'Medic G';







  document.getElementById('landing-brand').textContent=brand;







  document.getElementById('pt-brand').textContent=brand;







  if(cfg.logo){







    document.querySelectorAll('.landing-logo img,.patient-logo').forEach(img=>{img.src=cfg.logo;});







  }







  if(cfg.color) applyPublicTheme(cfg.color);







  fillPublicSpecialties('pub');







  loadPublicAvailability('pub');







}















function applyPublicTheme(hex){







  document.documentElement.style.setProperty('--primary',hex);







  document.documentElement.style.setProperty('--primary-dk',darken(hex,40));







  document.documentElement.style.setProperty('--primary-lt',lighten(hex));







}















function fillPublicSpecialties(prefix){







  const sel=document.getElementById(`${prefix}-esp`);







  if(!sel)return;







  const esps=publicOptions.especialidades?.length?publicOptions.especialidades:PUBLIC_FALLBACK.especialidades;







  sel.innerHTML='<option value="">Seleccionar especialidad...</option>'+esps.map(e=>`<option value="${esc(e.nombre)}">${esc(e.nombre)}</option>`).join('');







  fillPublicDoctors(prefix);







}















function fillPublicDoctors(prefix){







  const esp=document.getElementById(`${prefix}-esp`)?.value||'';







  const sel=document.getElementById(`${prefix}-med`);







  if(!sel)return;







  const meds=(publicOptions.medicos||[]).filter(m=>!esp||doctorSpecialties(m).includes(esp));







  sel.innerHTML=meds.length







    ? '<option value="">Primer medico disponible</option>'+meds.map(m=>`<option value="${m.id}">${esc(m.nombre)}${m.horario?' - '+esc(m.horario):''}</option>`).join('')







    : '<option value="">Primer medico disponible</option>';







  sel.onchange=()=>loadPublicAvailability(prefix);







  loadPublicAvailability(prefix);







}















function hideInlineMsg(id){







  const el=document.getElementById(id);







  if(el) el.classList.add('hidden');







}















function renderAvailableHourOptions(selectId, slots, selected=''){







  const sel=document.getElementById(selectId);







  if(!sel)return;







  const list=(slots||[]).map(s=>typeof s==='string'?{hora:s}:s).filter(s=>s&&s.hora);







  sel.innerHTML=list.length







    ? list.map(s=>`<option value="${esc(s.hora)}" data-med="${s.med||''}" ${String(s.hora)===String(selected)?'selected':''}>${esc(s.hora)}</option>`).join('')







    : '<option value="">Sin horarios disponibles</option>';







}















async function loadPublicAvailability(prefix){







  const fecha=document.getElementById(`${prefix}-fecha`)?.value||today();







  const esp=document.getElementById(`${prefix}-esp`)?.value||'';







  const med=document.getElementById(`${prefix}-med`)?.value||'';







  const horaSel=document.getElementById(`${prefix}-hora`);







  const selected=horaSel?.value||'';







  if(!fecha||!horaSel)return;
  horaSel.dataset.requestKey='';







  if(!esp){







    renderAvailableHourOptions(`${prefix}-hora`, [], selected);







    return;







  }







  const requestKey=JSON.stringify([fecha,esp,med]);horaSel.dataset.requestKey=requestKey;horaSel.disabled=true;
  try{







    const qs=new URLSearchParams({fecha,esp});







    if(med) qs.set('med',med);







    const res=await API.get('/api/public/availability?'+qs.toString());







    if(horaSel.dataset.requestKey!==requestKey)return;
    renderAvailableHourOptions(`${prefix}-hora`, res.slots||[], selected);horaSel.disabled=false;







    if(!(res.slots||[]).length) showInlineMsg(`${prefix}-msg`,'No hay horarios disponibles para esa fecha. Escoge otro dia o medico.','w');







    else hideInlineMsg(`${prefix}-msg`);







  }catch(err){
    if(horaSel.dataset.requestKey!==requestKey)return;
    showInlineMsg(`${prefix}-msg`,'No se pudo verificar disponibilidad. Vuelve a seleccionar fecha o médico.','w');







    renderAvailableHourOptions(`${prefix}-hora`, [], selected);







  }







}















function showInlineMsg(id,msg,kind='d'){







  const el=document.getElementById(id);







  if(!el)return;







  el.className=`alert alert-${kind}`;







  const icon=el.querySelector('i');







  if(icon) icon.className=kind==='s'?'ti ti-check':(kind==='w'?'ti ti-alert-triangle':(kind==='i'?'ti ti-info-circle':'ti ti-alert-circle'));







  el.querySelector('span').textContent=msg;







}















async function bookPublicAppointment(){







  const payload={







    name:document.getElementById('pub-name').value.trim(),







    last:document.getElementById('pub-last').value.trim(),







    email:document.getElementById('pub-email').value.trim(),







    tel:document.getElementById('pub-tel').value.trim(),







    cedula:document.getElementById('pub-cedula').value.trim(),







    esp:document.getElementById('pub-esp').value,







    med:document.getElementById('pub-med').value,







    fecha:document.getElementById('pub-fecha').value,







    hora:document.getElementById('pub-hora').value,







    motivo:document.getElementById('pub-motivo').value.trim(),







  };







  if(!payload.hora){showInlineMsg('pub-msg','Selecciona un horario disponible.','d');return;}







  try{







    const res=await API.post('/api/public/appointment',payload);







    showInlineMsg('pub-msg',res.message||'Cita solicitada correctamente','s');







    ['pub-name','pub-last','pub-email','pub-tel','pub-cedula','pub-motivo'].forEach(id=>document.getElementById(id).value='');







    document.getElementById('pub-fecha').value=today();







    loadPublicAvailability('pub');







    toast('Cita enviada a la agenda del sistema','ok');







  }catch(err){







    showInlineMsg('pub-msg',err.message||'No se pudo solicitar la cita','d');







  }







}















function switchAuth(mode){







  document.getElementById('login-form').classList.remove('hidden');







  document.getElementById('register-form').classList.toggle('hidden', mode!=='register');







  document.getElementById('register-placeholder')?.classList.toggle('hidden', mode==='register');







  document.getElementById('btn-login')?.classList.toggle('active', mode==='login');







  document.getElementById('btn-register')?.classList.toggle('active', mode==='register');







  document.getElementById('auth-title').textContent = mode==='login'?'Iniciar sesión':'Registro de paciente';







  document.getElementById('auth-sub').textContent = mode==='login'?'Usa tu correo para entrar como paciente, médico, recepción o dueño.':'Crea tu portal de paciente con verificación por correo.';







}















async function doLogin(){







  const email = document.getElementById('l-email').value.trim();







  const pass = document.getElementById('l-pass').value;







  document.getElementById('resend-verification-btn')?.classList.add('hidden');







  try{







    const auth = await API.post('/api/login',{email,password:pass});







    API.token = auth.token;







    localStorage.setItem('mg_token',auth.token);







    if(auth.user?.rol==='paciente'){







      const portal = await API.get('/api/patient/portal');







      currentUser = portal.user || auth.user;







      patientPortalData = portal.portal;







      launchPatientPortal();







      return;







    }







    const loaded = await API.get('/api/data');







    DB.load(loaded.data);







    DB.init();







    currentUser = loaded.user || auth.user;







    launchApp();







  }catch(err){







    const msg=err.message||'Correo o contraseña incorrectos';







    const needsVerification=msg.toLowerCase().includes('verifica tu correo');







    showAuthErr('login',msg,!needsVerification);







    document.getElementById('resend-verification-btn')?.classList.toggle('hidden',!needsVerification);







  }







}







async function doRegister(){







  const name=document.getElementById('r-name').value.trim();







  const last=document.getElementById('r-last').value.trim();







  const email=document.getElementById('r-email').value.trim();







  const password=document.getElementById('r-pass').value;







  const password2=document.getElementById('r-pass2').value;







  if(password!==password2) return showAuthErr('reg','Las contraseñas no coinciden');







  try{







    const result=await API.post('/api/register',{







      name,last,email,password,







      cedula:document.getElementById('r-cedula').value.trim(),







      tel:document.getElementById('r-tel').value.trim(),







      origen:'Landing pública'







    });







    showAuthMsg('reg',result.message||'Cuenta creada. Revisa tu correo para verificarla.',result.emailSent?'s':'w',false);







    if(result.emailSent){







      ['r-name','r-last','r-email','r-pass','r-pass2','r-cedula','r-tel'].forEach(id=>document.getElementById(id).value='');







    }







  }catch(err){







    showAuthErr('reg',err.message||'No se pudo crear la cuenta');







  }







}







async function resendVerificationEmail(){







  const email=document.getElementById('l-email').value.trim();







  const btn=document.getElementById('resend-verification-btn');







  if(!email) return showAuthErr('login','Ingresa el correo registrado para reenviar la verificacion.',false);







  const original=btn?.innerHTML;







  if(btn){btn.disabled=true;btn.innerHTML='<i class="ti ti-loader"></i> Enviando correo...';}







  showAuthMsg('login','Enviando nuevo correo de verificacion...','i',false);







  try{







    const res=await API.post('/api/resend-verification',{email});







    showAuthMsg('login',res.message||'Si el correo esta registrado, enviaremos un nuevo enlace.',res.emailSent?'s':'w',false);







    if(res.emailSent) btn?.classList.add('hidden');







  }catch(err){







    showAuthErr('login',err.message||'No se pudo reenviar el correo. Revisa SMTP/Resend en Vercel.',false);







  }finally{







    if(btn){btn.disabled=false;btn.innerHTML=original;}







  }







}







function showAuthErr(type,msg,autoHide=true){







  showAuthMsg(type,msg,'d',autoHide);







}







function showAuthMsg(type,msg,kind='d',autoHide=true){







  const el=document.getElementById(type==='login'?'login-err':'reg-err');







  el.className=`alert alert-${kind} mb8`;







  const icon=el.querySelector('i');







  if(icon) icon.className=kind==='s'?'ti ti-check':(kind==='w'?'ti ti-alert-triangle':(kind==='i'?'ti ti-info-circle':'ti ti-alert-circle'));







  el.querySelector('span').textContent=msg;







  if(autoHide) setTimeout(()=>el.classList.add('hidden'),5000);







}















function doLogout(){







  API.post('/api/logout',{}).catch(()=>{});







  localStorage.removeItem('mg_token');







  API.token='';currentUser=null;DB.cache={};patientPortalData=null;







  document.getElementById('app-screen').style.display='none';







  document.getElementById('patient-screen').style.display='none';







  document.getElementById('auth-screen').style.display='block';







  toast('Sesión cerrada exitosamente','ok');







}















function launchApp(){







  document.getElementById('auth-screen').style.display='none';







  document.getElementById('patient-screen').style.display='none';







  document.getElementById('app-screen').style.display='block';







  document.getElementById('sb-uname').textContent=currentUser.name+' '+currentUser.last;







  document.getElementById('sb-urole').textContent=ROLE_LABELS[userRoleKey(currentUser)]||currentUser.rol;







  document.getElementById('sb-av').textContent=(currentUser.name[0]+currentUser.last[0]).toUpperCase();







  document.getElementById('tb-date').textContent=new Date().toLocaleDateString('es-EC',{weekday:'long',year:'numeric',month:'long',day:'numeric'});







  applyTheme(DB.get('config')?.color||'#1B4F8A');







  applyLogo(DB.get('config')?.logo||DEFAULT_LOGO);







  applyPermissionUI();







  const first=firstAllowedModule();







  if(first) showMod(first,document.querySelector(`.nav-item[data-module="${first}"]`));







  else showNoAccess();







}















function portalMedName(id){







  const med=(publicOptions.medicos||[]).find(m=>String(m.id)===String(id));







  return med?med.nombre:'Médico por confirmar';







}















function launchPatientPortal(){







  document.getElementById('auth-screen').style.display='none';







  document.getElementById('app-screen').style.display='none';







  document.getElementById('patient-screen').style.display='block';







  renderPatientPortal();







}















function renderPatientPortal(){







  const data=patientPortalData||{};







  const p=data.patient||{};







  const citas=data.appointments||[];







  const notas=data.notes||[];







  const recetas=data.prescriptions||[];







  const archivos=data.files||[];







  const facturas=data.invoices||[];







  const futuras=citas.filter(c=>(!c.fecha||c.fecha>=today())&&citaBlocksSlot(c)).sort((a,b)=>(a.fecha+a.hora).localeCompare(b.fecha+b.hora));







  const iniciales=((p.nombres||currentUser?.name||'P')[0]+(p.apellidos||currentUser?.last||'G')[0]).toUpperCase();







  document.getElementById('patient-content').innerHTML=`<button class="btn btn-primary" onclick="showTelehealth()">Mis consultas online</button>







    <section class="patient-hero">







      <div class="av lg">${iniciales}</div>







      <div style="flex:1;">







        <div class="fw7" style="font-size:20px;">${esc(p.nombres||currentUser?.name||'Paciente')} ${esc(p.apellidos||currentUser?.last||'')}</div>







        <div class="text-sm text-muted">Historia #HCE-${String(p.id||0).padStart(4,'0')} · ${esc(p.email||currentUser?.email||'')}</div>







      </div>







      <span class="badge b-green">Portal activo</span>







    </section>















    <div class="stats-row">







      <div class="stat-box"><div class="stat-lbl">Citas registradas</div><div class="stat-val">${citas.length}</div><div class="stat-sub">Incluye solicitudes web</div></div>







      <div class="stat-box"><div class="stat-lbl">Notas clínicas</div><div class="stat-val">${notas.length}</div><div class="stat-sub">Historia y evoluciones</div></div>







      <div class="stat-box"><div class="stat-lbl">Resultados / estudios</div><div class="stat-val">${archivos.length}</div><div class="stat-sub">Laboratorio, imagen y otros</div></div>







      <div class="stat-box"><div class="stat-lbl">Recetas</div><div class="stat-val">${recetas.length}</div><div class="stat-sub">Indicaciones médicas</div></div>







    </div>















    <div class="patient-grid">







      <div class="card">







        <div class="card-hdr"><i class="ti ti-calendar-event" style="color:var(--primary);font-size:18px;"></i><span class="card-title">Mis citas</span></div>







        <div class="card-body">







          <div class="portal-list">







            ${futuras.length?futuras.map(c=>`







              <div class="portal-item">







                <div class="portal-item-head"><i class="ti ti-calendar"></i><b>${fmtDate(c.fecha)} · ${esc(c.hora||'')}</b><span class="badge ${c.estado==='Confirmada'?'b-green':'b-amber'}" style="margin-left:auto;">${esc(c.estado||'Pendiente')}</span></div>







                <div class="text-sm">${esc(c.esp||'Especialidad')} · ${esc(portalMedName(c.med))}</div>







                <div class="text-xs text-muted">${esc(c.motivo||c.tipo||'Consulta medica')}</div>



                ${patientAppointmentCanChange(c)?`<div class="flex gap6 mt8"><button class="btn-s btn-xs" onclick="patientRescheduleAppointment(${c.id})"><i class="ti ti-calendar-time"></i> Posponer</button><button class="btn-d btn-xs" onclick="patientCancelAppointment(${c.id})"><i class="ti ti-calendar-x"></i> Cancelar</button></div>`:''}







              </div>`).join(''):'<div class="text-sm text-muted">No tienes citas próximas.</div>'}







          </div>







        </div>







      </div>















      <div class="card">







        <div class="card-hdr"><i class="ti ti-calendar-plus" style="color:var(--green);font-size:18px;"></i><span class="card-title">Solicitar nueva cita</span></div>







        <div class="card-body">







          <div class="form-row">







            <div class="field"><label class="field-lbl">Especialidad</label><select id="pt-esp" onchange="fillPublicDoctors('pt')"></select></div>







            <div class="field"><label class="field-lbl">Médico</label><select id="pt-med"></select></div>







          </div>







          <div class="form-row">







            <div class="field"><label class="field-lbl">Fecha</label><input id="pt-fecha" type="date" value="${today()}" onchange="loadPublicAvailability('pt')"/></div>



            <div class="field"><label class="field-lbl">Hora disponible</label><select id="pt-hora"></select></div>







          </div>







          <div class="field"><label class="field-lbl">Motivo</label><textarea id="pt-motivo" rows="2" placeholder="Describe brevemente el motivo"></textarea></div>







          <div id="pt-msg" class="alert alert-d hidden"><i class="ti ti-alert-circle"></i><span></span></div>







          <button class="btn-p w100" onclick="bookPatientAppointment()"><i class="ti ti-send"></i> Enviar solicitud</button>







        </div>







      </div>















      <div class="card">







        <div class="card-hdr"><i class="ti ti-user-heart" style="color:var(--primary);font-size:18px;"></i><span class="card-title">Mis datos</span></div>







        <div class="card-body">







          <div class="grid2">







            <div><span class="field-lbl">Cédula / ID</span><div>${esc(p.cedula||'—')}</div></div>







            <div><span class="field-lbl">Teléfono</span><div>${esc(p.tel||'—')}</div></div>







            <div><span class="field-lbl">Fecha nacimiento</span><div>${fmtDate(p.fnac)}</div></div>







            <div><span class="field-lbl">Seguro</span><div>${esc(p.seguro||'—')}</div></div>







          </div>







          ${p.alergias?`<div class="alert alert-d mt12"><i class="ti ti-alert-triangle"></i><span><b>Alergias:</b> ${esc(p.alergias)}</span></div>`:''}







        </div>







      </div>















      <div class="card">







        <div class="card-hdr"><i class="ti ti-notes-medical" style="color:var(--secondary);font-size:18px;"></i><span class="card-title">Historia clínica</span></div>







        <div class="card-body">







          <div class="portal-list">







            ${notas.length?notas.slice(0,6).map(n=>`







              <div class="portal-item">







                <div class="portal-item-head"><i class="ti ti-notes"></i><b>${fmtDate(n.fecha)}</b><span class="text-xs text-muted" style="margin-left:auto;">${esc(n.esp||'')}</span></div>







                ${(n.cie10Code||n.dx)?`<div class="text-sm"><b>${n.cie10Code?`CIE-10 ${esc(n.cie10Code)} · `:''}</b>${esc(n.dx||n.cie10Desc||'')}</div>`:''}







                ${n.plan?`<div class="text-xs text-muted">${esc(n.plan)}</div>`:''}







              </div>`).join(''):'<div class="text-sm text-muted">Aún no hay notas clínicas publicadas.</div>'}







          </div>







        </div>







      </div>















      <div class="card">







        <div class="card-hdr"><i class="ti ti-paperclip" style="color:var(--accent);font-size:18px;"></i><span class="card-title">Resultados, imágenes y estudios</span></div>







        <div class="card-body">







          <div class="portal-list">







            ${archivos.length?archivos.map(a=>`







              <div class="portal-item">







                <div class="portal-item-head"><i class="ti ${archivoIcon(a)}"></i><b>${esc(a.nombre)}</b><span class="text-xs text-muted" style="margin-left:auto;">${fmtDate(a.fecha)}</span></div>







                <div class="text-xs text-muted">${esc(a.tipo||'Documento')} · ${fmtBytes(a.size)}</div>







                ${a.descripcion?`<div class="text-sm">${esc(a.descripcion)}</div>`:''}







                ${(a.dataUrl||a.hasFile)?`<button class="btn-s btn-xs mt8" onclick="openPatientFile(${a.id})"><i class="ti ti-eye"></i> Abrir</button>`:''}







              </div>`).join(''):'<div class="text-sm text-muted">Sin resultados adjuntos todavía.</div>'}







          </div>







        </div>







      </div>















      <div class="card">







        <div class="card-hdr"><i class="ti ti-prescription" style="color:var(--green);font-size:18px;"></i><span class="card-title">Recetas y comprobantes</span></div>







        <div class="card-body">







          <div class="portal-list">







            ${recetas.length?recetas.slice(0,4).map(r=>`







              <div class="portal-item">







                <div class="portal-item-head"><i class="ti ti-prescription"></i><b>${fmtDate(r.fecha)}</b><span class="text-xs text-muted" style="margin-left:auto;">${esc(r.medico||'Médico')}</span></div>







                <div class="text-sm" style="white-space:pre-wrap;">${esc(r.medicamentos||'')}</div>







              </div>`).join(''):'<div class="text-sm text-muted">Sin recetas registradas.</div>'}







            ${facturas.length?facturas.slice(0,4).map(f=>`







              <div class="portal-item">







                <div class="portal-item-head"><i class="ti ti-receipt"></i><b>${esc(f.id)}</b><span class="fw6" style="margin-left:auto;color:var(--green);">${fmtMoney(f.total)}</span></div>







                <div class="text-xs text-muted">${fmtDate(f.fecha)} · ${esc(f.serv||'Servicio')}</div>







              </div>`).join(''):''}







          </div>







        </div>







      </div>







    </div>`;







  fillPublicSpecialties('pt');



  loadPublicAvailability('pt');



  const ptFecha=document.getElementById('pt-fecha');







  if(ptFecha) ptFecha.value=today();







}















async function bookPatientAppointment(){



  const payload={



    esp:document.getElementById('pt-esp').value,



    med:document.getElementById('pt-med').value,



    fecha:document.getElementById('pt-fecha').value,



    hora:document.getElementById('pt-hora').value,



    motivo:document.getElementById('pt-motivo').value.trim(),



  };



  if(!payload.hora){showInlineMsg('pt-msg','Selecciona un horario disponible.','d');return;}



  try{



    const res=await API.post('/api/patient/appointment',payload);



    patientPortalData=res.portal;



    renderPatientPortal();



    toast('Solicitud enviada a la agenda del sistema','ok');



  }catch(err){



    showInlineMsg('pt-msg',err.message||'No se pudo solicitar la cita','d');



  }



}







function patientAppointmentCanChange(c){



  return c && (!c.fecha || c.fecha>=today()) && citaBlocksSlot(c);



}







async function patientCancelAppointment(id){



  const cita=(patientPortalData?.appointments||[]).find(c=>c.id===id);



  if(!cita)return;



  confirmDelete('Deseas cancelar esta cita?',async ()=>{



    try{



      const res=await API.post('/api/patient/appointment-update',{action:'cancel',id});



      patientPortalData=res.portal;



      renderPatientPortal();



      toast('Cita cancelada correctamente','inf');



    }catch(err){



      toast(err.message||'No se pudo cancelar la cita','err');



    }



  });



}







async function patientRescheduleAppointment(id){



  const cita=(patientPortalData?.appointments||[]).find(c=>c.id===id);



  if(!cita)return;



  const fecha=prompt('Nueva fecha para la cita (AAAA-MM-DD):',cita.fecha||today());



  if(!fecha)return;



  const hora=prompt('Nueva hora disponible (ej. 09:00):',cita.hora||'09:00');



  if(!hora)return;



  try{



    const res=await API.post('/api/patient/appointment-update',{action:'reschedule',id,fecha,hora});



    patientPortalData=res.portal;



    renderPatientPortal();



    toast('Cita pospuesta correctamente','ok');



  }catch(err){



    toast(err.message||'No se pudo posponer la cita','err');



  }



}







async function openPatientFile(fileId){







  const file=(patientPortalData?.files||[]).find(a=>a.id===fileId);







  if(!file||!(file.dataUrl||file.hasFile))return;
  const w=window.open('','_blank');
  if(!w){toast('Permite ventanas emergentes para abrir el archivo','err');return;}
  let fileUrl;
  try{fileUrl=await clinicalFileData(patientPortalData?.patient?.id,file);}catch(e){w.close();toast(e.message,'err');return;}







  const content=(file.mime||'').startsWith('image/')







    ? `<img src="${fileUrl}" style="max-width:100%;height:auto;display:block;margin:0 auto;">`
    : `<iframe src="${fileUrl}" style="width:100%;height:96vh;border:0;"></iframe>`;







  w.document.write(`<!doctype html><html><head><title>${esc(file.nombre)}</title></head><body style="margin:0;background:#111;">${content}</body></html>`);







}















// =========================================================







// TOAST & MODAL







// =========================================================







function toast(msg,type='inf'){
  if(type==='ok'&&DB.pending){DB.tail.then(()=>{if(!DB.failures.size)toast(msg,type);});return;}







  const w=document.getElementById('toast-wrap');







  const t=document.createElement('div');







  t.className='toast '+(type==='ok'?'ok':type==='err'?'err':'inf');







  const icons={ok:'ti-check',err:'ti-alert-circle',inf:'ti-info-circle'};







  t.innerHTML=`<i class="ti ${icons[type]}" style="font-size:16px;"></i>${msg}`;







  w.appendChild(t);setTimeout(()=>t.remove(),3500);







}















function openM(id){document.getElementById(id).classList.add('open');}







function closeM(id){document.getElementById(id).classList.remove('open');}







document.querySelectorAll('.modal-bg').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('open');}));















function confirmDelete(msg,fn){







  document.getElementById('confirm-msg').textContent=msg;







  document.getElementById('confirm-btn').onclick=()=>{fn();closeM('m-confirm');};







  openM('m-confirm');







}















// =========================================================







// MODULE NAVIGATION







// =========================================================







function applyPermissionUI(){







  document.querySelectorAll('.nav-item[data-module]').forEach(item=>{







    item.style.display=hasPerm(item.dataset.module)?'flex':'none';







  });







  document.querySelectorAll('.sb-sep,.nav-sec').forEach(el=>{el.style.display='';});







  const citaBtn=document.getElementById('top-new-cita');







  if(citaBtn) citaBtn.style.display=hasPerm('agenda')&&currentUser?.rol!=='medico'?'flex':'none';
  document.querySelectorAll('[onclick="openWalkin()"],[onclick="openCitaModal()"],[onclick="openPacModal()"]').forEach(el=>el.style.display=currentUser?.rol==='medico'?'none':'');







}















function showNoAccess(){







  document.querySelectorAll('.module').forEach(m=>{m.classList.remove('active');});







  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));







  document.getElementById('mod-noaccess')?.classList.add('active');







  document.getElementById('tb-title').textContent='Cuenta pendiente';







}















function showMod(id,el){







  if(!id) return showNoAccess();







  if(!hasPerm(id)){







    toast('No tienes permiso para acceder a este módulo','err');







    const fallback=firstAllowedModule();







    if(fallback&&fallback!==id) return showMod(fallback,document.querySelector(`.nav-item[data-module="${fallback}"]`));







    if(!fallback) return showNoAccess();







    return;







  }







  document.querySelectorAll('.module').forEach(m=>{m.classList.remove('active');});







  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));







  const mod=document.getElementById('mod-'+id);







  if(mod) mod.classList.add('active');







  if(el) el.classList.add('active');







  const titles={dashboard:'Dashboard',agenda:'Agenda centralizada',hce:'Historia Clínica Electrónica',facturacion:'Facturación — SRI Ecuador',reportes:'Reportes y estadísticas',pacientes:'Gestión de pacientes',medicos:'Médicos y especialidades',especialidades:'Especialidades médicas',seguros:'Convenios con seguros',quirofanos:'Gestión quirúrgica',servicios:'Servicios del centro médico',examenes:'Exámenes y cotizador',caja:'Caja',config:'Configuración del sistema'};







  document.getElementById('tb-title').textContent=titles[id]||id;







  const renderers={dashboard:initDashboard,agenda:initAgenda,hce:()=>renderPatList(),facturacion:()=>{renderFacStats();renderFacs();},reportes:renderReportes,pacientes:renderPacs,medicos:renderMeds,especialidades:renderEsps,seguros:renderSegs,quirofanos:renderQuirofanos,servicios:renderServicios,examenes:renderExamenes,caja:renderCaja,config:loadConfig};







  if(renderers[id]) renderers[id]();







}















// =========================================================







// THEME / COLORS







// =========================================================







const PALETTES=[







  {name:'Azul médico',hex:'#1B4F8A'},{name:'Verde salud',hex:'#0D7A6B'},{name:'Violeta',hex:'#6B3FA0'},







  {name:'Rojo clínico',hex:'#B83232'},{name:'Naranja',hex:'#D4650A'},{name:'Índigo',hex:'#3741A8'},







  {name:'Verde oliva',hex:'#4A7A2A'},{name:'Gris profesional',hex:'#374151'},{name:'Cian',hex:'#0891B2'},







  {name:'Rosa oscuro',hex:'#9D174D'},{name:'Café',hex:'#78350F'},{name:'Negro',hex:'#111827'},







];















function renderColorSwatches(){







  const cur=DB.get('config')?.color||'#1B4F8A';







  document.getElementById('color-swatches').innerHTML=PALETTES.map(p=>`







    <div class="color-swatch ${p.hex===cur?'active':''}" style="background:${p.hex};" title="${p.name}" onclick="applyTheme('${p.hex}');updateSwatches('${p.hex}')"></div>







  `).join('');







  document.getElementById('custom-color').value=cur;







}















function updateSwatches(hex){







  document.querySelectorAll('.color-swatch').forEach(s=>s.classList.toggle('active',s.style.background===hex||rgbToHex(s.style.background)===hex));







  document.getElementById('theme-preview-box').style.background=hex;







}















function applyCustomColor(){applyTheme(document.getElementById('custom-color').value);updateSwatches(document.getElementById('custom-color').value);}















function applyTheme(hex){







  document.documentElement.style.setProperty('--primary',hex);







  document.documentElement.style.setProperty('--primary-dk',darken(hex,40));







  document.documentElement.style.setProperty('--primary-lt',lighten(hex));







  document.querySelectorAll('.sidebar').forEach(s=>s.style.background=hex);







  // Theme application is visual only; configuration is persisted by its Save button.
  const cfg=DB.get('config')||{};cfg.color=hex;DB.cache.config=cfg;







  if(document.getElementById('theme-preview-box')) document.getElementById('theme-preview-box').style.background=hex;







}















function applyLogo(src){







  const img=document.getElementById('sb-logo-img');







  const icon=document.querySelector('.sb-icon');







  if(!img||!icon)return;







  const logoSrc=src||DEFAULT_LOGO;







  if(logoSrc){img.src=logoSrc;img.classList.remove('hidden');icon.classList.add('hidden');}







  else{img.classList.add('hidden');icon.classList.remove('hidden');}







}















function previewLogo(event){







  const file=event.target.files?.[0];







  if(!file)return;







  const reader=new FileReader();







  reader.onload=()=>{







    const cfg=DB.get('config')||{};







    cfg.logo=reader.result;







    DB.cache.config=cfg;







    showLogoPreview(cfg.logo);







    applyLogo(cfg.logo);







  };







  reader.readAsDataURL(file);







}















function showLogoPreview(src){







  const box=document.getElementById('cfg-logo-preview');







  if(!box)return;







  const logoSrc=src||DEFAULT_LOGO;







  box.innerHTML=`<img src="${logoSrc}" alt="Logo" style="max-height:70px;max-width:180px;object-fit:contain;border:1px solid var(--gray-bd);border-radius:var(--radius);padding:6px;background:#fff;"/> ${src?'<button class="btn-s btn-xs" onclick="removeLogo()">Usar predeterminado</button>':'<span class="text-xs text-muted">Logo predeterminado activo</span>'}`;







}















function removeLogo(){







  const cfg=DB.get('config')||{};







  cfg.logo='';







  DB.cache.config=cfg;







  showLogoPreview('');







  applyLogo(DEFAULT_LOGO);







}















function darken(hex,amt){const r=Math.max(0,parseInt(hex.slice(1,3),16)-amt);const g=Math.max(0,parseInt(hex.slice(3,5),16)-amt);const b=Math.max(0,parseInt(hex.slice(5,7),16)-amt);return`#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;}







function lighten(hex){const r=parseInt(hex.slice(1,3),16);const g=parseInt(hex.slice(3,5),16);const b=parseInt(hex.slice(5,7),16);const lr=Math.min(255,Math.round(r+(255-r)*.88));const lg=Math.min(255,Math.round(g+(255-g)*.88));const lb=Math.min(255,Math.round(b+(255-b)*.88));return`#${lr.toString(16).padStart(2,'0')}${lg.toString(16).padStart(2,'0')}${lb.toString(16).padStart(2,'0')}`;}







function rgbToHex(rgb){if(!rgb||!rgb.startsWith('rgb'))return rgb;const m=rgb.match(/\d+/g);if(!m)return rgb;return'#'+m.map(x=>parseInt(x).toString(16).padStart(2,'0')).join('');}















// =========================================================







// DASHBOARD







// =========================================================







function initDashboard(){







  const pacs=DB.get('pacientes')||[];







  const citas=DB.get('citas')||[];







  const facs=DB.get('facturas')||[];







  const hoy=today();







  const citasHoy=citas.filter(c=>c.fecha===hoy);







  const citasOnline=citas.filter(c=>c.origen==='Landing pública'||c.origen==='Portal paciente'||c.estado==='Solicitada online');







  const totalHoy=facs.filter(f=>f.fecha===hoy).reduce((a,f)=>a+f.total,0);







  document.getElementById('dash-stats').innerHTML=`







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-calendar-check" style="font-size:13px;"></i> Citas hoy</div><div class="stat-val">${citasHoy.length}</div><div class="stat-sub up">+${Math.max(0,citasHoy.length-5)} vs ayer</div></div>







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-users" style="font-size:13px;"></i> Pacientes activos</div><div class="stat-val">${pacs.length}</div><div class="stat-sub up">Total registrados</div></div>







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-cash" style="font-size:13px;"></i> Facturado hoy</div><div class="stat-val">${fmtMoney(totalHoy)}</div><div class="stat-sub up">${facs.filter(f=>f.fecha===hoy).length} comprobantes</div></div>







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-world-www" style="font-size:13px;"></i> Citas web</div><div class="stat-val">${citasOnline.length}</div><div class="stat-sub up">Solicitadas desde landing/portal</div></div>







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-clock" style="font-size:13px;"></i> Pendientes</div><div class="stat-val">${citas.filter(c=>c.estado==='Pendiente'||c.estado==='Solicitada online').length}</div><div class="stat-sub dn">Por confirmar</div></div>







    <div class="stat-box"><div class="stat-lbl"><i class="ti ti-stethoscope" style="font-size:13px;"></i> Médicos</div><div class="stat-val">${(DB.get('medicos')||[]).length}</div><div class="stat-sub">Especialistas</div></div>`;















  let citasHtml='';







  if(!citasHoy.length) citasHtml='<div style="padding:20px;text-align:center;color:var(--text3);">Sin citas programadas hoy</div>';







  citasHoy.slice(0,6).forEach(c=>{







    const col=getEspColor(c.esp);







    citasHtml+=`<div style="display:flex;align-items:center;gap:8px;padding:10px 16px;border-bottom:1px solid var(--gray-bd);">







      <div style="width:4px;height:36px;border-radius:2px;background:${col};flex-shrink:0;"></div>







      <div style="flex:1;"><div class="fw5" style="font-size:13px;">${getPacName(c.pac)}</div><div class="text-xs text-muted">${c.esp} · ${getMedName(c.med)} · ${c.tipo}</div></div>







      <span class="badge" style="background:${col}22;color:${col};">${c.hora}</span>







    </div>`;







  });







  document.getElementById('dash-citas').innerHTML=citasHtml;















  const onlineActivity=citasOnline.slice().sort((a,b)=>String(b.createdAt||b.fecha||'').localeCompare(String(a.createdAt||a.fecha||''))).slice(0,4).map(c=>`







      <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--amber-lt);border-radius:var(--radius);">







        <i class="ti ti-bell-ringing" style="font-size:20px;color:var(--amber);"></i>







        <div><div class="fw5" style="font-size:13px;">Nueva cita web: ${getPacName(c.pac)}</div><div class="text-xs text-muted">${c.esp} · ${fmtDate(c.fecha)} ${c.hora} · ${c.estado}</div></div>







      </div>`).join('');







  document.getElementById('dash-activ').innerHTML=`







    <div style="display:flex;flex-direction:column;gap:10px;">







      ${onlineActivity}







      ${[{i:'ti-user-check',t:`${pacs.length} pacientes registrados`,s:'Total en el sistema',c:'var(--primary)'},







         {i:'ti-receipt',t:`${fmtMoney(facs.reduce((a,f)=>a+f.total,0))} facturado total`,s:'Todos los periodos',c:'var(--green)'},







         {i:'ti-calendar',t:`${citas.length} citas registradas`,s:'Historial completo',c:'var(--secondary)'},







         {i:'ti-shield-check',t:`${(DB.get('seguros')||[]).length} convenios activos`,s:'Seguros médicos',c:'var(--amber)'}].map(a=>`







      <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--gray-lt);border-radius:var(--radius);">







        <i class="ti ${a.i}" style="font-size:20px;color:${a.c};"></i>







        <div><div class="fw5" style="font-size:13px;">${a.t}</div><div class="text-xs text-muted">${a.s}</div></div>







      </div>`).join('')}







    </div>`;















  // Chart por especialidad







  const esps=DB.get('especialidades')||[];







  const facsByEsp={};







  facs.forEach(f=>{facsByEsp[f.esp]=(facsByEsp[f.esp]||0)+f.total;});







  const maxFac=Math.max(1,...Object.values(facsByEsp));







  document.getElementById('dash-chart').innerHTML=esps.map(e=>`







    <div style="margin-bottom:10px;">







      <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px;"><span>${e.nombre}</span><strong>${fmtMoney(facsByEsp[e.nombre]||0)}</strong></div>







      <div class="progress"><div class="prog-fill" style="width:${Math.round((facsByEsp[e.nombre]||0)/maxFac*100)}%;background:${e.color};"></div></div>







    </div>`).join('');















  const pacsByEsp={};







  pacs.forEach(p=>{pacsByEsp[p.esp]=(pacsByEsp[p.esp]||0)+1;});







  const maxPac=Math.max(1,...Object.values(pacsByEsp));







  document.getElementById('dash-pacesp').innerHTML=esps.map(e=>`







    <div style="margin-bottom:10px;">







      <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px;"><span>${e.nombre}</span><strong>${pacsByEsp[e.nombre]||0} pac.</strong></div>







      <div class="progress"><div class="prog-fill" style="width:${Math.round((pacsByEsp[e.nombre]||0)/maxPac*100)}%;background:${e.color};"></div></div>







    </div>`).join('');







}















// =========================================================







// AGENDA







// =========================================================







let weekOff=0, calDate=new Date(), filterEsps=new Set();















function initAgenda(){







  if(!hasPerm('agenda')) return;







  const esps=DB.get('especialidades')||[];







  filterEsps=new Set(esps.map(e=>e.nombre));







  renderWeek();renderMiniCal();renderAgFilter();







}















function getWeekStart(off){







  const d=new Date();d.setDate(d.getDate()+off*7);







  const day=d.getDay();d.setDate(d.getDate()-(day===0?6:day-1));







  return d;







}















function citaEstadoKey(value){

  return String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();

}



function citaBlocksSlot(cita){

  const state=citaEstadoKey(cita?.estado);

  return !['cancelada','cancelado','anulada','anulado','no asistio','no asistida'].includes(state);

}



function citaStatusClass(estado){

  const state=citaEstadoKey(estado);

  if(state==='confirmada') return 'b-green';

  if(state==='cancelada'||state==='anulada') return 'b-red';

  if(state==='pospuesta') return 'b-amber';

  return 'b-amber';

}



function citaConflict(citas,med,fecha,hora,ignoreId=0){

  return (citas||[]).find(c=>citaBlocksSlot(c)&&String(c.fecha)===String(fecha)&&String(c.hora)===String(hora)&&String(c.med)===String(med)&&String(c.id)!==String(ignoreId||0));

}



function availableLocalHours(med,fecha,ignoreId=0){

  const citas=DB.get('citas')||[];

  return PUBLIC_HOURS.filter(h=>!citaConflict(citas,med,fecha,h,ignoreId));

}



let citaAvailabilityRequest=0;
async function renderCitaHours(){
  const request=++citaAvailabilityRequest;
  const med=document.getElementById('c-med').value;
  const esp=document.getElementById('c-esp').value;
  const fecha=document.getElementById('c-fecha').value;
  const ignoreId=document.getElementById('c-edit-id').value||0;
  const select=document.getElementById('c-hora');
  const current=select.value;
  select.disabled=true;
  const msg=document.getElementById('c-slot-msg');
  if(!med||!esp||!fecha){renderAvailableHourOptions('c-hora',[]);msg.textContent='Selecciona especialidad, médico y fecha.';return;}
  msg.textContent='Consultando disponibilidad…';
  try{
    const result=await API.get('/api/public/availability?'+new URLSearchParams({med,esp,fecha,ignoreId}));
    if(request!==citaAvailabilityRequest)return;
    renderAvailableHourOptions('c-hora',result.slots||[],current);
    select.disabled=false;
    msg.textContent=result.slots?.length?'Horarios disponibles verificados.':'No hay horarios disponibles para este médico en esta fecha.';
  }catch(error){
    if(request!==citaAvailabilityRequest)return;
    renderAvailableHourOptions('c-hora',[]);msg.textContent='No se pudo verificar disponibilidad: '+error.message;
  }
}
function setCitaEstadoFromModal(estado){

  const sel=document.getElementById('c-estado');

  if(sel) sel.value=estado;

  saveCita();

}



function renderWeek(){







  const start=getWeekStart(weekOff);







  const days=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];







  const ms=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];







  const end=new Date(start);end.setDate(end.getDate()+6);







  document.getElementById('week-lbl').textContent=`${start.getDate()} ${ms[start.getMonth()]} — ${end.getDate()} ${ms[end.getMonth()]} ${end.getFullYear()}`;







  const hoy=today();







  let hdr='<div class="ag-hc"></div>';







  for(let i=0;i<7;i++){const d=new Date(start);d.setDate(d.getDate()+i);const ds=d.toISOString().split('T')[0];hdr+=`<div class="ag-hc ${ds===hoy?'today':''}">${days[i]}<br><strong>${d.getDate()}</strong></div>`;}







  document.getElementById('ag-hdr').innerHTML=hdr;







  const horas=PUBLIC_HOURS;







  const citas=DB.get('citas')||[];







  let body='';







  horas.forEach(h=>{







    body+=`<div class="ag-row"><div class="ag-time">${h}</div>`;







    for(let i=0;i<7;i++){







      const d=new Date(start);d.setDate(d.getDate()+i);







      const ds=d.toISOString().split('T')[0];







      const appts=citas.filter(c=>citaBlocksSlot(c)&&c.fecha===ds&&c.hora===h&&filterEsps.has(c.esp));







      let cell='';







      if(appts.length){







        appts.forEach(c=>{const col=getEspColor(c.esp);cell+=`<div class="ag-appt" style="background:${col}18;border-left:3px solid ${col};" onclick="editCita(${c.id})" title="${getPacName(c.pac)} — ${c.esp}"><div class="fw5" style="font-size:11px;">${getPacName(c.pac).split(' ')[0]} ${getPacName(c.pac).split(' ').slice(-1)}</div><div style="font-size:10px;color:var(--text2);">${c.esp} · ${c.estado}</div></div>`;});







      } else {







        cell=`<button class="ag-add" onclick="openNewCita('${ds}','${h}')"><i class="ti ti-plus" style="font-size:13px;"></i></button>`;







      }







      body+=`<div class="ag-cell">${cell}</div>`;







    }







    body+='</div>';







  });







  document.getElementById('ag-body').innerHTML=body;







}















function prevW(){weekOff--;renderWeek();}







function nextW(){weekOff++;renderWeek();}







function goToday(){weekOff=0;renderWeek();}















function openCitaModal(){
  if(currentUser?.rol==='medico')return;







  if(!hasPerm('agenda')){toast('No tienes permiso para crear citas','err');return;}







  openNewCita(today(),'08:00');







}















async function openNewCita(fecha,hora){
  if(currentUser?.rol==='medico')return;
  if(!hasPerm('agenda'))return;
  document.getElementById('c-edit-id').value='';
  document.getElementById('c-modalidad').value='presencial';
  document.getElementById('m-cita-title').textContent='Nueva cita';
  document.getElementById('c-fecha').value=fecha;
  document.getElementById('c-motivo').value='';
  document.getElementById('c-estado').value='Confirmada';
  fillCitaSelects();
  openM('m-cita');
  await renderCitaHours();
  const select=document.getElementById('c-hora');
  if([...select.options].some(o=>o.value===hora))select.value=hora;
}
async function editCita(id){
  if(currentUser?.rol==='medico')return;
  if(!hasPerm('agenda'))return;
  const c=(DB.get('citas')||[]).find(x=>x.id===+id);if(!c)return;
  document.getElementById('c-edit-id').value=c.id;
  document.getElementById('m-cita-title').textContent='Editar cita';
  fillCitaSelects();
  for(const [key,value] of Object.entries({modalidad:c.modalidad||'presencial',pac:c.pac,esp:c.esp,fecha:c.fecha,tipo:c.tipo||'Primera vez',estado:c.estado||'Pendiente',motivo:c.motivo||'',notif:c.notif||'Sin recordatorio'}))document.getElementById('c-'+key).value=value;
  fillMeds();document.getElementById('c-med').value=c.med;
  openM('m-cita');await renderCitaHours();
  const select=document.getElementById('c-hora');if([...select.options].some(o=>o.value===c.hora))select.value=c.hora;
}
function fillCitaSelects(){

  const pacs=DB.get('pacientes')||[];

  const esps=DB.get('especialidades')||[];

  document.getElementById('c-pac').innerHTML='<option value="">Seleccionar paciente...</option>'+pacs.map(p=>`<option value="${p.id}">${p.nombres} ${p.apellidos} - ${p.cedula||''}</option>`).join('');

  document.getElementById('c-esp').innerHTML='<option value="">Seleccionar...</option>'+esps.filter(e=>e.estado==='activo').map(e=>`<option>${e.nombre}</option>`).join('');

  if(!document.getElementById('c-fecha').value) document.getElementById('c-fecha').value=today();

  const espSel=document.getElementById('c-esp');

  if(!espSel.value && espSel.options.length>1) espSel.selectedIndex=1;

  fillMeds();

}



function fillMeds(){

  const esp=document.getElementById('c-esp').value;

  const meds=(DB.get('medicos')||[]).filter(m=>doctorSpecialties(m).includes(esp));

  document.getElementById('c-med').innerHTML=meds.length?meds.map(m=>`<option value="${m.id}">${m.nombre}</option>`).join(''):'<option value="">Sin medicos en esta especialidad</option>';

}



let savingCita=false;
async function saveCita(){
  if(!hasPerm('agenda')||savingCita)return;
  const payload={};
  for(const key of ['pac','esp','med','fecha','hora','tipo','motivo','estado','notif','modalidad'])payload[key]=document.getElementById('c-'+key).value;
  payload.id=+(document.getElementById('c-edit-id').value||0);
  const original=(DB.get('citas')||[]).find(c=>+c.id===payload.id);
  if(original&&['Cancelada','Atendida'].includes(payload.estado)){payload.hora=payload.hora||original.hora;}
  if(!payload.pac||!payload.esp||!payload.med||!payload.fecha||!payload.hora){toast('Completa paciente, especialidad, médico y horario disponible.','err');return;}
  if(document.getElementById('c-hora').disabled&&!['Cancelada','Atendida'].includes(payload.estado)){toast('Espera la verificación de disponibilidad.','err');return;}
  payload.base=(DB.get('citas')||[]).find(c=>+c.id===payload.id)||null;
  savingCita=true;
  const buttons=[...document.querySelectorAll('#m-cita .modal-footer button')];buttons.forEach(b=>b.disabled=true);
  try{
    await DB.tail;
    if(DB.failures.size)throw new Error('Hay información pendiente de guardar. Revisa los errores.');
    const response=await API.post('/api/appointments',payload);
    if(response.nextIds){DB.cache.nextIds=response.nextIds;DB.confirmed.nextIds=JSON.parse(JSON.stringify(response.nextIds));}
    DB.cache.citas=normalizeData(response.appointments);DB.confirmed.citas=JSON.parse(JSON.stringify(DB.cache.citas));
    closeM('m-cita');toast(payload.id?'Cita actualizada y guardada':'Cita registrada y guardada','ok');
    renderWeek();renderMiniCal();initDashboard();
  }catch(error){toast('No se guardó la cita: '+error.message,'err');}
  finally{savingCita=false;buttons.forEach(b=>b.disabled=false);}
}
function renderMiniCal(){







  const m=calDate.getMonth(),y=calDate.getFullYear();







  const ms2=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];







  document.getElementById('cal-ml').textContent=`${ms2[m]} ${y}`;







  const days=['L','M','M','J','V','S','D'];







  let g=days.map(d=>`<div class="cal-dh">${d}</div>`).join('');







  const first=new Date(y,m,1).getDay();const off=first===0?6:first-1;







  for(let i=0;i<off;i++) g+=`<div class="cal-d om">${new Date(y,m,0-off+i+1).getDate()}</div>`;







  const dim=new Date(y,m+1,0).getDate();







  const hoy=today();const citas=DB.get('citas')||[];







  for(let i=1;i<=dim;i++){







    const ds=`${y}-${String(m+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;







    const isToday=ds===hoy;







    const has=citas.some(c=>citaBlocksSlot(c)&&c.fecha===ds);







    g+=`<div class="cal-d ${isToday?'today':''} ${has&&!isToday?'has':''}">${i}</div>`;







  }







  document.getElementById('cal-grid').innerHTML=g;







}







function calPrev(){calDate.setMonth(calDate.getMonth()-1);renderMiniCal();}







function calNext(){calDate.setMonth(calDate.getMonth()+1);renderMiniCal();}















function renderAgFilter(){







  const esps=DB.get('especialidades')||[];







  document.getElementById('ag-filter').innerHTML=esps.map(e=>`







    <label style="display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer;margin-bottom:8px;">







      <input type="checkbox" ${filterEsps.has(e.nombre)?'checked':''} onchange="toggleEspFilter('${e.nombre}',this.checked)" style="width:auto;"/>







      <span style="width:9px;height:9px;background:${e.color};border-radius:50%;display:inline-block;flex-shrink:0;"></span>${e.nombre}







    </label>`).join('');







}







function toggleEspFilter(e,on){if(on)filterEsps.add(e);else filterEsps.delete(e);renderWeek();}















// =========================================================







// HCE







// =========================================================







let selPac=null;







let returnToCitaAfterPac=false;















function renderPatList(){







  if(!hasPerm('hce')) return;







  const q=document.getElementById('hce-q')?.value.toLowerCase()||'';







  const pacs=DB.get('pacientes')||[];







  const fil=pacs.filter(p=>(p.nombres+' '+p.apellidos+p.cedula+p.tel).toLowerCase().includes(q));







  document.getElementById('pat-list-wrap').innerHTML=fil.map(p=>`







    <div class="pat-item ${selPac===p.id?'sel':''}" onclick="selectPat(${p.id})">







      <div class="pat-name">${p.nombres} ${p.apellidos}</div>







      <div class="pat-meta">${patientAge(p)} años · ${p.esp}</div>







      <div class="pat-meta">${p.cedula}</div>







    </div>`).join('')||'<div style="padding:20px;text-align:center;color:var(--text3);">Sin resultados</div>';







}















function selectPat(id){if(!hasPerm('hce')){toast('No tienes permiso para ver expedientes clínicos','err');return;}selPac=id;renderPatList();renderHCE(id);}















function renderHCE(id){







  if(!hasPerm('hce')) return;







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+id);







  if(!p)return;







  const notas=(DB.get('notas')||{})[id]||[];







  const archivos=(DB.get('archivosClinicos')||{})[id]||[];







  const recetas=((DB.get('recetas')||{})[id]||[]);







  const ini=((p.nombres||'P')[0]+(p.apellidos||'G')[0]).toUpperCase();







  const espColor=getEspColor(p.esp);







  document.getElementById('hce-detail').innerHTML=`







  <div class="card">







    <div class="card-hdr">







      <div class="av lg" style="background:${espColor}22;color:${espColor};">${ini}</div>







      <div style="flex:1;">







        <div class="fw7" style="font-size:16px;">${esc(p.nombres)} ${esc(p.apellidos)}</div>







        <div class="text-xs text-muted">HCU #HCE-${String(id).padStart(4,'0')} - ${esc(p.esp||'Consulta externa')}</div>







      </div>







      <button class="btn-p btn-sm" onclick="openClinicalTimeline(${id})">Historia por especialidad / Bitácora</button>
      <button class="btn-p btn-sm flex gap6" onclick="openNotaModal(${id})"><i class="ti ti-pencil"></i>Nueva HCU</button>







      ${notas.length?`<button class="btn-s btn-sm" onclick="printHcuNota(${id},0)"><i class="ti ti-printer"></i>Imprimir HCU</button>`:''}







      ${currentUser?.rol==='medico'||currentUser?.rol==='admin'?`<button class="btn-g btn-sm flex gap6" onclick="openRecetaModal(${id})"><i class="ti ti-prescription"></i>Receta</button><button class="btn-s btn-sm" onclick="printEtiqueta(${id})"><i class="ti ti-tag"></i>Etiqueta</button>`:''}







      <button class="btn-s btn-sm" onclick="openArchivoModal(${id})"><i class="ti ti-paperclip"></i>Adjuntar</button>







      ${currentUser?.rol!=='medico'?`<button class="btn-s btn-sm" onclick="editPacModal(${id})"><i class="ti ti-edit"></i>Editar</button>`:''}







    </div>







    <div class="card-body">







      <div class="official-strip"><i class="ti ti-shield-check"></i><span>Expediente estructurado como Historia Clinica Unica MSP: datos del paciente, antecedentes, enfermedad actual, revision por sistemas, signos vitales, examen fisico, diagnostico CIE-10 y planes.</span></div>







      <div class="grid3 mb16" style="gap:10px;">







        <div class="stat-box" style="padding:10px 12px;"><div class="stat-lbl">Fecha nacimiento</div><div style="font-size:14px;font-weight:600;">${fmtDate(p.fnac)}</div><div class="stat-sub">${patientAge(p)} anios - ${esc(p.genero||'')}</div></div>







        <div class="stat-box" style="padding:10px 12px;"><div class="stat-lbl">Tipo de sangre</div><div style="font-size:14px;font-weight:600;color:var(--red);">${esc(p.sangre||'?')}</div><div class="stat-sub">Cedula: ${esc(p.cedula||'')}</div></div>







        <div class="stat-box" style="padding:10px 12px;"><div class="stat-lbl">Seguro medico</div><div style="font-size:14px;font-weight:600;">${esc(p.seguro||'Ninguno')}</div><div class="stat-sub">${esc(p.afiliado||'---')}</div></div>







      </div>







      ${p.alergias?`<div class="alert alert-d mb12"><i class="ti ti-alert-triangle" style="font-size:16px;"></i><strong>Alergias:</strong> ${esc(p.alergias)}</div>`:''}







      <div class="grid2 mb12" style="gap:10px;">







        <div><span class="field-lbl">Telefono</span><div>${esc(p.tel||'---')}</div></div>







        <div><span class="field-lbl">Correo</span><div>${esc(p.email||'---')}</div></div>







        <div><span class="field-lbl">Direccion</span><div>${esc(p.dir||'---')}</div></div>







        <div><span class="field-lbl">Antecedentes registrados</span><div class="text-sm">${esc(p.antec||'Sin antecedentes')}</div></div>







      </div>







      <div class="divider"></div>







      <div class="tabs">







        <div class="tab active" onclick="swTab('t-evo',this)">HCU / Evoluciones (${notas.length})</div>







        <div class="tab" onclick="swTab('t-recetas',this)">Recetas (${recetas.length})</div>







        <div class="tab" onclick="swTab('t-archivos',this)">Archivos (${archivos.length})</div>







        <div class="tab" onclick="swTab('t-citas',this)">Citas</div>







        <div class="tab" onclick="swTab('t-fac',this)">Facturas</div>







      </div>







      <div id="t-evo" class="tab-panel active">







        ${notas.length?notas.map((n,idx)=>renderHcuNotaCard(n,id,idx)).join(''):'<div style="text-align:center;padding:20px;color:var(--text3);">Sin Historia Clinica Unica registrada. <button class="btn-s btn-sm mt8" onclick="openNotaModal('+id+')">Agregar HCU</button></div>'}







      </div>







      <div id="t-recetas" class="tab-panel">







        ${recetas.map(r=>renderRecetaCard(r,id)).join('')||'<div class="text-muted text-sm">Sin recetas registradas.</div>'}







      </div>







      <div id="t-archivos" class="tab-panel">







        <div class="mb12"><button class="btn-p btn-sm" onclick="openArchivoModal(${id})"><i class="ti ti-upload"></i> Adjuntar resultado, imagen o estudio</button></div>







        ${archivos.length?`<div class="file-grid">${archivos.map(a=>`







          <div class="file-card">







            <div class="file-icon"><i class="ti ${archivoIcon(a)}"></i></div>







            <div style="flex:1;min-width:0;">







              <div class="file-name">${esc(a.nombre)}</div>







              <div class="text-xs text-muted">${esc(a.tipo||'Documento')} - ${fmtDate(a.fecha)} - ${fmtBytes(a.size)}</div>







              ${a.descripcion?`<div class="file-desc">${esc(a.descripcion)}</div>`:''}







              <div class="text-xs text-muted mt4">Subido por: ${esc(a.subidoPor||'---')}</div>







              <div class="file-actions">







                <button class="btn-s btn-xs" onclick="openArchivoClinico(${id},${a.id})"><i class="ti ti-eye"></i> Abrir</button>







                <button class="btn-s btn-xs" onclick="downloadArchivoClinico(${id},${a.id})"><i class="ti ti-download"></i> Descargar</button>







                <button class="btn-d btn-xs" onclick="deleteArchivoClinico(${id},${a.id})"><i class="ti ti-trash"></i></button>







              </div>







            </div>







          </div>`).join('')}</div>`:'<div class="text-muted text-sm">Sin archivos adjuntos.</div>'}







      </div>







      <div id="t-citas" class="tab-panel">







        ${(DB.get('citas')||[]).filter(c=>c.pac===+id).map(c=>`







          <div style="display:flex;align-items:center;gap:8px;padding:10px;background:var(--gray-lt);border-radius:var(--radius);margin-bottom:8px;">







            <i class="ti ti-calendar" style="color:${getEspColor(c.esp)};font-size:18px;"></i>







            <div style="flex:1;"><div class="fw5 text-sm">${fmtDate(c.fecha)} ${esc(c.hora)} - ${esc(c.esp)}</div><div class="text-xs text-muted">${esc(getMedName(c.med))} - ${esc(c.tipo)} - ${esc(c.motivo||'---')}</div></div>







            <span class="badge ${c.estado==='Confirmada'?'b-green':'b-amber'}">${esc(c.estado)}</span>







          </div>`).join('')||'<div class="text-muted text-sm">Sin citas registradas.</div>'}







      </div>







      <div id="t-fac" class="tab-panel">







        ${(DB.get('facturas')||[]).filter(f=>f.pac===+id).map(f=>`







          <div style="display:flex;align-items:center;gap:8px;padding:10px;background:var(--gray-lt);border-radius:var(--radius);margin-bottom:8px;">







            <i class="ti ti-receipt" style="color:var(--primary);font-size:18px;"></i>







            <div style="flex:1;"><div class="fw5 text-sm">${esc(f.id)}</div><div class="text-xs text-muted">${fmtDate(f.fecha)} - ${esc(f.serv)} - ${esc(f.pago)}</div></div>







            <span class="fw6" style="color:var(--green);">${fmtMoney(f.total)}</span>







          </div>`).join('')||'<div class="text-muted text-sm">Sin facturas registradas.</div>'}







      </div>







    </div>







  </div>`;







}







function swTab(id,el){







  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));







  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));







  el.classList.add('active');







  const panel=document.getElementById(id);if(panel)panel.classList.add('active');







}















function normalizeCie10Code(code){return String(code||'').trim().toUpperCase();}







function cie10Catalog(){return DB.get('cie10')||CIE10_SEED;}







function getCie10ByCode(code){const c=normalizeCie10Code(code);return cie10Catalog().find(x=>normalizeCie10Code(x.code)===c);}







function searchCie10(q,limit=80){







  const term=String(q||'').trim().toLowerCase();







  const list=[...cie10Catalog()].sort((a,b)=>normalizeCie10Code(a.code).localeCompare(normalizeCie10Code(b.code)));







  const filtered=term?list.filter(x=>(x.code+' '+x.desc+' '+(x.chapter||'')).toLowerCase().includes(term)):list;







  return filtered.slice(0,limit);







}







function fillCie10Select(){







  const q=document.getElementById('n-cie-search')?.value||'';







  const sel=document.getElementById('n-cie');







  if(!sel)return;







  const items=searchCie10(q,70);







  sel.innerHTML='<option value="">Seleccionar CIE-10...</option>'+items.map(x=>`<option value="${esc(normalizeCie10Code(x.code))}">${esc(normalizeCie10Code(x.code))} — ${esc(x.desc)}</option>`).join('');







}







function applyCie10Selection(){







  const item=getCie10ByCode(document.getElementById('n-cie').value);







  if(!item){







    document.getElementById('n-cie-code').value='';







    document.getElementById('n-cie-desc').value='';







    return;







  }







  document.getElementById('n-cie-code').value=normalizeCie10Code(item.code);







  document.getElementById('n-cie-desc').value=item.desc;







  document.getElementById('n-dx').value=`${normalizeCie10Code(item.code)} — ${item.desc}`;







}















function hcuText(value){return esc(value||'---').replace(/\n/g,'<br>');}







function hcuLine(label,value){return `<div class="hcu-mini"><b>${label}</b>${hcuText(value)}</div>`;}







function hcuDateTime(n){return `${fmtDate(n.fecha)} ${esc(n.hora||'')}`.trim();}







function renderHcuNotaCard(n,pacId,idx){







  const formato=n.formato||'Nota clinica anterior';







  const dx=n.dx||n.cie10Desc||'';







  const plan=n.plan||[n.planDiagnostico,n.planTerapeutico,n.planEducacional].filter(Boolean).join('\n');







  return `<div class="card mb12" style="border-left:3px solid ${getEspColor(n.esp)||'#1B4F8A'};">







    <div class="card-hdr" style="padding:10px 14px;">







      <i class="ti ti-notes-medical" style="color:${getEspColor(n.esp)};font-size:16px;"></i>







      <div style="flex:1;"><div class="fw5 text-sm">${esc(n.med||'Profesional')} - ${esc(n.esp||'Consulta externa')}</div><div class="text-xs text-muted">${hcuDateTime(n)} - ${esc(formato)}</div></div>







      <button class="btn-s btn-xs" onclick="printHcuNota(${pacId},${idx})"><i class="ti ti-printer"></i> Imprimir HCU</button>







    </div>







    <div class="card-body" style="padding:10px 14px;">







      <div class="hcu-grid mb8">${hcuLine('PA',n.pa)}${hcuLine('FC',n.fc?n.fc+' lpm':'')}${hcuLine('FR',n.fr?n.fr+' rpm':'')}${hcuLine('Temp',n.temp?n.temp+' C':'')}${hcuLine('SpO2',n.spo2?n.spo2+' %':'')}${hcuLine('Peso',n.peso?n.peso+' kg':'')}${hcuLine('Talla',n.talla?n.talla+' cm':'')}${hcuLine('IMC',n.imc)}</div>







      <div class="hcu-section"><div class="hcu-section-title">Motivo y enfermedad actual</div><div class="text-sm"><b>Motivo:</b> ${hcuText(n.motivo)}<br><b>Enfermedad actual:</b> ${hcuText(n.enfermedadActual||n.enfActual)}</div></div>







      ${(n.antecedentesPersonales||n.antecedentesFamiliares)?`<div class="hcu-section"><div class="hcu-section-title">Antecedentes</div><div class="text-sm"><b>Personales:</b> ${hcuText(n.antecedentesPersonales)}<br><b>Familiares:</b> ${hcuText(n.antecedentesFamiliares)}</div></div>`:''}







      ${(n.revisionSistemas||n.explora||n.examenFisico)?`<div class="hcu-section"><div class="hcu-section-title">Revision y examen fisico</div><div class="text-sm"><b>Revision sistemas:</b> ${hcuText(n.revisionSistemas)}<br><b>Examen fisico:</b> ${hcuText(n.examenFisico||n.explora)}${n.organosRegionales?`<br><b>Organos/regiones:</b> ${hcuText(n.organosRegionales)}`:''}</div></div>`:''}







      ${(dx||n.cie10Code)?`<div class="hcu-section"><div class="hcu-section-title">Diagnostico</div>${n.cie10Code?`<span class="badge b-blue">CIE-10 ${esc(n.cie10Code)}</span> `:''}<span class="badge b-gray">${esc(n.dxTipo||'')}</span><div class="text-sm mt4"><strong>${hcuText(dx)}</strong></div>${n.dxAdicionales?`<div class="text-sm mt4">${hcuText(n.dxAdicionales)}</div>`:''}</div>`:''}







      ${plan?`<div class="hcu-section"><div class="hcu-section-title">Plan</div><div class="text-sm">${hcuText(plan)}</div></div>`:''}







    </div>







  </div>`;







}















function calcNotaImc(){







  const peso=+(document.getElementById('n-peso')?.value||0);







  const tallaCm=+(document.getElementById('n-talla')?.value||0);







  const imc=document.getElementById('n-imc');







  if(!imc)return;







  if(peso>0&&tallaCm>0){const t=tallaCm/100;imc.value=(peso/(t*t)).toFixed(2);}else imc.value='';







}















function selectedMedicoFromNota(){







  const id=+(document.getElementById('n-med')?.value||0);







  return (DB.get('medicos')||[]).find(m=>+m.id===id)||{};







}















function openNotaModal(pacId){







  if(!hasPerm('hce')){toast('No tienes permiso para crear Historia Clinica Unica','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId)||{};







  document.getElementById('n-pac-id').value=pacId;







  const esps=DB.get('especialidades')||[];







  const meds=DB.get('medicos')||[];







  document.getElementById('n-esp').innerHTML=esps.map(e=>`<option>${esc(e.nombre)}</option>`).join('');







  if(p.esp)document.getElementById('n-esp').value=p.esp;







  document.getElementById('n-med').innerHTML=meds.map(m=>`<option value="${m.id}">${esc(m.nombre)} - ${esc(m.esp||'')}</option>`).join('');







  const medId=currentDoctorId()||+(meds.find(m=>doctorSpecialties(m).includes(p.esp))?.id||0);







  if(medId)document.getElementById('n-med').value=String(medId);







  ['n-pa','n-fc','n-fr','n-temp','n-spo2','n-peso','n-talla','n-imc','n-motivo','n-ap','n-af','n-enf','n-ros','n-explora','n-organos','n-cie-search','n-cie-code','n-cie-desc','n-dx','n-dx-add','n-plan-dx','n-plan-tx','n-plan-edu','n-observaciones'].forEach(id=>{const el=document.getElementById(id);if(el)el.value='';});







  document.getElementById('n-ap').value=p.antec||'';







  document.getElementById('n-dx-tipo').value='Presuntivo';







  fillCie10Select();







  openM('m-nota');







}















function saveNota(){







  if(!hasPerm('hce')){toast('No tienes permiso para guardar Historia Clinica Unica','err');return;}







  const pacId=document.getElementById('n-pac-id').value;







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId)||{};







  const cfg=DB.get('config')||{};







  const med=selectedMedicoFromNota();







  const cieItem=getCie10ByCode(document.getElementById('n-cie-code').value || document.getElementById('n-cie').value);







  const dx=document.getElementById('n-dx').value.trim();







  const motivo=document.getElementById('n-motivo').value.trim();







  if(!motivo){toast('Ingresa el motivo de consulta','err');return;}







  const nota={







    id:Date.now(),formato:'SNS-MSP/HCU-form.002/2021',tipo:'Consulta externa',establecimiento:cfg.nombre||'Centro medico',historia:`HCE-${String(pacId).padStart(4,'0')}`,







    esp:document.getElementById('n-esp').value,med:med.nombre||currentUser.name+' '+currentUser.last,medId:med.id||0,medCedula:med.cedula||'',medSen:med.sen||'',fecha:today(),hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),







    motivo,antecedentesPersonales:document.getElementById('n-ap').value.trim(),antecedentesFamiliares:document.getElementById('n-af').value.trim(),enfermedadActual:document.getElementById('n-enf').value.trim(),revisionSistemas:document.getElementById('n-ros').value.trim(),







    pa:document.getElementById('n-pa').value,fc:document.getElementById('n-fc').value,fr:document.getElementById('n-fr').value,temp:document.getElementById('n-temp').value,spo2:document.getElementById('n-spo2').value,peso:document.getElementById('n-peso').value,talla:document.getElementById('n-talla').value,imc:document.getElementById('n-imc').value,







    examenFisico:document.getElementById('n-explora').value.trim(),organosRegionales:document.getElementById('n-organos').value.trim(),cie10Code:cieItem?normalizeCie10Code(cieItem.code):'',cie10Desc:cieItem?cieItem.desc:'',dxTipo:document.getElementById('n-dx-tipo').value,dx:dx||(cieItem?`${normalizeCie10Code(cieItem.code)} - ${cieItem.desc}`:''),dxAdicionales:document.getElementById('n-dx-add').value.trim(),







    planDiagnostico:document.getElementById('n-plan-dx').value.trim(),planTerapeutico:document.getElementById('n-plan-tx').value.trim(),planEducacional:document.getElementById('n-plan-edu').value.trim(),observaciones:document.getElementById('n-observaciones').value.trim()







  };







  nota.plan=[nota.planDiagnostico,nota.planTerapeutico,nota.planEducacional,nota.observaciones].filter(Boolean).join('\n');







  const notas=DB.get('notas')||{};







  if(!notas[pacId]) notas[pacId]=[];







  notas[pacId].unshift(nota);







  DB.set('notas',notas);







  const pacs=DB.get('pacientes')||[];const i=pacs.findIndex(x=>x.id===+pacId);if(i>=0&&currentUser?.rol!=='medico'){pacs[i].ultima=today();DB.set('pacientes',pacs);}







  closeM('m-nota');toast('Historia Clinica Unica guardada','ok');







  if(selPac===+pacId) renderHCE(pacId);







}















function printHcuNota(pacId,idx){







  if(!hasPerm('hce')){toast('No tienes permiso para imprimir HCU','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId);const n=((DB.get('notas')||{})[pacId]||[])[idx];if(!p||!n)return;
  if(n.clinicalVersion){printClinicalEntry(pacId,n.id);return;}







  const cfg=DB.get('config')||{};const logo=cfg.logo||DEFAULT_LOGO;







  const patientRows=`<tr><td><b>Paciente</b><br>${esc(p.apellidos||'')} ${esc(p.nombres||'')}</td><td><b>Cedula</b><br>${esc(p.cedula||'---')}</td><td><b>Edad</b><br>${patientAge(p)}</td><td><b>Sexo</b><br>${esc(p.genero||'---')}</td></tr><tr><td><b>HCU</b><br>HCE-${String(pacId).padStart(4,'0')}</td><td><b>Fecha</b><br>${fmtDate(n.fecha)} ${esc(n.hora||'')}</td><td><b>Especialidad</b><br>${esc(n.esp||'')}</td><td><b>Alergias</b><br>${esc(p.alergias||'No registradas')}</td></tr>`;







  const vitals=`<tr><td>PA: ${esc(n.pa||'---')}</td><td>FC: ${esc(n.fc||'---')}</td><td>FR: ${esc(n.fr||'---')}</td><td>Temp: ${esc(n.temp||'---')}</td></tr><tr><td>SpO2: ${esc(n.spo2||'---')}</td><td>Peso: ${esc(n.peso||'---')}</td><td>Talla: ${esc(n.talla||'---')}</td><td>IMC: ${esc(n.imc||'---')}</td></tr>`;







  printDoc('Historia Clinica Unica MSP',`<div class="hdr"><img class="logo" src="${logo}"><div><div class="big">${esc(cfg.nombre||'Centro Medico')}</div><div class="muted">${esc(cfg.dir||'')} - ${esc(cfg.tel||'')}</div><div class="muted">SNS-MSP / HCU-form.002 / 2021 - Consulta externa</div></div></div><table width="100%" border="1" cellspacing="0" cellpadding="6">${patientRows}</table><div class="box"><div class="label">1. Motivo de consulta</div>${hcuText(n.motivo)}</div><div class="box"><div class="label">2. Antecedentes personales y familiares</div><b>Personales:</b><br>${hcuText(n.antecedentesPersonales)}<br><b>Familiares:</b><br>${hcuText(n.antecedentesFamiliares)}</div><div class="box"><div class="label">3. Enfermedad actual</div>${hcuText(n.enfermedadActual)}</div><div class="box"><div class="label">4. Revision de organos y sistemas</div>${hcuText(n.revisionSistemas)}</div><table width="100%" border="1" cellspacing="0" cellpadding="6"><caption style="text-align:left;font-weight:bold;margin:8px 0;">5. Signos vitales y antropometria</caption>${vitals}</table><div class="box"><div class="label">6. Examen fisico</div>${hcuText(n.examenFisico)}<br><b>Organos/regiones:</b><br>${hcuText(n.organosRegionales)}</div><div class="box"><div class="label">7. Diagnostico CIE-10</div>${n.cie10Code?`<b>${esc(n.cie10Code)}</b> - `:''}${hcuText(n.dx||n.cie10Desc)}<br><b>Tipo:</b> ${esc(n.dxTipo||'')}<br>${hcuText(n.dxAdicionales)}</div><div class="box"><div class="label">8. Planes</div><b>Diagnostico:</b><br>${hcuText(n.planDiagnostico)}<br><b>Terapeutico:</b><br>${hcuText(n.planTerapeutico)}<br><b>Educacional:</b><br>${hcuText(n.planEducacional)}</div><div style="margin-top:50px;display:flex;justify-content:space-between;gap:20px;"><div style="border-top:1px solid #333;width:260px;text-align:center;">${esc(n.med||'Profesional')}<br><span class="muted">Registro: ${esc(n.medSen||n.medCedula||'---')}</span></div><div class="muted">Documento generado desde Medic G. Adjuntar firma/sello fisico o firma electronica si aplica.</div></div>`);







}







function archivoIcon(a){







  const mime=(a?.mime||'').toLowerCase();







  const tipo=(a?.tipo||'').toLowerCase();







  if(mime.startsWith('image/')||tipo==='imagen') return 'ti-photo';







  if(mime.includes('pdf')) return 'ti-file-type-pdf';







  if(mime.includes('word')||/\.(doc|docx)$/i.test(a?.nombre||'')) return 'ti-file-type-doc';







  if(mime.includes('excel')||/\.(xls|xlsx)$/i.test(a?.nombre||'')) return 'ti-file-spreadsheet';







  if(tipo==='laboratorio') return 'ti-flask';







  if(tipo==='estudio') return 'ti-device-heart-monitor';







  return 'ti-file-description';







}















function getArchivoClinico(pacId,archivoId){







  return ((DB.get('archivosClinicos')||{})[pacId]||[]).find(a=>a.id===+archivoId);







}















function openArchivoModal(pacId){







  if(!hasPerm('hce')){toast('No tienes permiso para adjuntar archivos clínicos','err');return;}







  document.getElementById('ar-pac-id').value=pacId;







  document.getElementById('ar-tipo').value='Laboratorio';







  document.getElementById('ar-file').value='';







  document.getElementById('ar-desc').value='';







  openM('m-archivo');







}















function saveArchivoClinico(){







  if(!hasPerm('hce')){toast('No tienes permiso para guardar archivos clínicos','err');return;}







  const pacId=document.getElementById('ar-pac-id').value;







  const tipo=document.getElementById('ar-tipo').value;







  const file=document.getElementById('ar-file').files[0];







  const descripcion=document.getElementById('ar-desc').value.trim();







  if(!pacId){toast('Selecciona un paciente','err');return;}







  if(!file){toast('Selecciona un archivo para adjuntar','err');return;}







  if(file.size>MAX_CLINICAL_FILE_BYTES){toast('El archivo supera el límite de 8 MB','err');return;}







  if(!isAllowedClinicalFile(file)){toast('Tipo de archivo no permitido. Usa PDF, imagen, TXT, Word o Excel.','err');return;}







  const reader=new FileReader();







  reader.onerror=()=>toast('No se pudo leer el archivo','err');







  reader.onload=()=>{







    const archivos=DB.get('archivosClinicos')||{};







    if(!archivos[pacId]) archivos[pacId]=[];







    archivos[pacId].unshift({







      id:Date.now(),







      fecha:today(),







      tipo,







      nombre:file.name,







      mime:file.type||'application/octet-stream',







      size:file.size,







      descripcion,







      dataUrl:reader.result,







      subidoPor:currentUser?(currentUser.name+' '+currentUser.last):'Usuario'







    });







    DB.set('archivosClinicos',archivos);







    closeM('m-archivo');







    toast('Archivo clínico guardado en la base de datos','ok');







    if(selPac===+pacId) renderHCE(+pacId);







  };







  reader.readAsDataURL(file);







}















async function openArchivoClinico(pacId,archivoId){







  if(!hasPerm('hce')){toast('No tienes permiso para abrir archivos clínicos','err');return;}







  const a=getArchivoClinico(pacId,archivoId);







  if(!a){toast('Archivo no encontrado','err');return;}







  const mime=(a.mime||'').toLowerCase();







  if(!mime.startsWith('image/') && !mime.includes('pdf') && !mime.startsWith('text/')){







    downloadArchivoClinico(pacId,archivoId);







    toast('Este tipo de archivo se descargó para abrirlo con su programa correspondiente','inf');







    return;







  }







  const w=window.open('','_blank','width=900,height=720');







  if(!w){toast('Permite ventanas emergentes para abrir el archivo','err');return;}
  let fileUrl;
  try{fileUrl=await clinicalFileData(pacId,a);}catch(e){w.close();toast(e.message,'err');return;}







  const body=mime.startsWith('image/')







    ? `<img src="${fileUrl}" style="max-width:100%;height:auto;display:block;margin:0 auto;">`







    : `<iframe src="${fileUrl}" style="width:100%;height:82vh;border:0;"></iframe>`;







  w.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${esc(a.nombre)}</title><style>body{font-family:Arial,sans-serif;margin:0;padding:18px;background:#f6f7f9;color:#222}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}.wrap{background:#fff;border:1px solid #ddd;border-radius:8px;padding:12px}</style></head><body><div class="top"><div><strong>${esc(a.nombre)}</strong><div style="font-size:12px;color:#666;">${esc(a.tipo||'Documento')} · ${fmtDate(a.fecha)} · ${fmtBytes(a.size)}</div></div><button onclick="window.print()">Imprimir</button></div><div class="wrap">${body}</div></body></html>`);







  w.document.close();







}















async function downloadArchivoClinico(pacId,archivoId){







  if(!hasPerm('hce')){toast('No tienes permiso para descargar archivos clínicos','err');return;}







  const a=getArchivoClinico(pacId,archivoId);







  if(!a){toast('Archivo no encontrado','err');return;}







  const link=document.createElement('a');







  try{link.href=await clinicalFileData(pacId,a);}catch(e){toast(e.message,'err');return;}







  link.download=a.nombre||'archivo-clinico';







  document.body.appendChild(link);







  link.click();







  link.remove();







}















function deleteArchivoClinico(pacId,archivoId){







  if(!hasPerm('hce')){toast('No tienes permiso para eliminar archivos clínicos','err');return;}







  const a=getArchivoClinico(pacId,archivoId);







  confirmDelete(`¿Eliminar el archivo "${a?a.nombre:'seleccionado'}"?`,()=>{







    const archivos=DB.get('archivosClinicos')||{};







    archivos[pacId]=(archivos[pacId]||[]).filter(x=>x.id!==+archivoId);







    DB.set('archivosClinicos',archivos);







    toast('Archivo eliminado','inf');







    if(selPac===+pacId) renderHCE(+pacId);







  });







}















function openRecetaModal(pacId){







  if(!hasPerm('hce')){toast('No tienes permiso para generar recetas','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId)||{};







  const med=linkedDoctorForUser()||{};







  const latest=((DB.get('notas')||{})[pacId]||[])[0]||{};







  document.getElementById('rx-pac-id').value=pacId;







  document.getElementById('rx-medico').value=med.nombre||currentUser.name+' '+currentUser.last;







  document.getElementById('rx-registro').value=med.sen||med.cedula||'';







  document.getElementById('rx-dx').value=latest.dx||latest.cie10Desc||'';







  document.getElementById('rx-alergias').value=p.alergias||'Sin alergias conocidas';







  document.getElementById('rx-meds').value='';







  document.getElementById('rx-ind').value='';







  document.getElementById('rx-validez').value='';







  openM('m-receta');







}















function saveReceta(print=false){







  if(!hasPerm('hce')){toast('No tienes permiso para guardar recetas','err');return;}







  const pacId=document.getElementById('rx-pac-id').value;







  const medicamentos=document.getElementById('rx-meds').value.trim();







  const dx=document.getElementById('rx-dx').value.trim();







  if(!dx){toast('Ingresa diagnostico o CIE-10 para la receta','err');return;}







  if(!medicamentos){toast('Ingresa los medicamentos de la receta','err');return;}







  const recetas=DB.get('recetas')||{};







  if(!recetas[pacId]) recetas[pacId]=[];







  const receta={id:Date.now(),numero:`RX-${new Date().getFullYear()}-${String(Date.now()).slice(-6)}`,formato:'Receta medica - AM 00031-2020 / ACESS',fecha:today(),hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),medico:document.getElementById('rx-medico').value.trim()||currentUser.name+' '+currentUser.last,registro:document.getElementById('rx-registro').value.trim(),diagnostico:dx,alergias:document.getElementById('rx-alergias').value.trim(),medicamentos,indicaciones:document.getElementById('rx-ind').value.trim(),validez:document.getElementById('rx-validez').value.trim()};







  recetas[pacId].unshift(receta);







  DB.set('recetas',recetas);







  closeM('m-receta');toast('Receta medica guardada','ok');







  if(selPac===+pacId) renderHCE(pacId);







  if(print) printReceta(+pacId,receta.id);







}















function renderRecetaCard(r,pacId){







  return `<div class="card mb12"><div class="card-hdr" style="padding:10px 14px;"><i class="ti ti-prescription" style="color:var(--green);font-size:16px;"></i><div style="flex:1;"><div class="fw5 text-sm">${esc(r.numero||'Receta')} - ${esc(r.medico||'Medico')}</div><div class="text-xs text-muted">${fmtDate(r.fecha)} ${esc(r.hora||'')} - ${esc(r.formato||'Receta medica')}</div></div><button class="btn-s btn-xs" onclick="printReceta(${pacId},${r.id})"><i class="ti ti-printer"></i> Imprimir</button></div><div class="card-body" style="padding:10px 14px;"><div class="field-lbl">Diagnostico</div><div class="text-sm mb8">${hcuText(r.diagnostico||r.dx||'---')}</div><div class="field-lbl">Medicamentos</div><div style="white-space:pre-wrap;">${esc(r.medicamentos)}</div>${r.indicaciones?`<div class="field-lbl mt8">Indicaciones</div><div style="white-space:pre-wrap;">${esc(r.indicaciones)}</div>`:''}</div></div>`;







}















function printDoc(title,html){







  const w=window.open('','_blank','width=820,height=900');







  if(!w){toast('Permite ventanas emergentes para imprimir','err');return;}







  w.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title><style>body{font-family:Arial,sans-serif;padding:28px;color:#111}.hdr{display:flex;gap:14px;align-items:center;border-bottom:2px solid #1B4F8A;padding-bottom:12px;margin-bottom:18px}.logo{max-width:80px;max-height:80px}.muted{color:#666;font-size:12px}.row{display:flex;justify-content:space-between;gap:12px}.box{border:1px solid #ccc;padding:12px;margin:12px 0}.label{font-weight:bold;font-size:12px;color:#555;text-transform:uppercase}.big{font-size:18px;font-weight:bold}pre{white-space:pre-wrap;font-family:inherit}.tag{width:360px;border:1px solid #111;padding:12px}.barcode{letter-spacing:3px;text-align:center;font-size:22px;margin-top:8px}table{border-collapse:collapse;margin:10px 0}td,th{vertical-align:top;font-size:12px}.rx-title{text-align:center;font-size:20px;font-weight:bold;margin:10px 0}.rx-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media print{button{display:none}body{padding:12mm}}</style></head><body>${html}<button onclick="window.print()">Imprimir</button><script>setTimeout(()=>window.print(),300)<\/script></body></html>`);







  w.document.close();







}















function printReceta(pacId,recetaId){







  if(!hasPerm('hce')){toast('No tienes permiso para imprimir recetas','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId);const r=((DB.get('recetas')||{})[pacId]||[]).find(x=>x.id===recetaId);if(!p||!r)return;







  const cfg=DB.get('config')||{};







  const logo=cfg.logo||DEFAULT_LOGO;







  printDoc('Receta medica',`<div class="hdr"><img class="logo" src="${logo}"><div><div class="big">${esc(cfg.nombre||'Centro Medico')}</div><div class="muted">RUC: ${esc(cfg.ruc||'---')} - ${esc(cfg.tel||'')} - ${esc(cfg.email||'')}</div><div class="muted">${esc(cfg.dir||'')}</div></div></div><div class="rx-title">RECETA MEDICA</div><div class="row"><div><div class="label">Numero</div>${esc(r.numero||String(r.id))}</div><div><div class="label">Fecha de emision</div>${fmtDate(r.fecha)} ${esc(r.hora||'')}</div></div><table width="100%" border="1" cellspacing="0" cellpadding="6"><tr><td><b>Paciente</b><br>${esc(p.apellidos||'')} ${esc(p.nombres||'')}</td><td><b>Identificacion</b><br>${esc(p.cedula||'---')}</td><td><b>Edad</b><br>${patientAge(p)}</td><td><b>HCU</b><br>HCE-${String(pacId).padStart(4,'0')}</td></tr><tr><td colspan="2"><b>Diagnostico</b><br>${hcuText(r.diagnostico||'---')}</td><td colspan="2"><b>Antecedentes de alergias</b><br>${hcuText(r.alergias||p.alergias||'No registradas')}</td></tr></table><div class="box"><div class="label">Medicamento: DCI, forma farmaceutica, concentracion, via, cantidad, dosis, frecuencia y duracion</div><pre>${esc(r.medicamentos)}</pre></div><div class="box"><div class="label">Indicaciones para el paciente</div><pre>${esc(r.indicaciones||'---')}</pre></div>${r.validez?`<div class="box"><div class="label">Validez / observacion</div>${hcuText(r.validez)}</div>`:''}<div style="margin-top:58px;display:flex;justify-content:space-between;gap:20px;"><div style="text-align:center;border-top:1px solid #333;width:280px;">${esc(r.medico)}<br><span class="muted">Registro profesional: ${esc(r.registro||'---')}</span><br><span class="muted">Firma y sello</span></div><div class="muted" style="max-width:300px;">Para medicamentos sujetos a fiscalizacion debe usarse receta especial segun normativa aplicable.</div></div>`);







}















function printEtiqueta(pacId){







  if(!hasPerm('hce')){toast('No tienes permiso para imprimir etiquetas clinicas','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+pacId);if(!p)return;







  printDoc('Etiqueta paciente',`<div class="tag"><div class="big">${esc(p.nombres)} ${esc(p.apellidos)}</div><div>Cedula: ${esc(p.cedula||'---')}</div><div>HCE-${String(p.id).padStart(4,'0')} - ${esc(p.esp||'---')}</div><div>Sangre: ${esc(p.sangre||'---')} - Alergias: ${esc(p.alergias||'Ninguna')}</div><div class="barcode">*HCE${String(p.id).padStart(4,'0')}*</div></div>`);







}







// =========================================================







// FACTURACIÓN







// =========================================================







function renderFacStats(){







  const facs=DB.get('facturas')||[];







  const hoy=today();







  const active=facs.filter(f=>f.estado!=='Anulado');







  const hoyFacs=active.filter(f=>f.fecha===hoy);







  const autorizadas=active.filter(f=>f.estado==='Autorizado SRI');







  const pendientes=active.filter(f=>['Pendiente SRI','Recibida SRI','En proceso SRI','GENERADO'].includes(f.estado)||['GENERADO','RECIBIDA','EN_PROCESO'].includes(f.sriEstado));







  const errores=active.filter(f=>['Error SRI','Devuelta SRI','No autorizado SRI'].includes(f.estado));







  document.getElementById('fac-stats').innerHTML=`







    <div class="stat-box"><div class="stat-lbl">Facturado hoy</div><div class="stat-val" style="font-size:20px;color:var(--green);">${fmtMoney(hoyFacs.reduce((a,f)=>a+(+f.total||0),0))}</div><div class="stat-sub">${hoyFacs.length} comprobantes</div></div>







    <div class="stat-box"><div class="stat-lbl">Autorizadas SRI</div><div class="stat-val" style="font-size:20px;color:var(--green);">${autorizadas.length}</div><div class="stat-sub">Listas para RIDE/XML</div></div>







    <div class="stat-box"><div class="stat-lbl">Pendientes SRI</div><div class="stat-val" style="font-size:20px;color:var(--amber);">${pendientes.length}</div><div class="stat-sub">Generadas o en proceso</div></div>







    <div class="stat-box"><div class="stat-lbl">Errores SRI</div><div class="stat-val" style="font-size:20px;color:var(--red);">${errores.length}</div><div class="stat-sub">Revisar y reintentar</div></div>`;







}















function sriStatusClass(status){







  const s=(status||'').toLowerCase();







  if(s.includes('autorizado')) return 'b-green';







  if(s.includes('recibida')||s.includes('proceso')||s.includes('pendiente')||s.includes('generado')) return 'b-amber';







  if(s.includes('seguro')) return 'b-blue';







  if(s.includes('pagado')) return 'b-green';







  if(s.includes('anulado')||s.includes('error')||s.includes('devuelta')||s.includes('no autorizado')) return 'b-red';







  return 'b-gray';







}







function invoiceStatus(f){return f.estado||f.sriEstado||'Pendiente SRI';}







function shortSriMsg(f){return esc(f.sriMensaje||f.emailError||f.claveAcceso||'');}







function updateLocalInvoice(invoice){







  if(!invoice)return;







  const facs=(DB.get('facturas')||[]).filter(f=>String(f.id)!==String(invoice.id));







  facs.unshift(normalizeData(invoice));







  DB.cache.facturas=facs;







}















function renderFacs(){







  const q=(document.getElementById('fac-q')?.value||'').toLowerCase();







  const est=document.getElementById('fac-est')?.value||'';







  const facs=DB.get('facturas')||[];







  const fil=facs.filter(f=>{







    const name=getPacName(f.pac).toLowerCase();







    const hay=[name,f.id,f.serv,f.esp,f.pago,f.claveAcceso,f.autorizacion,f.sriMensaje].join(' ').toLowerCase();







    return hay.includes(q)&&(!est||invoiceStatus(f)===est);







  });







  document.getElementById('fac-tbody').innerHTML=fil.map(f=>{







    const status=invoiceStatus(f);







    const canRetry=canSendClinicMail()&&!['Autorizado SRI','Anulado'].includes(status);







    return `<tr>







      <td class="fw5 text-xs">${esc(f.id)}</td><td>${fmtDate(f.fecha)}</td><td>${esc(getPacName(f.pac))}</td><td>${esc(f.esp||'')}</td>







      <td>${esc(f.serv||'Servicio médico')}<div class="text-xs text-muted">${shortSriMsg(f)}</div></td>







      <td class="fw6">${fmtMoney(f.total)}${f.cobroVersion===1?`<div class="text-xs">Abonado: ${fmtMoney(f.abonado)} · Saldo: ${fmtMoney(f.saldo)}</div>`:''}</td><td>${esc(f.pago||'')}</td>







      <td><span class="badge ${sriStatusClass(status)}">${esc(status)}</span>${f.emailEnviado?'<div class="text-xs text-muted mt4">Email enviado</div>':''}</td>







      <td style="white-space:nowrap;min-width:210px;">







        ${canRetry?`<button class="btn-s" title="Enviar factura al SRI" onclick="retrySriInvoice('${esc(f.id)}')">Enviar al SRI</button>`:''}







        <button class="btn-ic" title="RIDE A4" onclick="printComprobante('${esc(f.id)}','a4')"><i class="ti ti-printer" style="font-size:14px;"></i></button>







        <button class="btn-ic" title="RIDE ticket" onclick="printComprobante('${esc(f.id)}','ticket')"><i class="ti ti-receipt-2" style="font-size:14px;"></i></button>







        <button class="btn-ic" title="Descargar XML" onclick="downloadInvoiceXml('${esc(f.id)}')"><i class="ti ti-file-code" style="font-size:14px;color:var(--primary);"></i></button>







        ${canSendClinicMail()&&status!=='Anulado'?`<button class="btn-s" onclick="emailInvoice('${esc(f.id)}')">Enviar al paciente</button>`:''}







        ${status==='Pendiente'?`<button class="btn-ic" title="Marcar pagado" onclick="markPagado('${esc(f.id)}')"><i class="ti ti-check" style="font-size:14px;color:var(--green);"></i></button>`:''}







        ${status!=='Anulado'?`<button class="btn-ic" title="Anular localmente" onclick="anularFac('${esc(f.id)}')"><i class="ti ti-ban" style="font-size:14px;color:var(--red);"></i></button>`:''}







      </td>







    </tr>`;







  }).join('')||'<tr><td colspan="9" class="text-c text-muted">Sin facturas registradas</td></tr>';







}















function markPagado(id){if((DB.get('facturas')||[]).find(f=>f.id===id)?.cobroVersion===1){cashOpenAbono(id);return;}const facs=DB.get('facturas')||[];const i=facs.findIndex(f=>f.id===id);if(i>=0){facs[i].estado='Pagado';DB.set('facturas',facs);}renderFacs();renderFacStats();toast('Factura marcada como pagada','ok');}







function anularFac(id){if((DB.get('facturas')||[]).find(f=>f.id===id)?.cobroVersion===1){toast('Esta cuenta tiene un registro de pagos. No se puede anular desde este botón.','err');return;}confirmDelete(`¿Anular localmente el comprobante ${id}?`,()=>{const facs=DB.get('facturas')||[];const i=facs.findIndex(f=>f.id===id);if(i>=0){facs[i].estado='Anulado';DB.set('facturas',facs);}renderFacs();renderFacStats();toast('Comprobante anulado localmente','inf');});}















function openFacModal(){







  if(!hasPerm('facturacion')){toast('No tienes permiso para facturación','err');return;}







  const pacs=DB.get('pacientes')||[];







  const esps=DB.get('especialidades')||[];







  document.getElementById('f-pac').innerHTML='<option value="">Seleccionar...</option>'+pacs.map(p=>`<option value="${p.id}">${esc(p.nombres)} ${esc(p.apellidos)} — ${esc(p.cedula||'')}</option>`).join('');







  document.getElementById('f-esp').innerHTML='<option value="">Seleccionar...</option>'+esps.map(e=>`<option>${esc(e.nombre)}</option>`).join('');







  document.getElementById('f-fecha').value=today();







  const emailAuto=document.getElementById('f-email-auto');if(emailAuto)emailAuto.checked=false;







  document.getElementById('f-items').innerHTML=`<tr><td><input type="text" value="Consulta médica especialidad" style="min-width:160px;"/></td><td><input type="number" value="1" style="width:55px;" oninput="calcFac()"/></td><td><input type="number" value="85" style="width:70px;" oninput="calcFac()"/></td><td id="fs0">$85.00</td><td><button class="btn-ic" onclick="this.closest('tr').remove();calcFac()"><i class="ti ti-trash" style="color:var(--red);font-size:13px;"></i></button></td></tr>`;







  calcFac();openM('m-factura');







}















function addFItem(){







  const tr=document.createElement('tr');







  const idx=document.querySelectorAll('#f-items tr').length;







  tr.innerHTML=`<td><input type="text" value="Servicio médico" style="min-width:160px;"/></td><td><input type="number" value="1" style="width:55px;" oninput="calcFac()"/></td><td><input type="number" value="50" style="width:70px;" oninput="calcFac()"/></td><td id="fs${idx}">$50.00</td><td><button class="btn-ic" onclick="this.closest('tr').remove();calcFac()"><i class="ti ti-trash" style="color:var(--red);font-size:13px;"></i></button></td>`;







  document.getElementById('f-items').appendChild(tr);calcFac();







}















function sriIvaRate(){const cfg=DB.get('config')||{};return +(cfg.sriIvaRate||15);}







function calcFac(){







  let sub=0;







  document.querySelectorAll('#f-items tr').forEach((tr)=>{







    const ins=tr.querySelectorAll('input[type=number]');







    const v=(+ins[0]?.value||0)*(+ins[1]?.value||0);







    sub+=v;







    const td=tr.children[3];if(td) td.textContent=fmtMoney(v);







  });







  const rate=sriIvaRate();







  const iva=sub*rate/100;







  document.getElementById('f-sub').textContent=fmtMoney(sub);







  const lbl=document.getElementById('f-iva-lbl');if(lbl)lbl.textContent=`IVA ${rate}%:`;







  document.getElementById('f-iva').textContent=fmtMoney(iva);







  document.getElementById('f-total').textContent=fmtMoney(sub+iva);







}















async function saveFactura(){







  if(!hasPerm('facturacion')){toast('No tienes permiso para emitir facturas','err');return;}







  const pac=document.getElementById('f-pac').value;







  if(!pac){toast('Selecciona un paciente','err');return;}







  const esp=document.getElementById('f-esp').value;







  if(!esp){toast('Selecciona una especialidad','err');return;}







  const items=[...document.querySelectorAll('#f-items tr')].map(tr=>({







    desc:tr.children[0].querySelector('input').value.trim(),







    cant:+tr.children[1].querySelector('input').value||1,







    unit:+tr.children[2].querySelector('input').value||0,







    total:((+tr.children[1].querySelector('input').value||1)*(+tr.children[2].querySelector('input').value||0))







  })).filter(i=>i.desc&&i.total>=0);







  const sub=items.reduce((a,i)=>a+i.total,0);







  if(sub<=0){toast('Agrega al menos un servicio facturable','err');return;}







  try{







    toast('Guardando factura sin enviar...','inf');







    const res=await API.post('/api/invoices',{pac:+pac,esp,fecha:document.getElementById('f-fecha').value||today(),pago:document.getElementById('f-pago').value,items,emailAuto:false,sendSri:false});







    const f=res.invoice;







    updateLocalInvoice(f);







    closeM('m-factura');







    renderFacs();renderFacStats();







    addInvoiceToOpenCash(f);







    const msg=f.estado==='Autorizado SRI'?`Factura ${f.id} autorizada por SRI`:`Factura ${f.id} creada: ${f.sriMensaje||f.estado}`;







    toast(msg,f.estado==='Autorizado SRI'?'ok':(f.estado==='Error SRI'?'err':'warn'));







    if(f.estado==='Autorizado SRI') printComprobante(f.id,'a4');







  }catch(err){toast(err.message||'No se pudo emitir la factura SRI','err');}







}















function addInvoiceToOpenCash(f){







  if(!f||f.cobroVersion===1||!hasPerm('caja'))return;







  const cajas=DB.get('cajas')||[];const cajahoy=cajas.find(c=>c.estado==='abierta');







  if(cajahoy){cajahoy.movimientos=cajahoy.movimientos||[];cajahoy.movimientos.push({hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),pac:getPacName(+f.pac),concepto:f.serv,monto:+f.total||0,pago:f.pago,factura:f.id});DB.set('cajas',cajas);}







}















function printHtmlDocument(html){







  const w=window.open('','_blank');







  if(!w){toast('Permite ventanas emergentes para imprimir el RIDE','err');return;}







  w.document.write(html);







  w.document.close();







  setTimeout(()=>w.print(),400);







}















async function printComprobante(id,format='a4'){







  try{







    const res=await API.post('/api/invoices/ride',{id,format});







    printHtmlDocument(res.html);







  }catch(err){







    toast(err.message||'No se pudo generar RIDE desde el servidor, imprimiendo copia local','err');







    printLocalComprobante(id);







  }







}















function downloadTextFile(filename,content,type='text/plain'){







  const blob=new Blob([content||''],{type});







  const url=URL.createObjectURL(blob);







  const a=document.createElement('a');a.href=url;a.download=filename||'archivo.txt';document.body.appendChild(a);a.click();a.remove();







  setTimeout(()=>URL.revokeObjectURL(url),1000);







}















async function downloadInvoiceXml(id){







  try{







    const res=await API.post('/api/invoices/xml',{id});







    downloadTextFile(res.filename||`${id}.xml`,res.xml||'', 'application/xml;charset=utf-8');







    toast('XML descargado','ok');







  }catch(err){toast(err.message||'No se pudo descargar XML','err');}







}















function retrySriInvoice(id){openInvoiceDelivery(id,'sri');}
function emailInvoice(id){openInvoiceDelivery(id,'email');}

function printLocalComprobante(id){







  const f=(DB.get('facturas')||[]).find(x=>x.id===id);if(!f)return;







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+f.pac)||{};







  const cfg=DB.get('config')||{};







  const rows=(f.items||[{desc:f.serv,cant:1,unit:f.sub,total:f.sub}]).map(i=>`<tr><td>${esc(i.desc)}</td><td>${i.cant}</td><td>${fmtMoney(i.unit)}</td><td>${fmtMoney(i.total)}</td></tr>`).join('');







  const logo=cfg.logo||DEFAULT_LOGO;







  printDoc('RIDE SRI',`<div class="hdr"><img class="logo" src="${logo}"><div><div class="big">${cfg.nombre||'Centro Médico'}</div><div class="muted">RUC: ${cfg.ruc||'—'} · ${cfg.dir||''}</div><div class="muted">RIDE / comprobante electrónico</div></div></div><div class="row"><div><div class="label">Factura</div>${f.id}</div><div><div class="label">Fecha</div>${fmtDate(f.fecha)}</div></div><div class="box"><div><span class="label">Paciente:</span> ${p.nombres||''} ${p.apellidos||''}</div><div><span class="label">Cédula/RUC:</span> ${p.cedula||'—'}</div><div><span class="label">Especialidad:</span> ${f.esp||''}</div></div><table width="100%" border="1" cellspacing="0" cellpadding="6"><thead><tr><th>Descripción</th><th>Cant.</th><th>P.Unit.</th><th>Total</th></tr></thead><tbody>${rows}</tbody></table><div style="text-align:right;margin-top:12px;"><div>Subtotal: ${fmtMoney(f.sub)}</div><div>IVA: ${fmtMoney(f.iva)}</div><div class="big">Total: ${fmtMoney(f.total)}</div></div><div class="box"><div class="label">Clave de acceso</div>${f.claveAcceso||'—'}<br><span class="label">Autorización</span><br>${f.autorizacion||'—'}<br><span class="label">Estado</span><br>${f.estado||'—'}</div>`);







}







// =========================================================







// REPORTES







// =========================================================







function renderReportes(){







  const period=document.getElementById('rep-per')?.value||'mes';
  const end=today();
  const startDate=new Date(end+'T12:00:00');
  if(period==='semana') startDate.setDate(startDate.getDate()-((startDate.getDay()+6)%7));
  else if(period==='mes') startDate.setDate(1);
  else if(period!=='hoy') {startDate.setMonth(0);startDate.setDate(1);}
  const start=`${startDate.getFullYear()}-${String(startDate.getMonth()+1).padStart(2,'0')}-${String(startDate.getDate()).padStart(2,'0')}`;
  const inPeriod=value=>{const date=String(value||'').slice(0,10);return date>=start&&date<=end;};
  const facs=(DB.get('facturas')||[]).filter(f=>inPeriod(f.fecha)&&['Pagado','Autorizado SRI'].includes(f.estado)&&!f.demo&&!f.isDemo&&!(f.fecha==='2025-06-16'&&['001-001-000001842','001-001-000001843','001-001-000001844'].includes(f.id))).map(f=>({...f,total:Number(f.total)||0}));
  const citas=(DB.get('citas')||[]).filter(c=>inPeriod(c.fecha)&&['atendida','atendido','completada','completado','realizada','finalizada'].includes(String(c.estado||'').toLowerCase())&&!c.demo&&!c.isDemo);
  const attendedIds=new Set([...citas,...facs].map(x=>String(x.pac||'')).filter(Boolean));
  const pacs=(DB.get('pacientes')||[]).filter(p=>attendedIds.has(String(p.id)));








  const total=facs.reduce((a,f)=>a+f.total,0);







  document.getElementById('rep-stats').innerHTML=`







    <div class="stat-box"><div class="stat-lbl">Ingresos totales</div><div class="stat-val" style="font-size:20px;color:var(--green);">${fmtMoney(total)}</div><div class="stat-sub up">Comprobantes válidos del período</div></div>







    <div class="stat-box"><div class="stat-lbl">Pacientes atendidos</div><div class="stat-val" style="font-size:20px;">${pacs.length}</div><div class="stat-sub">En el período</div></div>







    <div class="stat-box"><div class="stat-lbl">Ticket promedio</div><div class="stat-val" style="font-size:20px;">${fmtMoney(facs.length?total/facs.length:0)}</div><div class="stat-sub">Por comprobante válido</div></div>







    <div class="stat-box"><div class="stat-lbl">Citas realizadas</div><div class="stat-val" style="font-size:20px;">${citas.length}</div><div class="stat-sub">Atenciones completadas</div></div>`;







  const esps=DB.get('especialidades')||[];







  const byEsp={};facs.forEach(f=>{byEsp[f.esp]=(byEsp[f.esp]||0)+f.total;});







  const maxE=Math.max(1,...Object.values(byEsp));







  document.getElementById('rep-esp').innerHTML=esps.map(e=>`







    <div style="margin-bottom:10px;">







      <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px;"><span>${e.nombre}</span><strong>${fmtMoney(byEsp[e.nombre]||0)}</strong></div>







      <div class="progress"><div class="prog-fill" style="width:${Math.round((byEsp[e.nombre]||0)/maxE*100)}%;background:${e.color};"></div></div>







    </div>`).join('');







  const byPago={};facs.forEach(f=>{byPago[f.pago]=(byPago[f.pago]||0)+f.total;});







  const colors=['#1B4F8A','#0D7A6B','#C47A0A','#B83232','#2A7A3B','#5A5A6A'];







  let piHtml='';Object.entries(byPago).forEach(([k,v],i)=>{piHtml+=`<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:12px;"><span style="width:12px;height:12px;background:${colors[i%colors.length]};border-radius:3px;display:inline-block;flex-shrink:0;"></span><span style="flex:1;">${k}</span><strong>${fmtMoney(v)} (${(total?Math.round(v/total*100):0)}%)</strong></div>`;});







  document.getElementById('rep-pagos').innerHTML=piHtml||'<div class="text-muted">Sin ingresos registrados en este período — $0.00</div>';







}















// =========================================================







// PACIENTES CRUD







// =========================================================







function renderPacs(){
  let trashButton=document.getElementById('patient-trash-button');
  if(!trashButton){trashButton=document.createElement('button');trashButton.id='patient-trash-button';trashButton.className='btn-s mb12';trashButton.textContent='Papelera de pacientes';trashButton.onclick=showPatientTrash;document.getElementById('pac-tbody').closest('.tbl-wrap').before(trashButton);}
  trashButton.hidden=currentUser?.rol!=='admin';








  if(!hasPerm('pacientes')) return;







  const q=(document.getElementById('pac-q')?.value||'').toLowerCase();







  const espF=document.getElementById('pac-esp-f')?.value||'';







  const pacs=(DB.get('pacientes')||[]).filter(p=>{







    const n=(p.nombres+' '+p.apellidos+p.cedula+p.tel).toLowerCase();







    return n.includes(q)&&(!espF||p.esp===espF);







  });







  fillPacEspFilter();







  document.getElementById('pac-tbody').innerHTML=pacs.map(p=>`







    <tr>







      <td><div style="display:flex;align-items:center;gap:8px;"><div class="av sm" style="background:${getEspColor(p.esp)}22;color:${getEspColor(p.esp)};">${(p.nombres[0]+p.apellidos[0]).toUpperCase()}</div><div><div class="fw5">${p.nombres} ${p.apellidos}</div><div class="text-xs text-muted">${p.email||'—'}</div></div></div></td>







      <td>${p.cedula}</td><td>${patientAge(p)} años</td><td>${p.tel||'—'}</td>







      <td><span class="badge" style="background:${getEspColor(p.esp)}22;color:${getEspColor(p.esp)};">${p.esp}</span></td>







      <td>${p.seguro||'—'}</td><td>${fmtDate(p.ultima)}</td>







      <td style="white-space:nowrap;">







        ${hasPerm('hce')?`<button class="btn-ic" title="Ver HCE" onclick="showMod('hce',document.querySelector('[data-module=hce]'));setTimeout(()=>selectPat(${p.id}),200)"><i class="ti ti-notes-medical" style="font-size:14px;color:var(--secondary);"></i></button>`:''}







        ${currentUser?.rol!=='medico'?`<button class="btn-s btn-sm" title="Cuenta y abonos" onclick="openPatientAccount(${p.id})">Cuenta / abonos</button>
        <button class="btn-ic" title="Editar" onclick="editPacModal(${p.id})"><i class="ti ti-edit" style="font-size:14px;color:var(--primary);"></i></button>`:''}







        ${['admin','recepcion','secretaria'].includes(currentUser?.rol)?`<button class="btn-ic" title="Enviar a papelera" onclick="deletePac(${p.id})"><i class="ti ti-trash" style="font-size:14px;color:var(--red);"></i></button>`:''}







      </td>







    </tr>`).join('')||'<tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text3);">Sin pacientes registrados</td></tr>';







}















function fillPacEspFilter(){







  const esps=DB.get('especialidades')||[];







  const sel=document.getElementById('pac-esp-f');







  if(!sel)return;







  const cur=sel.value;







  sel.innerHTML='<option value="">Todas las especialidades</option>'+esps.map(e=>`<option ${e.nombre===cur?'selected':''}>${e.nombre}</option>`).join('');







}















function openPacModal(){
  if(currentUser?.rol==='medico')return;
  if(typeof returnToWalkinAfterPac!=='undefined')returnToWalkinAfterPac=false;
  document.getElementById('patient-account-link')?.remove();







  if(!hasPerm('pacientes')){toast('No tienes permiso para administrar pacientes','err');return;}







  returnToCitaAfterPac=false;







  document.getElementById('p-edit-id').value='';







  document.getElementById('m-pac-title').textContent='Registrar paciente';







  ['p-nombres','p-apellidos','p-cedula','p-tel','p-email','p-dir','p-alergias','p-antec'].forEach(id=>document.getElementById(id).value='');







  document.getElementById('p-fnac').value='';
  document.getElementById('p-edad').value='';syncPatientAge();







  fillPacModalSelects();openM('m-pac');







}















function openPacFromCita(){
  if(currentUser?.rol==='medico')return;
  if(typeof returnToWalkinAfterPac!=='undefined')returnToWalkinAfterPac=false;







  if(!hasPerm('agenda')&&!hasPerm('pacientes')){toast('No tienes permiso para registrar pacientes','err');return;}







  returnToCitaAfterPac=true;







  closeM('m-cita');







  document.getElementById('p-edit-id').value='';







  document.getElementById('m-pac-title').textContent='Registrar paciente para cita';







  ['p-nombres','p-apellidos','p-cedula','p-tel','p-email','p-dir','p-alergias','p-antec'].forEach(id=>document.getElementById(id).value='');







  document.getElementById('p-fnac').value='';
  document.getElementById('p-edad').value='';syncPatientAge();







  fillPacModalSelects();







  openM('m-pac');







}















function editPacModal(id){
  if(currentUser?.rol==='medico')return;







  if(!hasPerm('pacientes')){toast('No tienes permiso para editar pacientes','err');return;}







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+id);if(!p)return;







  document.getElementById('p-edit-id').value=p.id;







  document.getElementById('m-pac-title').textContent='Editar paciente';







  fillPacModalSelects();







  setTimeout(()=>{







    document.getElementById('p-nombres').value=p.nombres||'';







    document.getElementById('p-apellidos').value=p.apellidos||'';







    document.getElementById('p-cedula').value=p.cedula||'';







    document.getElementById('p-fnac').value=p.fnac||'';
    document.getElementById('p-edad').value=p.edadDeclarada??'';syncPatientAge();







    document.getElementById('p-genero').value=p.genero||'Masculino';







    document.getElementById('p-tel').value=p.tel||'';







    document.getElementById('p-email').value=p.email||'';







    document.getElementById('p-dir').value=p.dir||'';







    document.getElementById('p-esp').value=p.esp||'';







    document.getElementById('p-seg').value=p.seguro||'';







    document.getElementById('p-sangre').value=p.sangre||'Desconocido';







    document.getElementById('p-alergias').value=p.alergias||'';







    document.getElementById('p-antec').value=p.antec||'';







  },50);







  let accountLink=document.getElementById('patient-account-link');
  if(!accountLink){accountLink=document.createElement('button');accountLink.id='patient-account-link';accountLink.type='button';accountLink.className='btn-s mt12';document.getElementById('m-pac').querySelector('.modal').appendChild(accountLink);}
  accountLink.textContent='Ver cuenta, saldo y abonos';accountLink.onclick=()=>openPatientAccount(id);
  openM('m-pac');







}















function fillPacModalSelects(){







  const esps=DB.get('especialidades')||[];







  const segs=DB.get('seguros')||[];







  document.getElementById('p-esp').innerHTML=esps.map(e=>`<option>${e.nombre}</option>`).join('');







  document.getElementById('p-seg').innerHTML='<option value="">Ninguno</option>'+segs.map(s=>`<option>${s.nombre}</option>`).join('');







}















let savingPatient=false;
async function savePac(){if(savingPatient)return;savingPatient=true;try{await savePacInternal();}finally{savingPatient=false;}}
async function savePacInternal(){
  if(currentUser?.rol==='medico')return;







  if(!hasPerm('pacientes')&&!returnToCitaAfterPac&&!(typeof returnToWalkinAfterPac!=='undefined'&&returnToWalkinAfterPac&&hasPerm('agenda'))){toast('No tienes permiso para guardar pacientes','err');return;}







  const nombres=document.getElementById('p-nombres').value.trim();







  const apellidos=document.getElementById('p-apellidos').value.trim();







  const cedula=document.getElementById('p-cedula').value.trim();







  if(!nombres||!apellidos||!cedula){toast('Completa los campos obligatorios','err');return;}







  const ageInput=document.getElementById('p-edad').value;
  if(!document.getElementById('p-fnac').value&&ageInput!==''&&(!Number.isInteger(Number(ageInput))||Number(ageInput)<0||Number(ageInput)>130)){toast('Ingresa una edad entera entre 0 y 130 años.','err');return;}
  const obj={nombres,apellidos,cedula,fnac:document.getElementById('p-fnac').value,genero:document.getElementById('p-genero').value,tel:document.getElementById('p-tel').value,email:document.getElementById('p-email').value,dir:document.getElementById('p-dir').value,esp:document.getElementById('p-esp').value,seguro:document.getElementById('p-seg').value,sangre:document.getElementById('p-sangre').value,alergias:document.getElementById('p-alergias').value,antec:document.getElementById('p-antec').value,ultima:today()};







  obj.edadDeclarada=!obj.fnac&&ageInput!==''?Number(ageInput):null;
  obj.edadDeclaradaFecha=obj.edadDeclarada!==null?today():null;
  const editId=document.getElementById('p-edit-id').value;







  const pacs=DB.get('pacientes')||[];







  let newId=null;







  if(editId){const i=pacs.findIndex(x=>x.id===+editId);if(i>=0)pacs[i]={...pacs[i],...obj};}







  else{obj.id=DB.nextId('pac');newId=obj.id;pacs.push(obj);}







  const patientSaved=await DB.set('pacientes',pacs);
  if(!patientSaved){if(newId)document.getElementById('p-edit-id').value=newId;toast('No se guardó el paciente. Revisa el error y vuelve a intentar.','err');return;}







  closeM('m-pac');toast(editId?'Paciente actualizado':'Paciente registrado exitosamente','ok');







  renderPacs();initDashboard();







  if(typeof returnToWalkinAfterPac!=='undefined'&&returnToWalkinAfterPac){walkinPatientSaved(newId||editId);}
  if(returnToCitaAfterPac){







    returnToCitaAfterPac=false;







    openCitaModal();







    setTimeout(()=>{document.getElementById('c-pac').value=newId||'';},50);







  }







}















function deletePac(id){
  if(!['admin','recepcion','secretaria'].includes(currentUser?.rol)){toast('No tienes permiso para eliminar pacientes','err');return;}
  cashModal('m-archive-patient','Enviar paciente a papelera',`<p>${esc(getPacName(id))}</p><label>Motivo de eliminación<textarea id="patient-delete-reason" minlength="5" maxlength="1000" placeholder="Explica por qué se elimina este registro"></textarea></label><p>El administrador podrá revisar el motivo y restaurar el paciente.</p><button class="btn-d mt12" onclick="archivePatient(${id},this)">Enviar a papelera</button>`);
}
async function archivePatient(id,button){
 const reason=document.getElementById('patient-delete-reason').value.trim();if(reason.length<5){toast('Escribe el motivo de eliminación (mínimo 5 caracteres).','err');return;}
 button.disabled=true;
 try{await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de continuar.');await API.post('/api/patients/archive',{patientId:id,reason});const res=await API.get('/api/data');DB.load(res.data);closeM('m-archive-patient');renderPacs();toast('Paciente enviado a papelera. Motivo registrado.','ok');}catch(e){toast(e.message,'err');}finally{button.disabled=false;}
}
async function showPatientTrash(){
 if(currentUser?.rol!=='admin')return;
 try{const result=await API.get('/api/patients/trash');cashModal('m-patient-trash','Papelera de pacientes',result.patients.map(p=>`<article class="cash-account"><strong>${esc(p.nombres)} ${esc(p.apellidos)}</strong><p>Eliminado: ${esc(p.deletedAt)} · Por: ${esc(p.deletedByName||p.deletedBy)}</p><p>Motivo: ${esc(p.deletionReason)}</p><button class="btn-g" onclick="restorePatient(${p.id},this)">Restaurar paciente</button></article>`).join('')||'<p>La papelera está vacía.</p>');}catch(e){toast(e.message,'err');}
}
async function restorePatient(id,button){button.disabled=true;try{await DB.tail;if(DB.failures.size)throw new Error('Resuelve los cambios sin guardar antes de continuar.');await API.post('/api/patients/restore',{patientId:id});DB.load((await API.get('/api/data')).data);renderPacs();await showPatientTrash();toast('Paciente restaurado.','ok');}catch(e){toast(e.message,'err');button.disabled=false;}}


function renderMeds(){







  const q=(document.getElementById('med-q')?.value||'').toLowerCase();







  const meds=(DB.get('medicos')||[]).filter(m=>m.nombre.toLowerCase().includes(q)||m.esp.toLowerCase().includes(q));







  document.getElementById('meds-grid').innerHTML=meds.map(m=>`







    <div class="card">







      <div class="card-body">







        <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">







          <div class="av lg" style="background:${getEspColor(m.esp)}22;color:${getEspColor(m.esp)};">${m.nombre.replace(/Dr[a]?\. /,'').split(' ').map(x=>x[0]).join('').substring(0,2).toUpperCase()}</div>







          <div><div class="fw6" style="font-size:14px;">${m.nombre}</div><span class="badge" style="background:${getEspColor(m.esp)}22;color:${getEspColor(m.esp)};">${esc(doctorSpecialties(m).join(' / '))}</span></div>







        </div>







        <div class="text-sm mb4"><i class="ti ti-id-badge" style="font-size:13px;color:var(--text3);"></i> ${m.cedula||'—'}</div>







        <div class="text-sm mb4"><i class="ti ti-certificate" style="font-size:13px;color:var(--text3);"></i> ${m.sen||'—'}</div>







        <div class="text-sm mb4"><i class="ti ti-clock" style="font-size:13px;color:var(--text3);"></i> ${m.horario||'—'}</div>







        <div class="text-sm mb12"><i class="ti ti-phone" style="font-size:13px;color:var(--text3);"></i> ${m.tel||'—'}</div>







        <div style="display:flex;gap:6px;">







          <button class="btn-s btn-sm" onclick="editMedModal(${m.id})"><i class="ti ti-edit"></i> Editar</button>







          <button class="btn-s btn-sm" onclick="deleteMed(${m.id})"><i class="ti ti-trash" style="color:var(--red);"></i></button>







        </div>







      </div>







    </div>`).join('')||'<div class="text-muted text-sm">Sin médicos registrados</div>';







}















function openMedModal(){







  document.getElementById('md-edit-id').value='';







  document.getElementById('m-med-title').textContent='Registrar médico';







  ['md-nombre','md-ced','md-sen','md-horario','md-tel','md-email'].forEach(id=>document.getElementById(id).value='');







  fillMedEsp();openM('m-med');







}







function editMedModal(id){







  const m=(DB.get('medicos')||[]).find(x=>x.id===+id);if(!m)return;







  document.getElementById('md-edit-id').value=m.id;







  document.getElementById('m-med-title').textContent='Editar médico';







  fillMedEsp();







  setTimeout(()=>{







    document.getElementById('md-nombre').value=m.nombre||'';







    document.getElementById('md-esp').value=m.esp||'';
    document.getElementById('md-esp2').value=m.esp2||'';
    document.getElementById('md-esp3').value=m.esp3||'';
    document.getElementById('md-esp4').value=m.esp4||'';







    document.getElementById('md-ced').value=m.cedula||'';







    document.getElementById('md-sen').value=m.sen||'';







    document.getElementById('md-horario').value=m.horario||'';







    document.getElementById('md-tel').value=m.tel||'';







    document.getElementById('md-email').value=m.email||'';







  },50);







  openM('m-med');







}







function fillMedEsp(){const esps=DB.get('especialidades')||[];const options=esps.map(e=>`<option>${esc(e.nombre)}</option>`).join('');document.getElementById('md-esp').innerHTML=options;for(const n of [2,3,4])document.getElementById('md-esp'+n).innerHTML='<option value="">Sin especialidad adicional</option>'+options;}







function saveMed(){







  const nombre=document.getElementById('md-nombre').value.trim();







  if(!nombre){toast('Ingresa el nombre del médico','err');return;}







  const obj={nombre,esp:document.getElementById('md-esp').value,esp2:document.getElementById('md-esp2').value,esp3:document.getElementById('md-esp3').value,esp4:document.getElementById('md-esp4').value,cedula:document.getElementById('md-ced').value,sen:document.getElementById('md-sen').value,horario:document.getElementById('md-horario').value,tel:document.getElementById('md-tel').value,email:document.getElementById('md-email').value};







  const selected=[obj.esp,obj.esp2,obj.esp3,obj.esp4].filter(Boolean);
  if(!obj.esp||new Set(selected).size!==selected.length){toast('Selecciona la especialidad principal y evita especialidades repetidas.','err');return;}
  const editId=document.getElementById('md-edit-id').value;







  const meds=DB.get('medicos')||[];







  if(editId){const i=meds.findIndex(x=>x.id===+editId);if(i>=0)meds[i]={...meds[i],...obj};}







  else{obj.id=DB.nextId('med');meds.push(obj);}







  DB.set('medicos',meds);closeM('m-med');toast(editId?'Médico actualizado':'Médico registrado','ok');renderMeds();







}







function deleteMed(id){







  const m=(DB.get('medicos')||[]).find(x=>x.id===+id);







  confirmDelete(`¿Eliminar al médico ${m?.nombre}?`,()=>{







    const meds=(DB.get('medicos')||[]).filter(x=>x.id!==+id);DB.set('medicos',meds);renderMeds();toast('Médico eliminado','inf');







  });







}















// =========================================================







// ESPECIALIDADES CRUD







// =========================================================







function renderEsps(){







  const esps=DB.get('especialidades')||[];







  const pacs=DB.get('pacientes')||[];







  const meds=DB.get('medicos')||[];







  document.getElementById('esp-tbody').innerHTML=esps.map(e=>`







    <tr>







      <td><div style="display:flex;align-items:center;gap:8px;"><span style="width:14px;height:14px;background:${e.color};border-radius:50%;display:inline-block;"></span><strong>${e.nombre}</strong></div><div class="text-xs text-muted">${e.desc||'—'}</div></td>







      <td><div style="width:28px;height:28px;background:${e.color};border-radius:var(--radius);"></div></td>







      <td>${meds.filter(m=>doctorSpecialties(m).includes(e.nombre)).length} médico(s)</td>







      <td>${pacs.filter(p=>p.esp===e.nombre).length} paciente(s)</td>







      <td><span class="badge ${e.estado==='activo'?'b-green':'b-gray'}">${e.estado==='activo'?'Activo':'Inactivo'}</span></td>







      <td style="white-space:nowrap;">







        <button class="btn-ic" title="Editar" onclick="editEspModal(${e.id})"><i class="ti ti-edit" style="font-size:14px;color:var(--primary);"></i></button>







        <button class="btn-ic" title="Eliminar" onclick="deleteEsp(${e.id})"><i class="ti ti-trash" style="font-size:14px;color:var(--red);"></i></button>







      </td>







    </tr>`).join('');







}















function openEspModal(){







  document.getElementById('esp-edit-id').value='';







  document.getElementById('m-esp-title').textContent='Nueva especialidad';







  document.getElementById('esp-nombre').value='';







  document.getElementById('esp-color').value='#1B4F8A';







  document.getElementById('esp-desc').value='';







  document.getElementById('esp-estado').value='activo';







  openM('m-esp');







}







function editEspModal(id){







  const e=(DB.get('especialidades')||[]).find(x=>x.id===+id);if(!e)return;







  document.getElementById('esp-edit-id').value=e.id;







  document.getElementById('m-esp-title').textContent='Editar especialidad';







  document.getElementById('esp-nombre').value=e.nombre;







  document.getElementById('esp-color').value=e.color;







  document.getElementById('esp-desc').value=e.desc||'';







  document.getElementById('esp-estado').value=e.estado;







  openM('m-esp');







}







function saveEsp(){







  const nombre=document.getElementById('esp-nombre').value.trim();







  if(!nombre){toast('Ingresa el nombre de la especialidad','err');return;}







  const obj={nombre,color:document.getElementById('esp-color').value,desc:document.getElementById('esp-desc').value,estado:document.getElementById('esp-estado').value};







  const editId=document.getElementById('esp-edit-id').value;







  const esps=DB.get('especialidades')||[];







  if(editId){const i=esps.findIndex(x=>x.id===+editId);if(i>=0)esps[i]={...esps[i],...obj};}







  else{obj.id=DB.nextId('esp');esps.push(obj);}







  DB.set('especialidades',esps);closeM('m-esp');toast(editId?'Especialidad actualizada':'Especialidad creada','ok');renderEsps();







}







function deleteEsp(id){







  const e=(DB.get('especialidades')||[]).find(x=>x.id===+id);







  confirmDelete(`¿Eliminar la especialidad "${e?.nombre}"?`,()=>{







    const esps=(DB.get('especialidades')||[]).filter(x=>x.id!==+id);DB.set('especialidades',esps);renderEsps();toast('Especialidad eliminada','inf');







  });







}















// =========================================================







// SEGUROS CRUD







// =========================================================







function renderSegs(){







  const segs=DB.get('seguros')||[];







  document.getElementById('seg-tbody').innerHTML=segs.map(s=>`







    <tr>







      <td><div style="display:flex;align-items:center;gap:8px;"><i class="ti ti-shield-check" style="color:var(--green);font-size:16px;"></i><strong>${s.nombre}</strong></div></td>







      <td>${s.tipo}</td><td>${s.copago}%</td><td class="text-sm">${s.cobertura||'—'}</td><td class="text-sm">${s.contacto||'—'}</td>







      <td><span class="badge ${s.estado==='activo'?'b-green':'b-gray'}">${s.estado==='activo'?'Activo':'Inactivo'}</span></td>







      <td style="white-space:nowrap;">







        <button class="btn-ic" onclick="editSegModal(${s.id})"><i class="ti ti-edit" style="font-size:14px;color:var(--primary);"></i></button>







        <button class="btn-ic" onclick="deleteSeg(${s.id})"><i class="ti ti-trash" style="font-size:14px;color:var(--red);"></i></button>







      </td>







    </tr>`).join('');







}







function openSegModal(){







  document.getElementById('sg-edit-id').value='';document.getElementById('m-seg-title').textContent='Nuevo convenio';







  ['sg-nombre','sg-copago','sg-cobertura','sg-contacto'].forEach(id=>document.getElementById(id).value='');







  document.getElementById('sg-copago').value='0';document.getElementById('sg-estado').value='activo';openM('m-seg');







}







function editSegModal(id){







  const s=(DB.get('seguros')||[]).find(x=>x.id===+id);if(!s)return;







  document.getElementById('sg-edit-id').value=s.id;document.getElementById('m-seg-title').textContent='Editar convenio';







  document.getElementById('sg-nombre').value=s.nombre||'';document.getElementById('sg-tipo').value=s.tipo||'Privado';







  document.getElementById('sg-copago').value=s.copago||'0';document.getElementById('sg-cobertura').value=s.cobertura||'';







  document.getElementById('sg-contacto').value=s.contacto||'';document.getElementById('sg-estado').value=s.estado||'activo';openM('m-seg');







}







function saveSeg(){







  const nombre=document.getElementById('sg-nombre').value.trim();







  if(!nombre){toast('Ingresa el nombre del seguro','err');return;}







  const obj={nombre,tipo:document.getElementById('sg-tipo').value,copago:+document.getElementById('sg-copago').value,cobertura:document.getElementById('sg-cobertura').value,contacto:document.getElementById('sg-contacto').value,estado:document.getElementById('sg-estado').value};







  const editId=document.getElementById('sg-edit-id').value;







  const segs=DB.get('seguros')||[];







  if(editId){const i=segs.findIndex(x=>x.id===+editId);if(i>=0)segs[i]={...segs[i],...obj};}







  else{obj.id=DB.nextId('seg');segs.push(obj);}







  DB.set('seguros',segs);closeM('m-seg');toast(editId?'Convenio actualizado':'Convenio registrado','ok');renderSegs();







}







function deleteSeg(id){







  const s=(DB.get('seguros')||[]).find(x=>x.id===+id);







  confirmDelete(`¿Eliminar el convenio con ${s?.nombre}?`,()=>{







    const segs=(DB.get('seguros')||[]).filter(x=>x.id!==+id);DB.set('seguros',segs);renderSegs();toast('Convenio eliminado','inf');







  });







}















// =========================================================







// QUIRÓFANOS / EQUIPOS / STOCK







// =========================================================







function badgeEstadoQx(estado){







  const cls=estado==='Disponible'?'b-green':estado==='Ocupado'||estado==='En uso'?'b-amber':estado==='Limpieza'?'b-blue':'b-red';







  return `<span class="badge ${cls}">${estado}</span>`;







}















function renderQuirofanos(){







  const qx=DB.get('quirofanos')||[];







  const eq=DB.get('equipos')||[];







  const st=DB.get('stockQx')||[];







  document.getElementById('qx-tbody').innerHTML=qx.map(q=>`<tr><td class="fw5">${q.nombre}</td><td>${badgeEstadoQx(q.estado)}</td><td class="text-r"><select onchange="setQuirofanoEstado(${q.id},this.value)" style="width:140px;"><option ${q.estado==='Disponible'?'selected':''}>Disponible</option><option ${q.estado==='Ocupado'?'selected':''}>Ocupado</option><option ${q.estado==='Limpieza'?'selected':''}>Limpieza</option><option ${q.estado==='Mantenimiento'?'selected':''}>Mantenimiento</option></select><button class="btn-ic" onclick="deleteQuirofano(${q.id})"><i class="ti ti-trash"></i></button></td></tr>`).join('')||'<tr><td colspan="3" class="text-c text-muted">Sin quirófanos registrados</td></tr>';







  document.getElementById('eq-tbody').innerHTML=eq.map(e=>`<tr><td class="fw5">${e.nombre}</td><td>${badgeEstadoQx(e.estado)}</td><td class="text-r"><select onchange="setEquipoEstado(${e.id},this.value)" style="width:150px;"><option ${e.estado==='Disponible'?'selected':''}>Disponible</option><option ${e.estado==='En uso'?'selected':''}>En uso</option><option ${e.estado==='Mantenimiento'?'selected':''}>Mantenimiento</option><option ${e.estado==='Fuera de servicio'?'selected':''}>Fuera de servicio</option></select><button class="btn-ic" onclick="deleteEquipo(${e.id})"><i class="ti ti-trash"></i></button></td></tr>`).join('')||'<tr><td colspan="3" class="text-c text-muted">Sin equipos registrados</td></tr>';







  document.getElementById('st-tbody').innerHTML=st.map(s=>`<tr><td class="fw5">${s.nombre}</td><td><input type="number" value="${s.cantidad}" onchange="setStockCantidad(${s.id},this.value)" style="width:76px;"/></td><td>${s.minimo}</td><td>${(+s.cantidad)<= (+s.minimo)?'<span class="badge b-red">Bajo stock</span>':'<span class="badge b-green">OK</span>'}</td><td class="text-r"><button class="btn-ic" onclick="deleteStock(${s.id})"><i class="ti ti-trash"></i></button></td></tr>`).join('')||'<tr><td colspan="5" class="text-c text-muted">Sin material registrado</td></tr>';







}















function addQuirofano(){







  const nombre=document.getElementById('qx-nombre').value.trim();







  const estado=document.getElementById('qx-estado').value;







  if(!nombre){toast('Ingresa el nombre del quirófano','err');return;}







  const qx=DB.get('quirofanos')||[];qx.push({id:DB.nextId('qx'),nombre,estado});DB.set('quirofanos',qx);







  document.getElementById('qx-nombre').value='';toast('Quirófano guardado','ok');renderQuirofanos();







}







function setQuirofanoEstado(id,estado){const qx=DB.get('quirofanos')||[];const q=qx.find(x=>x.id===id);if(q){q.estado=estado;DB.set('quirofanos',qx);toast('Estado de quirófano actualizado','ok');renderQuirofanos();}}







function deleteQuirofano(id){confirmDelete('¿Eliminar quirófano?',()=>{DB.set('quirofanos',(DB.get('quirofanos')||[]).filter(x=>x.id!==id));renderQuirofanos();toast('Quirófano eliminado','ok');});}















function addEquipo(){







  const nombre=document.getElementById('eq-nombre').value.trim();







  const estado=document.getElementById('eq-estado').value;







  if(!nombre){toast('Ingresa el nombre del equipo','err');return;}







  const eq=DB.get('equipos')||[];eq.push({id:DB.nextId('eq'),nombre,estado});DB.set('equipos',eq);







  document.getElementById('eq-nombre').value='';toast('Equipo guardado','ok');renderQuirofanos();







}







function setEquipoEstado(id,estado){const eq=DB.get('equipos')||[];const e=eq.find(x=>x.id===id);if(e){e.estado=estado;DB.set('equipos',eq);toast('Disponibilidad actualizada','ok');renderQuirofanos();}}







function deleteEquipo(id){confirmDelete('¿Eliminar equipo?',()=>{DB.set('equipos',(DB.get('equipos')||[]).filter(x=>x.id!==id));renderQuirofanos();toast('Equipo eliminado','ok');});}















function addStock(){







  const nombre=document.getElementById('st-nombre').value.trim();







  const cantidad=+(document.getElementById('st-cant').value||0);







  const minimo=+(document.getElementById('st-min').value||0);







  if(!nombre){toast('Ingresa el material quirúrgico','err');return;}







  const st=DB.get('stockQx')||[];st.push({id:DB.nextId('st'),nombre,cantidad,minimo});DB.set('stockQx',st);







  document.getElementById('st-nombre').value='';document.getElementById('st-cant').value=0;toast('Material guardado','ok');renderQuirofanos();







}







function setStockCantidad(id,cantidad){const st=DB.get('stockQx')||[];const s=st.find(x=>x.id===id);if(s){s.cantidad=+cantidad||0;DB.set('stockQx',st);toast('Stock actualizado','ok');renderQuirofanos();}}







function deleteStock(id){confirmDelete('¿Eliminar material del stock?',()=>{DB.set('stockQx',(DB.get('stockQx')||[]).filter(x=>x.id!==id));renderQuirofanos();toast('Material eliminado','ok');});}















// =========================================================







// SERVICIOS / EXÁMENES / COTIZADOR







// =========================================================







let cotItems=[];















function allChargeItems(){







  const servicios=(DB.get('servicios')||[]).map(s=>({kind:'servicio',id:s.id,nombre:s.nombre,categoria:s.categoria||'Servicio',precio:+s.precio||0,descuento:0}));







  const examenes=(DB.get('examenes')||[]).map(e=>({kind:'examen',id:e.id,nombre:e.nombre,categoria:e.categoria||'Examen',precio:+e.precio||0,descuento:+e.descuento||0}));







  return [...servicios,...examenes];







}















function chargeItemKey(item){return `${item.kind}:${item.id}`;}







function chargeItemFinal(item,extra=0){const d=Math.min(100,Math.max(0,(+item.descuento||0)+(+extra||0)));return {discount:d,total:(+item.precio||0)*(1-d/100)};}







function chargeOptionsHtml(){return allChargeItems().map(i=>{const fin=chargeItemFinal(i);return `<option value="${chargeItemKey(i)}">${esc(i.nombre)} (${esc(i.categoria)}) — ${fmtMoney(fin.total)}</option>`;}).join('');}







function getChargeItem(key){const [kind,id]=String(key||'').split(':');return allChargeItems().find(i=>i.kind===kind&&i.id===+id);}















function renderServicios(){







  if(!hasPerm('servicios')) return;







  const isAdmin=currentUser?.rol==='admin';

  const canEdit=canEditCatalog('servicios');







  const adminForm=document.getElementById('srv-admin-form');







  if(adminForm) adminForm.style.display=canEdit?'block':'none';







  const servicios=DB.get('servicios')||[];







  document.getElementById('srv-tbody').innerHTML=servicios.map(s=>`<tr><td class="fw5">${esc(s.nombre)}</td><td>${esc(s.categoria||'Servicio')}</td><td class="fw6">${fmtMoney(s.precio)}</td><td class="text-r">${canEdit?`<button class="btn-ic" title="Editar precio" onclick="editServicio(${s.id})"><i class="ti ti-edit" style="color:var(--primary);"></i></button>${isAdmin?`<button class="btn-ic" title="Eliminar" onclick="deleteServicio(${s.id})"><i class="ti ti-trash" style="color:var(--red);"></i></button>`:''}`:''}</td></tr>`).join('')||'<tr><td colspan="4" class="text-c text-muted">Sin servicios registrados</td></tr>';







  const total=servicios.reduce((a,s)=>a+(+s.precio||0),0);







  document.getElementById('srv-summary').innerHTML=`<div class="stat-box"><div class="stat-lbl">Servicios</div><div class="stat-val">${servicios.length}</div><div class="stat-sub">Activos</div></div><div class="stat-box"><div class="stat-lbl">Precio promedio</div><div class="stat-val">${fmtMoney(servicios.length?total/servicios.length:0)}</div><div class="stat-sub">Referencial</div></div>`;







}















function addServicio(){







  if(!canEditCatalog('servicios')){toast('No tienes permiso para editar este catalogo','err');return;}







  const nombre=document.getElementById('srv-nombre').value.trim();







  const categoria=document.getElementById('srv-cat').value.trim()||'Servicio';







  const precio=+(document.getElementById('srv-precio').value||0);







  if(!nombre||precio<=0){toast('Ingresa nombre y precio del servicio','err');return;}







  const editId=+(document.getElementById('srv-edit-id').value||0);







  const servicios=DB.get('servicios')||[];







  if(editId){







    const i=servicios.findIndex(s=>s.id===editId);







    if(i>=0) servicios[i]={...servicios[i],nombre,categoria,precio};







  }else{







    servicios.push({id:DB.nextId('serv'),nombre,categoria,precio});







  }







  DB.set('servicios',servicios);







  resetServicioForm();







  toast(editId?'Servicio actualizado':'Servicio agregado','ok');renderServicios();refreshChargeSelectors();







}















function editServicio(id){







  if(!canEditCatalog('servicios')){toast('No tienes permiso para editar este catalogo','err');return;}







  const s=(DB.get('servicios')||[]).find(x=>x.id===id);if(!s)return;







  document.getElementById('srv-edit-id').value=s.id;







  document.getElementById('srv-nombre').value=s.nombre||'';







  document.getElementById('srv-cat').value=s.categoria||'Servicio';







  document.getElementById('srv-precio').value=s.precio||0;







  document.getElementById('srv-save-btn').innerHTML='<i class="ti ti-device-floppy"></i> Guardar cambios';







  document.getElementById('srv-cancel-btn').style.display='inline-flex';







  document.getElementById('srv-nombre').focus();







}















function resetServicioForm(){







  document.getElementById('srv-edit-id').value='';







  ['srv-nombre','srv-cat'].forEach(id=>document.getElementById(id).value='');







  document.getElementById('srv-precio').value=0;







  document.getElementById('srv-save-btn').innerHTML='<i class="ti ti-plus"></i> Agregar servicio';







  document.getElementById('srv-cancel-btn').style.display='none';







}















function deleteServicio(id){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede eliminar servicios','err');return;}







  confirmDelete('¿Eliminar este servicio?',()=>{DB.set('servicios',(DB.get('servicios')||[]).filter(s=>s.id!==id));renderServicios();refreshChargeSelectors();toast('Servicio eliminado','inf');});







}















function renderExamenes(){







  if(!hasPerm('examenes')) return;







  const isAdmin=currentUser?.rol==='admin';

  const canEdit=canEditCatalog('examenes');







  const adminForm=document.getElementById('ex-admin-form');







  if(adminForm) adminForm.style.display=canEdit?'block':'none';







  const examenes=DB.get('examenes')||[];







  document.getElementById('ex-tbody').innerHTML=examenes.map(e=>{const final=(+e.precio||0)*(1-(+e.descuento||0)/100);return `<tr><td class="fw5">${esc(e.nombre)}</td><td>${esc(e.categoria||'Examen')}</td><td>${fmtMoney(e.precio)}</td><td>${+e.descuento||0}%</td><td class="fw6" style="color:var(--green);">${fmtMoney(final)}</td><td class="text-r">${canEdit?`<button class="btn-ic" title="Editar precio" onclick="editExamen(${e.id})"><i class="ti ti-edit" style="color:var(--primary);"></i></button>${isAdmin?`<button class="btn-ic" title="Eliminar" onclick="deleteExamen(${e.id})"><i class="ti ti-trash" style="color:var(--red);"></i></button>`:''}`:''}</td></tr>`;}).join('')||'<tr><td colspan="6" class="text-c text-muted">Sin exámenes registrados</td></tr>';







  refreshChargeSelectors();







  renderCotizador();







}















function addExamen(){







  if(!canEditCatalog('examenes')){toast('No tienes permiso para editar este catalogo','err');return;}







  const nombre=document.getElementById('ex-nombre').value.trim();







  const categoria=document.getElementById('ex-cat').value.trim()||'Examen';







  const precio=+(document.getElementById('ex-precio').value||0);







  const descuento=Math.min(100,Math.max(0,+(document.getElementById('ex-desc').value||0)));







  if(!nombre||precio<=0){toast('Ingresa nombre y precio del examen','err');return;}







  const editId=+(document.getElementById('ex-edit-id').value||0);







  const examenes=DB.get('examenes')||[];







  if(editId){







    const i=examenes.findIndex(e=>e.id===editId);







    if(i>=0) examenes[i]={...examenes[i],nombre,categoria,precio,descuento};







  }else{







    examenes.push({id:DB.nextId('exam'),nombre,categoria,precio,descuento});







  }







  DB.set('examenes',examenes);







  resetExamenForm();







  toast(editId?'Examen actualizado':'Examen agregado','ok');renderExamenes();







}















function editExamen(id){







  if(!canEditCatalog('examenes')){toast('No tienes permiso para editar este catalogo','err');return;}







  const e=(DB.get('examenes')||[]).find(x=>x.id===id);if(!e)return;







  document.getElementById('ex-edit-id').value=e.id;







  document.getElementById('ex-nombre').value=e.nombre||'';







  document.getElementById('ex-cat').value=e.categoria||'Examen';







  document.getElementById('ex-precio').value=e.precio||0;







  document.getElementById('ex-desc').value=e.descuento||0;







  document.getElementById('ex-save-btn').innerHTML='<i class="ti ti-device-floppy"></i> Guardar cambios';







  document.getElementById('ex-cancel-btn').style.display='inline-flex';







  document.getElementById('ex-nombre').focus();







}















function resetExamenForm(){







  document.getElementById('ex-edit-id').value='';







  ['ex-nombre','ex-cat'].forEach(id=>document.getElementById(id).value='');







  document.getElementById('ex-precio').value=0;







  document.getElementById('ex-desc').value=0;







  document.getElementById('ex-save-btn').innerHTML='<i class="ti ti-plus"></i> Agregar examen';







  document.getElementById('ex-cancel-btn').style.display='none';







}















function deleteExamen(id){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede eliminar exámenes','err');return;}







  confirmDelete('¿Eliminar este examen?',()=>{DB.set('examenes',(DB.get('examenes')||[]).filter(e=>e.id!==id));renderExamenes();toast('Examen eliminado','inf');});







}















function refreshChargeSelectors(){







  const html=chargeOptionsHtml();







  ['cot-item','cb-serv','inline-serv'].forEach(id=>{const el=document.getElementById(id);if(el){const cur=el.value;el.innerHTML=html;if(cur)el.value=cur;}});







  const inlineMonto=document.getElementById('inline-monto');const inlineServ=document.getElementById('inline-serv');







  if(inlineMonto&&inlineServ) updateMontoFromService(inlineServ,inlineMonto);







  const cbMonto=document.getElementById('cb-monto');const cbServ=document.getElementById('cb-serv');







  if(cbMonto&&cbServ) updateMontoFromService(cbServ,cbMonto);







}















function updateMontoFromService(sel,input){







  const item=getChargeItem(sel.value);







  if(item&&input) input.value=chargeItemFinal(item).total.toFixed(2);







}















function renderCotizador(){







  const pacs=DB.get('pacientes')||[];







  const pacSel=document.getElementById('cot-pac');







  if(pacSel) pacSel.innerHTML='<option value="">Paciente sin seleccionar</option>'+pacs.map(p=>`<option value="${p.id}">${esc(p.nombres)} ${esc(p.apellidos)} — ${esc(p.cedula)}</option>`).join('');







  const itemSel=document.getElementById('cot-item');







  if(itemSel) itemSel.innerHTML=chargeOptionsHtml();







  renderCotItems();







  renderCotList();







}















function addCotItem(){







  if(!hasPerm('examenes')){toast('No tienes permiso para cotizar','err');return;}







  const item=getChargeItem(document.getElementById('cot-item').value);







  if(!item){toast('Selecciona un servicio o examen','err');return;}







  const cantidad=Math.max(1,+(document.getElementById('cot-cant').value||1));







  const extra=+(document.getElementById('cot-extra').value||0);







  const fin=chargeItemFinal(item,extra);







  cotItems.push({key:chargeItemKey(item),tipo:item.kind,nombre:item.nombre,categoria:item.categoria,cantidad,precio:item.precio,descuento:fin.discount,total:fin.total*cantidad});







  document.getElementById('cot-cant').value=1;document.getElementById('cot-extra').value=0;







  renderCotItems();







}















function renderCotItems(){







  const tbody=document.getElementById('cot-tbody');if(!tbody)return;







  tbody.innerHTML=cotItems.map((i,idx)=>`<tr><td>${esc(i.nombre)}<div class="text-xs text-muted">${esc(i.categoria)} · ${i.tipo==='examen'?'Examen':'Servicio'}</div></td><td>${i.cantidad}</td><td>${fmtMoney(i.precio)}</td><td>${i.descuento}%</td><td class="fw6">${fmtMoney(i.total)}</td><td><button class="btn-ic" onclick="cotItems.splice(${idx},1);renderCotItems();"><i class="ti ti-trash" style="color:var(--red);"></i></button></td></tr>`).join('')||'<tr><td colspan="6" class="text-c text-muted">Agrega servicios o exámenes para cotizar</td></tr>';







  document.getElementById('cot-total').textContent=fmtMoney(cotItems.reduce((a,i)=>a+i.total,0));







}















function clearCotizador(){cotItems=[];renderCotItems();}















function saveCotizacion(sendCaja=false){







  if(!hasPerm('examenes')){toast('No tienes permiso para guardar cotizaciones','err');return;}







  if(sendCaja&&!hasPerm('caja')){toast('No tienes permiso para enviar cotizaciones a caja. Se guardará solo como cotización.','inf');sendCaja=false;}







  if(!cotItems.length){toast('Agrega al menos un servicio o examen','err');return;}







  const total=cotItems.reduce((a,i)=>a+i.total,0);







  const cot={id:DB.nextId('cot'),numero:`COT-${new Date().getFullYear()}-${String(Date.now()).slice(-6)}`,fecha:today(),pac:+(document.getElementById('cot-pac').value||0),items:[...cotItems],total,estado:sendCaja?'Enviado a caja':'Cotizado',creadoPor:currentUser.name+' '+currentUser.last};







  const cots=DB.get('cotizaciones')||[];cots.unshift(cot);DB.set('cotizaciones',cots);







  if(sendCaja) sendCotizacionCaja(cot);







  printCotizacion(cot.id);







  clearCotizador();renderCotList();toast(sendCaja?'Cotización guardada y enviada a caja':'Cotización guardada','ok');







}















function sendCotizacionCaja(cot){







  const cajas=DB.get('cajas')||[];const caja=cajas.find(c=>c.estado==='abierta');







  if(!caja){toast('No hay caja abierta. La cotización quedó guardada.','inf');return;}







  caja.movimientos=caja.movimientos||[];







  caja.movimientos.unshift({hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),pac:cot.pac?getPacName(cot.pac):'Paciente sin seleccionar',concepto:cot.numero+' · Servicios/exámenes',monto:cot.total,pago:'Pendiente'});







  DB.set('cajas',cajas);







}















function renderCotList(){







  const tbody=document.getElementById('cot-list-tbody');if(!tbody)return;







  const cots=DB.get('cotizaciones')||[];







  tbody.innerHTML=cots.map(c=>`<tr><td class="fw6">${c.numero}</td><td>${fmtDate(c.fecha)}</td><td>${c.pac?getPacName(c.pac):'—'}</td><td>${(c.items||[]).map(i=>esc(i.nombre)).join(', ')}</td><td class="fw6" style="color:var(--green);">${fmtMoney(c.total)}</td><td><span class="badge ${c.estado==='Enviado a caja'?'b-green':'b-blue'}">${c.estado}</span></td><td><button class="btn-ic" onclick="printCotizacion(${c.id})"><i class="ti ti-printer"></i></button></td></tr>`).join('')||'<tr><td colspan="7" class="text-c text-muted">Sin cotizaciones registradas</td></tr>';







}















function printCotizacion(id){







  const c=(DB.get('cotizaciones')||[]).find(x=>x.id===id);if(!c)return;







  const cfg=DB.get('config')||{};







  const p=(DB.get('pacientes')||[]).find(x=>x.id===+c.pac)||{};







  const rows=(c.items||[]).map(i=>`<tr><td>${esc(i.nombre)}</td><td>${i.cantidad}</td><td>${fmtMoney(i.precio)}</td><td>${i.descuento}%</td><td>${fmtMoney(i.total)}</td></tr>`).join('');







  printDoc('Cotización',`<div class="hdr"><img class="logo" src="${cfg.logo||DEFAULT_LOGO}"><div><div class="big">${cfg.nombre||'Centro Médico'}</div><div class="muted">${cfg.dir||''} · ${cfg.tel||''}</div><div class="muted">Cotización de servicios y exámenes</div></div></div><div class="row"><div><div class="label">Cotización</div>${c.numero}</div><div><div class="label">Fecha</div>${fmtDate(c.fecha)}</div></div><div class="box"><div><span class="label">Paciente:</span> ${p.nombres||'—'} ${p.apellidos||''}</div><div><span class="label">Cédula:</span> ${p.cedula||'—'}</div></div><table width="100%" border="1" cellspacing="0" cellpadding="6"><thead><tr><th>Detalle</th><th>Cant.</th><th>Precio</th><th>Desc.</th><th>Total</th></tr></thead><tbody>${rows}</tbody></table><div style="text-align:right;margin-top:12px;"><div class="big">Total: ${fmtMoney(c.total)}</div><div class="muted">Cotización válida según disponibilidad y tarifas vigentes.</div></div>`);







}















// =========================================================







// CAJA







// =========================================================







function renderCajaLegacy(){







  if(!hasPerm('caja')) return;







  const cajas=DB.get('cajas')||[];







  const cajaAbierta=cajas.find(c=>c.estado==='abierta');







  const ultimaCaja=[...cajas].reverse().find(c=>c.estado==='cerrada');







  const cajaHoy=cajaAbierta;







  const pacs=DB.get('pacientes')||[];















  if(!cajaHoy){







    document.getElementById('caja-content').innerHTML=`







      <div class="caja-closed">







        <i class="ti ti-lock" style="font-size:64px;color:var(--text3);display:block;margin-bottom:16px;"></i>







        <div class="fw7 text-md mb8">Caja no abierta</div>







        <div class="text-sm text-muted mb16">El administrador puede abrir caja cuando lo necesite para registrar movimientos.</div>







        ${currentUser?.rol==='admin'?`<button class="btn-g" onclick="abrirCaja()"><i class="ti ti-lock-open"></i> Abrir caja</button>`:'<div class="alert alert-w" style="max-width:420px;margin:0 auto;"><i class="ti ti-alert-circle"></i><span>Solo el administrador puede abrir caja.</span></div>'}







        ${ultimaCaja?.movimientos?.length?`<div class="card mt16" style="max-width:700px;margin:16px auto 0;text-align:left;"><div class="card-hdr"><span class="card-title">Última caja cerrada · ${fmtDate(ultimaCaja.fecha)} ${ultimaCaja.horaCierre||''}</span></div><div class="card-body"><div class="fw6 mb8">Total: ${fmtMoney(ultimaCaja.movimientos.reduce((a,m)=>a+m.monto,0)||0)}</div><table class="tbl"><thead><tr><th>Hora</th><th>Paciente</th><th>Concepto</th><th>Monto</th><th>Método</th></tr></thead><tbody>${ultimaCaja.movimientos.map(m=>`<tr><td>${m.hora}</td><td>${m.pac}</td><td>${m.concepto}</td><td class="fw6" style="color:var(--green);">${fmtMoney(m.monto)}</td><td>${m.pago}</td></tr>`).join('')}</tbody></table></div></div>`:''}







      </div>`;







    return;







  }















  // Caja abierta







  const movs=cajaHoy.movimientos||[];







  const totalEfectivo=movs.filter(m=>m.pago==='Efectivo').reduce((a,m)=>a+m.monto,0);







  const totalTarjeta=movs.filter(m=>m.pago.startsWith('Tarjeta')).reduce((a,m)=>a+m.monto,0);







  const totalSeg=movs.filter(m=>m.pago==='IESS'||m.pago==='Seguro privado').reduce((a,m)=>a+m.monto,0);







  const totalDia=movs.reduce((a,m)=>a+m.monto,0);















  document.getElementById('caja-content').innerHTML=`







    <div class="caja-status-bar caja-open"><i class="ti ti-lock-open" style="font-size:18px;"></i><strong>Caja abierta</strong> · ${fmtDate(cajaHoy.fecha)} desde las ${cajaHoy.horaApertura||'—'} · Apertura: ${cajaHoy.cajero||'—'}</div>







    <div class="grid2">







      <div>







        <div class="stats-row" style="grid-template-columns:1fr 1fr;margin-bottom:14px;">







          <div class="stat-box"><div class="stat-lbl">Total del día</div><div class="stat-val" style="color:var(--green);">${fmtMoney(totalDia)}</div><div class="stat-sub">${movs.length} movimientos</div></div>







          <div class="stat-box"><div class="stat-lbl">Efectivo</div><div class="stat-val">${fmtMoney(totalEfectivo)}</div><div class="stat-sub up">${totalDia?Math.round(totalEfectivo/totalDia*100):0}%</div></div>







          <div class="stat-box"><div class="stat-lbl">Tarjeta</div><div class="stat-val">${fmtMoney(totalTarjeta)}</div><div class="stat-sub">${totalDia?Math.round(totalTarjeta/totalDia*100):0}%</div></div>







          <div class="stat-box"><div class="stat-lbl">Seguros</div><div class="stat-val">${fmtMoney(totalSeg)}</div><div class="stat-sub">${totalDia?Math.round(totalSeg/totalDia*100):0}%</div></div>







        </div>







        <div class="card">







          <div class="card-hdr"><i class="ti ti-list" style="color:var(--primary);font-size:18px;"></i><span class="card-title">Movimientos del día</span>







            <button class="btn-g btn-sm" onclick="openCobroModal()"><i class="ti ti-plus"></i> Cobro rápido</button>







          </div>







          <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Hora</th><th>Paciente</th><th>Concepto</th><th>Monto</th><th>Método</th></tr></thead>







            <tbody>${movs.length?movs.map(m=>`<tr><td class="fw5 text-sm">${m.hora}</td><td>${m.pac}</td><td>${m.concepto}</td><td class="fw6" style="color:var(--green);">${fmtMoney(m.monto)}</td><td><span class="badge ${m.pago==='Efectivo'?'b-green':m.pago.includes('IESS')?'b-blue':'b-amber'}">${m.pago}</span></td></tr>`).join(''):'<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text3);">Sin movimientos aún</td></tr>'}</tbody>







          </table></div>







        </div>







        <div class="mt12 text-r">







          ${currentUser?.rol==='admin'?`<button class="btn-d" onclick="cerrarCaja()"><i class="ti ti-lock"></i> Cerrar caja</button>`:''}







        </div>







      </div>







      <div>







        <div class="card">







          <div class="card-hdr"><i class="ti ti-calculator" style="color:var(--primary);font-size:18px;"></i><span class="card-title">Cobro rápido</span></div>







          <div class="card-body">







            <div class="field"><label class="field-lbl">Paciente</label><select id="inline-pac">${pacs.map(p=>`<option value="${p.id}">${p.nombres} ${p.apellidos}</option>`).join('')}</select></div>







            <div class="field"><label class="field-lbl">Servicio</label><select id="inline-serv" onchange="updateMontoFromService(this,document.getElementById('inline-monto'))">${chargeOptionsHtml()}</select></div>







            <div class="form-row"><div class="field"><label class="field-lbl">Forma de pago</label><select id="inline-pago"><option>Efectivo</option><option>Tarjeta débito</option><option>Tarjeta crédito</option><option>Transferencia</option><option>IESS</option><option>Seguro privado</option></select></div>







            <div class="field"><label class="field-lbl">Monto ($)</label><input type="number" id="inline-monto" value="40"/></div></div>







            <button class="btn-g w100" onclick="procesarCobroInline()"><i class="ti ti-check"></i> Procesar cobro</button>







          </div>







        </div>







      </div>







    </div>`;







  refreshChargeSelectors();







}















function abrirCaja(){







  if(!hasPerm('caja')){toast('No tienes permiso para acceder a caja','err');return;}







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede abrir caja','err');return;}







  const cajas=DB.get('cajas')||[];







  if(cajas.find(c=>c.estado==='abierta')){toast('La caja ya está abierta','inf');renderCaja();return;}







  cajas.push({id:DB.nextId('caja'),fecha:today(),horaApertura:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),estado:'abierta',cajero:currentUser.name+' '+currentUser.last,movimientos:[]});







  DB.set('cajas',cajas);toast('Caja abierta exitosamente','ok');renderCaja();







}















function cerrarCaja(){







  if(!hasPerm('caja')){toast('No tienes permiso para acceder a caja','err');return;}







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede cerrar caja','err');return;}







  confirmDelete('¿Cerrar la caja abierta? No podrás agregar más movimientos a esta caja.',()=>{







    const cajas=DB.get('cajas')||[];







    const i=cajas.findIndex(c=>c.estado==='abierta');







    if(i>=0){cajas[i].estado='cerrada';cajas[i].horaCierre=new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'});cajas[i].cerradoPor=currentUser.name+' '+currentUser.last;DB.set('cajas',cajas);}







    toast('Caja cerrada. Resumen guardado.','ok');renderCaja();







  });







}















function procesarCobroInlineLegacy(){







  if(!hasPerm('caja')){toast('No tienes permiso para procesar cobros','err');return;}







  const cajas=DB.get('cajas')||[];const hoy=today();







  const i=cajas.findIndex(c=>c.estado==='abierta');if(i<0){toast('La caja no está abierta','err');return;}







  const pacId=document.getElementById('inline-pac').value;







  const servText=document.getElementById('inline-serv').options[document.getElementById('inline-serv').selectedIndex].text;







  const pago=document.getElementById('inline-pago').value;







  const monto=parseFloat(document.getElementById('inline-monto').value)||0;







  if(!monto){toast('Ingresa el monto','err');return;}







  const iva=monto*0.15;const total=monto+iva;







  const mov={hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),pac:getPacName(+pacId),concepto:servText.split('—')[0].trim(),monto:total,pago};







  cajas[i].movimientos=cajas[i].movimientos||[];cajas[i].movimientos.unshift(mov);DB.set('cajas',cajas);







  // También crear factura







  const nro=`001-001-${String(1000000000+DB.nextId('fac')).substring(1)}`;







  const facs=DB.get('facturas')||[];facs.unshift({id:nro,fecha:hoy,pac:+pacId,esp:'General',serv:mov.concepto,sub:monto,iva,total,pago,estado:'Pagado'});DB.set('facturas',facs);







  toast(`Cobro procesado: ${fmtMoney(total)} · Factura ${nro}`,'ok');renderCaja();







}















function openCobroModalLegacy(){







  if(!hasPerm('caja')){toast('No tienes permiso para procesar cobros','err');return;}







  const pacs=DB.get('pacientes')||[];







  document.getElementById('cb-pac').innerHTML=pacs.map(p=>`<option value="${p.id}">${p.nombres} ${p.apellidos}</option>`).join('');







  refreshChargeSelectors();







  openM('m-cobro');







}















function procesarCobroLegacy(){







  if(!hasPerm('caja')){toast('No tienes permiso para procesar cobros','err');return;}







  const cajas=DB.get('cajas')||[];const hoy=today();







  const i=cajas.findIndex(c=>c.estado==='abierta');if(i<0){toast('La caja no está abierta','err');return;}







  const pacId=document.getElementById('cb-pac').value;







  const servEl=document.getElementById('cb-serv');const servText=servEl.options[servEl.selectedIndex].text;







  const pago=document.getElementById('cb-pago').value;const monto=parseFloat(document.getElementById('cb-monto').value)||0;







  const iva=monto*0.15;const total=monto+iva;







  cajas[i].movimientos=cajas[i].movimientos||[];cajas[i].movimientos.unshift({hora:new Date().toLocaleTimeString('es-EC',{hour:'2-digit',minute:'2-digit'}),pac:getPacName(+pacId),concepto:servText.split('—')[0].trim(),monto:total,pago});DB.set('cajas',cajas);







  const nro=`001-001-${String(1000000000+DB.nextId('fac')).substring(1)}`;







  const facs=DB.get('facturas')||[];facs.unshift({id:nro,fecha:hoy,pac:+pacId,esp:'General',serv:servText.split('—')[0].trim(),sub:monto,iva,total,pago,estado:'Pagado'});DB.set('facturas',facs);







  closeM('m-cobro');toast(`Cobro procesado: ${fmtMoney(total)}`,'ok');renderCaja();







}















// =========================================================







// CONFIG







// =========================================================







let editingUserId=null;







let pendingSriCertBase64="";







let pendingSriCertName="";















function loadConfig(){
  loadEmailSettings();







  const cfg=DB.get('config')||{};







  document.getElementById('cfg-nombre').value=cfg.nombre||'';







  document.getElementById('cfg-ruc').value=cfg.ruc||'';







  document.getElementById('cfg-dir').value=cfg.dir||'';







  document.getElementById('cfg-tel').value=cfg.tel||'';







  document.getElementById('cfg-wa').value=cfg.wa||'';







  document.getElementById('cfg-email').value=cfg.email||'';







  const setVal=(id,val)=>{const el=document.getElementById(id);if(el)el.value=val;};







  const setChecked=(id,val)=>{const el=document.getElementById(id);if(el)el.checked=!!val;};







  setVal('cfg-sri-ambiente',cfg.sriAmbiente||'1');







  setVal('cfg-sri-estab',cfg.sriEstab||'001');







  setVal('cfg-sri-pto',cfg.sriPtoEmi||'001');







  setVal('cfg-sri-ruc',cfg.sriRuc||cfg.ruc||'');







  setVal('cfg-sri-razon',cfg.sriRazonSocial||cfg.nombre||'');







  setVal('cfg-sri-iva',cfg.sriIvaRate||15);







  setVal('cfg-sri-iva-code',cfg.sriIvaCode||'4');







  setVal('cfg-sri-contab',cfg.sriObligadoContabilidad||'NO');







  setChecked('cfg-sri-auto',false);







  const sriPass=document.getElementById('cfg-sri-cert-pass');if(sriPass)sriPass.value='';







  const sriFile=document.getElementById('cfg-sri-cert-file');if(sriFile)sriFile.value='';







  pendingSriCertBase64='';pendingSriCertName='';







  renderSriCertStatus();







  showLogoPreview(cfg.logo||'');







  document.getElementById('cfg-wtoken').value=cfg.wtoken||'';







  document.getElementById('cfg-remind').value=cfg.remind||'24 horas antes';







  document.getElementById('cfg-tpl').value=cfg.tpl||'';







  renderColorSwatches();







  // Users table







  const panel=document.getElementById('admin-users-panel');







  if(panel) panel.style.display = currentUser?.rol==='admin' ? 'block' : 'none';







  const users=DB.get('users')||[];







  renderCreatePerms();







  document.getElementById('users-tbody').innerHTML=users.map(renderUserRow).join('');







  const cieForm=document.getElementById('cie10-admin-form');







  if(cieForm) cieForm.style.display=currentUser?.rol==='admin'?'block':'none';







  renderCie10Catalog();







}















function userRoleOptions(selected){







  return Object.entries(ROLE_LABELS)







    .filter(([role])=>role!=='pendiente')







    .map(([role,label])=>`<option value="${role}" ${role===selected?'selected':''}>${label}</option>`)







    .join('');







}















function renderUserRow(u){







  if(editingUserId===+u.id) return renderUserEditRow(u);







  const isSelf=currentUser?.id===u.id;







  const needsVerify=u.estado==='pendiente_verificacion'||!u.emailVerified;







  const canSavePerms=u.rol!=='admin'&&u.rol!=='paciente';







  const linkedMed=linkedDoctorForUser(u);







  const roleExtra=(u.rol==='medico'||u.superadminMedico)?`<div class="text-xs text-muted mt4">${linkedMed?`Perfil: ${esc(linkedMed.nombre)} - ${esc(linkedMed.esp||'')}`:'Sin perfil medico vinculado'}</div>`:'';







  return `<tr>







    <td class="text-sm"><div class="fw6">${esc(u.email)}</div><div class="text-xs text-muted">ID ${u.id}</div></td>







    <td>${esc(u.name||'')} ${esc(u.last||'')}</td>







    <td><span class="badge b-blue">${ROLE_LABELS[userRoleKey(u)]||esc(u.rol)}</span>${roleExtra}</td>







    <td>${renderUserPerms(u)}</td>







    <td>${renderUserStatus(u)}</td>







    <td style="min-width:210px;">







      <div class="flex gap6" style="flex-wrap:wrap;justify-content:flex-end;">







        ${canSavePerms?`<button class="btn-p btn-xs" onclick="saveUserPerms(${u.id})"><i class="ti ti-device-floppy"></i> Guardar permisos</button>`:''}







        <button class="btn-s btn-xs" onclick="editUserRow(${u.id})"><i class="ti ti-edit"></i> Editar</button>







        ${needsVerify?`<button class="btn-s btn-xs" onclick="verifyUserAccount(${u.id})"><i class="ti ti-mail-check" style="color:var(--green);"></i> Verificar</button>`:''}







        ${!isSelf?`<button class="btn-s btn-xs" onclick="deleteUserAccount(${u.id})"><i class="ti ti-trash" style="color:var(--red);"></i> Eliminar</button>`:'<span class="text-xs text-muted">Tu usuario</span>'}







      </div>







    </td>







  </tr>`;







}















function renderUserEditRow(u){







  const isSelf=currentUser?.id===u.id;







  const linkedMed=linkedDoctorForUser(u);







  const linkedId=u.medicoId||linkedMed?.id||'';







  return `<tr class="row-editing">







    <td><input id="edit-u-email-${u.id}" type="email" value="${esc(u.email||'')}" style="min-width:190px;"/></td>







    <td>







      <div class="form-row" style="gap:6px;grid-template-columns:1fr 1fr;min-width:260px;">







        <input id="edit-u-name-${u.id}" value="${esc(u.name||'')}" placeholder="Nombre"/>







        <input id="edit-u-last-${u.id}" value="${esc(u.last||'')}" placeholder="Apellido"/>







      </div>







      <input id="edit-u-pass-${u.id}" type="password" placeholder="Nueva clave opcional" style="margin-top:6px;"/>







    </td>







    <td>







      <select id="edit-u-rol-${u.id}" ${isSelf&&!u.superadminMedico?'disabled':''} onchange="toggleEditMedicoLink(${u.id})">${userRoleOptions(userRoleKey(u))}</select>







      <div id="edit-u-medico-wrap-${u.id}" class="mt8">







        <label class="field-lbl">Perfil medico vinculado</label>







        <select id="edit-u-medico-${u.id}" ${(u.rol==='medico'||u.superadminMedico)?'':'disabled'}>${renderMedicoLinkOptions(linkedId)}</select>







      </div>







    </td>







    <td>${renderUserPerms(u)}</td>







    <td>







      <select id="edit-u-estado-${u.id}" ${isSelf?'disabled':''}>







        <option value="activo" ${u.estado==='activo'?'selected':''}>Activo</option>







        <option value="pendiente_verificacion" ${u.estado==='pendiente_verificacion'?'selected':''}>Pendiente verificacion</option>







        <option value="inactivo" ${u.estado==='inactivo'?'selected':''}>Inactivo</option>







      </select>







      <div class="text-xs text-muted mt8">${u.emailVerified?'Correo verificado':'Correo sin verificar'}</div>







    </td>







    <td style="min-width:180px;">







      <div class="flex gap6" style="flex-wrap:wrap;justify-content:flex-end;">







        <button class="btn-p btn-xs" onclick="saveUserEdit(${u.id})"><i class="ti ti-device-floppy"></i> Guardar cambios</button>







        <button class="btn-s btn-xs" onclick="cancelUserEdit()">Cancelar</button>







      </div>







    </td>







  </tr>`;







}















function editUserRow(id){







  if(currentUser?.rol!=='admin'){toast('Solo el dueño/administrador puede editar usuarios','err');return;}







  editingUserId=+id;







  loadConfig();







}















function cancelUserEdit(){







  editingUserId=null;







  loadConfig();







}















function updateLocalUser(user){







  const users=DB.get('users')||[];







  const i=users.findIndex(u=>u.id===+user.id);







  if(i>=0) users[i]=user; else users.push(user);







  DB.cache.users=users;







  if(currentUser?.id===+user.id){currentUser=user;applyPermissionUI();}







}















async function saveUserEdit(userId){







  if(currentUser?.rol!=='admin'){toast('Solo el dueño/administrador puede editar usuarios','err');return;}







  const current=(DB.get('users')||[]).find(u=>u.id===+userId);







  if(!current){toast('Usuario no encontrado','err');return;}







  const payload={







    action:'update',







    userId:+userId,







    name:document.getElementById(`edit-u-name-${userId}`).value.trim(),







    last:document.getElementById(`edit-u-last-${userId}`).value.trim(),







    email:document.getElementById(`edit-u-email-${userId}`).value.trim(),







    password:document.getElementById(`edit-u-pass-${userId}`).value,







    rol:document.getElementById(`edit-u-rol-${userId}`)?.value||current.rol,







    medicoId:document.getElementById(`edit-u-medico-${userId}`)?.value||'',







    estado:document.getElementById(`edit-u-estado-${userId}`)?.value||current.estado||'activo',







    permissions:MODULE_PERMS.map(p=>p.id).filter(id=>document.getElementById(`perm-${userId}-${id}`)?.checked)







  };







  try{







    const res=await API.post('/api/users',payload);







    updateLocalUser(res.user);







    editingUserId=null;







    loadConfig();







    toast('Usuario actualizado','ok');







  }catch(err){toast(err.message||'No se pudo actualizar el usuario','err');}







}















async function verifyUserAccount(userId){







  if(currentUser?.rol!=='admin'){toast('Solo el dueño/administrador puede verificar usuarios','err');return;}







  try{







    const res=await API.post('/api/users',{action:'verify',userId:+userId});







    updateLocalUser(res.user);







    loadConfig();







    toast('Cuenta verificada manualmente','ok');







  }catch(err){toast(err.message||'No se pudo verificar la cuenta','err');}







}















function deleteUserAccount(userId){







  if(currentUser?.rol!=='admin'){toast('Solo el dueño/administrador puede eliminar usuarios','err');return;}







  const u=(DB.get('users')||[]).find(x=>x.id===+userId);







  if(!u){toast('Usuario no encontrado','err');return;}







  confirmDelete(`¿Eliminar al usuario ${u.email}?`,async()=>{







    try{







      await API.post('/api/users',{action:'delete',userId:+userId});







      DB.cache.users=(DB.get('users')||[]).filter(x=>x.id!==+userId);







      if(editingUserId===+userId) editingUserId=null;







      loadConfig();







      toast('Usuario eliminado','inf');







    }catch(err){toast(err.message||'No se pudo eliminar el usuario','err');}







  });







}







function renderUserStatus(u){







  if(u.estado==='pendiente_verificacion'||!u.emailVerified) return '<span class="badge b-amber">Pendiente de verificación</span>';







  if((u.permissions||[]).length===0&&u.rol!=='admin'&&u.rol!=='paciente') return '<span class="badge b-amber">Pendiente de permisos</span>';







  if(u.estado&&u.estado!=='activo') return '<span class="badge b-red">Inactivo</span>';







  return '<span class="badge b-green">Activo</span>';







}















async function createSystemUser(){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede crear usuarios','err');return;}







  const payload={







    name:document.getElementById('u-name').value.trim(),







    last:document.getElementById('u-last').value.trim(),







    email:document.getElementById('u-email').value.trim(),







    password:document.getElementById('u-pass').value,







    rol:document.getElementById('u-rol').value,







    medicoId:document.getElementById('u-medico-link')?.value||'',







    permissions:getCheckedPerms('u-perm-')







  };







  try{







    const res=await API.post('/api/users',payload);







    const users=DB.get('users')||[];







    users.push(res.user);







    DB.cache.users=users;







    ['u-name','u-last','u-email','u-pass'].forEach(id=>document.getElementById(id).value='');







    const medLink=document.getElementById('u-medico-link');if(medLink)medLink.value='';







    renderCreatePerms();







    loadConfig();







    toast('Usuario creado correctamente','ok');







  }catch(err){toast(err.message||'No se pudo crear el usuario','err');}







}















function renderPermChecks(prefix,perms,disabled=false){







  const clean=cleanPermissions(perms,'recepcion');







  return MODULE_PERMS.map(p=>`<label class="perm-check"><input type="checkbox" id="${prefix}${p.id}" value="${p.id}" ${clean.includes(p.id)||perms?.includes(p.id)?'checked':''} ${disabled||p.id==='config'?'disabled':''}/> ${p.label}</label>`).join('');







}















function renderCreatePerms(){







  const box=document.getElementById('u-perms');







  if(!box)return;







  const role=document.getElementById('u-rol')?.value||'recepcion';







  const perms=defaultPermsForRole(role);







  box.innerHTML=renderPermChecks('u-perm-',perms,role==='admin'||role==='medico_superadmin');







  renderCreateMedicoLink();







}















function renderCreateMedicoLink(){







  const role=document.getElementById('u-rol')?.value||'recepcion';







  const wrap=document.getElementById('u-medico-link-wrap');







  const sel=document.getElementById('u-medico-link');







  if(!wrap||!sel)return;







  const prev=sel.value||'';







  sel.innerHTML=renderMedicoLinkOptions(prev);







  sel.disabled=role!=='medico'&&role!=='medico_superadmin';







  wrap.style.opacity=(role==='medico'||role==='medico_superadmin')?'1':'.75';







}















function toggleEditMedicoLink(userId){







  const role=document.getElementById(`edit-u-rol-${userId}`)?.value||'';







  const sel=document.getElementById(`edit-u-medico-${userId}`);







  if(sel)sel.disabled=role!=='medico'&&role!=='medico_superadmin';







}















function renderUserPerms(u){







  if(u.rol==='admin') return '<span class="badge b-green">Todos los módulos</span>';







  if(u.rol==='paciente') return '<span class="badge b-gray">Portal paciente</span>';







  return `<div class="perm-grid" style="min-width:420px;">${MODULE_PERMS.filter(p=>p.id!=='config').map(p=>`<label class="perm-check"><input type="checkbox" id="perm-${u.id}-${p.id}" value="${p.id}" ${hasPerm(p.id,u)?'checked':''}/> ${p.label}</label>`).join('')}</div>`;







}















function getCheckedPerms(prefix){







  return MODULE_PERMS.map(p=>p.id).filter(id=>document.getElementById(prefix+id)?.checked);







}















async function saveUserPerms(userId){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede configurar permisos','err');return;}







  const user=(DB.get('users')||[]).find(u=>u.id===+userId);







  if(!user){toast('Usuario no encontrado','err');return;}







  const permissions=MODULE_PERMS.map(p=>p.id).filter(id=>document.getElementById(`perm-${userId}-${id}`)?.checked);







  try{







    const res=await API.post('/api/users',{action:'permissions',userId,permissions});







    const users=DB.get('users')||[];







    const i=users.findIndex(u=>u.id===+userId);







    if(i>=0) users[i]=res.user;







    DB.cache.users=users;







    if(currentUser.id===+userId){currentUser=res.user;applyPermissionUI();}







    loadConfig();







    toast('Permisos actualizados','ok');







  }catch(err){toast(err.message||'No se pudieron guardar los permisos','err');}







}















function renderCie10Catalog(){







  const tbody=document.getElementById('cie10-tbody');







  if(!tbody)return;







  const q=document.getElementById('cie-q')?.value||'';







  const items=searchCie10(q,140);







  tbody.innerHTML=items.map(x=>`<tr><td class="fw6">${esc(normalizeCie10Code(x.code))}</td><td>${esc(x.desc)}</td><td>${esc(x.chapter||'General')}</td><td class="text-r">${currentUser?.rol==='admin'?`<button class="btn-ic" title="Eliminar código" onclick="deleteCie10Code('${esc(normalizeCie10Code(x.code))}')"><i class="ti ti-trash" style="font-size:14px;color:var(--red);"></i></button>`:''}</td></tr>`).join('')||'<tr><td colspan="4" class="text-c text-muted">Sin códigos encontrados</td></tr>';







}















function addCie10Code(){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede modificar el catálogo CIE-10','err');return;}







  const code=normalizeCie10Code(document.getElementById('cie-code').value);







  const desc=document.getElementById('cie-desc').value.trim();







  const chapter=document.getElementById('cie-chapter').value.trim()||'General';







  if(!code||!desc){toast('Ingresa código y descripción CIE-10','err');return;}







  const list=cie10Catalog().filter(x=>normalizeCie10Code(x.code)!==code);







  list.push({code,desc,chapter});







  DB.set('cie10',list);







  ['cie-code','cie-desc','cie-chapter'].forEach(id=>document.getElementById(id).value='');







  renderCie10Catalog();







  fillCie10Select();







  toast('Código CIE-10 guardado','ok');







}















function deleteCie10Code(code){







  if(currentUser?.rol!=='admin'){toast('Solo el administrador puede modificar el catálogo CIE-10','err');return;}







  const clean=normalizeCie10Code(code);







  confirmDelete(`¿Eliminar el código CIE-10 ${clean}?`,()=>{







    DB.set('cie10',cie10Catalog().filter(x=>normalizeCie10Code(x.code)!==clean));







    renderCie10Catalog();







    fillCie10Select();







    toast('Código CIE-10 eliminado','inf');







  });







}















function renderSriCertStatus(){







  const el=document.getElementById('sri-cert-status');







  if(!el)return;







  const st=DB.get('sriCertificateStatus')||{};







  const fileTxt=st.filename?` Archivo: ${esc(st.filename)}.`:'';







  const dateTxt=st.updatedAt?` Actualizado: ${fmtDate(String(st.updatedAt).slice(0,10))}.`:'';







  if(st.configured){







    el.innerHTML=`<span class="badge b-green">Certificado configurado</span> ${esc(st.source||'Base de datos')}.${fileTxt}${dateTxt} ${st.hasPassword?'Clave guardada.':'Falta clave.'}`;







  }else{







    el.innerHTML='<span class="badge b-amber">Certificado SRI pendiente</span> Sube el archivo .p12/.pfx y escribe la clave para poder enviar facturas al SRI.';







  }







  const delBtn=[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Eliminar certificado'));







  if(delBtn) delBtn.disabled=!!st.envLocked;







}















function readSriCertFile(event){







  const file=event.target.files&&event.target.files[0];







  pendingSriCertBase64='';







  pendingSriCertName='';







  if(!file){renderSriCertStatus();return;}







  const name=file.name||'certificado-sri.p12';







  if(!/\.(p12|pfx)$/i.test(name)){toast('Selecciona un archivo .p12 o .pfx','err');event.target.value='';return;}







  const reader=new FileReader();







  reader.onload=()=>{







    pendingSriCertBase64=String(reader.result||'').split(',').pop();







    pendingSriCertName=name;







    const el=document.getElementById('sri-cert-status');







    if(el)el.innerHTML=`<span class="badge b-blue">Archivo listo</span> ${esc(name)} seleccionado. Escribe la clave y pulsa Guardar certificado SRI.`;







  };







  reader.onerror=()=>toast('No se pudo leer el certificado seleccionado','err');







  reader.readAsDataURL(file);







}















async function saveSriCertificate(){







  if(currentUser?.rol!=='admin'){toast('Solo el dueno/administrador puede guardar el certificado SRI','err');return;}







  const password=document.getElementById('cfg-sri-cert-pass')?.value||'';







  if(!pendingSriCertBase64){toast('Primero selecciona el archivo .p12 o .pfx','err');return;}







  if(!password){toast('Ingresa la clave del certificado','err');return;}







  try{







    const res=await API.post('/api/sri/certificate',{action:'save',filename:pendingSriCertName,p12Base64:pendingSriCertBase64,password});







    DB.cache.sriCertificateStatus=res.status||{};







    pendingSriCertBase64='';pendingSriCertName='';







    const file=document.getElementById('cfg-sri-cert-file');if(file)file.value='';







    const pass=document.getElementById('cfg-sri-cert-pass');if(pass)pass.value='';







    renderSriCertStatus();







    toast('Certificado SRI guardado correctamente','ok');







  }catch(err){toast(err.message||'No se pudo guardar el certificado SRI','err');}







}















function deleteSriCertificate(){







  if(currentUser?.rol!=='admin'){toast('Solo el dueno/administrador puede eliminar el certificado SRI','err');return;}







  const st=DB.get('sriCertificateStatus')||{};







  if(st.envLocked){toast('El certificado viene de variables privadas de Vercel. Cambialo en Vercel.','err');return;}







  confirmDelete('Eliminar el certificado SRI guardado?',async()=>{







    try{







      const res=await API.post('/api/sri/certificate',{action:'delete'});







      DB.cache.sriCertificateStatus=res.status||{};







      pendingSriCertBase64='';pendingSriCertName='';







      const file=document.getElementById('cfg-sri-cert-file');if(file)file.value='';







      const pass=document.getElementById('cfg-sri-cert-pass');if(pass)pass.value='';







      renderSriCertStatus();







      toast('Certificado SRI eliminado','inf');







    }catch(err){toast(err.message||'No se pudo eliminar el certificado SRI','err');}







  });







}







function saveCfg(){







  const cfg=DB.get('config')||{};







  cfg.nombre=document.getElementById('cfg-nombre').value;







  cfg.ruc=document.getElementById('cfg-ruc').value;







  cfg.dir=document.getElementById('cfg-dir').value;







  cfg.tel=document.getElementById('cfg-tel').value;







  cfg.wa=document.getElementById('cfg-wa').value;







  cfg.email=document.getElementById('cfg-email').value;







  cfg.sriAmbiente=document.getElementById('cfg-sri-ambiente')?.value||'1';







  cfg.sriEstab=(document.getElementById('cfg-sri-estab')?.value||'001').padStart(3,'0').slice(0,3);







  cfg.sriPtoEmi=(document.getElementById('cfg-sri-pto')?.value||'001').padStart(3,'0').slice(0,3);







  cfg.sriRuc=document.getElementById('cfg-sri-ruc')?.value||cfg.ruc||'';







  cfg.sriRazonSocial=document.getElementById('cfg-sri-razon')?.value||cfg.nombre||'';







  cfg.sriIvaRate=+(document.getElementById('cfg-sri-iva')?.value||15);







  cfg.sriIvaCode=document.getElementById('cfg-sri-iva-code')?.value||'4';







  cfg.sriObligadoContabilidad=document.getElementById('cfg-sri-contab')?.value||'NO';







  cfg.sriAutoSend=false;







  cfg.logo=cfg.logo||'';







  cfg.wtoken=document.getElementById('cfg-wtoken').value;







  cfg.remind=document.getElementById('cfg-remind').value;







  cfg.tpl=document.getElementById('cfg-tpl').value;







  DB.set('config',cfg);applyLogo(cfg.logo||DEFAULT_LOGO);toast('Configuración guardada','ok');







}















// =========================================================







// INIT







// =========================================================







async function initSession(){







  repairMojibakeText();







  await initPublicLanding();







  if(!API.token) return;







  try{







    try{







      const portal=await API.get('/api/patient/portal');







      currentUser=portal.user;







      patientPortalData=portal.portal;







      launchPatientPortal();







      return;







    }catch(patientErr){}







    const loaded=await API.get('/api/data');







    DB.load(loaded.data);







    DB.init();







    currentUser=loaded.user;







    launchApp();







  }catch(err){







    localStorage.removeItem('mg_token');







    API.token='';







  }







}







window.addEventListener('beforeunload',event=>{if(DB.pending||DB.failures.size){event.preventDefault();event.returnValue='';}});
initSession();















// Responsive







if(window.innerWidth<768){document.getElementById('mob-btn').style.display='block';}







window.addEventListener('resize',()=>{if(window.innerWidth<768)document.getElementById('mob-btn').style.display='block';else{document.getElementById('mob-btn').style.display='none';document.getElementById('sidebar').classList.remove('open');}});







