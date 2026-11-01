/* ラボ共通の部品。各ラボの <script> の先頭に build/labs.py が差し込む。
   設定 window.__LABCFG__（build が場面ごとに書き込む）:
     mode   最初に開くモード
     modes  タブに出すモード（省略時：mode があればそれだけ、なければ全部）
     set    そのモードに渡す値（モードごとの apply が受け取る）
     unlock 予想のある版でも選べるままにする set の選択欄（本文の手順で切り替えるとき）
     task   課題の文
     predict {type:"number"|"choice", key, label, unit, options, tol}  予想してから結果を見せる
     why    結果のあとに出す一言
     steps  法則を見つける：[{label, task, set, predict, why}, …]。条件を変えて予想→観察を何段か重ね、最後に law（決まり）を式で見せる
     law    {title, lines:[式…], text, limit}  最後に「式で説明する」で開く。limit は式の外にあること（前提が崩れる条件など）
     tour   解説付き再生（#90）：{kmax, decimals, steps:[{title, text, set, frames, focus, ms}, …]}
            段の状態＝前の段の終わり＋set、frames を順に重ねる（値は補間しない）。text の **…** を強調し、
            focus と同じ data-focus を持つ要素を囲む。前へ／再生／次へ。再生は今の段だけ動かして止まる（自動で次へ進めない）。
            「自分で動かす」で解説を止め、「解説に戻る」で値・説明・強調をその段（止めた frame）に戻す。
   予想のある版では、set で決めた選択欄（data-key の select）を文字に置き換え、問題と関係のない選択をさせない。
   Notion の埋め込み（iframe。高さ約320pxで変えられない）では「小さい表示」にする：
     見出し・説明文を省き、予想の前は課題カードだけ、結果のあとは要点と操作だけを出す。
     表・式・図は「くわしく」で開く。全部を広く使うときは「大きく開く ↗」で別の画面に出す。
   ?embed=1 で小さい表示を試せる（テスト用）。
*/
const LK=(()=>{
 const cfg=window.__LABCFG__||{};
 const STEPS=Array.isArray(cfg.steps)&&cfg.steps.length?cfg.steps:null;let si=0;const hist=[];
 if(STEPS){const s0=STEPS[0];cfg.task=s0.task;cfg.predict=s0.predict;cfg.why=s0.why;}
 const $=id=>document.getElementById(id);
 const modes={},order=[];let cur=null,locked=false,last=null,revealed=false,moved=false;
 const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 // 手触り（#42）：動きを減らす設定では動かさない。flash＝結果が出た所を一度だけ光らせる。haptic＝iPhone でスイッチの振動を借りる試み
 const RM=()=>{try{return matchMedia("(prefers-reduced-motion: reduce)").matches;}catch(e){return false;}};
 function flash(el){if(!el||RM()||!el.animate)return;const cs=getComputedStyle(document.documentElement);el.animate([{backgroundColor:cs.getPropertyValue("--flash").trim()||"transparent"},{backgroundColor:"transparent"}],{duration:parseFloat(cs.getPropertyValue("--dur-flash"))||700,easing:"ease-out"});}
 let sw=null;function haptic(){if(!/iP(hone|ad|od)/.test(navigator.userAgent))return;if(!sw){sw=document.createElement("label");sw.setAttribute("aria-hidden","true");sw.style.display="none";const i=document.createElement("input");i.type="checkbox";i.setAttribute("switch","");sw.appendChild(i);document.body.appendChild(sw);}sw.click();}
 document.addEventListener("touchstart",()=>{},{passive:true});   // iPhone の Safari で :active（押した返事）を出す
 const EMBED=(()=>{try{return window.self!==window.top;}catch(e){return true;}})()||/[?&]embed=1/.test(location.search);
 // 知識ネットワークの中（host=kn）では、↗ のリンクを別の画面に出さず、親の画面に全面で開いてもらう（閉じれば元の画面に戻れる）
 if(/[?&]host=kn\b/.test(location.search))document.addEventListener("click",e=>{const l=e.target.closest&&e.target.closest('a.lk-link[target="_blank"]');if(!l)return;
  e.preventDefault();parent.postMessage({type:"lab:open",url:l.href.replace(/([?&])host=kn(&|$)/,(m,a,b)=>b?a:"")},"*");});
 const FOCUS=!!(cfg.task&&cfg.mode);
 function register(key,spec){modes[key]=spec;order.push(key);}
 function show(k,ease){cur=k;order.forEach(m=>{const e=$("m-"+m);e.style.display=m===k?"block":"none";e.classList.toggle("lk-in",!!ease&&m===k);});
  document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.m===k));
  if(modes[k].render)modes[k].render();live();}
 function fmtNum(v){if(typeof v!=="number")return String(v);return String(+v.toFixed(3));}
 // −／＋ 付きスライダー：<input type=range id=.. data-name="A" data-unit="℃">
 function stepper(input,onchange){
  const wrap=document.createElement("div");wrap.className="lk-step ctl";
  const name=document.createElement("span");name.className="lk-name";name.textContent=input.dataset.name||"";
  const minus=document.createElement("button");minus.type="button";minus.textContent="−";minus.setAttribute("aria-label",(input.dataset.name||"")+"を下げる");
  const plus=document.createElement("button");plus.type="button";plus.textContent="＋";plus.setAttribute("aria-label",(input.dataset.name||"")+"を上げる");
  const val=document.createElement("span");val.className="lk-val";
  input.parentNode.insertBefore(wrap,input);wrap.append(name,minus,input,plus,val);
  const step=()=>+input.step||1,dec=()=>Math.max(0,(String(input.step).split(".")[1]||"").length);
  const upd=()=>{val.textContent=(+input.value).toFixed(dec())+(input.dataset.unit||"");};
  const bump=d=>{const v=Math.min(+input.max,Math.max(+input.min,+input.value+d*step()));input.value=v.toFixed(dec());upd();onchange&&onchange();};
  minus.onclick=()=>bump(-1);plus.onclick=()=>bump(1);
  input.addEventListener("input",()=>{upd();onchange&&onchange();});
  input._lkUpd=upd;upd();return wrap;}
 function setRange(id,v){const e=$(id);e.value=v;e._lkUpd&&e._lkUpd();}
 // 式で計算
 function formula(lines,title){return `<div class="lk-formula res"><div class="lk-ft">${esc(title||"式で計算")}</div>${lines.map(l=>`<div class="l">${esc(l)}</div>`).join("")}</div>`;}
 // 予想のある版：set で決めた選択欄は文字にする（問題と関係のない選択をさせない）
 function fixPicks(){if(!cfg.predict||!cfg.set)return;
  Object.keys(cfg.set).filter(k=>!(cfg.unlock||[]).includes(k)).forEach(k=>{const el=document.querySelector(`#m-${cur} select[data-key="${k}"]`);if(!el)return;
   const lab=el.closest("label"),name=lab?lab.firstChild.textContent.trim():"";
   const t=document.createElement("span");t.className="lk-fixed";t.innerHTML=`${esc(name)}：<b>${esc(el.options[el.selectedIndex].text)}</b>`;
   el.style.display="none";(lab||el).after(t);if(lab)lab.style.display="none";});}
 // 大きく開く・自由に動かす・くわしく
 const web=/^https?:$/.test(location.protocol);
 function bar(){const b=$("lk-bar");if(!b)return;let h="";
  if(EMBED&&FOCUS&&cfg.predict)h+=`<button type="button" class="lk-link" id="lk-more" aria-expanded="false">くわしく（表・式）▾</button>`;
  if(EMBED&&web)h+=`<a class="lk-link" href="${esc(location.href.replace(/[?&]embed=1\b/,""))}" target="_blank" rel="noopener">大きく開く ↗</a>`;
  if(FOCUS&&web&&window.__LABPRESETS__)h+=`<a class="lk-link" href="./" target="_blank" rel="noopener">ほかのモードも試す ↗</a>`;
  b.innerHTML=h;b.hidden=!h;const m=$("lk-more");
  if(m)m.onclick=()=>{const on=!document.body.classList.contains("lk-more");document.body.classList.toggle("lk-more",on);m.setAttribute("aria-expanded",on);m.textContent=on?"たたむ ▴":"くわしく（表・式）▾";};}
 // 課題カードと予想
 function taskCard(){const box=$("lk-task");if(!cfg.task){box.remove();return;}
  const p=cfg.predict;const head=STEPS?`🔍 法則を見つける ${si+1}／${STEPS.length}`:"🎯 課題";let h=`<div class="lk-task"><div class="lk-tt">${head}</div>${STEPS&&hist.length?histTable():""}<div class="lk-q">${esc(cfg.task)}</div>`;
  if(p){h+=`<div id="lk-ask"><div class="mut lk-note">先に予想を決める。決めるまで結果は隠れている。</div>`;
   if(p.type==="number")h+=`<div class="row"><label>${esc(p.label||"予想")} <input type="number" id="lk-in" inputmode="decimal" step="any">${esc(p.unit||"")}</label></div>`;
   else h+=`<div class="mut">${esc(p.label||"予想")}</div><div class="lk-choices" id="lk-ch">${p.options.map(o=>`<button type="button" data-v="${esc(o)}">${esc(o)}</button>`).join("")}</div>`;
   h+=`<div class="row"><button class="act" id="lk-go" disabled>予想を決めて確かめる</button><button class="lk-skip" id="lk-skip">予想せずに見る</button></div></div>`;}
  h+=`<div id="lk-verdict"></div></div>`;box.innerHTML=h;
  if(!p)return;
  let guess=null;const go=$("lk-go");
  if(p.type==="number")$("lk-in").addEventListener("input",e=>{guess=e.target.value===""?null:+e.target.value;go.disabled=guess===null||isNaN(guess);});
  else $("lk-ch").querySelectorAll("button").forEach(b=>b.onclick=()=>{guess=b.dataset.v;$("lk-ch").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));go.disabled=false;});
  go.onclick=()=>reveal(guess);$("lk-skip").onclick=()=>reveal(null);}
 function lock(on){locked=on;document.body.classList.toggle("lk-locked",on);
  document.querySelectorAll("#tabs button").forEach(b=>b.disabled=on&&b.dataset.m!==cur);}
 // 結果のあと：動かすと予想の値がその場で変わる
 function live(){const el=$("lk-live");if(!el||!revealed||!moved)return;el.hidden=false;const p=cfg.predict,r=modes[cur].value(p.key);
  el.innerHTML=`動かすと変わる → ${esc(p.label||"結果")}：<b>${esc(r.text)}</b>`;}
 function reveal(guess){const p=cfg.predict;lock(false);revealed=true;if(modes[cur].render)modes[cur].render();
  const r=modes[cur].value(p.key);last=r;let h="";
  if(STEPS)hist.push({label:STEPS[si].label||`${si+1}`,guess:guess===null?"—":(p.type==="number"?fmtNum(guess)+(p.unit||""):String(guess)),result:r.text+(p.type==="number"?(p.unit||""):"")});
  const both=`予想 <b>${esc(p.type==="number"?fmtNum(guess)+(p.unit||""):guess)}</b> ／ ラボ <b>${esc(r.text)}</b>`;
  if(guess===null)h=`<div>ラボの結果：<b>${esc(r.text)}</b></div>`;
  else if(p.type==="number"){const tol=p.tol??Math.max(Math.abs(r.v)*0.01,0.005);const d=guess-r.v,hit=Math.abs(d)<=tol;
   h=hit?`<div><span class="ok">◎ 予想どおり</span>　${both}</div>`:
    `<div><span class="ng">✕ ずれ ${d>0?"+":""}${esc(fmtNum(d))}${esc(p.unit||"")}</span>　${both}</div><div class="mut">外れた所が学びどころ。</div>`;}
  else{const hit=guess===r.text;h=hit?`<div><span class="ok">◎ 予想どおり</span>　${both}</div>`:
    `<div><span class="ng">✕ 予想と違った</span>　${both}</div><div class="mut">なぜかを1文で書く。</div>`;}
  if(cfg.why)h+=`<div class="lk-why">${esc(cfg.why)}</div>`;
  h+=`<div class="lk-live" id="lk-live" hidden></div>`;
  if(STEPS){if(si<STEPS.length-1)h+=`<div class="row"><button type="button" class="act" id="lk-next">次の条件で予想する ▶</button></div>`;
   else if(cfg.law)h+=`<div class="lk-lawask"><div class="mut">ここまでの結果から、決まりを1文で書いてみる。書けたら式で確かめる。</div><div class="row"><button type="button" class="act" id="lk-law">式で説明する ▼</button></div></div><div id="lk-lawbox"></div>`;}
  $("lk-verdict").innerHTML=`<div class="lk-verdict">${h}</div>`;flash($("lk-verdict").firstElementChild);haptic();
  const nx=$("lk-next");if(nx)nx.onclick=nextStep;const lw=$("lk-law");if(lw)lw.onclick=showLaw;
  const ask=$("lk-ask");if(ask)ask.remove();document.querySelector(".lk-task").classList.add("lk-done");
  live();bar();if(EMBED)window.scrollTo(0,0);}
 // 探究：次の条件へ
 function histTable(){const p=cfg.predict||{};return `<table class="lk-hist"><tr><th>条件</th><th>予想</th><th>結果</th></tr>${hist.map(r=>`<tr><td>${esc(r.label)}</td><td>${esc(r.guess)}</td><td><b>${esc(r.result)}</b></td></tr>`).join("")}</table>`;}
 function nextStep(){si++;const s=STEPS[si];cfg.task=s.task;cfg.predict=s.predict;cfg.why=s.why;revealed=false;moved=false;
  if(s.set&&modes[cur].apply)modes[cur].apply(s.set);if(modes[cur].render)modes[cur].render();
  taskCard();lock(true);bar();$("lk-bar").hidden=true;if(EMBED)window.scrollTo(0,0);}
 function showLaw(){const L=cfg.law,box=$("lk-lawbox");if(!L||!box)return;
  box.innerHTML=`<div class="lk-law">${histTable()}<div class="lk-tt">📐 ${esc(L.title||"式で説明する")}</div>${(L.lines||[]).map(l=>`<div class="l">${esc(l)}</div>`).join("")}${L.text?`<div class="lk-why">${esc(L.text)}</div>`:""}${L.limit?`<div class="lk-limit"><b>この式で言えないこと</b>　${esc(L.limit)}</div>`:""}</div>`;
  const b=$("lk-law");if(b)b.closest(".lk-lawask").remove();const top=document.querySelector(".lk-task > .lk-hist");if(top)top.remove();}
 // 解説付き再生
 const TOUR=cfg.tour&&Array.isArray(cfg.tour.steps)&&cfg.tour.steps.length?cfg.tour:null;
 const T={i:0,f:-1,timer:null,free:false,states:[]};
 function tourStates(){let c={};return TOUR.steps.map(s=>{if(s.mode&&s.mode!==c.mode)c={mode:s.mode};const start={...c,...(s.set||{})};let st=start;const fr=(s.frames||[]).map(x=>(st={...st,...x}));c=fr.length?fr[fr.length-1]:start;return {start,frames:fr,end:c};});}
 const say=t=>esc(t).replace(/\*\*(.+?)\*\*/g,"<mark>$1</mark>");
 function tState(){const S=T.states[T.i];return T.f<0?S.start:S.frames[T.f];}
 function tPlace(){const m=$("m-"+cur),box=$("lk-tour");if(!m||!box)return;const a=m.querySelector("[data-tour-anchor]")||m.querySelector(".res.key")||m.lastElementChild;if(box.previousElementSibling!==a)a.after(box);}
 function tApply(){document.body.classList.toggle("lk-gist",!!TOUR.steps[T.i].gist&&!T.free);const st=tState();
  if(st.mode&&st.mode!==cur&&modes[st.mode]){show(st.mode);tPlace();}   // 段がモードを変える（例：二項→幾何を並べて比べる）
  modes[cur].apply&&modes[cur].apply(st);if(modes[cur].render)modes[cur].render();tFocus();}
 function tFocus(){const fo=T.free?null:TOUR.steps[T.i].focus;
  document.querySelectorAll(".lk-hl").forEach(e=>e.classList.remove("lk-hl"));   // ほかのモードに残った強調も消す
  document.querySelectorAll(`#m-${cur} [data-focus]`).forEach(e=>e.classList.toggle("lk-hl",!!fo&&e.dataset.focus.split(" ").includes(fo)));}
 function tStop(){if(T.timer){clearTimeout(T.timer);T.timer=null;}}
 function tGo(i){tStop();T.i=Math.max(0,Math.min(TOUR.steps.length-1,i));T.f=-1;T.free=false;tApply();tDraw();}
 function tFrame(j){T.f=j;tApply();tDraw();}
 function tPlay(){const S=T.states[T.i],n=S.frames.length;if(!n)return;
  if(T.timer){tStop();tDraw();return;}               // 一時停止
  if(T.f>=n-1)T.f=-1,tApply();                        // 終わっていたら、段の始めからもう一度
  const ms=TOUR.steps[T.i].ms||900;
  const tick=()=>{T.f++;tApply();if(T.f>=n-1){T.timer=null;tDraw();return;}tDraw();T.timer=setTimeout(tick,ms);};
  T.timer=setTimeout(tick,T.f<0?300:ms);tDraw();}
 function tFree(){tStop();T.free=true;document.body.classList.add("lk-free");document.body.classList.remove("lk-gist");tFocus();tDraw();}
 function tBack(){T.free=false;document.body.classList.remove("lk-free");tApply();tDraw();}
 function tDraw(){const box=$("lk-tour");if(!box)return;const N=TOUR.steps.length,s=TOUR.steps[T.i],S=T.states[T.i],n=S.frames.length;
  if(T.free){box.innerHTML=`<div class="lk-tfree"><span>✋ 自分で動かしている（解説 ${T.i+1}／${N} で止めた）</span><button type="button" class="act" id="lk-back">↩ 解説に戻る</button></div>`;
   $("lk-back").onclick=tBack;return;}
  const playing=!!T.timer,done=n&&T.f>=n-1;
  const big=EMBED&&web?`<a class="lk-link" href="${esc(location.href.replace(/[?&]embed=1\b/,""))}" target="_blank" rel="noopener">大きく開く ↗</a>`:"";
  box.innerHTML=`<div class="lk-tt">📖 解説 ${T.i+1}／${N}　${esc(s.title||"")}</div>
   <div class="lk-say" id="lk-say"><span class="lk-tno">${T.i+1}／${N}　</span>${say(s.text)}</div>
   <div class="lk-tctl"><button type="button" class="sub" id="lk-prev" ${T.i?"":"disabled"}>◀ 前へ</button><button type="button" class="act" id="lk-play" ${n?"":"disabled"} aria-label="${playing?"一時停止":"再生"}">${!n?"動きなし":playing?"⏸ 一時停止":done?"↺ もう一度":"▶ 再生"}</button><button type="button" class="sub" id="lk-tnext" ${T.i<N-1?"":"disabled"}>次へ ▶</button></div>
   <div class="lk-tsub"><button type="button" class="lk-link" id="lk-free">✋ <span class="lk-long">自分で</span>動かす</button><button type="button" class="lk-link" id="lk-all" aria-expanded="false">全文 ▾</button>${big}</div>
   <ol class="lk-tlist" id="lk-tlist" hidden>${TOUR.steps.map((x,k)=>`<li class="${k===T.i?"on":""}"><button type="button" data-i="${k}">${say(x.text)}</button></li>`).join("")}</ol>`;
  $("lk-prev").onclick=()=>tGo(T.i-1);$("lk-tnext").onclick=()=>tGo(T.i+1);$("lk-play").onclick=tPlay;$("lk-free").onclick=tFree;
  const all=$("lk-all");all.onclick=()=>{const l=$("lk-tlist"),on=l.hidden;l.hidden=!on;all.setAttribute("aria-expanded",on);all.textContent=on?"全文 ▴":"全文 ▾";};
  box.querySelectorAll("#lk-tlist button").forEach(b=>b.onclick=()=>tGo(+b.dataset.i));}
 function tourStart(){T.states=tourStates();document.body.classList.add("lk-touring");const t=$("lk-task");if(t)t.remove();
  const box=document.createElement("div");box.id="lk-tour";box.className="lk-tour";document.body.appendChild(box);tPlace();
  // 自由に動かした値は、解説の外の操作として扱う（解説に戻ると段の値を渡し直す）
  document.querySelectorAll(".mode").forEach(m=>m.addEventListener("input",()=>{if(!T.free)tFree();}));
  tGo(0);$("lk-bar").hidden=true;}

 function start(def){const tabs=$("tabs");
  const m=cfg.mode&&modes[cfg.mode]?cfg.mode:def;
  const shown=(cfg.modes||(cfg.mode?[cfg.mode]:order)).filter(k=>modes[k]);
  shown.forEach(k=>{const b=document.createElement("button");b.type="button";b.textContent=modes[k].name;b.dataset.m=k;b.onclick=()=>{if(!b.disabled)show(k,k!==cur);};tabs.appendChild(b);});
  if(shown.length<2)tabs.hidden=true;
  document.body.classList.toggle("lk-embed",EMBED);document.body.classList.toggle("lk-focus",FOCUS);document.body.classList.toggle("lk-pred",!!(FOCUS&&cfg.predict));
  if(!$("lk-bar")){const b=document.createElement("div");b.id="lk-bar";b.className="lk-bar";document.body.appendChild(b);}
  order.forEach(k=>modes[k].init&&modes[k].init());
  if(cfg.set&&modes[m].apply)modes[m].apply(cfg.set);
  if(STEPS&&STEPS[0].set&&modes[m].apply)modes[m].apply(STEPS[0].set);
  show(m);if(TOUR){tourStart();return;}fixPicks();taskCard();if(cfg.predict)lock(true);
  if(!cfg.predict){const t=$("lk-task");if(t&&EMBED)t.after($("lk-bar"));bar();}else $("lk-bar").hidden=true;
  ["input","change","click"].forEach(ev=>document.addEventListener(ev,e=>{if(e.target.closest&&e.target.closest(".mode"))moved=true;setTimeout(live,0);}));}
 // 乱数（issue 144 の P6）：ラボの中に乱数を書かない。math-lab の種つき乱数（同じ種なら同じ結果）。r() は 0〜1、r.normal()・r.shuffle(a)・r.sample(a,k)・r.int(lo,hi)
 const rng=seed=>{const R=MLRandom.createRandom(seed);const f=()=>R.next();f.seed=R.seed;f.int=(lo,hi)=>R.int(lo,hi);f.normal=()=>MLRandom.normal(R);f.shuffle=a=>MLRandom.shuffle(R,a);f.sample=(a,k)=>MLRandom.sampleWithout(R,a,k);return f;};
 return {cfg,$,esc,rng,get step(){return si;},register,show,start,stepper,setRange,formula,fmtNum,embed:EMBED,focus:FOCUS,get last(){return last;},get locked(){return locked;},value:k=>modes[cur].value(k),get mode(){return cur;},
  tour:TOUR?{go:tGo,frame:tFrame,play:tPlay,free:tFree,back:tBack,get state(){return {i:T.i,f:T.f,free:T.free,playing:!!T.timer};}}:null};
})();
