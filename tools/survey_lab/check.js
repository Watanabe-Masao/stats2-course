// 標本調査ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-survey.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v);
  set('tw',0.2);set('tb',200);set('ts',50);const t=L.tVals();
  set('dd',1);set('dp',0);set('ds',1);const d1=L.dVals();set('dd',2);const d2=L.dVals();set('dd',0);set('dp',2);const d3=L.dVals();
  set('bp',0.5);set('b1',0.6);set('b0',0.3);set('bn',400);const b1=L.bVals();set('bn',10000);const b2=L.bVals();
  set('aw',0.2);set('a1',30);set('a2',5);set('am',40);set('an',100);const a=L.aVals();
  [['mA',10],['ma',2],['mB',15],['mb',3],['mC',200],['mc',20]].forEach(([k,v])=>set(k,v));const m=L.mVals();
  return {t:[t.weighted,t.naive],d1:[d1.best,d1.rClus,d1.rStrat],d2:[d2.rClus,d2.rStrat],d3:[d3.best,d3.rSys],b:[b1.est,b1.bias,b1.rmse,b2.se,b2.covers],a:[a.n1p,a.n1n,a.seP,a.seN,a.seS],m:[m.prob,m.weight]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-4)=>Math.abs(x-y)<=t;
 const ok=r.t[0]===80&&r.t[1]===125&&r.d1[0]==='層化'&&n(r.d1[1],2.8547)&&n(r.d1[2],0.5339)&&n(r.d2[0],3.1827)&&n(r.d2[1],0.295)&&r.d3[0]==='集落'&&n(r.d3[1],2.9302)
  &&n(r.b[0],2/3)&&n(r.b[1],1/6)&&n(r.b[2],0.16833)&&n(r.b[3],0.004714)&&r.b[4]==='含まない'&&r.a[0]===20&&r.a[1]===60&&n(r.a[2],Math.SQRT2)&&n(r.a[3],1)&&n(r.a[4],2.13542)&&n(r.m[0],0.004,1e-12)&&n(r.m[1],250,1e-9);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
