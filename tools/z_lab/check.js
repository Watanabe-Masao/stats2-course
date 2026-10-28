// 標準化ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-z.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  const sk=k=>L.moments(L.kCounts(k)).g1;
  set('fq1',10);set('fq3',14);set('fx',21);const F=L.fVals();
  set('im',62);set('is',8);set('iz',1.5);const I=L.iVals();
  return {p2:1-L.Phi(2),p1:2*L.Phi(1)-1,p2in:2*L.Phi(2)-1,pm3:L.Phi(-3),right:sk(6),left:sk(-6),sym:sk(0),hi:F.hi,out:F.out,dev:I.dev,x:I.x};});
 console.log(JSON.stringify(r));
 const near=(a,b,t)=>Math.abs(a-b)<t;
 const ok=near(r.p2,0.02275,1e-5)&&near(r.p1,0.6827,1e-4)&&near(r.p2in,0.9545,1e-4)&&near(r.pm3,0.00135,1e-5)&&r.right>0&&r.left<0&&Math.abs(r.sym)<0.05
  &&r.hi===20&&r.out===true&&near(r.dev,65,1e-9)&&near(r.x,74,1e-9);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
