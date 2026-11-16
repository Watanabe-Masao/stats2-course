// 分布ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-dist.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,F=L.five(L.DATA.sales.v),G=L.five(L.DATA.nine.v),V=L.five(L.DATA.visits.v);
  const c=L.classes(L.DATA.sales.v,10,10).map(x=>x.n),x=L.five(L.SHAPE.X),y=L.five(L.SHAPE.Y),C=L.five(L.STORES.C);
  return {F:[F.q1,F.q2,F.q3,F.iqr,F.lo,F.hi,F.whi,F.out.join(),F.mean],G:[G.q1,G.q2,G.q3,G.iqr,G.hi,G.out.join()],V:[V.q1,V.q2,V.q3,V.iqr,V.hi,V.out.join()],c,
   same:[x.min,x.q1,x.q2,x.q3,x.max].join()===[y.min,y.q1,y.q2,y.q3,y.max].join(),C:C.iqr,
   // 創造の待ち時間：件数（140・60）と5の倍数の件数（70・9）。表から並べる expand の誤り（件数のずれ）を見つける
   W:[L.DATA.wait.v.length,L.DATA.wait.v.filter(v=>v%5===0).length,L.DATA.waitauto.v.length,L.DATA.waitauto.v.filter(v=>v%5===0).length],
   // 発展：1年の365日の幅10の度数（26・135・150・44・10）と、Z店の幅10の度数（2・6・5・1）と幅5の度数（1・1・4・2・4・1・1）
   Y:L.classes(L.DATA.year.v,10,10).map(x=>x.n),S:L.classes(L.DATA.zstore.v,10,10).map(x=>x.n).concat(L.classes(L.DATA.zstore.v,10,5).map(x=>x.n)),N:L.DATA.year.v.length};});
 console.log(JSON.stringify(r));
 const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 const ok=eq(r.F,[21.5,26.5,32,10.5,5.75,47.75,42,"55",27.6])&&eq(r.G,[5.5,8,11,5.5,19.25,"30"])&&eq(r.V,[50,53.5,59,9,72.5,"120"])&&eq(r.c,[4,9,5,1,1])&&r.same&&r.C===32&&eq(r.W,[140,70,60,9])&&eq(r.Y,[26,135,150,44,10])&&eq(r.S,[2,6,5,1,1,1,4,2,4,1,1])&&r.N===365;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
