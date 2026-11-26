// 生成物：packages/ui/src/draw から scripts/bundle-formula.mjs で作る。手で直さない（npm run lab:bundle）
Object.fromEntries(Object.entries({
	α: "\\alpha",
	β: "\\beta",
	γ: "\\gamma",
	δ: "\\delta",
	ε: "\\varepsilon",
	θ: "\\theta",
	λ: "\\lambda",
	μ: "\\mu",
	ν: "\\nu",
	π: "\\pi",
	ρ: "\\rho",
	σ: "\\sigma",
	τ: "\\tau",
	φ: "\\varphi",
	χ: "\\chi",
	ω: "\\omega",
	Σ: "\\Sigma",
	Φ: "\\Phi",
	Ω: "\\Omega",
	"∩": "\\cap ",
	"∪": "\\cup ",
	"−": "-"
}).filter(([k]) => /\p{L}/u.test(k)).map(([k, v]) => [v.slice(1).replace("var", ""), v]));
// packages/engine/src/lab.ts
const lnFact = (() => {
	const t = [0];
	return (k) => {
		for (let i = t.length; i <= k; i++) t[i] = t[i - 1] + Math.log(i);
		return t[k];
	};
})();
const lnComb = (n, k) => k < 0 || k > n ? -Infinity : lnFact(n) - lnFact(k) - lnFact(n - k);
const key = (v) => Number(v.toPrecision(15));
/** 値の表を n 回引いて足した値の分布（たたみこみ）：とる値（小さい順）と確率 */
function tableSum(m) {
	const tot = m.weights.reduce((a, b) => a + b, 0);
	let dist = /* @__PURE__ */ new Map([[0, 1]]);
	for (let i = 0; i < m.n; i++) {
		const next = /* @__PURE__ */ new Map();
		for (const [s, q] of dist) m.values.forEach((v, j) => {
			const w = m.weights[j] / tot;
			if (w > 0) next.set(key(s + v), (next.get(key(s + v)) ?? 0) + q * w);
		});
		dist = next;
	}
	const support = [...dist.keys()].sort((a, b) => a - b);
	return {
		support,
		probs: support.map((x) => dist.get(x))
	};
}
/** 理論のモデルの確率（supportOf の並び。0/1 の起き方は k＝0〜n。合計1） */
function modelPmf(m) {
	if (m.kind === "table") return tableSum(m).probs;
	const out = [];
	for (let k = 0; k <= m.n; k++) if (m.kind === "binom") {
		if (m.p === 0 || m.p === 1) {
			out.push(k === (m.p === 1 ? m.n : 0) ? 1 : 0);
			continue;
		}
		out.push(Math.exp(lnComb(m.n, k) + k * Math.log(m.p) + (m.n - k) * Math.log(1 - m.p)));
	} else out.push(Math.exp(lnComb(m.success, k) + lnComb(m.total - m.success, m.n - k) - lnComb(m.total, m.n)));
	return out;
}
/** モデルの期待値・分散 */
function modelMoments(m) {
	if (m.kind === "binom") return {
		mean: m.n * m.p,
		variance: m.n * m.p * (1 - m.p)
	};
	if (m.kind === "table") {
		const tot = m.weights.reduce((a, b) => a + b, 0);
		const mu = m.values.reduce((s, v, j) => s + v * m.weights[j] / tot, 0);
		const v2 = m.values.reduce((s, v, j) => s + (v - mu) ** 2 * m.weights[j] / tot, 0);
		return {
			mean: m.n * mu,
			variance: m.n * v2
		};
	}
	const q = m.success / m.total, fpc = m.total > 1 ? (m.total - m.n) / (m.total - 1) : 0;
	return {
		mean: m.n * q,
		variance: m.n * q * (1 - q) * fpc
	};
}
// packages/ui/src/draw/svg.ts
const COLORS = Object.fromEntries(Object.entries({
	"$type": "color",
	"bg": {
		"$value": "#f6f7f7",
		"$extensions": { "dark": "#0f1111" },
		"$description": "地"
	},
	"surface": {
		"$value": "#ffffff",
		"$extensions": { "dark": "#161919" },
		"$description": "カード"
	},
	"surface-2": {
		"$value": "#eef1f0",
		"$extensions": { "dark": "#1c2020" },
		"$description": "くぼみ（切り替えの台など）"
	},
	"raised": {
		"$value": "#ffffff",
		"$extensions": { "dark": "#222727" },
		"$description": "浮いた面（下から開く面・選んだ切り替え）"
	},
	"ink": {
		"$value": "#161a1a",
		"$extensions": { "dark": "#e6e9e8" },
		"$description": "文字（主）"
	},
	"ink-2": {
		"$value": "#48504f",
		"$extensions": { "dark": "#a6adab" },
		"$description": "文字（従）"
	},
	"ink-3": {
		"$value": "#68706f",
		"$extensions": { "dark": "#7e8684" },
		"$description": "文字（補足）"
	},
	"line": {
		"$value": "#e0e4e3",
		"$extensions": { "dark": "#252a2a" },
		"$description": "区切りの線"
	},
	"line-strong": {
		"$value": "#cbd1d0",
		"$extensions": { "dark": "#333a39" },
		"$description": "枠"
	},
	"accent": {
		"$value": "#0f7f73",
		"$extensions": { "dark": "#4fbfae" },
		"$description": "強い色（選んだもの・主ボタンだけ）"
	},
	"accent-ink": {
		"$value": "#ffffff",
		"$extensions": { "dark": "#06201c" },
		"$description": "強い色の上の文字"
	},
	"accent-soft": {
		"$value": "rgba(15, 127, 115, .08)",
		"$extensions": { "dark": "rgba(79, 191, 174, .12)" },
		"$description": "強い色の淡い地"
	},
	"scrim": {
		"$value": "rgba(0, 0, 0, .28)",
		"$extensions": { "dark": "rgba(0, 0, 0, .55)" },
		"$description": "シートを全体に広げたときの後ろの暗さ"
	},
	"flash": {
		"$value": "rgba(15, 127, 115, .16)",
		"$extensions": { "dark": "rgba(79, 191, 174, .20)" },
		"$description": "変わった所を一度だけ光らせる色"
	},
	"good": {
		"$value": "#2f7d3f",
		"$extensions": { "dark": "#7bc98a" },
		"$description": "予想が合った"
	},
	"bad": {
		"$value": "#c53b3b",
		"$extensions": { "dark": "#e66767" },
		"$description": "予想が外れた・成り立たない"
	},
	"accent-line": {
		"$value": "rgba(15, 127, 115, .35)",
		"$extensions": { "dark": "rgba(79, 191, 174, .40)" },
		"$description": "強い色の淡い枠（課題カード・解説の枠）"
	},
	"focus": {
		"$value": "#0f7f73",
		"$extensions": { "dark": "#4fbfae" },
		"$description": "解説で今見る所を囲む（強い色と同じ系統。注目する値の琥珀 data-hi と分ける）"
	},
	"mark": {
		"$value": "rgba(255, 196, 0, .45)",
		"$extensions": { "dark": "rgba(255, 196, 0, .35)" },
		"$description": "文の強調（蛍光ペン）"
	},
	"data-1": {
		"$value": "#2a78d6",
		"$extensions": { "dark": "#3987e5" },
		"$description": "データ：主の系列（棒・点・線）。ラボと静止図で同じ"
	},
	"data-hi": {
		"$value": "#b86e00",
		"$extensions": { "dark": "#c98500" },
		"$description": "データ：注目する値・求める確率"
	},
	"data-2": {
		"$value": "#6250d6",
		"$extensions": { "dark": "#9085e9" },
		"$description": "データ：2つ目の系列（比べる分布）"
	},
	"data-3": {
		"$value": "#c2416f",
		"$extensions": { "dark": "#d55181" },
		"$description": "データ：3つ目の系列"
	},
	"data-1-soft": {
		"$value": "#9dbfe8",
		"$extensions": { "dark": "#2b4566" },
		"$description": "データ：主の系列の注目しない棒"
	},
	"data-bg": {
		"$value": "#eaf1fb",
		"$extensions": { "dark": "#172231" },
		"$description": "データ：範囲の地（区間・面積）"
	},
	"data-hi-bg": {
		"$value": "#fbf1e3",
		"$extensions": { "dark": "#2e2412" },
		"$description": "データ：注目する範囲の地"
	},
	"figure-bg": {
		"$value": "#ffffff",
		"$extensions": { "dark": "#ffffff" },
		"$description": "図の地（静止図がダークに対応するまで白のまま）"
	},
	"band-1": {
		"$value": "#7d8f1c",
		"$extensions": { "dark": "#8a9d24" },
		"$description": "柱の色（上から1つ目。統計検定2級では「データを記述する」）。ライブラリ・島の地図。データの図の色と分ける。3色は色覚の違いでも見分けられる（全部の組で OKLab の差 ≥ 8）"
	},
	"band-2": {
		"$value": "#5556b2",
		"$extensions": { "dark": "#8384e0" },
		"$description": "柱の色（2つ目。「確率で考える」）"
	},
	"band-3": {
		"$value": "#923f1c",
		"$extensions": { "dark": "#bd5530" },
		"$description": "柱の色（3つ目。「推測する」）"
	},
	"k-pre": {
		"$value": "#6d7574",
		"$extensions": { "dark": "#7a8280" },
		"$description": "関係：前提"
	},
	"k-der": {
		"$value": "#2a78d6",
		"$extensions": { "dark": "#3987e5" },
		"$description": "関係：導出"
	},
	"k-gen": {
		"$value": "#2a78d6",
		"$extensions": { "dark": "#3987e5" },
		"$description": "関係：一般化・特殊化"
	},
	"k-conv": {
		"$value": "#b86e00",
		"$extensions": { "dark": "#c98500" },
		"$description": "関係：変換"
	},
	"k-con": {
		"$value": "#c2416f",
		"$extensions": { "dark": "#d55181" },
		"$description": "関係：対比"
	},
	"k-int": {
		"$value": "#2a78d6",
		"$extensions": { "dark": "#3987e5" },
		"$description": "関係：統合"
	},
	"k-app": {
		"$value": "#8b9392",
		"$extensions": { "dark": "#a6adab" },
		"$description": "関係：応用"
	}
}).filter(([k, v]) => !k.startsWith("$") && typeof v === "object").map(([k, v]) => [k, v.$value]));
const hexOf = (name) => {
	const v = COLORS[name];
	if (!v) throw new Error(`色 ${name} が tokens.json にない`);
	return v;
};
/** 小数1桁で書き、.0 を落とす（svgkit の f と同じ） */
const f1 = (v) => {
	const s = v.toFixed(1);
	return s.endsWith(".0") ? s.slice(0, -2) : s;
};
/** 小数3桁までで書き、末尾の0と点を落とす（figures.py の _num と同じ） */
const num = (v) => v.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const NO_HEAD = "、。，．）」』】〕・ー々…）)";
const NO_TAIL = "（「『【〔(";
const charW = (ch) => ch.codePointAt(0) < 8192 ? .55 : 1;
/** 折り返し（全角1字＝1em、半角＝0.55em で幅を見積もる。半角の英数字の並びは途中で折らない。行頭・行末の禁則） */
function wrap(text, width, size) {
	const lines = [];
	let cur = "", cw = 0;
	for (const tok of text.match(/[0-9A-Za-z.,%₀-₉]+|\n|./gsu) ?? []) {
		if (tok === "\n") {
			lines.push(cur);
			cur = "";
			cw = 0;
			continue;
		}
		const tw = [...tok].reduce((s, ch) => s + charW(ch), 0) * size;
		if (cw + tw > width && cur) {
			lines.push(cur);
			cur = "";
			cw = 0;
		}
		cur += tok;
		cw += tw;
	}
	if (cur) lines.push(cur);
	for (let i = 1; i < lines.length; i++) {
		while (lines[i] && NO_HEAD.includes(lines[i][0]) && lines[i - 1]) {
			lines[i - 1] += lines[i][0];
			lines[i] = lines[i].slice(1);
		}
		while (lines[i - 1] && NO_TAIL.includes(lines[i - 1].slice(-1))) {
			lines[i] = lines[i - 1].slice(-1) + lines[i];
			lines[i - 1] = lines[i - 1].slice(0, -1);
		}
	}
	const out = lines.filter((l) => l);
	return out.length ? out : [""];
}
/** 高さをあとで決める描き場（figures.py の Canvas と同じ：幅 360・角の丸い地） */
var Canvas = class {
	theme;
	w = 360;
	parts = [];
	constructor(theme) {
		this.theme = theme;
	}
	/** 字の大きさ：page は図が画面の幅（約 330px）に縮むので、実寸で 11px を下回らないよう 1.1 倍にする（画面の原則 6） */
	fs(size) {
		return this.theme === "page" ? Math.round(size * 1.1 * 10) / 10 : size;
	}
	/** 文字のふち（棒に重なる数を読めるようにする）：file は図の地、page は画面の面の色 */
	get halo() {
		return this.theme === "file" ? "figure-bg" : "surface";
	}
	/** 色の付け方：file は値、page は CSS の変数（値は予備） */
	paint(props) {
		if (this.theme === "file") return Object.entries(props).map(([p, n]) => ` ${p}="${hexOf(n)}"`).join("");
		return ` style="${Object.entries(props).map(([p, n]) => `${p}:var(--${n}, ${hexOf(n)})`).join(";")}"`;
	}
	add(s) {
		this.parts.push(s);
	}
	text(x, y, t, size = 12, color = "ink", anchor = "start", weight) {
		const wt = weight ? ` font-weight="${weight}"` : "";
		this.add(`<text x="${f1(x)}" y="${f1(y)}" font-size="${this.fs(size)}"${this.paint({ fill: color })} text-anchor="${anchor}"${wt}>${esc(t)}</text>`);
	}
	line(x1, y1, x2, y2, color = "ink-2", width = 1, dash) {
		const d = dash ? ` stroke-dasharray="${dash}"` : "";
		this.add(`<line x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}"${this.paint({ stroke: color })} stroke-width="${width}"${d}/>`);
	}
	rect(x, y, w, h, fill, rx = 0) {
		this.add(`<rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" rx="${rx}"${this.paint({ fill })}/>`);
	}
	para(x, y, text, width, size = 13, color = "ink", weight, lh = 1.45) {
		const ls = wrap(text, width, this.fs(size));
		const step = this.fs(size) * lh;
		ls.forEach((l, i) => this.text(x, y + i * step, l, size, color, "start", weight));
		return y + ls.length * step;
	}
	/** 仕上げ：高さを決め、地を一番下に敷く。page では幅を画面に合わせる */
	done(h, label) {
		const H = Math.trunc(h);
		const bg = this.theme === "file" ? `<rect width="${this.w}" height="${H}" rx="10"${this.paint({ fill: "figure-bg" })}/>` : "";
		const size = this.theme === "file" ? ` width="${this.w}" height="${H}"` : "";
		return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${this.w} ${H}"${size} font-family="sans-serif" role="img" aria-label="${esc(label)}">` + bg + this.parts.join("") + "</svg>";
	}
};
// packages/ui/src/draw/dist.ts
/** この関数で描ける設定か（D0：二項分布で、重ねる分布・帯・境目のないもの） */
function canDrawDist(sp) {
	return sp.family === "binom" && !sp.overlay && !sp.band && sp.upto === void 0;
}
function drawDist(sp, theme = "file") {
	if (sp.family !== "binom") throw new Error(`分布 ${String(sp.family)} はまだ描けない（D0 は二項分布だけ）`);
	const { n, p } = sp;
	const c = new Canvas(theme);
	const unit = sp.unit ?? "";
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	const top = y + 26, base = y + 190, left = 20, right = 340;
	const all = modelPmf({
		kind: "binom",
		n,
		p
	});
	const k0 = sp.kmin ?? 0, k1 = sp.kmax ?? n;
	const pmf = [];
	for (let k = k0; k <= k1; k++) pmf.push([k, all[k] ?? 0]);
	const mean = modelMoments({
		kind: "binom",
		n,
		p
	}).mean;
	const lo = pmf[0][0] - .5, hi = pmf[pmf.length - 1][0] + .5;
	const X = (v) => left + (v - lo) / (hi - lo) * 320;
	const pmax = Math.max(...pmf.map((q) => q[1]));
	const scale = (base - top - 18) / pmax;
	const slot = 320 / pmf.length;
	const bw = Math.min(40, slot * .62);
	const dec = sp.decimals ?? 2;
	const hl = new Set(sp.highlight ?? []);
	c.line(left, base, right, base, "ink-2", 1);
	const every = Math.max(1, Math.ceil(pmf.length / 12));
	for (const [x, q] of pmf) {
		const cx = X(x);
		c.rect(cx - bw / 2, base - q * scale, bw, q * scale, hl.has(x) ? "data-hi" : "data-1-soft", 3);
		if (q * scale > 1.5 && pmf.length <= 12 || hl.has(x)) c.add(`<text x="${cx.toFixed(1)}" y="${(base - q * scale - 5).toFixed(1)}" font-size="${c.fs(11.5)}"${c.paint({
			fill: "ink",
			stroke: c.halo
		})} text-anchor="middle" stroke-width="4" paint-order="stroke">${q.toFixed(dec)}</text>`);
		if ((x - pmf[0][0]) % every === 0 || hl.has(x)) c.text(cx, base + 15, `${num(x)}${unit}`, 11.5, "ink-2", "middle");
	}
	if (sp.mark_mean ?? true) {
		const mx = X(mean);
		c.add(`<path d="M${mx.toFixed(1)},${base + 20} l-7,12 h14 z"${c.paint({ fill: "data-hi" })}/>`);
		c.text(mx, base + 46, `期待値 ${num(Number(mean.toFixed(2)))}${unit}`, 12, "data-hi", "middle", "bold");
	}
	y = base + 58;
	if (sp.label) {
		c.rect(8, y + 2, 12, 12, "data-1-soft", 2);
		c.text(24, y + 12, sp.label, 12, "ink-2");
		y += 20;
		for (const line of sp.lines ?? []) {
			c.text(8, y + 12, line, 12.5, "ink");
			y += 20;
		}
		if (sp.maxdiff !== void 0) {
			const d = sp.decimals ?? 3;
			const md = sp.maxdiff < 10 ** -d ? `${(10 ** -d).toFixed(d)}未満` : sp.maxdiff.toFixed(d);
			c.text(8, y + 12, `${sp.maxdiff_label ?? "棒どうしの差の最大"} ${md}`, 12.5, "ink", "start", "bold");
			y += 20;
		}
	}
	if (sp.note) y = c.para(8, y + 10, sp.note, 344, 12.5, "ink-2");
	const most = pmf.reduce((b, q) => q[1] > b[1] + 1e-12 ? q : b, pmf[0]);
	return c.done(y + 6, `二項分布 B(${n}, ${p}) の棒。いちばん高いのは ${num(most[0])}${unit}、期待値は ${num(Number(mean.toFixed(2)))}${unit}`);
}
export { canDrawDist, drawDist, wrap };
