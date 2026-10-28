// 数え方ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-count.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  set('ln',5);set('lr',2);const l1=L.lVals();set('ln',8);set('lr',3);const l2=L.lVals();set('ln',10);set('lr',2);const l3=L.lVals();
  set('pn',7);set('pr',3);const p1=L.bVals();set('pn',4);set('pr',1);set('pp',0.25);const p2=L.bVals();set('pn',10);set('pr',5);const p3=L.bVals();
  set('mn',3);set('mr',2);const m=L.mVals();set('mn',4);set('mr',6);const m2=L.mVals();
  set('pa',4);set('pb',3);const a=L.aVals();
  set('dn',4);const d=L.dVals();
  return {l1,l2,l3,p1,p2:{psum:p2.psum,c:p2.c,rowsum:p2.rowsum},p3:p3.c,m,m2:m2.h,a:a.paths,d};});
 console.log(JSON.stringify(r));
 const ok=r.l1.perm===20&&r.l1.comb===10&&r.l2.perm===336&&r.l2.comb===56&&r.l3.comb===45&&r.p1.c===35&&r.p1.left===15&&r.p1.right===20
  &&Math.abs(r.p2.psum-1)<1e-12&&r.p2.c===4&&r.p2.rowsum===16&&r.p3===252&&r.m.pow===9&&r.m.h===6&&r.m2===84&&r.a===35&&r.d.d===9&&r.d.all===24;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
