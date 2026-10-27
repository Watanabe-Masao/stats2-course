// 分布ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-dist.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,F=L.five(L.DATA.sales.v),G=L.five(L.DATA.nine.v),V=L.five(L.DATA.visits.v);
  const c=L.classes(L.DATA.sales.v,10,10).map(x=>x.n),x=L.five(L.SHAPE.X),y=L.five(L.SHAPE.Y),C=L.five(L.STORES.C);
  return {F:[F.q1,F.q2,F.q3,F.iqr,F.lo,F.hi,F.whi,F.out.join(),F.mean],G:[G.q1,G.q2,G.q3,G.iqr,G.hi,G.out.join()],V:[V.q1,V.q2,V.q3,V.iqr,V.hi,V.out.join()],c,
   same:[x.min,x.q1,x.q2,x.q3,x.max].join()===[y.min,y.q1,y.q2,y.q3,y.max].join(),C:C.iqr};});
 console.log(JSON.stringify(r));
 const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 const ok=eq(r.F,[21.5,26.5,32,10.5,5.75,47.75,42,"55",27.6])&&eq(r.G,[5.5,8,11,5.5,19.25,"30"])&&eq(r.V,[50,53.5,59,9,72.5,"120"])&&eq(r.c,[4,9,5,1,1])&&r.same&&r.C===32;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
