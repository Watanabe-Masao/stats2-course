// ラボの版を SHARD=k/n の組に分ける（#129）。GitHub の6台の時間をそろえ、いちばん遅い組で決まる待ち時間を縮める。
//  - 時間の記録 tools/lab_times.json（版の名前 → 1版の秒）を使い、長い版から順に、その時点で合計のいちばん短い組へ入れる（LPT）
//  - 記録のない版（新しい版）は、記録の中央値で見積もる（記録が空なら全部同じ重さ＝数でそろえる）
//  - 同じ入力なら同じ組になる（並べ替えは秒→名前→並び順。同じ合計の組は番号の小さい方）
//  - どの版もちょうど1つの組に入ることを毎回確かめる（漏れ・重なりがあれば止める）
// 版の名前は、アップロード用は asset（LAB-x@場面）、公開サイトは site:asset。
// 記録の作り直し：python3 build/lab_times.py <実行の ID>…（GitHub のラボのジョブのログの「⏱」行から平均を書く）
const fs=require('fs');const path=require('path');
const TIMES=path.join(__dirname,'lab_times.json');
const key=v=>(v.site?'site:':'')+v.asset;
function loadTimes(file=TIMES){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch(e){return {};}}
// items：版の名前の配列。返り値：組ごとの、items の添え字の配列（各組の中は元の並び順）
function assign(items,n,times){
  const known=items.map(k=>times[k]).filter(x=>typeof x==='number'&&x>0).sort((a,b)=>a-b);
  const est=known.length?known[Math.floor((known.length-1)/2)]:1;
  const w=items.map(k=>typeof times[k]==='number'&&times[k]>0?times[k]:est);
  const order=items.map((_,i)=>i).sort((a,b)=>w[b]-w[a]||(items[a]<items[b]?-1:items[a]>items[b]?1:0)||a-b);
  const load=Array(n).fill(0),groups=Array.from({length:n},()=>[]);
  for(const i of order){let g=0;for(let j=1;j<n;j++)if(load[j]<load[g])g=j;groups[g].push(i);load[g]+=w[i];}
  for(const g of groups)g.sort((a,b)=>a-b);
  const seen=groups.flat().sort((a,b)=>a-b);   // 自己点検：全部の版がちょうど1回
  if(seen.length!==items.length||seen.some((x,i)=>x!==i))throw new Error('組分けで版が漏れたか重なった');
  return {groups,load:load.map(x=>Math.round(x)),est};
}
module.exports={key,loadTimes,assign};
// node tools/lab_shard.js：今の記録で6組に分けた見積もりを出す（out/ の manifest が要る。python3 build/build.py のあと）
if(require.main===module){
  const read=f=>fs.existsSync(path.join(__dirname,'..',f))?JSON.parse(fs.readFileSync(path.join(__dirname,'..',f),'utf8')):[];
  const man=[...read('out/labs/manifest.json'),...read('out/site_manifest.json').map(v=>({...v,site:true}))];
  const n=Number(process.argv[2]||6),times=loadTimes();const items=man.map(key);
  const {groups,load,est}=assign(items,n,times);const rr=Array(n).fill(0);
  items.forEach((k,i)=>{rr[i%n]+=typeof times[k]==='number'&&times[k]>0?times[k]:est;});
  console.log(`版 ${items.length}・記録なし ${items.filter(k=>!(times[k]>0)).length}（${est}秒で見積もり）`);
  console.log('時間で分けた組の秒：'+load.join(' / ')+`（最大−最小 ${Math.max(...load)-Math.min(...load)}）`);
  console.log('並び順で分けた組の秒：'+rr.map(Math.round).join(' / ')+`（最大−最小 ${Math.round(Math.max(...rr)-Math.min(...rr))}）`);
}
