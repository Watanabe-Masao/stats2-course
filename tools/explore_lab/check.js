// 探究ラボのデータの仕組み：キャンペーンの差は、全体では大きく見えるが、平日・週末に分けると小さい（週末に多く行ったため）
const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+path.resolve(__dirname,'../../out/labs/LAB-explore.html'));
 const r=await p.evaluate(()=>{const L=window.__LAB__,d=(g,f)=>{document.getElementById('xv').value='sales';document.getElementById('xg').value=g;document.getElementById('xf').value=f;const C=L.cur();return C.st[1].S.mean-C.st[0].S.mean;};
  return {all:d('camp','all'),wd:d('camp','weekday'),we:d('camp','weekend'),n:L.DAYS.length,ev:L.DAYS.filter(x=>x.ev).length};});
 console.log(JSON.stringify(r));
 const ok=r.n===240&&r.ev===2&&r.all>4&&Math.abs(r.wd)<2.5&&Math.abs(r.we)<2.5;
 console.log(ok?'✅ 数値の検算 OK':'❌ データの仕組みが想定と違う');await b.close();process.exit(ok?0:1);})();
