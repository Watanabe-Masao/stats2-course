// カイ二乗検定ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-chisq.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,sel=(id,v)=>{document.getElementById(id).value=String(v);};
  sel('ir',2);sel('ic',2);sel('ialpha',0.05);L.setT([[30,20],[20,30]]);const a=L.iVals();L.setT([[15,10],[10,15]]);const h=L.iVals();
  sel('ir',2);sel('ic',3);L.setT([[30,40,30],[20,40,40]]);const t=L.iVals();
  sel('gk',2);sel('gm',0);sel('galpha',0.05);L.setG([60,40],[1,1]);const g=L.gVals();
  sel('gk',4);L.setG([26,14,22,18],[1,1,1,1]);const g4=L.gVals();
  return {a:[a.e11,a.chi2,a.df,a.crit,a.p,a.decision],h:[h.chi2,h.decision],t:[t.chi2,t.df,t.crit],g:[g.chi2,g.df,g.p],g4:[g4.chi2,g4.df,g4.crit]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-4)=>Math.abs(x-y)<=t;
 const ok=n(r.a[0],25,1e-9)&&n(r.a[1],4,1e-9)&&r.a[2]===1&&r.a[3]===3.841&&n(r.a[4],0.0455)&&r.a[5]==='棄却する'
  &&n(r.h[0],2,1e-9)&&r.h[1]==='棄却しない'&&n(r.t[0],3.428571)&&r.t[1]===2&&r.t[2]===5.991
  &&n(r.g[0],4,1e-9)&&r.g[1]===1&&n(r.g[2],0.0455)&&n(r.g4[0],4,1e-9)&&r.g4[1]===3&&r.g4[2]===7.815;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
