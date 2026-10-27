/* ラボ共通の部品。各ラボの <script> の先頭に build/labs.py が差し込む。
   設定 window.__LABCFG__（build が場面ごとに書き込む）:
     mode   最初に開くモード
     modes  タブに出すモード（省略時：mode があればそれだけ、なければ全部）
     set    そのモードに渡す値（モードごとの apply が受け取る）
     unlock 予想のある版でも選べるままにする set の選択欄（本文の手順で切り替えるとき）
     task   課題の文
     predict {type:"number"|"choice", key, label, unit, options, tol}  予想してから結果を見せる
     why    結果のあとに出す一言
   予想のある版では、set で決めた選択欄（data-key の select）を文字に置き換え、問題と関係のない選択をさせない。
   Notion の埋め込み（iframe。高さ約320pxで変えられない）では「小さい表示」にする：
     見出し・説明文を省き、予想の前は課題カードだけ、結果のあとは要点と操作だけを出す。
     表・式・図は「くわしく」で開く。全部を広く使うときは「大きく開く ↗」で別の画面に出す。
   ?embed=1 で小さい表示を試せる（テスト用）。
*/
const LK=(()=>{
 const cfg=window.__LABCFG__||{};
 const $=id=>document.getElementById(id);
 const modes={},order=[];let cur=null,locked=false,last=null,revealed=false,moved=false;
 const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 const EMBED=(()=>{try{return window.self!==window.top;}catch(e){return true;}})()||/[?&]embed=1/.test(location.search);
 const FOCUS=!!(cfg.task&&cfg.mode);
 function register(key,spec){modes[key]=spec;order.push(key);}
 function show(k){cur=k;order.forEach(m=>{$("m-"+m).style.display=m===k?"block":"none";});
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
  const p=cfg.predict;let h=`<div class="lk-task"><div class="lk-tt">🎯 課題</div><div class="lk-q">${esc(cfg.task)}</div>`;
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
  const both=`予想 <b>${esc(p.type==="number"?fmtNum(guess)+(p.unit||""):guess)}</b> ／ ラボ <b>${esc(r.text)}</b>`;
  if(guess===null)h=`<div>ラボの結果：<b>${esc(r.text)}</b></div>`;
  else if(p.type==="number"){const tol=p.tol??Math.max(Math.abs(r.v)*0.01,0.005);const d=guess-r.v,hit=Math.abs(d)<=tol;
   h=hit?`<div><span class="ok">◎ 予想どおり</span>　${both}</div>`:
    `<div><span class="ng">✕ ずれ ${d>0?"+":""}${esc(fmtNum(d))}${esc(p.unit||"")}</span>　${both}</div><div class="mut">外れた所が学びどころ。</div>`;}
  else{const hit=guess===r.text;h=hit?`<div><span class="ok">◎ 予想どおり</span>　${both}</div>`:
    `<div><span class="ng">✕ 予想と違った</span>　${both}</div><div class="mut">なぜかを1文で書く。</div>`;}
  if(cfg.why)h+=`<div class="lk-why">${esc(cfg.why)}</div>`;
  h+=`<div class="lk-live" id="lk-live" hidden></div>`;
  $("lk-verdict").innerHTML=`<div class="lk-verdict">${h}</div>`;
  const ask=$("lk-ask");if(ask)ask.remove();document.querySelector(".lk-task").classList.add("lk-done");
  live();bar();if(EMBED)window.scrollTo(0,0);}
 function start(def){const tabs=$("tabs");
  const m=cfg.mode&&modes[cfg.mode]?cfg.mode:def;
  const shown=(cfg.modes||(cfg.mode?[cfg.mode]:order)).filter(k=>modes[k]);
  shown.forEach(k=>{const b=document.createElement("button");b.type="button";b.textContent=modes[k].name;b.dataset.m=k;b.onclick=()=>{if(!b.disabled)show(k);};tabs.appendChild(b);});
  if(shown.length<2)tabs.hidden=true;
  document.body.classList.toggle("lk-embed",EMBED);document.body.classList.toggle("lk-focus",FOCUS);document.body.classList.toggle("lk-pred",!!(FOCUS&&cfg.predict));
  if(!$("lk-bar")){const b=document.createElement("div");b.id="lk-bar";b.className="lk-bar";document.body.appendChild(b);}
  order.forEach(k=>modes[k].init&&modes[k].init());
  if(cfg.set&&modes[m].apply)modes[m].apply(cfg.set);
  show(m);fixPicks();taskCard();if(cfg.predict)lock(true);
  if(!cfg.predict){const t=$("lk-task");if(t&&EMBED)t.after($("lk-bar"));bar();}else $("lk-bar").hidden=true;
  ["input","change","click"].forEach(ev=>document.addEventListener(ev,e=>{if(e.target.closest&&e.target.closest(".mode"))moved=true;setTimeout(live,0);}));}
 return {cfg,$,esc,register,show,start,stepper,setRange,formula,fmtNum,embed:EMBED,focus:FOCUS,get last(){return last;},get locked(){return locked;},value:k=>modes[cur].value(k),get mode(){return cur;}};
})();
