// 統計図ラボの数値の検算と、点のドラッグで図と数が変わるか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:380,height:900}});await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-graph.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,sel=(id,v)=>{const e=document.getElementById(id);e.value=v;e.dispatchEvent(new Event('change'));};
  const a=L.lVals();LK.show('stem');const s=L.sVals();LK.show('cum');const c=L.cVals();LK.show('qual');const q=L.qVals();LK.show('link');
  return {a:[a.mean,a.median,a.q1,a.q3,a.outliers],s:[s.topStem,s.maxStemCount,s.median],c:[c.xq,c['below:30']],q:[q['angle:0'],q.top2]};});
 await p.click('#tabs button[data-m="link"]');const before=await p.evaluate(()=>window.__LAB__.lVals().mean);
 const d=await p.$('#ldots circle.sel');const bb=await d.boundingBox();await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2);await p.mouse.down();await p.mouse.move(bb.x-120,bb.y,{steps:6});await p.mouse.up();
 const after=await p.evaluate(()=>window.__LAB__.lVals().mean);
 console.log(JSON.stringify(r),before,after);
 const n=(x,y,t=1e-6)=>Math.abs(x-y)<=t;
 const ok=n(r.a[0],27.6)&&n(r.a[1],26.5)&&n(r.a[2],21.5)&&n(r.a[3],32)&&r.a[4]===1&&r.s[0]===2&&r.s[1]===9&&n(r.s[2],26.5)&&n(r.c[0],26.6667,1e-3)&&n(r.c[1],0.65)&&n(r.q[0],162)&&n(r.q[1],0.7)&&after<before;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
