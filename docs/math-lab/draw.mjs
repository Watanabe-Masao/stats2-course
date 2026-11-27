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
const isCount = (x) => Number.isInteger(x) && x >= 0;
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
/** ポアソン分布 Po(λ) の確率（k＝0〜kmax）。つながりの図で二項分布と並べる（stats2-course #188 04）。
*  上限のない分布なので kmax で切る（合計は1より少し小さい）。λ は0以上 */
function poissonPmf(lambda, kmax) {
	if (!(lambda >= 0) || !Number.isFinite(lambda)) throw new Error(`λ は0以上の有限の数：${lambda}`);
	if (!isCount(kmax)) throw new Error(`kmax は0以上の整数：${kmax}`);
	if (lambda === 0) return Array.from({ length: kmax + 1 }, (_, k) => k === 0 ? 1 : 0);
	return Array.from({ length: kmax + 1 }, (_, k) => Math.exp(-lambda + k * Math.log(lambda) - lnFact(k)));
}
/** r 回目の成功が k 回目の試行で起きる確率（k＝0〜kmax。k＜r は0）。r＝1 で幾何分布、2以上で負の二項分布。
*  P(k)＝C(k−1, r−1) p^r (1−p)^(k−r)。平均 r/p・分散 r(1−p)/p²（stats2-course #188 04b） */
function negbinomPmf(r, p, kmax) {
	if (!isCount(r) || r < 1) throw new Error(`r は1以上の整数：${r}`);
	if (!(p > 0 && p <= 1)) throw new Error(`p は0より大きく1以下：${p}`);
	if (!isCount(kmax)) throw new Error(`kmax は0以上の整数：${kmax}`);
	return Array.from({ length: kmax + 1 }, (_, k) => {
		if (k < r) return 0;
		if (p === 1) return k === r ? 1 : 0;
		return Math.exp(lnComb(k - 1, r - 1) + r * Math.log(p) + (k - r) * Math.log(1 - p));
	});
}
/** 正規分布 N(μ, σ²) の密度。二項分布の棒に重ねる曲線に使う（棒の幅1なので、密度の値が棒の高さに並ぶ）。σ は0より大きい */
function normalDensity(x, mean, sd) {
	if (!(sd > 0)) throw new Error(`σ は0より大きい：${sd}`);
	const z = (x - mean) / sd;
	return Math.exp(-z * z / 2) / (sd * Math.sqrt(2 * Math.PI));
}
// packages/engine/src/dists.ts
/** ln Γ(x)（x＞0。Lanczos の近似） */
function lnGamma(x) {
	const c = [
		76.18009172947146,
		-86.50532032941678,
		24.01409824083091,
		-1.231739572450155,
		.001208650973866179,
		-5395239384953e-18
	];
	let y = x, t = x + 5.5;
	t -= (x + .5) * Math.log(t);
	let s = 1.000000000190015;
	for (const ci of c) s += ci / ++y;
	return -t + Math.log(2.5066282746310007 * s / x);
}
/** t 分布 t(df) の密度・分布関数・左側累積 p の点 */
const tDensity = (t, df) => Math.exp(lnGamma((df + 1) / 2) - lnGamma(df / 2) - .5 * Math.log(df * Math.PI) - (df + 1) / 2 * Math.log(1 + t * t / df));
/** カイ二乗分布 χ²(df) */
const chi2Density = (x, df) => x <= 0 ? 0 : Math.exp((df / 2 - 1) * Math.log(x) - x / 2 - df / 2 * Math.log(2) - lnGamma(df / 2));
/** F 分布 F(d1, d2) */
const fDensity = (x, d1, d2) => x <= 0 ? 0 : Math.exp(.5 * (d1 * Math.log(d1 * x) + d2 * Math.log(d2) - (d1 + d2) * Math.log(d1 * x + d2)) - Math.log(x) - (lnGamma(d1 / 2) + lnGamma(d2 / 2) - lnGamma((d1 + d2) / 2)));
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
		"$extensions": { "dark": "#161919" },
		"$description": "図の地（静止図は端末がダークのとき暗い色に替わるので、地も面の色に合わせる。stats2-course #582）"
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
	rect(x, y, w, h, fill, rx = 0, opacity) {
		const op = opacity !== void 0 ? ` fill-opacity="${opacity}"` : "";
		this.add(`<rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" rx="${rx}"${this.paint({ fill })}${op}/>`);
	}
	/** 丸：fill を null にすると塗らない（枠だけ） */
	circle(cx, cy, r, fill, stroke, width = 1.5) {
		const props = {};
		if (fill) props.fill = fill;
		if (stroke) props.stroke = stroke;
		const nofill = fill ? "" : " fill=\"none\"";
		const sw = stroke ? ` stroke-width="${width}"` : "";
		this.add(`<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}"${nofill}${this.paint(props)}${sw}/>`);
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
// packages/ui/src/draw/curve.ts
const CURVE_FAMILIES = [
	"normal",
	"uniform",
	"expo",
	"t",
	"chi2",
	"f"
];
/** 密度の関数と平均（平均がない分布は NaN） */
function densityOf(sp) {
	switch (sp.family) {
		case "normal": return {
			f: (x) => normalDensity(x, sp.mu, sp.sigma),
			mean: sp.mu,
			name: `正規分布 N(${num(sp.mu)}, ${num(sp.sigma)}²)`,
			short: `N(${num(sp.mu)}, ${num(sp.sigma)}²)`
		};
		case "uniform": return {
			f: (x) => x >= sp.a && x <= sp.b ? 1 / (sp.b - sp.a) : 0,
			mean: (sp.a + sp.b) / 2,
			name: `一様分布（${num(sp.a)}〜${num(sp.b)}）`,
			short: `一様 ${num(sp.a)}〜${num(sp.b)}`
		};
		case "expo": return {
			f: (x) => x >= 0 ? sp.lam * Math.exp(-sp.lam * x) : 0,
			mean: 1 / sp.lam,
			name: `指数分布（λ＝${num(sp.lam)}）`,
			short: `指数 λ＝${num(sp.lam)}`
		};
		case "t": return {
			f: (x) => tDensity(x, sp.df),
			mean: sp.df > 1 ? 0 : NaN,
			name: `t 分布 t(${sp.df})`,
			short: `t(${sp.df})`
		};
		case "chi2": {
			const g = (x) => chi2Density(x === 0 ? 1e-12 : x, sp.df);
			const cap = sp.df < 2 ? 2.5 * g(.5) : Infinity;
			return {
				f: (x) => Math.min(g(x), cap),
				mean: sp.df,
				name: `カイ二乗分布 χ²(${sp.df})`,
				short: `χ²(${sp.df})`
			};
		}
		case "f": {
			const g = (x) => fDensity(x === 0 ? 1e-12 : x, sp.d1, sp.d2);
			const cap = sp.d1 <= 2 ? 2.5 * g(.5) : Infinity;
			return {
				f: (x) => Math.min(g(x), cap),
				mean: sp.d2 > 2 ? sp.d2 / (sp.d2 - 2) : NaN,
				name: `F 分布 F(${sp.d1}, ${sp.d2})`,
				short: `F(${sp.d1}, ${sp.d2})`
			};
		}
	}
}
function drawCurve(sp, theme = "file") {
	const c = new Canvas(theme);
	const unit = sp.unit ?? "";
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	const top = y + 26, base = y + 190, left = 20, right = 340;
	const { f, mean, name, short } = densityOf(sp);
	const [lo, hi, step] = sp.ticks;
	const X = (v) => left + (v - lo) / (hi - lo) * 320;
	const xs = Array.from({ length: 241 }, (_, i) => lo + (hi - lo) * i / 240);
	const g = sp.overlay ? (x) => normalDensity(x, sp.overlay.mu, sp.overlay.sigma) : null;
	const pmax = Math.max(...xs.map(f).filter(Number.isFinite), ...g ? xs.map(g) : []);
	const scale = (base - top - 18) / pmax;
	const Y = (v) => base - (Number.isFinite(v) ? v : pmax) * scale;
	c.line(left, base, right, base, "ink-2", 1);
	for (const sh of sp.shade ?? []) {
		const outside = "outside" in sh;
		const parts = outside ? [[lo, sh.outside[0]], [sh.outside[1], hi]] : [[sh.from, sh.to]];
		for (const [a0, b0] of parts) {
			const a = Math.max(a0, lo), b = Math.min(b0, hi);
			if (b <= a) continue;
			const pts = Array.from({ length: 81 }, (_, i) => a + (b - a) * i / 80);
			const d = `M${f1(X(a))},${base} ` + pts.map((x) => `L${f1(X(x))},${f1(Y(f(x)))}`).join(" ") + ` L${f1(X(b))},${base} Z`;
			c.add(`<path d="${d}"${c.paint({ fill: outside ? "data-hi" : "data-1" })} fill-opacity="${outside ? .55 : .35}"/>`);
		}
		if (sh.label) {
			if (outside) c.text(right, base - 62, sh.label, 11.5, "data-hi", "end", "bold");
			else {
				const mid = (sh.from + sh.to) / 2;
				c.add(`<text x="${f1(X(mid))}" y="${f1(base - f(mid) * scale * .45)}" font-size="${c.fs(12.5)}"${c.paint({
					fill: "ink",
					stroke: c.halo
				})} text-anchor="middle" font-weight="bold" stroke-width="4" paint-order="stroke">${esc(sh.label)}</text>`);
			}
		}
	}
	c.add(`<path d="M${xs.map((x) => `${f1(X(x))},${f1(Y(f(x)))}`).join(" L")}" fill="none"${c.paint({ stroke: "data-1" })} stroke-width="2.2"/>`);
	(sp.marks ?? []).forEach((mk, i) => {
		c.line(X(mk.x), top - 4 + i * 16, X(mk.x), base, "ink-2", 1.2, "4 3");
		c.text(X(mk.x) + 4, top + 6 + i * 16, mk.label, 11.5, "ink-2");
	});
	if (g) c.add(`<path d="M${xs.map((x) => `${f1(X(x))},${f1(Y(g(x)))}`).join(" L")}" fill="none"${c.paint({ stroke: "ink" })} stroke-width="1.6" stroke-dasharray="4 3"/>`);
	for (let t = lo; t <= hi + 1e-9; t += step) c.text(X(t), base + 15, num(t), 11, "ink-2", "middle");
	if ((sp.mark_mean ?? true) && Number.isFinite(mean)) {
		const mx = X(mean);
		c.add(`<path d="M${f1(mx)},${base + 20} l-7,12 h14 z"${c.paint({ fill: "data-hi" })}/>`);
		c.text(mx, base + 46, `平均 ${num(Number(mean.toFixed(2)))}${unit}`, 12, "data-hi", "middle", "bold");
	}
	y = base + 58;
	if (sp.overlay || sp.label) {
		c.line(8, y + 8, 20, y + 8, "data-1", 2.2);
		const lab = sp.label ?? short;
		c.text(24, y + 12, lab, 12, "ink-2");
		if (sp.overlay) {
			let ox = 190;
			if (lab.length > 14) {
				y += 20;
				ox = 8;
			}
			c.line(ox, y + 8, ox + 12, y + 8, "ink", 1.6, "4 3");
			c.text(ox + 16, y + 12, sp.overlay.label ?? "重ねる分布", 12, "ink-2");
		}
		y += 20;
		for (const line of sp.lines ?? []) {
			c.text(8, y + 12, line, 12.5, "ink");
			y += 20;
		}
	}
	if (sp.note) y = c.para(8, y + 10, sp.note, 344, 12.5, "ink-2");
	return c.done(y + 6, `${name} の曲線${Number.isFinite(mean) ? `。平均は ${num(Number(mean.toFixed(2)))}${unit}` : ""}`);
}
// packages/ui/src/draw/dist.ts
const FAMILIES = [
	"binom",
	"bernoulli",
	"poisson",
	"geom",
	"hyper"
];
/** この関数で描ける設定か（離散：重ねる分布・帯・境目のないもの。連続：帯がなく、重ねるのは正規分布だけで、横軸 ticks があるもの） */
function canDrawDist(sp) {
	if (CURVE_FAMILIES.includes(String(sp.family))) return !sp.band && Array.isArray(sp.ticks) && (!sp.overlay || sp.overlay.family === "normal");
	if (!FAMILIES.includes(String(sp.family)) || sp.overlay || sp.band || sp.upto !== void 0) return false;
	return sp.family !== "poisson" && sp.family !== "geom" || sp.kmax !== void 0;
}
/** 棒の値（[k, 確率]）と期待値・図の説明の名前 */
function distPoints(sp) {
	let all, mean, name, top;
	switch (sp.family) {
		case "binom":
			all = modelPmf({
				kind: "binom",
				n: sp.n,
				p: sp.p
			});
			mean = sp.n * sp.p;
			name = `二項分布 B(${sp.n}, ${sp.p})`;
			top = sp.n;
			break;
		case "bernoulli":
			all = modelPmf({
				kind: "binom",
				n: 1,
				p: sp.p
			});
			mean = sp.p;
			name = `ベルヌーイ分布（p＝${sp.p}）`;
			top = 1;
			break;
		case "poisson":
			top = sp.kmax;
			all = poissonPmf(sp.lam, top);
			mean = sp.lam;
			name = `ポアソン分布（λ＝${sp.lam}）`;
			break;
		case "geom": {
			const r = sp.r ?? 1;
			top = sp.kmax;
			all = negbinomPmf(r, sp.p, top);
			mean = r / sp.p;
			name = r === 1 ? `幾何分布（p＝${sp.p}）` : `負の二項分布（r＝${r}、p＝${sp.p}）`;
			break;
		}
		case "hyper":
			all = modelPmf({
				kind: "hyper",
				n: sp.n,
				total: sp.N,
				success: sp.K
			});
			mean = sp.n * sp.K / sp.N;
			name = `超幾何分布（${sp.N}個のうち当たり${sp.K}個から${sp.n}個取る）`;
			top = sp.n;
	}
	const k0 = sp.kmin ?? (sp.family === "geom" ? sp.r ?? 1 : 0), k1 = sp.kmax ?? top;
	const pmf = [];
	for (let k = k0; k <= k1; k++) pmf.push([k, all[k] ?? 0]);
	return {
		pmf,
		mean,
		name
	};
}
function drawDist(sp, theme = "file") {
	if (!canDrawDist(sp)) throw new Error(`この設定はまだ描けない：${JSON.stringify(sp)}`);
	return CURVE_FAMILIES.includes(sp.family) ? drawCurve(sp, theme) : drawBars(sp, theme);
}
function drawBars(sp, theme) {
	const c = new Canvas(theme);
	const unit = sp.unit ?? "";
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	const top = y + 26, base = y + 190, left = 20, right = 340;
	const { pmf, mean, name } = distPoints(sp);
	const lo = pmf[0][0] - .5, hi = pmf[pmf.length - 1][0] + .5;
	const X = (v) => left + (v - lo) / (hi - lo) * 320;
	const pmax = Math.max(...pmf.map((q) => q[1]));
	const scale = (base - top - 18) / pmax;
	const slot = 320 / pmf.length;
	const bw = Math.min(40, slot * .62);
	const dec = sp.decimals ?? 2;
	const hl = new Set(sp.highlight ?? []);
	c.line(left, base, right, base, "ink-2", 1);
	const em = (t) => [...t].reduce((w, ch) => w + (ch.charCodeAt(0) < 8192 ? .6 : 1), 0) * 11.5;
	const widest = Math.max(...pmf.map(([x]) => em(`${num(x)}${unit}`)));
	const every = Math.max(1, Math.ceil(pmf.length / 12), Math.ceil((widest + 6) / slot));
	for (const [x, q] of pmf) {
		const cx = X(x);
		c.rect(cx - bw / 2, base - q * scale, bw, q * scale, hl.has(x) ? "data-hi" : "data-1-soft", 3);
		if (q * scale > 1.5 && pmf.length <= 12 || hl.has(x)) c.add(`<text x="${cx.toFixed(1)}" y="${(base - q * scale - 5).toFixed(1)}" font-size="${c.fs(11.5)}"${c.paint({
			fill: "ink",
			stroke: c.halo
		})} text-anchor="middle" stroke-width="4" paint-order="stroke">${q.toFixed(dec)}</text>`);
		const nearHl = [...hl].some((h) => h !== x && Math.abs(h - x) < every);
		if (hl.has(x) || (x - pmf[0][0]) % every === 0 && !nearHl) c.text(cx, base + 15, `${num(x)}${unit}`, 11.5, "ink-2", "middle");
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
	return c.done(y + 6, `${name} の棒。いちばん高いのは ${num(most[0])}${unit}、期待値は ${num(Number(mean.toFixed(2)))}${unit}`);
}
// packages/ui/src/draw/data.ts
const median = (s) => {
	const n = s.length;
	return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
};
/** 5つの数と柵（Q₁−1.5×IQR・Q₃＋1.5×IQR）。ひげは柵の内の最小・最大まで */
function five(values) {
	const s = [...values].sort((a, b) => a - b);
	const n = s.length, h = Math.floor(n / 2);
	const q1 = median(s.slice(0, h)), q2 = median(s), q3 = median(s.slice(n - h));
	const iqr = q3 - q1, lo = q1 - 1.5 * iqr, hi = q3 + 1.5 * iqr;
	const inside = s.filter((x) => x >= lo && x <= hi);
	return {
		min: s[0],
		max: s[n - 1],
		q1,
		q2,
		q3,
		iqr,
		lo,
		hi,
		wlo: inside[0],
		whi: inside[inside.length - 1],
		out: s.filter((x) => x < lo || x > hi),
		mean: s.reduce((a, b) => a + b, 0) / n
	};
}
function box(c, F, y, X, color, o) {
	if (o.label) c.text(8, y - 22, o.label, 12.5, "ink", "start", "bold");
	if (o.fence) for (const v of [F.lo, F.hi]) c.line(X(v), y - 16, X(v), y + 16, "bad", 1.2, "3 3");
	c.line(X(F.wlo), y, X(F.q1), y, color, 2);
	c.line(X(F.q3), y, X(F.whi), y, color, 2);
	for (const v of [F.wlo, F.whi]) c.line(X(v), y - 7, X(v), y + 7, color, 2);
	const bw = Math.max(1, X(F.q3) - X(F.q1));
	c.rect(X(F.q1), y - 11, bw, 22, color, 3, .15);
	c.add(`<rect x="${f1(X(F.q1))}" y="${y - 11}" width="${f1(bw)}" height="22" rx="3" fill="none"${c.paint({ stroke: color })} stroke-width="2"/>`);
	c.line(X(F.q2), y - 11, X(F.q2), y + 11, color, 3);
	for (const v of F.out) c.circle(X(v), y, 4.5, "surface", "bad", 2);
	if (o.mean !== void 0) {
		const m = X(o.mean);
		c.add(`<path d="M${f1(m)} ${y + 13} l-5 8 h10 z"${c.paint({ fill: "ink" })}/>`);
		c.text(m, y + 32, `平均 ${num(Number(o.mean.toFixed(2)))}`, 11, "ink", "middle");
	}
}
function axis(c, lo, hi, y, step, X) {
	c.line(16, y, 344, y, "ink-2", 1);
	for (let t = lo; t <= hi + 1e-9; t += step) c.text(X(t), y + 15, num(t), 11, "ink-2", "middle");
}
function drawHist(sp, theme = "file") {
	const c = new Canvas(theme);
	let cls;
	if (sp.data) {
		const w = sp.width, top = Math.max(...sp.data);
		cls = [];
		for (let a = sp.start; a <= top; a += w) cls.push([
			a,
			a + w,
			sp.data.filter((x) => a <= x && x < a + w).length
		]);
	} else cls = sp.classes;
	const dens = sp.density ?? false;
	const lo = cls[0][0], hi = cls[cls.length - 1][1];
	const X = (v) => 16 + (v - lo) / (hi - lo) * 328;
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	const top = y + 26, base = y + 170;
	const hts = cls.map(([a, b, n]) => dens ? n / (b - a) : n);
	const mx = Math.max(...hts) || 1;
	const total = cls.reduce((t, q) => t + q[2], 0);
	cls.forEach(([a, b, n], i) => {
		const hh = hts[i] / mx * (base - top - 18);
		c.rect(X(a), base - hh, X(b) - X(a) - 1.5, hh, sp.mark === i ? "data-hi" : "data-1", 0, .8);
		const lab = dens ? num(Number(hts[i].toFixed(3))) : String(n);
		c.add(`<text x="${f1((X(a) + X(b)) / 2)}" y="${f1(base - hh - 5)}" font-size="${c.fs(12)}"${c.paint({
			fill: "ink",
			stroke: c.halo
		})} text-anchor="middle" font-weight="bold" stroke-width="4" paint-order="stroke">${esc(lab)}</text>`);
	});
	const ticks = [...new Set(cls.flatMap(([a, b]) => [a, b]))].sort((a, b) => a - b);
	c.line(16, base, 344, base, "ink-2", 1);
	for (const t of ticks) c.text(X(t), base + 15, num(t), 11, "ink-2", "middle");
	y = base + 24;
	if (sp.axis_label) {
		c.text(344, base + 31, sp.axis_label, 11, "ink-2", "end");
		y = base + 46;
	}
	if (dens) {
		y += 8;
		for (const [a, b, n] of cls) y = c.para(8, y + 4, `${num(a)}〜${num(b)}：度数${n}÷幅${num(b - a)}＝高さ${num(Number((n / (b - a)).toFixed(3)))}（面積＝${n}）`, 344, 12.5, "ink");
	} else if (sp.cumulative) {
		y += 8;
		let cum = 0;
		const row = cls.map(([, b, n]) => {
			cum += n;
			return `${num(b)}未満 ${(cum / total).toFixed(2)}`;
		});
		y = c.para(8, y + 4, "累積相対度数：" + row.join("、"), 344, 12.5, "ink");
	}
	if (sp.box) {
		const F = five(sp.box);
		y += 40;
		box(c, F, y, X, "data-hi", { fence: true });
		y += 26;
		y = c.para(8, y + 10, `箱ひげ図：Q₁ ${num(F.q1)}・中央値 ${num(F.q2)}・Q₃ ${num(F.q3)}。柵 ${num(F.lo)}〜${num(F.hi)} の外（○）が外れ値候補`, 344, 12, "ink-2");
	}
	if (sp.note) y = c.para(8, y + 10, sp.note, 344, 12.5, "ink-2");
	const most = cls.reduce((b, q) => q[2] > b[2] ? q : b, cls[0]);
	return c.done(y + 6, `ヒストグラム（${cls.length}階級・全部で ${total}）。いちばん多いのは ${num(most[0])}〜${num(most[1])}`);
}
function drawBoxplot(sp, theme = "file") {
	const c = new Canvas(theme);
	const Fs = sp.rows.map((r) => five(r.data));
	const step = sp.step ?? 10;
	let lo = sp.lo ?? Math.min(...sp.rows.flatMap((r) => r.data));
	let hi = sp.hi ?? Math.max(Math.max(...sp.rows.flatMap((r) => r.data)), sp.fence ? Math.max(...Fs.map((F) => F.hi)) : 0);
	lo = step * Math.floor(lo / step);
	hi = step * Math.ceil(hi / step);
	const X = (v) => 16 + (v - lo) / (hi - lo) * 328;
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	y += 38;
	sp.rows.forEach((r, i) => {
		const mean = sp.mean ? Fs[i].mean : void 0;
		box(c, Fs[i], y, X, "data-1", {
			fence: sp.fence,
			label: r.label,
			mean
		});
		y += mean !== void 0 ? 64 : 52;
	});
	axis(c, lo, hi, y - 22, step, X);
	y += 6;
	sp.rows.forEach((r, i) => {
		const F = Fs[i];
		const head = r.label ? `${r.label}：` : "";
		y = c.para(8, y + 4, `${head}Q₁ ${num(F.q1)}・中央値 ${num(F.q2)}・Q₃ ${num(F.q3)}・IQR ${num(F.iqr)}`, 344, 12.5, "ink");
		if (sp.fence) {
			const out = F.out.map(num).join("・") || "なし";
			y = c.para(8, y, `柵 ${num(F.lo)} と ${num(F.hi)} → 外れ値候補：${out}`, 344, 12.5, F.out.length ? "bad" : "ink-2");
		}
	});
	if (sp.note) y = c.para(8, y + 4, sp.note, 344, 12.5, "ink-2");
	const F = Fs[0];
	return c.done(y + 6, `箱ひげ図。Q₁ ${num(F.q1)}・中央値 ${num(F.q2)}・Q₃ ${num(F.q3)}`);
}
/** 代表値の位置：点を数直線に積み、平均・中央値・最頻値に縦線（名前は下の凡例） */
function drawCenters(sp, theme = "file") {
	const c = new Canvas(theme);
	const d = [...sp.data].sort((a, b) => a - b), n = d.length;
	const lo = sp.lo ?? d[0], hi = sp.hi ?? d[n - 1];
	const X = (v) => 24 + (v - lo) / (hi - lo) * 312;
	const mean = d.reduce((a, b) => a + b, 0) / n;
	const med = (d[Math.floor((n - 1) / 2)] + d[Math.floor(n / 2)]) / 2;
	const cnt = /* @__PURE__ */ new Map();
	for (const v of d) cnt.set(v, (cnt.get(v) ?? 0) + 1);
	const top = Math.max(...cnt.values());
	const modes = [...cnt].filter(([, k]) => k === top).map(([v]) => v);
	let y = 8;
	if (sp.title) y = c.para(8, 22, sp.title, 344, 13.5, "ink", "bold") - 8;
	const marks = [[
		"平均",
		mean,
		"data-1",
		void 0
	]];
	if (sp.median ?? true) marks.push([
		"中央値",
		med,
		"data-hi",
		"6 4"
	]);
	if (sp.mode ?? true) for (const mv of modes.sort((a, b) => a - b)) marks.push([
		"最頻値",
		mv,
		"data-2",
		"2 3"
	]);
	const base = y + 30 + 12 * top;
	const seen = /* @__PURE__ */ new Map();
	for (const v of d) {
		const k = (seen.get(v) ?? 0) + 1;
		seen.set(v, k);
		c.circle(X(v), base - 8 - (k - 1) * 12, 5, "ink-2");
	}
	for (const [, v, col, dash] of marks) c.line(X(v), y + 14, X(v), base, col, 2.5, dash);
	c.line(16, base, 344, base, "ink-2", 1);
	for (const t of sp.ticks ?? []) c.text(X(t), base + 15, num(t), 11, "ink-2", "middle");
	y = base + 22;
	for (const [name, v, col, dash] of marks) {
		c.line(10, y + 10, 30, y + 10, col, 2.5, dash);
		c.text(36, y + 14, `${name} ${num(Number(v.toFixed(2)))}`, 12, "ink-2");
		y += 18;
	}
	if (sp.axis_label) y = c.para(8, y + 14, sp.axis_label, 344, 12, "ink-2");
	if (sp.note) y = c.para(8, y + 4, sp.note, 344, 12.5, "ink-2");
	return c.done(y + 6, `${n}個の値の点。平均 ${num(Number(mean.toFixed(2)))}・中央値 ${num(med)}・最頻値 ${modes.map(num).join("と")}`);
}
/** データの図を描く（type で選ぶ） */
function drawData(sp, theme = "file") {
	if (sp.type === "hist") return drawHist(sp, theme);
	if (sp.type === "boxplot") return drawBoxplot(sp, theme);
	return drawCenters(sp, theme);
}
const DATA_TYPES = [
	"hist",
	"boxplot",
	"centers"
];
export { DATA_TYPES, canDrawDist, densityOf, distPoints, drawBoxplot, drawCenters, drawData, drawDist, drawHist, five, wrap };
