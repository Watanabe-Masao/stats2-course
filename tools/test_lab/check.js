// 検定の考え方ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-test.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  sel('zside','two');sel('zalpha','0.05');set('zx',104.4);set('zm',100);set('zs',10);set('zn',25);const z=L.zVals();sel('zalpha','0.01');const z1=L.zVals();
  sel('wside','two');sel('walpha','0.05');set('wm0',100);set('wm1',104);set('ws',10);set('wn',25);const w=L.wVals();set('wm1',100);const w0=L.wVals();
  sel('kalpha','0.05');document.getElementById('kbon').checked=false;set('kk',20);const k=L.kVals();
  return {z:[z.z,z.p,z.decision,z1.decision],w:[w.power,w.beta,w.n80,w0.power],k:[k.fwer,k.sim]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-5)=>Math.abs(x-y)<=t;
 const ok=n(r.z[0],2.2,1e-9)&&n(r.z[1],0.027807)&&r.z[2]==='棄却する'&&r.z[3]==='棄却しない'&&n(r.w[0],0.515991)&&n(r.w[1],0.484009)&&r.w[2]===50&&n(r.w[3],0.049996)&&n(r.k[0],0.641514)&&Math.abs(r.k[1]-0.64)<0.04;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
