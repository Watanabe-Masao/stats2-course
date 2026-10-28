// 中心極限定理ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-clt.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  set('bn',100);set('bp',0.5);set('bk',55);sel('bkind','le');const a=L.bVals();
  sel('cshape','expo');set('cn',30);const c=L.cVals();set('cn',1);const c1=L.cVals();
  set('lp',0.3);set('lN',100);const l=L.lVals();set('hk',2);const h=L.hVals();
  return {a:[a.approx,a.exact,a.nocc,a.z],c:[c.gmean,c.shapeLabel,c.se,c.simsd,c1.shapeLabel],l:l.se,h:[h.bound,h.normal]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-6)=>Math.abs(x-y)<t;
 const ok=n(r.a[0],0.8643339,2e-6)&&n(r.a[1],0.8643735,1e-6)&&n(r.a[2],0.8413447,2e-6)&&n(r.a[3],1.1)&&n(r.c[0],2/Math.sqrt(30))&&r.c[1]==='左右対称に近い'&&n(r.c[2],5/Math.sqrt(30))&&Math.abs(r.c[3]-5/Math.sqrt(30))<0.05&&r.c[4]==='右に歪む'&&n(r.l,Math.sqrt(0.0021))&&n(r.h[0],0.25)&&n(r.h[1],0.0455003,2e-6);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
