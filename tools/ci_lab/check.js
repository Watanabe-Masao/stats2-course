// 信頼区間ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-ci.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  sel('mkind','z');sel('mlevel','0.95');set('mx',50);set('ms',10);set('mn',100);set('md',1);const m=L.mVals();
  sel('mkind','t');set('mx',52);set('ms',8);set('mn',16);const t=L.mVals();
  set('pn',400);set('px',80);set('pd',0.03);const pr=L.pVals();set('pn',20);set('px',2);const w=L.pVals();
  sel('ckind','z');sel('clevel','0.95');set('cn',25);set('cs',10);const c1=L.cVals();sel('ckind','zs');set('cn',5);const c2=L.cVals();sel('ckind','t');const c3=L.cVals();
  return {m:[m.lo,m.hi,m.margin,m.nFor],t:[t.crit,t.margin],p:[pr.phat,pr.se,pr.lo,pr.hi,pr.nWorst],w:[w.lo,w.wLo,w.wHi],c:[c1.rate,c1.coverLabel,c2.rate,c2.coverLabel,c3.rate,c3.coverLabel]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<=t;
 const ok=n(r.m[0],48.04)&&n(r.m[1],51.96)&&n(r.m[2],1.96)&&r.m[3]===385&&n(r.t[0],2.131449,2e-6)&&n(r.t[1],4.262899,4e-6)
  &&n(r.p[0],0.2)&&n(r.p[1],0.02)&&n(r.p[2],0.1608)&&n(r.p[3],0.2392)&&r.p[4]===1068&&n(r.w[0],-0.031481,2e-6)&&n(r.w[1],0.027866,2e-6)&&n(r.w[2],0.301038,2e-6)
  &&Math.abs(r.c[0]-0.95)<0.02&&r.c[1]==='約95%が含む'&&Math.abs(r.c[2]-0.878)<0.03&&r.c[3]==='95%より少ない'&&Math.abs(r.c[4]-0.95)<0.02&&r.c[5]==='約95%が含む';
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
