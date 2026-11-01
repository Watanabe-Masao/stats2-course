// 実験計画ラボの数値の検算：本文・問題に書いた値とラボの計算が一致するか
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-doe.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,LK=L.LK,sel=(id,v)=>{document.getElementById(id).value=v;};
  const A=(d,rep=1)=>{sel('adata',d);LK.setRange('akb',1);LK.setRange('akw',1);LK.setRange('arep',rep);return L.aVals();};
  const a=A('ex'),a2=A('ex',2),b=A('b');
  const S=m=>{sel('smethod',m);LK.setRange('stau',3);return L.sVals();};const sc=S('choose'),sr=S('random'),sb=S('block');
  LK.setRange('mk',3);LK.setRange('mn',5);const m=L.mVals();LK.setRange('mk',6);const m6=L.mVals();LK.setRange('mk',3);
  LK.setRange('ies',4);LK.setRange('iel',0);LK.setRange('ip',0.5);const i=L.iVals();
  return {a:[a.ssb,a.ssw,a.F,a.crit,a.decision],a2:[a2.F,a2.decision],b:[b.F,b.crit],s:[sc.biased,sr.biased,sb.biased,sb.spread],m:[m.pairs,m.fwerT,m.fwerF],m6:[m6.pairs,m6.fwerT,m6.fwerF],i:[i.avg,i.inter]};});
 console.log(JSON.stringify(r));
 const n=(x,y,t=1e-6)=>Math.abs(x-y)<=t;
 // t 検定のくり返し（ラボは種を固定して2000回）：理論の値と、割合の標準誤差 √(p(1−p)/2000) の5倍の幅で照らす（issue 144 P6）。
 // 理論の値はラボとは別に求めた：numpy（PCG64・種 20261101）で200万回、各5店・正規分布。3群 t＝0.1232、6群 t＝0.3699（どちらも ±0.0003）。
 // F 検定の割合は理論どおり 0.05（分散分析の第1種の過誤）。本文の値（約0.13・約0.36）はラボの値と一致するか（下の Math.abs）
 const within=(x,p)=>Math.abs(x-p)<5*Math.sqrt(p*(1-p)/2000);
 const ok=n(r.a[0],16)&&n(r.a[1],6)&&n(r.a[2],4)&&r.a[3]===9.552&&r.a[4]==='棄却しない'&&n(r.a2[0],12)&&r.a2[1]==='棄却する'&&n(r.b[0],6.75)&&r.b[1]===5.143
  &&r.s[0]==='偏りあり'&&r.s[1]==='偏りなし'&&r.s[2]==='偏りなし'&&r.s[3]==='くじより小さい'&&r.m[0]===3&&r.m6[0]===15&&within(r.m[1],0.1232)&&within(r.m[2],0.05)&&within(r.m6[1],0.3699)&&within(r.m6[2],0.05)&&Math.round(r.m[1]*100)===13&&Math.round(r.m6[1]*100)===36&&n(r.i[0],2)&&n(r.i[1],4);
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
