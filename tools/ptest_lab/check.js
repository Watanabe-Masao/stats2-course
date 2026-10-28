// 比率・分散の検定ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-ptest.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  sel('aside','two');sel('aalpha','0.05');set('an',100);set('ax',30);set('ap',0.2);const a=L.aVals();
  sel('bside','two');sel('balpha','0.05');set('bn1',100);set('bn2',100);set('bx1',20);set('bx2',30);const b1=L.bVals();set('bn1',200);set('bn2',200);set('bx1',40);set('bx2',60);const b2=L.bVals();
  sel('cside','two');sel('calpha','0.05');set('cn',10);set('cs',16);set('cv',9);const c=L.cVals();sel('cside','upper');const cu=L.cVals();
  sel('dside','two');sel('dalpha','0.05');set('dn1',11);set('dn2',11);set('ds1',16);set('ds2',4);const d=L.dVals();
  return {a:[a.se,a.z,a.p,a.decision],b:[b1.pool,b1.se,b1.z,b1.decision,b2.z,b2.decision],c:[c.q,c.lo,c.hi,c.decision,cu.hi,cu.p],d:[d.F,d.hi,d.decision]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-4)=>Math.abs(x-y)<=t;
 const ok=n(r.a[0],0.04,1e-9)&&n(r.a[1],2.5,1e-9)&&n(r.a[2],0.012419)&&r.a[3]==='棄却する'
  &&n(r.b[0],0.25,1e-9)&&n(r.b[1],0.061237)&&n(r.b[2],-1.632993)&&r.b[3]==='棄却しない'&&n(r.b[4],-2.309401)&&r.b[5]==='棄却する'
  &&n(r.c[0],16,1e-9)&&r.c[1]===2.7&&r.c[2]===19.023&&r.c[3]==='棄却しない'&&r.c[4]===16.919&&n(r.c[5],0.066882)
  &&n(r.d[0],4,1e-9)&&r.d[1]===3.717&&r.d[2]==='棄却する';
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
