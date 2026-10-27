// out/labs/ の全部の版を調べる（python3 build/build.py のあとに実行）。
// 使い方: node tools/test_labs.js [スクリーンショットの保存先]
//  - アップロード用の版（out/labs）と公開サイト（out/site の ?p=場面）の両方
//  - エラーがない、380px で横にはみ出さない（ライト／ダーク）
//  - 予想がある版：予想する前は結果（.res）が見えない。予想を入れると結果が出る
//  - expect：ラボが計算した値（LK.last）と一致する
//  - ラボのモードが tool.yaml の modes と一致し、全モードを開いてボタンを押してもエラーが出ない
const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
const ROOT=path.resolve(__dirname,'..');
(async()=>{const read=f=>fs.existsSync(path.join(ROOT,f))?JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8')):[];
 const man=[...read('out/labs/manifest.json'),...read('out/site_manifest.json').map(v=>({...v,site:true}))];
 const shots=process.argv[2];const b=await chromium.launch();let fail=0;const embedH=[];
 const bad=(m)=>{console.log('❌ '+m);fail++;};
 for(const v of man){for(const scheme of ['light','dark']){
  const p=await b.newPage({viewport:{width:380,height:900},colorScheme:scheme});
  const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await p.goto('file://'+path.join(ROOT,v.file)+(v.query||''));
  const tag=`${v.site?'公開サイト ':''}${v.asset} (${scheme})`;
  const sw=()=>p.evaluate(()=>document.documentElement.scrollWidth);
  if(await sw()>380)bad(`${tag}: 横にはみ出し`);
  if(v.cfg.mode){const m=await p.evaluate(()=>LK.mode);if(m!==v.cfg.mode)bad(`${tag}: 最初のモードが ${m}`);}
  const pr=v.cfg.predict;
  if(pr){
   const vis=await p.evaluate(()=>[...document.querySelectorAll('.mode').values()].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).some(e=>e.offsetParent!==null));
   if(vis)bad(`${tag}: 予想の前に結果が見えている`);
   if(shots&&scheme==='light'&&!v.site)await p.screenshot({path:`${shots}/${v.asset.replace('@','__')}_before.png`,fullPage:true});
   if(pr.type==='number')await p.fill('#lk-in',String(v.expect));
   else await p.click(`#lk-ch button[data-v="${v.expect}"]`);
   await p.click('#lk-go');
   const r=await p.evaluate(()=>({last:LK.last,locked:LK.locked,vis:[...document.querySelectorAll('.mode')].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).every(e=>e.offsetParent!==null),verdict:document.getElementById('lk-verdict').innerText}));
   if(r.locked||!r.vis)bad(`${tag}: 予想のあとも結果が出ない`);
   const ok=typeof v.expect==='number'?Math.abs(r.last.v-v.expect)<=Math.max(5e-4,Math.abs(v.expect)*5e-4):r.last.text===v.expect;
   if(!ok)bad(`${tag}: expect ${v.expect} とラボの値 ${r.last.text} が違う`);
   if(!/予想どおり/.test(r.verdict))bad(`${tag}: 正しい予想なのに「予想どおり」にならない`);
   if(await sw()>380)bad(`${tag}: 結果を出したあと横にはみ出し`);
   if(shots&&scheme==='light'&&!v.site)await p.screenshot({path:`${shots}/${v.asset.replace('@','__')}_after.png`,fullPage:true});
  }else if(shots&&scheme==='light'&&!v.site)await p.screenshot({path:`${shots}/${v.asset.replace('@','__')}.png`,fullPage:true});
  // 全モードを回して、主なボタンと −／＋ を押す
  const modes=await p.$$eval('#tabs button',bs=>bs.map(x=>x.dataset.m));
  const want=v.cfg.modes||(v.cfg.mode?[v.cfg.mode]:v.modes);
  if(want&&modes.join()!==want.join())bad(`${tag}: タブ ${modes} が ${want} と違う（場面の modes／mode／tool.yaml の modes）`);
  for(const m of modes){if(modes.length>1)await p.click(`#tabs button[data-m="${m}"]`);
   for(const btn of await p.$$(`#m-${m} button.act, #m-${m} .lk-step button`)){if(await btn.isVisible()&&await btn.isEnabled())await btn.click();}
   if(await sw()>380)bad(`${tag}/${m}: 横にはみ出し`);}
  if(errs.length)bad(`${tag}: エラー ${errs.join(' / ')}`);
  await p.close();}
  // Notion の埋め込み（高さ約320px）：予想の前は枠に収まる。結果のあとは「くわしく」で表・式が開く
  const p=await b.newPage({viewport:{width:360,height:320}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
  await p.goto('file://'+path.join(ROOT,v.file)+(v.query?v.query+'&':'?')+'embed=1');
  const tag=`埋め込み ${v.site?'公開サイト ':''}${v.asset}`;
  const h=()=>p.evaluate(()=>document.documentElement.scrollHeight);
  if(await p.evaluate(()=>document.documentElement.scrollWidth)>360)bad(`${tag}: 横にはみ出し`);
  if(v.cfg.predict){
   if(await h()>320)bad(`${tag}: 予想の前に枠（320px）に収まらない（${await h()}px）`);
   const fixed=Object.keys(v.cfg.set||{});
   for(const k of fixed)if(await p.$eval(`#m-${v.cfg.mode}`,(m,k)=>{const s=m.querySelector(`select[data-key="${k}"]`);return s&&s.offsetParent!==null;},k))bad(`${tag}: 問題で決めた ${k} が選べてしまう`);
   if(v.cfg.predict.type==='number')await p.fill('#lk-in',String(v.expect));else await p.click(`#lk-ch button[data-v="${v.expect}"]`);
   await p.click('#lk-go');
   embedH.push(`${v.asset}:${await h()}`);
   await p.click('#lk-more');
   if(!(await p.evaluate(()=>[...document.querySelectorAll('.mode')].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).every(e=>e.offsetParent!==null))))bad(`${tag}: くわしくで結果が開かない`);
  }
  if(errs.length)bad(`${tag}: エラー ${errs.join(' / ')}`);
  await p.close();}
 await b.close();if(process.env.EMBED_H)console.log('結果のあとの高さ',embedH.join(' '));console.log(fail?`❌ ${fail} 件`:`✅ ${man.length} 版：エラー・はみ出しなし、予想の前は結果が隠れ、答えはラボの値と一致`);process.exit(fail?1:0);})();
