/* ラボ共通の部品。各ラボの <script> の先頭に build/labs.py が差し込む。
   設定 window.__LABCFG__（build が場面ごとに書き込む）:
     mode   最初に開くモード
     set    そのモードに渡す値（モードごとの apply が受け取る）
     task   課題の文
     predict {type:"number"|"choice", key, label, unit, options, tol}  予想してから結果を見せる
     why    結果のあとに出す一言
*/
const LK=(()=>{
 const cfg=window.__LABCFG__||{};
 const $=id=>document.getElementById(id);
 const modes={},order=[];let cur=null,locked=false,last=null;
 const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
 function register(key,spec){modes[key]=spec;order.push(key);}
 function show(k){cur=k;order.forEach(m=>{$("m-"+m).style.display=m===k?"block":"none";});
  document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.m===k));
  if(modes[k].render)modes[k].render();}
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
 // 課題カードと予想
 function taskCard(){const box=$("lk-task");if(!cfg.task){box.remove();return;}
  const p=cfg.predict;let h=`<div class="lk-task"><div class="lk-tt">🎯 課題</div><div>${esc(cfg.task)}</div>`;
  if(p){h+=`<div class="mut" style="margin-top:6px">先に予想を決める。決めるまで結果は隠れている。</div>`;
   if(p.type==="number")h+=`<div class="row"><label>${esc(p.label||"予想")} <input type="number" id="lk-in" inputmode="decimal" step="any">${esc(p.unit||"")}</label></div>`;
   else h+=`<div class="mut">${esc(p.label||"予想")}</div><div class="lk-choices" id="lk-ch">${p.options.map(o=>`<button type="button" data-v="${esc(o)}">${esc(o)}</button>`).join("")}</div>`;
   h+=`<div class="row"><button class="act" id="lk-go" disabled>予想を決めて確かめる</button><button class="lk-skip" id="lk-skip">予想せずに見る</button></div>`;}
  h+=`<div id="lk-verdict"></div></div>`;box.innerHTML=h;
  if(!p)return;
  let guess=null;const go=$("lk-go");
  if(p.type==="number")$("lk-in").addEventListener("input",e=>{guess=e.target.value===""?null:+e.target.value;go.disabled=guess===null||isNaN(guess);});
  else $("lk-ch").querySelectorAll("button").forEach(b=>b.onclick=()=>{guess=b.dataset.v;$("lk-ch").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));go.disabled=false;});
  go.onclick=()=>reveal(guess);$("lk-skip").onclick=()=>reveal(null);}
 function lock(on){locked=on;document.body.classList.toggle("lk-locked",on);
  document.querySelectorAll("#tabs button").forEach(b=>b.disabled=on&&b.dataset.m!==cur);}
 function reveal(guess){const p=cfg.predict;lock(false);if(modes[cur].render)modes[cur].render();
  const r=modes[cur].value(p.key);last=r;let h="";
  if(guess===null)h=`<div>ラボの結果：<b>${esc(r.text)}</b></div>`;
  else if(p.type==="number"){const tol=p.tol??Math.max(Math.abs(r.v)*0.01,0.005);const d=guess-r.v,hit=Math.abs(d)<=tol;
   h=`<div>あなたの予想：<b>${esc(fmtNum(guess))}${esc(p.unit||"")}</b>　ラボの結果：<b>${esc(r.text)}</b></div>`+
    (hit?`<div class="ok">◎ 予想どおり</div>`:`<div class="ng">✕ ずれ ${d>0?"+":""}${esc(fmtNum(d))}${esc(p.unit||"")}。外れた所が学びどころ。</div>`);}
  else{const hit=guess===r.text;h=`<div>あなたの予想：<b>${esc(guess)}</b>　ラボの結果：<b>${esc(r.text)}</b></div>`+(hit?`<div class="ok">◎ 予想どおり</div>`:`<div class="ng">✕ 予想と違った。なぜかを1文で書く。</div>`);}
  if(cfg.why)h+=`<div class="mut" style="margin-top:4px">${esc(cfg.why)}</div>`;
  h+=`<div class="mut">ここからは自由に動かしてよい。</div>`;
  $("lk-verdict").innerHTML=`<div class="lk-verdict">${h}</div>`;
  const go=$("lk-go"),sk=$("lk-skip");if(go)go.remove();if(sk)sk.remove();}
 function start(def){const tabs=$("tabs");
  order.forEach(k=>{const b=document.createElement("button");b.textContent=modes[k].name;b.dataset.m=k;b.onclick=()=>{if(!b.disabled)show(k);};tabs.appendChild(b);});
  order.forEach(k=>modes[k].init&&modes[k].init());
  const m=cfg.mode&&modes[cfg.mode]?cfg.mode:def;
  if(cfg.set&&modes[m].apply)modes[m].apply(cfg.set);
  show(m);taskCard();if(cfg.predict)lock(true);}
 return {cfg,$,esc,register,show,start,stepper,setRange,formula,fmtNum,get last(){return last;},get locked(){return locked;},value:k=>modes[cur].value(k),get mode(){return cur;}};
})();
