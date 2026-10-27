// 散らばりラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-spread.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,S=k=>L.stats(L.DATA[k].v);
  const u=[2,3,4,5,6].map(n=>{L.LK.setRange?0:0;document.getElementById('un').value=n;const U=L.uVals();return [U.av,U.as2,U.cnt];});
  ['g1','g2','g3','g4'].forEach((id,i)=>document.getElementById(id).value=[1,1,2,6][i]);const G=L.gVals();
  return {B:S('B'),A:S('A'),t3:S('t3'),t4:S('t4'),rx:S('rx'),ry:S('ry'),u,gini:G.gini,area:G.area};});
 const near=(a,b,t=1e-9)=>Math.abs(a-b)<t;
 const ok=near(r.B.ss,90)&&near(r.B.v,18)&&near(r.B.s2,22.5)&&near(r.B.s,4.743,1e-3)&&near(r.B.sx2,590)
  &&near(r.A.ss,10)&&near(r.A.s2,2.5)&&near(r.t3.s2,4)&&near(r.t4.ss,20)&&near(r.t4.v,5)&&near(r.rx.ss,50)&&near(r.ry.ss,100)
  &&r.u.every(([av,as2,c],i)=>{const n=i+2;return near(av,8*(n-1)/n)&&near(as2,8)&&c===5**n;})&&near(r.gini,0.4)&&near(r.area,0.3);
 console.log(JSON.stringify({gini:r.gini,u:r.u.map(x=>x.map(v=>+v.toFixed(4)))}));
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
