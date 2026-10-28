// t・χ²・F ラボの数値の検算：本文・問題に書いた確率点（数表の値）とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-tcf.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v);
  set('sx',52);set('sm',50);set('ss',8);set('sn',16);const s=L.sVals();
  const t=[[1,0.975],[4,0.975],[8,0.975],[9,0.975],[15,0.975],[20,0.95],[20,0.975],[24,0.975],[30,0.975],[35,0.975],[100,0.975],[120,0.975]].map(([d,q])=>L.tq(q,d));
  const c=[[0.025,9],[0.975,9],[0.95,9],[0.95,15],[0.95,20]].map(([q,d])=>L.chiq(q,d));
  const f=[[10,12],[9,7],[12,10],[1,15]].map(([a,d])=>L.fq(0.95,a,d));
  return {s:[s.se,s.t,s.df,s.wrong],t,c,f,pchi:1-L.chicdf(30,20)};});
 console.log(JSON.stringify(r));
 const near=(x,y,t)=>Math.abs(x-y)<=t;
 const T=[12.706,2.776,2.306,2.262,2.131,1.725,2.086,2.064,2.042,2.030,1.984,1.980],C=[2.700,19.023,16.919,24.996,31.410],F=[2.753,3.677,2.913,4.543];
 const ok=r.s[0]===2&&r.s[1]===1&&r.s[2]===15&&r.s[3]===0.25&&T.every((v,i)=>near(r.t[i],v,6e-4))&&C.every((v,i)=>near(r.c[i],v,6e-4))&&F.every((v,i)=>near(r.f[i],v,6e-4))&&near(r.pchi,0.0699,5e-5)&&near(r.t[4]**2,r.f[3],1e-6);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
