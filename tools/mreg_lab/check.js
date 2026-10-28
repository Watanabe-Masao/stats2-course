// 重回帰ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか。点のドラッグで係数が変わるか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:380,height:900}});await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-mreg.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__;
  L.apply('coef',{x1:10,x2:4});const c=L.cVals();
  L.apply('dummy',{inter:false});const d=L.dVals();
  L.apply('colin',{r:0.9,n:30});const k=L.kVals();
  L.apply('add',{k:8});const a=L.aVals();
  L.apply('anova',{n:20,k:2,ssr:180,sse:120});const v=L.vVals();
  L.apply('tval',{b:0.6,se:0.2,n:20,k:3});const t=L.tVals();
  L.apply('coef',{x1:10,x2:4});
  return {c:[c.b0,c.b1,c.b2,c.bs,c.yhat,c.r2],d:[d.bD,d.mdiff,d.b1],k:[k.vif],a:[a.best,a.r2up,a.adjup],v:[v.r2,v.adjr2,v.F,v.crit],t:[t.t,t.crit,t.lo,t.hi]};});
 // 点を1つドラッグすると b₁ が変わる
 await p.click('#tabs button[data-m="coef"]').catch(()=>{});
 const before=await p.evaluate(()=>window.__LAB__.cVals().b1);
 const pt=await p.$('#cbox .pt[data-i="0"]');const bb=await pt.boundingBox();
 await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2);await p.mouse.down();await p.mouse.move(bb.x+bb.width/2,bb.y-60,{steps:6});await p.mouse.up();
 const after=await p.evaluate(()=>window.__LAB__.cVals().b1);
 console.log(JSON.stringify(r),before,after);
 const n=(x,y,e=1e-6)=>Math.abs(x-y)<=e;
 const ok=n(r.c[0],40,1e-6)&&n(r.c[1],-1,1e-9)&&n(r.c[2],3,1e-9)&&n(r.c[3],1.377358,1e-5)&&n(r.c[4],42,1e-9)&&n(r.c[5],0.843902,1e-5)
  &&n(r.d[0],6,1e-9)&&n(r.d[1],10,1e-9)&&n(r.d[2],2,1e-9)&&n(r.k[0],5.263158,1e-5)&&r.a[0]===0&&r.a[1]==='上がる'&&r.a[2]==='下がる'
  &&n(r.v[0],0.6)&&n(r.v[1],0.552941,1e-5)&&n(r.v[2],12.75)&&r.v[3]===3.592&&n(r.t[0],3)&&r.t[1]===2.12&&n(r.t[2],0.176)&&n(r.t[3],1.024)&&!n(before,after);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
