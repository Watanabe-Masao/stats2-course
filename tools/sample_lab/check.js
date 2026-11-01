// 標本ラボの数値の検算：無作為なら x̄ の平均≒μ、名簿の漏れ・自分から回答では μ からずれる
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-sample.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__;const mean=L.mean;
  // 検算の乱数は種を固定する（毎回種が変わって偶然落ちる運用にしない。issue 144）。ラボの乱数（math-lab）とは別の作り方（Park–Miller）で、同じ誤りを共有しない
  let sd=20261101;const rnd=()=>{sd=(sd*16807)%2147483647;return (sd-1)/2147483646;};
  const sim=(f,T=4000)=>{let s=0;for(let t=0;t<T;t++)s+=f();return s/T;};
  const pick=(idx,n)=>{const a=idx.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a.slice(0,n);};
  const all=[...L.POP.keys()];
  const rand=sim(()=>mean(pick(all,10).map(i=>L.POP[i])));
  const full=mean(pick(all,100).map(i=>L.POP[i]));
  // 名簿の漏れ20%
  const out=new Set(L.ORDER.slice(0,20));const fr=all.filter(i=>!out.has(i));
  const frame=sim(()=>mean(pick(fr,60).map(i=>L.POP[i])));
  const resp=k=>sim(()=>{const a=all.filter(i=>rnd()<L.respProb(L.POP[i],k));return a.length?mean(a.map(i=>L.POP[i])):NaN;},2000);
  return {fm:L.frameMean(),rm6:L.respMean(6),rm0:L.respMean(0),mu:L.MU,min:Math.min(...L.POP),max:Math.max(...L.POP),rand,full,frame,resp6:resp(6),resp0:resp(0)};});
 console.log(JSON.stringify(r,null,1));
 // ラボの「集まる所」（frameMean・respMean）が、何度も取り直したときの平均と一致する
 // 本文に書いた値：μ≒2.54、名簿の漏れ20%で約−0.18、自分から回答（強さ6）で約2.17
 const ok=Math.abs(r.mu-2.542)<1e-9&&Math.abs(r.frame-r.mu+0.18)<0.02&&Math.abs(r.resp6-2.17)<0.03&&Math.abs(r.rand-r.mu)<0.02&&Math.abs(r.full-r.mu)<1e-9&&r.frame<r.mu-0.1&&r.resp6<r.mu-0.1&&Math.abs(r.resp0-r.mu)<0.03&&Math.abs(r.fm-2.36375)<1e-9&&Math.abs(r.rm6-r.resp6)<0.03&&Math.abs(r.rm0-r.mu)<1e-9;
 console.log(ok?'✅ 数値の検算 OK':'❌ 数値が想定と違う');await b.close();process.exit(ok?0:1);})();
