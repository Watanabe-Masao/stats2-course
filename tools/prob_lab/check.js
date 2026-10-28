// 確率ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-prob.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{document.getElementById(id).value=v;};
  set('da','even');set('db','ge4');const d1=L.dVals();set('da','odd');set('db','le3');const d2=L.dVals();set('da','one');set('db','six');const d3=L.dVals();
  set('ra',50);set('rb',40);set('rab',20);const r1=L.rVals();set('ra',40);set('rb',30);set('rab',10);const r2=L.rVals();set('ra',70);set('rb',60);set('rab',50);const r3=L.rVals();
  const at=(a,b,n)=>{set('ta',a);set('tb',b);set('tn',n);return L.tVals();};
  const u=(r,b,rep)=>{set('ur',r);set('ub',b);set('urep',rep);return L.uVals();};const u1=u(2,3,'なし'),u2=u(2,3,'あり'),u3=u(3,2,'なし'),u4=u(2,8,'なし'),u5=u(3,7,'なし');
  const x=(a,b,c,d)=>{set('xa',a);set('xb',b);set('xc',c);set('xd',d);return L.xVals();};const x1=x(12,28,6,54),x2=x(16,24,18,42),x3=x(24,6,28,42);
  return {u1:[u1.cond,u1.both,u1.second,u1.br],u2:[u2.both,u2.indep],u3:u3.both,u4:u4.second,u5:u5.both,x1:[x1.condBA,x1.condBnA],x2:[x2.condBA,x2.condBnA,x2.pB,x2.indep],x3:x3.condAB,d1:d1.union,d2:d2.union,d3:d3.excl,r1:[r1.union,r1.none],r2:[r2.union,r2.none],r3:r3.lo,t2:at(1,6,2).atleast,t3:at(1,6,3).atleast,t10:at(1,10,10).atleast,t10n:at(1,10,10).naive};});
 console.log(JSON.stringify(r));
 const n=(a,b,e=1e-9)=>Math.abs(a-b)<e;
 const ok=n(r.d1,2/3)&&n(r.d2,2/3)&&r.d3==='はい'&&r.r1[0]===70&&r.r1[1]===30&&r.r2[0]===60&&r.r2[1]===40&&r.r3===30&&n(r.t2,11/36)&&n(r.t3,91/216)&&n(r.t10,1-0.9**10)&&n(r.t10n,1)&&n(r.u1[0],1/4)&&n(r.u1[1],1/10)&&n(r.u1[2],2/5)&&n(r.u1[3],3/10)&&n(r.u2[0],4/25)&&r.u2[1]==='はい'&&n(r.u3,3/10)&&n(r.u4,0.2)&&n(r.u5,1/15)&&n(r.x1[0],30)&&n(r.x1[1],10)&&n(r.x2[0],40)&&n(r.x2[1],30)&&n(r.x2[2],34)&&r.x2[3]==='いいえ'&&n(r.x3,24/52*100);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
