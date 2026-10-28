// 抽出ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-srs.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v);
  set('iN',100);LK.show('incl');set('in',10);set('im',5);const a=L.iVals();
  set('iN',200);LK.show('incl');set('in',20);const a2=L.iVals();
  set('iN',40);LK.show('incl');set('in',4);const a3=L.iVals();
  document.getElementById('ev').value='3,5,7,9,11';LK.show('enum');set('en',2);set('et',1);set('ec',8);const e=L.eVals();
  set('rN',30);LK.show('repl');set('rn',5);const rr=L.rVals();
  return {a:[a.pi,a.piMiss,a.cover],a2:[a2.pi,a2.pair],a3:a3.either,e:[e.count,e.meanmean,e.within,e.sdmean,e.min,e.max,e.formula],r:rr.pDup};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<t;
 const ok=n(r.a[0],0.1)&&r.a[1]===0&&n(r.a[2],100/105)&&n(r.a2[0],0.1)&&n(r.a2[1],380/39800)&&n(r.a3,1-36*35/(40*39))
  &&r.e[0]===10&&n(r.e[1],7)&&n(r.e[2],0.6)&&n(r.e[3],Math.sqrt(3))&&n(r.e[4],4)&&n(r.e[5],10)&&n(r.e[6],Math.sqrt(3))&&n(r.r,1-30*29*28*27*26/30**5);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
