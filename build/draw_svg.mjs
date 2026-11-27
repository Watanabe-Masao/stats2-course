// 静止図を、画面と同じ math-lab の描く関数で作る（#582 の D0。#188 の 01b）。同じ計算を Python に書き写さず、束（docs/math-lab/draw.mjs。写し）を使う。
// 入力（標準入力）：[{id, spec}]（spec は図の設定。型 dist で描けるものと、hist・boxplot・centers）。出力（標準出力）：[{id, svg, error}]
import { drawDist, canDrawDist, drawData, DATA_TYPES } from "../docs/math-lab/draw.mjs";

let raw = "";
for await (const chunk of process.stdin) raw += chunk;
const out = JSON.parse(raw).map(({ id, spec }) => {
  try {
    if (DATA_TYPES.includes(spec.type)) return { id, svg: drawData(spec, "file"), error: "" }; // データの図（D3a）
    if (spec.type !== "dist" || !canDrawDist(spec)) return { id, svg: "", error: "この設定はまだ math-lab で描けない" };
    return { id, svg: drawDist(spec, "file"), error: "" };
  } catch (e) {
    return { id, svg: "", error: e.message };
  }
});
process.stdout.write(JSON.stringify(out));
