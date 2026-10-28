// 相関ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか。点のドラッグで値が動くか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:380,height:900}});await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-corr.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v);
  LK.show('scatter');const s=L.sVals();
  LK.show('unit');set('ua',1.8);set('ub',32);set('uc',1);const u=L.uVals();
  LK.show('strata');set('td',4);const t=L.tVals();
  LK.show('partial');set('pxy',0.8);set('pxz',0.8);set('pyz',0.8);const pp=L.pVals();
  LK.show('range');set('rmin',8);const g=L.rVals();
  LK.show('rtest');set('qr',0.5);set('qn',20);const q=L.qVals();
  LK.show('scatter');
  return {s:[s.sxy,s.cov,s.r,s.vsum],u:[u.cov,u.r],t:[t.r,t.rA,t.rB,t.rp],p:pp.rp,g:[g.r,g.n,g.rAll],q:[q.t,q.crit,q.decision]};});
 const c=await p.$('#sbox circle.pt[data-i="4"]');const bb=await c.boundingBox();
 await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2);await p.mouse.down();await p.mouse.move(bb.x+bb.width/2,bb.y+200,{steps:6});await p.mouse.up();
 const after=await p.evaluate(()=>window.__LAB__.sVals().r);
 console.log(JSON.stringify(r),after);
 const n=(x,y,t=1e-4)=>Math.abs(x-y)<=t;
 const ok=n(r.s[0],9,1e-9)&&n(r.s[1],2.25,1e-9)&&n(r.s[2],0.9,1e-9)&&n(r.s[3],9.5,1e-9)
  &&n(r.u[0],4.05,1e-9)&&n(r.u[1],0.9,1e-9)
  &&n(r.t[0],0.69282)&&n(r.t[1],0,1e-12)&&n(r.t[2],0,1e-12)&&n(r.t[3],0,1e-9)
  &&n(r.p,0.444444)&&n(r.g[0],0.430793)&&r.g[1]===5&&n(r.g[2],0.859575)
  &&n(r.q[0],2.449490)&&r.q[1]===2.101&&r.q[2]==='棄却する'&&after<0.9-0.05;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
