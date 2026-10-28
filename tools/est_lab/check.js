// 推定量ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-est.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),inp=v=>{document.getElementById('dv').value=v;};
  inp('2,4,4,6,9');const d=L.dVals();
  set('vs',10);set('vn',5);const v=L.vVals();set('vs',100);const v2=L.vVals();
  set('ks',10);set('kn',10);set('kb',2);const k=L.kVals();set('kn',25);set('kb',0);const k2=L.kVals();
  set('sp',0.5);set('s1',0.6);set('s0',0.2);set('sn',1000);const s=L.sVals();
  return {d:[d.mean,d.ss,d.v,d.s2],v:[v.meanV,v.biasV,v.mseS2,v.mseV,v.ratio,v.better],v2:v2.meanS,k:[k.mseMean,k.mseShift,k.mseFirst,k.best,k.seMed,k.biasMed],k2:[k2.seMean,k2.seMed,1/k2.effMed],s:[s.target,s.bias]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<=t;
 const ok=n(r.d[0],5)&&n(r.d[1],28)&&n(r.d[2],5.6)&&n(r.d[3],7)&&n(r.v[0],8)&&n(r.v[1],-2)&&n(r.v[2],50)&&n(r.v[3],36)&&n(r.v[4],0.8)&&r.v[5]==='n で割る v'&&n(r.v2,9.3999,2e-4)
  &&n(r.k[0],10)&&n(r.k[1],14)&&n(r.k[2],100)&&r.k[3]==='標本平均'&&Math.abs(r.k[5])<0.3&&n(r.k2[0],2)&&Math.abs(r.k2[1]-2.45)<0.2&&r.k2[2]>1.3&&r.k2[2]<1.75&&n(r.s[0],0.75)&&n(r.s[1],0.25);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
