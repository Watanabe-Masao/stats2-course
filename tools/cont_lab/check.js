// 連続分布ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-cont.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  const no=(mu,sd,a,b,kind)=>{set('nm',mu);set('ns',sd);LK.show('norm');set('na',a);set('nb',b);sel('nkind',kind);return L.nVals();};
  const n1=no(100,10,90,110,'between'),n2=no(100,10,120,130,'ge'),n3=no(60,4,52,66,'between'),n4=no(100,10,80,120,'between');
  set('qm',60);set('qs',10);set('qp',5);sel('qside','upper');const q=L.qVals();
  set('ua',2);set('ub',8);LK.show('unif');set('uc',3);set('ud',5);const u=L.uVals();
  set('em',0.5);LK.show('expo');set('et',1);set('es',0.5);const e=L.eVals();
  set('ds',0.2);LK.show('dens');set('dx',0);set('dw',0);const d=L.dVals();
  return {n:[n1.p,n2.p,n3.p,n4.p,n1.za,n1.zb],q:[q.z,q.x],u:[u.p,u.mean,u.var],e:[e.pgt,e.cond,e.mean,e.var],d:[d.fx,d.p,d.over1]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-6)=>Math.abs(x-y)<t;
 const ok=n(r.n[0],0.682689,1e-6)&&n(r.n[1],0.0227501,1e-6)&&n(r.n[2],0.9331928-0.0227501,1e-6)&&n(r.n[3],0.9544997,1e-6)&&n(r.n[4],-1)&&n(r.n[5],1)
  &&n(r.q[0],1.6448536,1e-6)&&n(r.q[1],76.448536,1e-5)&&n(r.u[0],1/3)&&n(r.u[1],5)&&n(r.u[2],3)
  &&n(r.e[0],Math.exp(-2))&&n(r.e[1],Math.exp(-2))&&n(r.e[2],0.5)&&n(r.e[3],0.25)&&n(r.d[0],1/(0.2*Math.sqrt(2*Math.PI)))&&n(r.d[1],0)&&r.d[2]==='超える';
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
