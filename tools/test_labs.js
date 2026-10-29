// out/labs/ の全部の版を調べる（python3 build/build.py のあとに実行）。
// 使い方: node tools/test_labs.js [スクリーンショットの保存先]
//  - アップロード用の版（out/labs）と公開サイト（out/site の ?p=場面）の両方
//  - エラーがない、380px で横にはみ出さない（ライト／ダーク）
//  - 予想がある版：予想する前は結果（.res）が見えない。.res の外にも答えの数が出ていない。予想を入れると結果が出る
//  - expect：ラボが計算した値（LK.last）と一致する
//  - ラボのモードが tool.yaml の modes と一致し、全モードを開いてボタンを押してもエラーが出ない
const {chromium}=require('playwright');const path=require('path');const fs=require('fs');
const ROOT=path.resolve(__dirname,'..');
(async()=>{const read=f=>fs.existsSync(path.join(ROOT,f))?JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8')):[];
 const man=[...read('out/labs/manifest.json'),...read('out/site_manifest.json').map(v=>({...v,site:true}))].filter(v=>{const O=process.env.ONLY,A=process.env.ASSETS;  // ONLY=LAB-sigma,LAB-z（そのラボの全部の版）・ASSETS=LAB-prob@s6-free,…（その版だけ）で絞れる
   if(!O&&!A)return true;
   return (O&&O.split(',').some(o=>v.asset===o||v.asset.startsWith(o+'@')))||(A&&A.split(',').includes(v.asset));});
 // SHARD=k/n：版を n 組に分けて k 組目だけ（GitHub で別々の機械に分けて並行に走らせる。1台の中では同時に2つ走らせない）
 if(process.env.SHARD){const [k,n]=process.env.SHARD.split('/').map(Number);if(!(n>=1&&k>=1&&k<=n)){console.log('❌ SHARD は k/n（1≤k≤n）');process.exit(1);}
   const all=man.length;man.splice(0,all,...man.filter((_,i)=>i%n===k-1));console.log(`組 ${k}/${n}：${man.length}/${all} 版`);}
 if(!man.length){console.log('❌ 絞り込みに合う版がない');process.exit(1);}
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
  const ST=v.cfg.steps||null,EX=ST?v.expect:[v.expect],pr=ST?ST[0].predict:v.cfg.predict;const v0={...v,expect:EX[0],cfg:{...v.cfg,task:ST?ST[0].task:v.cfg.task,set:{...(v.cfg.set||{}),...(ST?ST[0].set||{}:{})}}};
  const first=(v.cfg.set||{}).items?v.cfg.set.items[0]:(v.cfg.set||{}).item;
  if(first&&await p.evaluate(()=>document.getElementById('jitem').textContent)!==first)bad(`${tag}: 最初のデータが ${first} にならない`);
  if(pr){
   const vis=await p.evaluate(()=>[...document.querySelectorAll('.mode').values()].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).some(e=>e.offsetParent!==null));
   if(vis)bad(`${tag}: 予想の前に結果が見えている`);
   // .res の付け忘れも見逃さない：予想の前に、課題・操作・説明文の外に答えの数が出ていないか
   if(typeof v0.expect==='number'&&v0.expect!==0){
    const given=[String(v0.cfg.task||''),JSON.stringify(v0.cfg.set||{})].join(' ');
    const nums=t=>(t.replace(/[,，]/g,'').replace(/[−–]/g,'-').match(/-?\d+(?:\.\d+)?/g)||[]).map(Number);
    const near=x=>Math.abs(Math.abs(x)-Math.abs(v0.expect))<=Math.max(1e-9,Math.abs(v0.expect)*1e-3);
    if(!nums(given).some(near)){
     const txt=await p.evaluate(()=>{const m=[...document.querySelectorAll('.mode')].find(d=>d.style.display!=='none');if(!m)return '';
      return [...m.querySelectorAll(':scope *')].filter(e=>e.children.length===0&&e.offsetParent!==null&&!e.closest('.lk-step,select,.res,.lk-wait')&&!(e.closest('p.mut')&&e.closest('p.mut').parentElement===m)).map(e=>e.textContent).join(' ');});
     const hit=nums(txt).find(near);
     if(hit!==undefined)bad(`${tag}: 予想の前に答えの数（${hit}）が見えている（.res の付け忘れ？）`);}
   }
   if(shots&&scheme==='light'&&!v.site)await p.screenshot({path:`${shots}/${v.asset.replace('@','__')}_before.png`,fullPage:true});
   for(let i=0;i<EX.length;i++){const P=ST?ST[i].predict:pr,E=EX[i],st=ST?`（段${i+1}）`:'';
   if(i>0){await p.click('#lk-next');
    const vis2=await p.evaluate(()=>[...document.querySelectorAll('.mode')].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).some(e=>e.offsetParent!==null));
    if(vis2)bad(`${tag}${st}: 予想の前に結果が見えている`);}
   if(P.type==='number')await p.fill('#lk-in',String(E));
   else await p.click(`#lk-ch button[data-v="${E}"]`);
   await p.click('#lk-go');
   const r=await p.evaluate(()=>({last:LK.last,locked:LK.locked,vis:[...document.querySelectorAll('.mode')].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).every(e=>e.offsetParent!==null),verdict:document.getElementById('lk-verdict').innerText}));
   if(r.locked||!r.vis)bad(`${tag}${st}: 予想のあとも結果が出ない`);
   const ok=typeof E==='number'?Math.abs(r.last.v-E)<=Math.max(5e-4,Math.abs(E)*5e-4):r.last.text===E;
   if(!ok)bad(`${tag}${st}: expect ${E} とラボの値 ${r.last.text} が違う`);
   if(!/予想どおり/.test(r.verdict))bad(`${tag}${st}: 正しい予想なのに「予想どおり」にならない`);}
   if(ST){await p.click('#lk-law');if(!(await p.$('.lk-law .l')))bad(`${tag}: 最後に式（law）が出ない`);}
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
  // 解説付き再生（tour）：段・frame ごとにラボの値と静止図の数（build が計算）が一致／再生は今の段だけ／自由操作から戻る
  if(v.cfg.tour&&scheme==='light'){const TE=v.tour_expect;
   if(!TE)bad(`${tag}: tour の照合する数がない（build/tour.py の MODES）`);
   else for(let i=0;i<TE.length;i++){for(let j=0;j<TE[i].length;j++){
     const got=await p.evaluate(([i,j,keys])=>{LK.tour.go(i);if(j>0)LK.tour.frame(j-1);return Object.fromEntries(keys.map(k=>[k,LK.value(k).v]));},[i,j,Object.keys(TE[i][j])]);
     for(const [k,e] of Object.entries(TE[i][j]))if(!(Math.abs(got[k]-e)<=Math.max(1e-9,Math.abs(e)*1e-9)))bad(`${tag}: 段${i+1}・frame${j}：${k} がラボ ${got[k]}、静止図 ${e}`);}}
   const N=v.cfg.tour.steps.length,fi=v.cfg.tour.steps.findIndex(s=>(s.frames||[]).length);
   if(fi>=0){await p.evaluate(i=>LK.tour.go(i),fi);await p.click('#lk-play');
    await p.waitForFunction(()=>!LK.tour.state.playing,null,{timeout:20000});
    const st=await p.evaluate(()=>LK.tour.state);
    if(st.i!==fi||st.f!==v.cfg.tour.steps[fi].frames.length-1)bad(`${tag}: 再生が段${fi+1}の終わりで止まらない（${JSON.stringify(st)}）`);
    await p.evaluate(i=>LK.tour.frame(0),fi);const want=await p.evaluate(()=>({say:document.getElementById('lk-say').textContent,hl:document.querySelectorAll('.lk-hl').length}));
    await p.click('#lk-free');
    if(!(await p.evaluate(()=>[...document.querySelectorAll('.mode .ctl')].some(e=>e.offsetParent!==null))))bad(`${tag}: 自分で動かすで操作が出ない`);
    const btn=await p.$(`#m-${v.cfg.mode} .lk-step button:last-of-type`);if(btn)await btn.click();else bad(`${tag}: 自分で動かす操作が見つからない`);
    await p.click('#lk-back');
    const back=await p.evaluate(()=>({st:LK.tour.state,say:document.getElementById('lk-say').textContent,hl:document.querySelectorAll('.lk-hl').length}));
    if(back.st.i!==fi||back.st.f!==0||back.st.free)bad(`${tag}: 解説に戻ると段${fi+1}の frame に戻らない（${JSON.stringify(back.st)}）`);
    if(back.say!==want.say||back.hl!==want.hl)bad(`${tag}: 解説に戻ると説明・強調が戻らない`);
    const e=TE[fi][1];for(const [k,x] of Object.entries(e)){const g=await p.evaluate(k=>LK.value(k).v,k);if(Math.abs(g-x)>Math.max(1e-9,Math.abs(x)*1e-9))bad(`${tag}: 解説に戻ったあと ${k} が ${g}（段の値 ${x}）`);}}
   if(N<2)bad(`${tag}: tour が2段未満`);}
  if(errs.length)bad(`${tag}: エラー ${errs.join(' / ')}`);
  await p.close();}
  // Notion の埋め込み（高さ約320px）：予想の前は枠に収まる。結果のあとは「くわしく」で表・式が開く
  const p=await b.newPage({viewport:{width:360,height:320}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
  await p.goto('file://'+path.join(ROOT,v.file)+(v.query?v.query+'&':'?')+'embed=1');
  const tag=`埋め込み ${v.site?'公開サイト ':''}${v.asset}`;
  const h=()=>p.evaluate(()=>document.documentElement.scrollHeight);
  if(await p.evaluate(()=>document.documentElement.scrollWidth)>360)bad(`${tag}: 横にはみ出し`);
  const ST=v.cfg.steps||null,EX=ST?v.expect:[v.expect],pr=ST?ST[0].predict:v.cfg.predict;
  if(pr){
   if(await h()>320)bad(`${tag}: 予想の前に枠（320px）に収まらない（${await h()}px）`);
   const fixed=Object.keys(v.cfg.set||{}).filter(k=>!(v.cfg.unlock||[]).includes(k));
   for(const k of fixed)if(await p.$eval(`#m-${v.cfg.mode}`,(m,k)=>{const s=m.querySelector(`select[data-key="${k}"]`);return s&&s.offsetParent!==null;},k))bad(`${tag}: 問題で決めた ${k} が選べてしまう`);
   if(pr.type==='number')await p.fill('#lk-in',String(EX[0]));else await p.click(`#lk-ch button[data-v="${EX[0]}"]`);
   await p.click('#lk-go');
   embedH.push(`${v.asset}:${await h()}`);
   await p.click('#lk-more');
   if(!(await p.evaluate(()=>[...document.querySelectorAll('.mode')].filter(d=>d.style.display!=='none').flatMap(d=>[...d.querySelectorAll('.res')]).every(e=>e.offsetParent!==null))))bad(`${tag}: くわしくで結果が開かない`);
  }
  if(v.cfg.tour){   // 解説付き再生：どの段・frame でも、図・説明・前へ／再生／次へ・自分で動かすが枠に収まる（iPhone の Notion は幅が約320px）
   for(const W of [360,320]){await p.setViewportSize({width:W,height:320});
    for(let i=0;i<v.cfg.tour.steps.length;i++){const nf=(v.cfg.tour.steps[i].frames||[]).length;
     for(let j=-1;j<nf;j++){await p.evaluate(([i,j])=>{LK.tour.go(i);if(j>=0)LK.tour.frame(j);},[i,j]);
      const where=`幅${W}・段${i+1}${j>=0?`・frame${j}`:""}`;
      if(await h()>320)bad(`${tag}: ${where}が枠（320px）に収まらない（${await h()}px）`);
      if(await p.evaluate(()=>document.documentElement.scrollWidth)>W)bad(`${tag}: ${where}で横にはみ出し`);
      for(const id of ['lk-say','lk-prev','lk-play','lk-tnext','lk-free'])if(!(await p.evaluate(([id,W])=>{const e=document.getElementById(id);if(!e||e.offsetParent===null)return false;const r=e.getBoundingClientRect();return r.bottom<=320&&r.right<=W;},[id,W])))bad(`${tag}: ${where}で ${id} が枠の中に見えない`);
      if(!(await p.evaluate(()=>[...document.querySelectorAll('.seqs > div')].every(d=>d.getBoundingClientRect().height<30))))bad(`${tag}: ${where}で並びが折り返している`);}}}}
  if(errs.length)bad(`${tag}: エラー ${errs.join(' / ')}`);
  await p.close();}
 await b.close();if(process.env.EMBED_H)console.log('結果のあとの高さ',embedH.join(' '));console.log(fail?`❌ ${fail} 件`:`✅ ${man.length} 版：エラー・はみ出しなし、予想の前は結果が隠れ、答えはラボの値と一致`);process.exit(fail?1:0);})();
