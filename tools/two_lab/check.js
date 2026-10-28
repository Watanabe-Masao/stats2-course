// 2群・分散の区間ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-two.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  sel('vlevel','0.95');set('vn',10);set('vs',4);const v=L.vVals();
  sel('dmeth','welch');set('dx1',30);set('ds1',2);set('dn1',10);set('dx2',25);set('ds2',8);set('dn2',20);const w=L.dVals();sel('dmeth','pooled');const po=L.dVals();
  set('pd',3);set('ps',4);set('pn',16);const pa=L.pVals();
  set('qn1',200);set('qx1',60);set('qn2',200);set('qx2',40);const q=L.qVals();
  set('rs1',18);set('rn1',11);set('rs2',9);set('rn2',13);const ra=L.rVals();
  set('cr',0.5);set('cn',100);const c=L.cVals();
  return {v:[v.lo,v.hi,v.sdLo,v.sdHi],w:[w.se,w.df,w.lo,w.hi,w.contains0],po:[po.sp2,po.se,po.df,po.lo,po.contains0],pa:[pa.lo,pa.hi],q:[q.diff,q.se,q.lo,q.hi],ra:[ra.lo,ra.hi,ra.contains1],c:[c.zr,c.lo,c.hi]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=2e-5)=>Math.abs(x-y)<=t;
 const ok=n(r.v[0],1.892469)&&n(r.v[1],13.331410)&&n(r.v[2],1.375670)&&n(r.v[3],3.651220)
  &&n(r.w[0],1.897367)&&n(r.w[1],23.278992)&&n(r.w[2],1.077599)&&n(r.w[3],8.922401)&&r.w[4]==='0を含まない'
  &&n(r.po[0],44.714286)&&n(r.po[1],2.589815)&&r.po[2]===28&&n(r.po[3],-0.304996)&&r.po[4]==='0を含む'
  &&n(r.pa[0],0.868550)&&n(r.pa[1],5.131450)&&n(r.q[0],0.1)&&n(r.q[1],0.043012)&&n(r.q[2],0.015697)&&n(r.q[3],0.184303)
  &&n(r.ra[0],0.592847)&&n(r.ra[1],7.241891)&&r.ra[2]==='1を含む'&&n(r.c[0],0.549306)&&n(r.c[1],0.336640)&&n(r.c[2],0.634142);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
