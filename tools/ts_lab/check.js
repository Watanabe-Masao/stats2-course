// 時系列ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-ts.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__;
  const ma=L.maOf([10,14,12,18,16],3,"center"),ma2=L.maOf([20,26,23,29,32],3,"center"),tr=L.maOf([10,14,12,18,16],3,"trail");
  const x=L.daily(6,2),r=Array.from({length:14},(_,i)=>L.acf(x,i+1));const y=L.daily(0,0),r0=Array.from({length:14},(_,i)=>L.acf(y,i+1));
  const big=L.daily(0,10),rb=Array.from({length:14},(_,i)=>L.acf(big,i+1));
  return {ma,ma2,tr,peak:r.indexOf(Math.max(...r))+1,r7:r[6],r1:r[0],peak0:Math.max(...r0.map(Math.abs)),trendPos:rb.every(v=>v>0)};});
 console.log(JSON.stringify(r));
 const near=(a,b)=>Math.abs(a-b)<0.005;
 const ok=r.ma[0]===null&&near(r.ma[1],12)&&near(r.ma[2],44/3)&&near(r.ma[3],46/3)&&r.ma[4]===null&&near(r.ma2[1],23)&&near(r.ma2[2],26)&&near(r.ma2[3],28)
  &&r.tr[0]===null&&r.tr[1]===null&&near(r.tr[4],46/3)&&r.peak===7&&r.r7>0.5&&r.peak0<0.35&&r.trendPos;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
