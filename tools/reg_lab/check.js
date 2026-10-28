// 回帰ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか。点のドラッグで値が動くか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:380,height:900}});await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-reg.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__;
  L.apply('fit',{data:'1,3 2,5 3,4 4,6 5,7',px:5});const f=L.fVals();L.apply('fit',{data:'1,3 2,5 3,4 4,6 5,7',px:20});const f20=L.fVals();
  L.apply('line',{data:'1,3 2,5 3,4 4,6 5,7',m:0.5,c:4});const l=L.lVals();
  L.apply('resid',{data:'1,2 2,5 3,7 4,8 5,8.5'});const rs=L.rVals();
  L.apply('dir',{data:'1,2 2,3 3,6 4,7'});const d=L.dVals();
  L.apply('fit',{data:'1,3 2,5 3,4 4,6 5,7',px:5});
  return {f:[f.b,f.a,f.sse,f.r2,f.f,f.yhat,f.inrange,f.esum],f20:[f20.yhat,f20.inrange],l:[l.sseUser,l.sseLS],rs:[rs.r2,rs.shape],d:[d.bxy,d.byx,d.prod,d.r2]};});
 const c=await p.$('#fbox circle.pt[data-i="4"]');const bb=await c.boundingBox();
 await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2);await p.mouse.down();await p.mouse.move(bb.x+bb.width/2,bb.y+150,{steps:6});await p.mouse.up();
 const after=await p.evaluate(()=>window.__LAB__.fVals().b);
 console.log(JSON.stringify(r),after);
 const n=(x,y,t=1e-4)=>Math.abs(x-y)<=t;
 const ok=n(r.f[0],0.9,1e-9)&&n(r.f[1],2.3,1e-9)&&n(r.f[2],1.9,1e-9)&&n(r.f[3],0.81,1e-9)&&n(r.f[4],12.789474)&&n(r.f[5],6.8,1e-9)&&r.f[6]==='範囲内'&&n(r.f[7],0,1e-9)
  &&n(r.f20[0],20.3,1e-9)&&r.f20[1]==='外挿'&&n(r.l[0],4.75,1e-9)&&n(r.l[1],1.9,1e-9)&&n(r.rs[0],0.907801)&&r.rs[1]==='山形'
  &&n(r.d[0],1.8,1e-9)&&n(r.d[1],0.529412)&&n(r.d[2],r.d[3],1e-9)&&after<0.9-0.1;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
