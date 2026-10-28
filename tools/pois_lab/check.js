// 離散分布ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-pois.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,set=(id,v)=>{const e=document.getElementById(id);e.value=v;};
  const po=(rt,t,k,kind)=>{set('pr',rt);set('pt',t);set('pk',k);document.getElementById('pkind').value=kind;return L.pVals();};
  const a=po(2,1,0,'eq'),b=po(2,0.5,0,'eq'),c=po(2,1,3,'ge'),d=po(3,1,1,'le');
  set('an',1000);set('ap',0.002);set('ak',2);const e=L.aVals();
  set('gp',0.5);set('gr',2);set('gk',3);const g=L.gVals();set('gp',0.25);set('gr',1);set('gk',4);const g2=L.gVals();
  set('hN',10);set('hK',2);set('hn',3);set('hk',1);const h=L.hVals();
  return {a:a.p0,b:b.p0,c:c.ge,d:d.le,e:[e.poi,e.bin],g:g.pk,g2:g2.mean,g3:[g.mean,g.var],h:[h.pk,h.mean]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-9)=>Math.abs(x-y)<t;
 const ok=n(r.a,Math.exp(-2))&&n(r.b,Math.exp(-1))&&n(r.c,1-5*Math.exp(-2))&&n(r.d,4*Math.exp(-3))&&n(r.e[0],2*Math.exp(-2))&&n(r.e[1],0.27094159847598337,1e-12)&&n(r.g,0.25)&&n(r.g2,4)&&n(r.g3[0],4)&&n(r.g3[1],4)&&n(r.h[0],7/15)&&n(r.h[1],0.6);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
