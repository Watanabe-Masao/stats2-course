// 標本平均ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-xbar.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v);
  const se=(mu,sd,n)=>{set('sm',mu);set('ss',sd);set('sn',n);return L.sVals();};
  const a=se(50,12,9),b=se(50,12,36),c=se(50,12,144),d=se(0,10,25);
  set('pp',0.2);set('pn',100);set('pe',0.02);const pr=L.pVals();set('pp',0.5);const pr2=L.pVals();
  document.getElementById('uv').value='1,3,5';set('un',2);const u=L.uVals();
  document.getElementById('ssim').click();set('sn',36);
  return {se:[a.se,b.se,c.se,d.var,d.se,b.sdsum],p:[pr.se,pr2.nFor],u:[u.sigma2,u.meanV,u.meanS2,u.count,u.varM]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<t;
 const ok=n(r.se[0],4)&&n(r.se[1],2)&&n(r.se[2],1)&&n(r.se[3],4)&&n(r.se[4],2)&&n(r.se[5],72)&&n(r.p[0],0.04)&&r.p[1]===625&&n(r.u[0],8/3)&&n(r.u[1],4/3)&&n(r.u[2],8/3)&&r.u[3]===9&&n(r.u[4],4/3);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
