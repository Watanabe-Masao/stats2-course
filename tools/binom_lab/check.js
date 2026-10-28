// 二項分布ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-binom.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{const e=document.getElementById(id);if(e.max&&+e.max<+v)e.max=v;e.value=v;};
  const b=(n,pp,k)=>{set('bn',n);set('bp',pp);set('bk',k);return L.bVals();};
  const a=b(4,0.25,1),c=b(4,0.25,2),d=b(5,0.2,2),e=b(20,0.1,3),g=b(100,0.5,60);
  set('qn',3);set('qp',0.5);set('qk',2);const q=L.qVals();set('qn',4);set('qp',0.25);set('qk',1);const q2=L.qVals();
  set('ep',0.25);set('en',4);const e1=L.eVals();
  return {a:[a.pk,a.p0,a.atleast1,a.mean,a.var],c:c.ge,d:[d.pk,d.mean,d.var],e:e.ge,g:g.ge,q:[q.pk,q.ncr],q2:[q2.ncr,q2.path],e1:[e1.mean,e1.var,e1.bvar]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<t;
 const ok=n(r.a[0],0.421875)&&n(r.a[1],0.31640625)&&n(r.a[2],0.68359375)&&n(r.a[3],1)&&n(r.a[4],0.75)&&n(r.c,0.26171875)&&n(r.d[0],0.2048)&&n(r.d[1],1)&&n(r.d[2],0.8)
  &&n(r.e,0.32307319481053354,1e-9)&&n(r.g,0.0284439668,1e-8)&&n(r.q[0],0.375)&&r.q[1]===3&&r.q2[0]===4&&n(r.q2[1],0.25*0.75**3)&&n(r.e1[0],1)&&n(r.e1[1],0.75)&&n(r.e1[2],0.1875);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
