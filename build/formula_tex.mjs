// 木から TeX を作り、木を検査する（#118 単位 A・#72）。式の元は木だけ。同じ計算を Python に書き写さず、math-lab の束（docs/math-lab/formula.mjs。写し）を使う。
// 入力（標準入力）：[{id, tree, symbols, checks?: [木]}]。出力（標準出力）：[{id, tex, errors}]。checks（契約の組の条件）も同じ記号で検査する
import { toTex, validateFormula } from "../docs/math-lab/formula.mjs";

let raw = "";
for await (const chunk of process.stdin) raw += chunk;
const out = JSON.parse(raw).map(({ id, tree, symbols = [], checks = [] }) => {
  const syms = symbols.filter((s) => s.key);
  const errors = [...validateFormula({ tree, symbols: syms })];
  for (const c of checks) errors.push(...validateFormula({ tree: c, symbols: syms }).map((e) => `組の条件：${e}`));
  let tex = "";
  try { tex = toTex(tree, { symbols: syms }); } catch (e) { errors.push(`TeX を作れない：${e.message}`); }
  return { id, tex, errors };
});
process.stdout.write(JSON.stringify(out));
