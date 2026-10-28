// 確率ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-prob.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  set('da','even');set('db','ge4');const d1=L.dVals();set('da','odd');set('db','le3');const d2=L.dVals();set('da','one');set('db','six');const d3=L.dVals();
  set('ra',50);set('rb',40);set('rab',20);const r1=L.rVals();set('ra',40);set('rb',30);set('rab',10);const r2=L.rVals();set('ra',70);set('rb',60);set('rab',50);const r3=L.rVals();
  const at=(a,b,n)=>{set('ta',a);set('tb',b);set('tn',n);return L.tVals();};
  return {d1:d1.union,d2:d2.union,d3:d3.excl,r1:[r1.union,r1.none],r2:[r2.union,r2.none],r3:r3.lo,t2:at(1,6,2).atleast,t3:at(1,6,3).atleast,t10:at(1,10,10).atleast,t10n:at(1,10,10).naive};});
 console.log(JSON.stringify(r));
 const n=(a,b,e=1e-9)=>Math.abs(a-b)<e;
 const ok=n(r.d1,2/3)&&n(r.d2,2/3)&&r.d3==='はい'&&r.r1[0]===70&&r.r1[1]===30&&r.r2[0]===60&&r.r2[1]===40&&r.r3===30&&n(r.t2,11/36)&&n(r.t3,91/216)&&n(r.t10,1-0.9**10)&&n(r.t10n,1);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
