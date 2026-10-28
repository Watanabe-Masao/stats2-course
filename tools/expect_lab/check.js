// 期待値ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-expect.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  L.dApply({xs:"0,1,2",p:[20,50,30]});const d1=L.dVals();L.dApply({xs:"0,2",p:[45,55]});const d2=L.dVals();L.dApply({xs:"0,1",p:[70,30]});const d3=L.dVals();
  L.dApply({xs:"0,1,2",p:[20,50,30]});set('la',200);set('lb',50);const l1=L.lVals();set('la',2);set('lb',3);const l2=L.lVals();
  set('svx',4);set('svy',9);set('scv',1);const s1=L.sVals();set('scv',0);const s0=L.sVals();
  set('tn',300);set('tmu',1.1);set('tvr',0.49);const t1=L.tVals();
  set('j11',30);set('j10',20);set('j01',10);const j1=L.jVals();set('j11',20);set('j10',30);set('j01',20);const j2=L.jVals();
  return {d1:[d1.mean,d1.ex2,d1.var,d1.sd],d2:d2.var,d3:[d3.mean,d3.var],l1:[l1.ey,l1.vy,l1.sdy],l2:[l2.ey,l2.vy],s1:[s1.vsum,s1.vdiff],s0:[s0.vsum,s0.vdiff],t1:[t1.etot,t1.vtot,t1.sdtot],j1:[j1.px,j1.py,j1.cov,j1.indep],j2:[j2.cov,j2.indep]};});
 console.log(JSON.stringify(r));
 const n=(a,b,e=1e-9)=>Math.abs(a-b)<e;
 const ok=n(r.d1[0],1.1)&&n(r.d1[1],1.7)&&n(r.d1[2],0.49)&&n(r.d1[3],0.7)&&n(r.d2,0.99)&&n(r.d3[0],0.3)&&n(r.d3[1],0.21)&&n(r.l1[0],270)&&n(r.l1[1],19600)&&n(r.l1[2],140)&&n(r.l2[0],5.2)&&n(r.l2[1],1.96)
  &&r.s1[0]===15&&r.s1[1]===11&&r.s0[0]===13&&r.s0[1]===13&&n(r.t1[0],330)&&n(r.t1[1],147)&&n(r.t1[2],Math.sqrt(147))&&n(r.j1[0],0.5)&&n(r.j1[1],0.4)&&n(r.j1[2],0.1)&&r.j1[3]==='いいえ'&&n(r.j2[0],0)&&r.j2[1]==='はい';
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
