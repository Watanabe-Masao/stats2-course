// 尺度ラボの数値の検算：本文に書いた値と一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-scale.html'));  // python3 build/build.py で作る
 const r=await p.evaluate(()=>{const L=window.__LAB__;const t=L.KINDS.temp.units,w=L.KINDS.wt.units,y=L.KINDS.year.units;
  const rr=(u,a,b)=>u.map(([,f])=>L.ratio(f(a),f(b)));
  const s=v5=>[1,2,3,4,v5];
  return {temp:rr(t,10,20),wt:rr(w,10,20),year:rr(y,2010,2020),
   mA:L.lmean(L.ST.A,s(5)),mB:L.lmean(L.ST.B,s(5)),mB41:L.lmean(L.ST.B,s(4.1)),mBm1:L.lmean(L.ST.B,[-1,2,3,4,5]),
   medA:L.lmedian(L.ST.A),medB:L.lmedian(L.ST.B),tA:L.ltop(L.ST.A),tB:L.ltop(L.ST.B),
   ageMean:L.bClassMean(1),age10:L.bClassMean(10),age5:L.bClassMean(5),items:L.ITEMS.length,
   money:rr(L.KINDS.money.units,10,20)};});
 console.log(JSON.stringify(r));
 const near=(a,b,e=1e-3)=>Math.abs(a-b)<e;
 const ok=near(r.temp[0],2)&&near(r.temp[1],1.035)&&near(r.temp[2],1.36)&&r.wt.every(x=>near(x,2,1e-9))
  &&near(r.year[0],1.005)&&near(r.year[1],2)&&near(r.year[2],1.091)
  &&near(r.mA,3.4)&&near(r.mB,3.8)&&near(r.mB41,3.26)&&near(r.mBm1,3.4)
  &&r.medA.join()==="2,2"&&r.medB.join()==="4,4"&&near(r.tA,0.4)&&near(r.tB,0.7)
  &&near(r.ageMean,41.6)&&near(r.age10,41.5)&&r.items===15&&r.money.every(x=>near(x,2,1e-9));
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
