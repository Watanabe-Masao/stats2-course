// 使い方: node tools/test_lab.js tools/sample_lab/sample_lab.html [出力先フォルダ]
// 全モードを開いてエラー・横はみ出し（380px）を調べ、ライト／ダークの画面を保存する。
const {chromium}=require('playwright');const path=require('path');
(async()=>{const file=path.resolve(process.argv[2]);const out=process.argv[3]||'/tmp';
 const b=await chromium.launch();let fail=0;
 for(const scheme of ['light','dark']){const p=await b.newPage({viewport:{width:380,height:900},colorScheme:scheme});
  const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await p.goto('file://'+file);
  const modes=await p.$$eval('.tabs button',bs=>bs.map(b=>b.dataset.m));
  for(const m of modes){await p.click(`.tabs button[data-m="${m}"]`);
   for(const btn of await p.$$(`#m-${m} button.act`)){await btn.click();}
   const sw=await p.evaluate(()=>document.documentElement.scrollWidth);
   if(sw>380){console.log(`❌ ${scheme}/${m}: 横にはみ出し ${sw}px`);fail++;}
   await p.screenshot({path:`${out}/${path.basename(file,'.html')}_${m}_${scheme}.png`,fullPage:true});}
  if(errs.length){console.log(`❌ ${scheme}: エラー`,errs);fail++;}
  await p.close();}
 await b.close();console.log(fail?`❌ ${fail} 件`:'✅ エラー・はみ出しなし');process.exit(fail?1:0);})();
