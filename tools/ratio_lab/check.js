// 割合ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-ratio.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  set('bfind','base');set('bpart',800);set('brate',80);const b1=L.bVals().base;
  set('bfind','rate');set('bpart',50);set('bbase',200);const b2=L.bVals().rate;
  set('cx',1000);set('cr1',20);set('cr2',-20);const c1=L.cVals();
  set('cx',200);set('cr1',-10);set('cr2',10);const c2=L.cVals();
  set('pp1',10);set('pp2',12);const p1=L.pVals();
  set('ea',3);set('eb',6);set('ec',21);const e1=L.eVals().x;
  set('mp',1000);set('mc',700);const m=L.mVals();
  return {b1,b2,c1f:c1.x2,c1t:c1.total,back:c1.back,c2t:c2.total,pt:p1.pt,rel:p1.rel,e1,margin:m.margin,markup:m.markup,cost:m.cost};});
 console.log(JSON.stringify(r));
 const near=(a,b)=>Math.abs(a-b)<1e-6;
 const ok=near(r.b1,1000)&&near(r.b2,0.25)&&near(r.c1f,960)&&near(r.c1t,-4)&&Math.abs(r.back+16.667)<0.001&&near(r.c2t,-1)&&r.pt===2&&near(r.rel,20)&&near(r.e1,5)
  &&near(r.margin,30)&&Math.abs(r.markup-42.857)<0.001&&near(r.cost,70);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
