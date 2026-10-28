// Σ・階乗ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-sigma.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  set('sn',3);set('sx1',2);set('sx2',4);set('sx3',6);const s1=L.sVals();
  set('sx1',1);set('sx2',3);set('sx3',5);const s2=L.sVals();
  set('sx1',2);set('sx2',4);set('sx3',6);set('ra',3);set('rc',1);const r1=L.rVals();
  set('fn',5);set('fr',2);const f1=L.fVals();set('fn',0);set('fr',0);const f0=L.fVals();
  set('ga',2);set('gb',1);set('gx',3);const g=L.gVals();
  return {s1,s2,r1:r1.lhs,f1,f0:f0.fact,g:g.fx};});
 console.log(JSON.stringify(r));
 const ok=r.s1.sum===12&&r.s1.sumsq===56&&r.s1.sqsum===144&&r.s1.mean===4&&r.s1.ss===8&&r.s1.devsum===0
  &&r.s2.sum===9&&r.s2.sumsq===35&&r.s2.ss===8&&r.r1===39&&r.f1.fact===120&&r.f1.perm===20&&r.f1.comb===10&&r.f0===1&&r.g===7;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
