// 平均の t 検定ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-ttest.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,set=(id,v)=>LK.setRange(id,v),sel=(id,v)=>{document.getElementById(id).value=v;};
  sel('oside','two');sel('oalpha','0.05');set('ox',104);set('om',100);set('os',8);set('on',16);const a=L.oVals();sel('oside','upper');const a1=L.oVals();
  sel('pside','two');sel('palpha','0.05');set('pd',2);set('ps',5);set('pn',25);const pa=L.pVals();
  sel('tside','two');sel('talpha','0.05');sel('tmeth','welch');set('tx1',30);set('ts1',2);set('tn1',10);set('tx2',25);set('ts2',8);set('tn2',20);const w=L.tVals();sel('tmeth','pooled');const po=L.tVals();
  const q=[5,15,24,30,63].map(d=>L.tq(0.975,d));
  return {a:[a.t,a.df,a.p,a.crit,a.decision],a1:[a1.p,a1.crit,a1.decision],pa:[pa.t,pa.p,pa.decision],w:[w.se,w.df,w.t,w.p,w.decision],po:[po.se,po.df,po.t,po.p,po.decision],q};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=2e-5)=>Math.abs(x-y)<=t;
 const ok=n(r.a[0],2)&&r.a[1]===15&&n(r.a[2],0.063945)&&n(r.a[3],2.131450)&&r.a[4]==='棄却しない'
  &&n(r.a1[0],0.031973)&&n(r.a1[1],1.753050)&&r.a1[2]==='棄却する'
  &&n(r.pa[0],2)&&n(r.pa[1],0.056940)&&r.pa[2]==='棄却しない'
  &&n(r.w[0],1.897367)&&n(r.w[1],23.278992)&&n(r.w[2],2.635231)&&n(r.w[3],0.014708)&&r.w[4]==='棄却する'
  &&n(r.po[0],2.589815)&&r.po[1]===28&&n(r.po[2],1.930640)&&n(r.po[3],0.063711)&&r.po[4]==='棄却しない'
  &&n(r.q[0],2.570582)&&n(r.q[1],2.131450)&&n(r.q[2],2.063899)&&n(r.q[3],2.042272)&&n(r.q[4],1.998341);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
