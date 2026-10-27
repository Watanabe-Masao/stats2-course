// 代表値ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-center.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,D=L.DATA,v=k=>D[k].v;
  const shape=k=>{L.LK.setRange?0:0;document.getElementById('ssk').value=k;return L.order(L.sVals());};
  return {b:[L.mean(v('buy10')),L.median(v('buy10')),L.modes(v('buy10')),L.quart(v('buy10')),L.trim(v('buy10'),0.1)],
   five:[L.mean(v('five')),L.median(v('five')),L.modes(v('five'))],q06:[L.mean(v('q06')),L.median(v('q06')),L.quart(v('q06'))],
   sk:[L.mean(v('skew5')),L.median(v('skew5')),L.modes(v('skew5'))],six:[L.mean(v('six')),L.median(v('six')),L.modes(v('six'))],
   inc:[L.mean(v('income')),L.median(v('income'))],
   right:shape(8),left:shape(-8),sym:shape(0)};});
 console.log(JSON.stringify(r));
 const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),near=(a,b)=>Math.abs(a-b)<0.005;
 const ok=eq(r.b.slice(0,3),[4,2.5,[2]])&&eq(r.b[3],{q1:2,q3:4})&&r.b[4]===2.75
  &&eq(r.five,[6,5,[5]])&&eq(r.q06,[4,3,{q1:2,q3:6.5}])&&eq(r.sk,[6,2,[2]])&&eq(r.six,[20,16.5,[15]])
  &&near(r.inc[0],5150/9)&&r.inc[1]===450&&r.right==='最頻値＜中央値＜平均'&&r.left==='平均＜中央値＜最頻値'&&r.sym==='ほぼ等しい';
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
