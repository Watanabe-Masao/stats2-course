"""語の印（全129語。stats2-course #220。knowledge-net #109 の試作から移した）。
48×48 の枠・線 2.4・丸い端・色は currentColor（画面では置き場所の柱の色で塗る）。分類ごとに形の系統をそろえる（推定は的・確率は円など）。
form：形＝しくみや形で特徴を描いた語、記号＝形にしにくく記号や文字を主にした語。
ここが原本（設定から作る。手で描いた SVG を置かない）。build が out/site/icons/<語のID>.svg に書き、概念の icon にその URL を入れる。
"""
import math
import re
def f(x): return f"{x:.1f}".rstrip("0").rstrip(".")
def P(d, **a):
    extra = "".join(f' {k.replace("_","-")}="{v}"' for k, v in a.items())
    return f'<path d="{d}"{extra}/>'
def C(x, y, r, fill=False, **a):
    extra = "".join(f' {k.replace("_","-")}="{v}"' for k, v in a.items())
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"{" fill=\"currentColor\"" if fill else ""}{extra}/>'
def D(x, y, r=2.4): return C(x, y, r, True, stroke="none")
def R(x, y, w, h, rx=1.5, fill=None, op=None, **a):
    extra = "".join(f' {k.replace("_","-")}="{v}"' for k, v in a.items())
    fl = f' fill="currentColor" fill-opacity="{op}"' if op is not None else (' fill="currentColor" stroke="none"' if fill else "")
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}"{fl}{extra}/>'
def T(t, x=24, y=31, s=17, w=700, op=None):
    o = f' fill-opacity="{op}"' if op else ""
    return f'<text x="{f(x)}" y="{f(y)}" text-anchor="middle" font-size="{s}" font-weight="{w}" fill="currentColor" stroke="none"{o} font-family="system-ui,-apple-system,sans-serif">{t}</text>'
def bell(cx=24, w=13, top=11, base=40):
    return f"M{f(cx-w*1.45)} {base} C{f(cx-w*.6)} {base} {f(cx-w*.55)} {top} {cx} {top} S{f(cx+w*.6)} {base} {f(cx+w*1.45)} {base}"
def AX(): return P("M6 40h36")
def AXES(): return P("M8 8v32h32")
def bars(hs, x0=8, gap=5, w=3.6, base=40, fill=True, op=None):
    return "".join(R(x0+i*gap, base-h, w, h, 1, fill=fill if op is None else None, op=op) for i, h in enumerate(hs) if h > 0)
def arrow(x1, y1, x2, y2, head=3.2):
    a = math.atan2(y2-y1, x2-x1)
    l = (x2-head*math.cos(a-0.5), y2-head*math.sin(a-0.5)); r = (x2-head*math.cos(a+0.5), y2-head*math.sin(a+0.5))
    return P(f"M{f(x1)} {f(y1)}L{f(x2)} {f(y2)} M{f(l[0])} {f(l[1])}L{f(x2)} {f(y2)}L{f(r[0])} {f(r[1])}")
def target(r1=16, r2=8, cx=24, cy=24): return C(cx, cy, r1) + C(cx, cy, r2) + D(cx, cy, 1.6)
def tail(x0, x1, cx=24, w=13, top=11, base=40, op=.45):
    # 山の右（または左）の裾を塗る（近似の多角形）
    pts = []
    for i in range(13):
        x = x0 + (x1-x0)*i/12
        z = (x-cx)/(w*0.62)
        y = base - (base-top)*math.exp(-z*z/2)
        pts.append(f"{f(x)} {f(y)}")
    return f'<path d="M{f(x0)} {base} L{" L".join(pts)} L{f(x1)} {base}Z" fill="currentColor" fill-opacity="{op}" stroke="none"/>'
def venn(a=True, b=True, inter=False, cx1=19, cx2=29, r=11, cy=24):
    s = C(cx1, cy, r) + C(cx2, cy, r)
    if inter:
        s += f'<path d="M24 {f(cy-math.sqrt(r*r-25))} A{r} {r} 0 0 1 24 {f(cy+math.sqrt(r*r-25))} A{r} {r} 0 0 1 24 {f(cy-math.sqrt(r*r-25))}Z" fill="currentColor" fill-opacity=".4" stroke="none"/>'
    return s
def frame(): return R(6, 8, 36, 32, 4)   # 標本空間・名簿などの枠
def grid(nx, ny, x0, y0, dx, dy, on=lambda i, j: False, r=2.2):
    return "".join(D(x0+i*dx, y0+j*dy, r) if on(i, j) else C(x0+i*dx, y0+j*dy, r) for i in range(nx) for j in range(ny))
def scatter(pts, r=2.2): return "".join(D(x, y, r) for x, y in pts)
UP = [(12, 34), (16, 30), (20, 31), (24, 25), (28, 23), (32, 18), (36, 16)]

I = {}
def add(k, svg, form="形"): I[k] = {"svg": svg, "form": form}

# ── 数学の道具：並べる・選ぶ・数える
add("TERM-perm", C(9, 26, 4) + C(24, 26, 4) + C(39, 26, 4) + arrow(14.5, 26, 18.5, 26) + arrow(29.5, 26, 33.5, 26) + T("1", 10, 16, 9) + T("2", 24, 16, 9) + T("3", 38, 16, 9))
add("TERM-comb", "".join(C(8+i*8, 18, 2.8, i in (1, 3)) for i in range(5)) + P("M14 25 q2 4 4 0 M30 25 q2 4 4 0") + T("ₙCₖ", 24, 43, 12))
add("TERM-sigma", T("Σ", 24, 34, 26) + T("i", 39, 42, 8, 600) + T("n", 39, 14, 8, 600), "記号")
add("TERM-fact", T("n!", 24, 32, 20), "記号")

# ── データと変数：全体と一部・物差し・札
add("TERM-population", C(24, 24, 17) + "".join(C(x, y, 1.8) for x, y in [(14, 17), (24, 12), (34, 17), (13, 28), (24, 24), (35, 28), (18, 35), (30, 35)]))
add("TERM-sample", C(24, 24, 17) + "".join(C(x, y, 1.8) for x, y in [(14, 17), (30, 14), (34, 28), (16, 32), (24, 35)]) + C(24, 22, 7, stroke_dasharray="3 2.5") + D(22, 20, 1.8) + D(27, 24, 1.8))
add("TERM-parameter", C(24, 24, 17) + T("μ", 24, 31, 18) + T("?", 37, 14, 10), "記号")
add("TERM-statistic", P("M15 14h18") + T("x", 24, 35, 22), "記号")
add("TERM-frame", R(10, 7, 28, 34, 3) + P("M16 15h16 M16 21h16 M16 27h16 M16 33h10") + D(13.5, 15, 1.2) + D(13.5, 21, 1.2) + D(13.5, 27, 1.2) + D(13.5, 33, 1.2))
add("TERM-qual", R(7, 12, 15, 10, 2) + R(26, 12, 15, 10, 2) + R(16, 27, 15, 10, 2) + T("A", 14.5, 20.5, 8) + T("B", 33.5, 20.5, 8) + T("O", 23.5, 35.5, 8))
add("TERM-quant", R(6, 18, 36, 12, 2) + P("M12 18v5 M18 18v3 M24 18v5 M30 18v3 M36 18v5"))
add("TERM-scale", P("M8 38h7v-6h7v-7h7v-7h7v-8") + T("名", 11.5, 47, 6, 600) + T("順", 18.5, 47, 6, 600) + T("間", 25.5, 47, 6, 600) + T("比", 32.5, 47, 6, 600))
add("TERM-ratio", C(24, 24, 15) + f'<path d="M24 24 L24 9 A15 15 0 0 1 38.3 28.6 Z" fill="currentColor" fill-opacity=".45" stroke="none"/>' + P("M24 24V9 M24 24L38.3 28.6"))
add("TERM-point", T("%", 13, 30, 14) + T("−", 24, 29, 14) + T("%", 35, 30, 14) + T("pt", 24, 44, 9), "記号")

# ── 確率：集合の円と枠
add("TERM-sample-space", frame() + "".join(D(x, y, 1.9) for x, y in [(14, 16), (24, 15), (34, 17), (13, 26), (23, 25), (33, 27), (17, 34), (29, 34)]) + T("Ω", 38, 14, 7, 600))
add("TERM-event", frame() + C(20, 24, 9, False) + f'<circle cx="20" cy="24" r="9" fill="currentColor" fill-opacity=".35" stroke="none"/>' + T("A", 20, 28, 9))
add("TERM-complement", frame() + '<path d="M10 8h28a4 4 0 0 1 4 4v24a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4V12a4 4 0 0 1 4-4Z M29 24a9 9 0 1 0-18 0a9 9 0 1 0 18 0Z" fill="currentColor" fill-opacity=".35" fill-rule="evenodd" stroke="none"/>' + C(20, 24, 9) + T("A", 20, 28, 9) + T("Aᶜ", 34, 37, 7, 600))
add("TERM-exclusive", frame() + C(16, 24, 7) + C(32, 24, 7))
add("TERM-indep", C(15, 24, 9) + C(33, 24, 9))
add("TERM-cond", venn(inter=True) + C(29, 24, 11, stroke_width="3.4"))
add("TERM-bayes", T("A", 11, 29, 13) + T("B", 37, 29, 13) + P("M17 18 q7 -6 14 0 M28 16l3 2-3.4 1.2 M31 30 q-7 6 -14 0 M20 32l-3-2 3.4-1.2"))
add("TERM-prior", P(bell(24, 15, 22, 40), stroke_dasharray="3 2.5") + AX() + T("前", 10, 14, 9))
add("TERM-likelihood", AX() + bars([4, 10, 18, 26, 18, 10, 4], 8, 5) + T("L", 40, 14, 10), "形")
add("TERM-posterior", P(bell(24, 15, 26, 40), stroke_dasharray="3 2.5", stroke_opacity=".45") + P(bell(27, 8, 9, 40)) + AX() + T("後", 10, 14, 9))
add("TERM-prob", AX() + R(8, 34, 32, 4, 2, op=".15") + R(8, 34, 20, 4, 2, fill=True) + T("0", 8, 28, 9) + T("1", 40, 28, 9) + T("P", 24, 20, 13))
add("TERM-addition", venn(inter=False) + f'<circle cx="19" cy="24" r="11" fill="currentColor" fill-opacity=".25" stroke="none"/><circle cx="29" cy="24" r="11" fill="currentColor" fill-opacity=".25" stroke="none"/>' + T("+", 24, 46, 10))
add("TERM-multiplication", venn(inter=True) + T("×", 24, 46, 10))
add("TERM-total-prob", frame() + P("M18 8v32 M30 8v32") + P("M6 26 C14 20 30 32 42 22", stroke_width="3") + f'<path d="M6 26 C14 20 30 32 42 22 V40 H6Z" fill="currentColor" fill-opacity=".2" stroke="none"/>')

# ── 調査・実験：点の並びの選び方
add("TERM-random-sampling", grid(4, 4, 10, 11, 9, 9, lambda i, j: (i*7+j*3) % 5 == 1))
add("TERM-bias", target() + D(33, 14) + D(36, 17) + D(31, 18))
add("TERM-strat-sampling", R(6, 8, 36, 9, 2) + R(6, 20, 36, 9, 2) + R(6, 32, 36, 9, 2) + "".join(D(x, y, 1.8) if (x+y) % 3 == 0 else C(x, y, 1.6) for y in (12.5, 24.5, 36.5) for x in (12, 18, 24, 30, 36)))
add("TERM-cluster-sampling", C(13, 15, 7) + C(35, 15, 7) + f'<circle cx="24" cy="34" r="7" fill="currentColor" fill-opacity=".35"/>' + "".join(D(x, y, 1.5) for x, y in [(21, 32), (26, 32), (24, 37)]) + "".join(C(x, y, 1.4) for x, y in [(11, 13), (15, 17), (33, 13), (37, 17)]))
add("TERM-systematic-sampling", "".join(D(7+i*4.2, 24, 2) if i % 3 == 1 else C(7+i*4.2, 24, 1.5) for i in range(9)) + P("M11.2 16 q6.3-5 12.6 0 M23.8 16 q6.3-5 12.6 0") + T("k", 17.5, 12, 7, 600) + T("k", 30.1, 12, 7, 600))
add("TERM-multistage-sampling", R(6, 6, 36, 36, 4) + R(12, 12, 24, 24, 3) + R(18, 18, 12, 12, 2, op=".35") + D(24, 24, 1.8))
add("TERM-sampling-error", target() + D(19, 17) + D(31, 27) + D(22, 33) + D(33, 19))
add("TERM-nonsampling-error", R(10, 8, 28, 32, 3) + P("M15 16h18 M15 23h18 M15 30h9") + P("M29 28l8 8 M37 28l-8 8", stroke_width="3"))
add("TERM-randomize", C(10, 14, 3) + C(10, 24, 3, True) + C(10, 34, 3) + R(28, 8, 14, 12, 3) + R(28, 28, 14, 12, 3) + P("M14 14 L27 31 M14 24 L27 14 M14 34 L27 34", stroke_opacity=".7"))
add("TERM-confound", T("X", 10, 37, 11) + T("Y", 38, 37, 11) + T("Z", 24, 16, 11) + arrow(20, 19, 13, 28) + arrow(28, 19, 35, 28) + P("M16 33h16", stroke_dasharray="2 2.5"))

# ── 要約：数直線の上の印
NL = P("M5 34h38")
add("TERM-mode", AX() + bars([6, 12, 28, 16, 9, 4], 8, 5.5, 4, 40, fill=None, op=".25") + R(19, 12, 4, 28, 1, fill=True))
add("TERM-median", NL + "".join(D(x, 34, 2.2) for x in (8, 14, 19, 31, 38)) + C(24, 34, 3.6, True) + P("M24 10v18", stroke_dasharray="2 2"))
add("TERM-quartile", NL + "".join(D(x, 34, 1.8) for x in (7, 11, 15, 22, 27, 33, 37, 41)) + P("M13 18v12 M24 14v16 M35 18v12"))
add("TERM-iqr", NL + R(14, 26, 20, 14, 1.5) + arrow(24, 18, 14, 18) + arrow(24, 18, 34, 18))
add("TERM-outlier", NL + "".join(D(x, 34, 2) for x in (8, 11, 14, 17, 20, 23)) + C(40, 34, 3.4) + P("M40 14v14", stroke_dasharray="2 2") + T("!", 40, 12, 9))
add("TERM-dev", P("M24 8v34", stroke_dasharray="2 3") + D(36, 22, 3) + arrow(24, 22, 32.5, 22) + T("x̄", 18, 14, 9))
add("TERM-var", P("M24 8v32", stroke_dasharray="2 3") + D(9, 20) + D(15, 30) + D(31, 16) + D(39, 28) + P("M9 40h30") + arrow(24, 40, 9, 40) + arrow(24, 40, 39, 40))
add("TERM-unbvar", P("M24 8v22", stroke_dasharray="2 3") + D(12, 16) + D(18, 24) + D(31, 14) + D(36, 22) + T("n−1", 24, 43, 11), "記号")
add("TERM-sd", P(bell()) + P("M15 26v13 M33 26v13", stroke_dasharray="2 2.5") + T("±σ", 24, 47, 9))
add("TERM-cv", T("σ", 24, 20, 14) + P("M14 25h20") + T("μ", 24, 40, 14), "記号")
add("TERM-std", AX() + P(bell(24, 12, 12, 40)) + P("M24 12v28", stroke_dasharray="2 2.5") + T("0", 24, 47, 8) + T("z", 38, 15, 10))
add("TERM-skew", AX() + P("M6 40 C10 40 12 12 17 12 S30 34 42 38"))
add("TERM-kurt", AX() + P(bell(24, 13, 22, 40), stroke_opacity=".45") + P(bell(24, 6, 8, 40)))
add("TERM-expect", P("M6 32h36") + bars([8, 14, 20, 14, 8, 4], 7, 6, 4, 32) + f'<path d="M24 34l-4 7h8z" fill="currentColor"/>')
add("TERM-geomean", P("M6 27l4-2 5 11 6-22h21") + T("×", 32, 32, 13) + T("n", 9, 18, 8, 600), "記号")
add("TERM-mean", NL + "".join(D(x, 34, 2.2) for x in (8, 15, 20, 30, 39)) + f'<path d="M22.4 37l-4 6h8z" fill="currentColor" stroke="none"/>' + T("x̄", 22.4, 24, 11))
add("TERM-data-var", NL + "".join(D(x, 34, 2.2) for x in (8, 14, 30, 38)) + P("M23 10v28", stroke_dasharray="2 3") + arrow(23, 18, 8, 18) + arrow(23, 18, 38, 18) + T("²", 40, 14, 10))
add("TERM-data-sd", NL + "".join(D(x, 34, 2.2) for x in (8, 14, 30, 38)) + P("M23 10v28", stroke_dasharray="2 3") + arrow(23, 20, 14, 20) + arrow(23, 20, 32, 20) + T("s", 23, 15, 10))
add("TERM-quantile", AX() + P(bell(24, 13, 11, 40)) + tail(5, 14, 24, 13, 11, 40, .45) + P("M14 18v22", stroke_dasharray="2 2") + T("10%", 9, 14, 7, 600))
add("TERM-range", NL + "".join(D(x, 34, 2) for x in (16, 21, 26, 31)) + C(8, 34, 3, True) + C(40, 34, 3, True) + arrow(24, 22, 8, 22) + arrow(24, 22, 40, 22))

# ── 図表：図そのもの
add("TERM-freqtable", R(8, 8, 32, 32, 2) + P("M8 16h32 M8 24h32 M8 32h32 M22 8v32") + R(24, 18.5, 6, 3, .5, fill=True) + R(24, 26.5, 12, 3, .5, fill=True) + R(24, 34.5, 8, 3, .5, fill=True))
add("TERM-hist", AX() + "".join(R(7+i*6, 40-h, 6, h, 0, op=".3") for i, h in enumerate([8, 18, 28, 20, 10, 5])))
add("TERM-boxplot", P("M6 24h8 M34 24h8 M6 19v10 M42 19v10") + R(14, 16, 20, 16, 1.5) + P("M22 16v16", stroke_width="3"))
add("TERM-crosstab", R(7, 8, 34, 32, 2) + P("M7 18h34 M19 8v32 M7 29h34 M30 8v32") + R(20.5, 19.5, 8, 8, 1, op=".45") + R(31.5, 30.5, 8, 8, 1, op=".45"))
add("TERM-scatter", AXES() + scatter([(14, 33), (18, 28), (22, 30), (26, 22), (30, 20), (34, 14), (37, 17)]))

# ── 推定：的と区間
add("TERM-unbiased", target() + P("M24 4v6 M24 38v6 M4 24h6 M38 24h6") + D(20, 21) + D(28, 22) + D(22, 28) + D(27, 27))
add("TERM-estimator", C(34, 24, 9) + D(34, 24, 2) + arrow(6, 30, 24, 26) + T("θ̂", 10, 18, 10))
add("TERM-point-est", P("M6 32h36") + "".join(P(f"M{x} 29v6") for x in (10, 17, 24, 31, 38)) + D(27, 22, 3.6) + P("M27 26v4", stroke_dasharray="1.5 1.5"))
add("TERM-consistency", target(16, 8) + D(37, 12, 1.6) + D(31, 17, 1.9) + D(27, 21, 2.2) + P("M37 12 L27 21", stroke_dasharray="2 2.5"))
add("TERM-efficiency", target(16, 8) + D(22, 22, 1.8) + D(26, 25, 1.8) + D(23, 27, 1.8) + D(26, 21, 1.8))
add("TERM-mse", C(24, 24, 15) + D(24, 24, 1.6) + D(33, 16, 2.6) + R(24, 16, 9, 8, 0, op=".3") + T("²", 37, 14, 8, 600))
add("TERM-ci", P("M6 32h36") + P("M12 18v10 M12 23h24 M36 18v10", stroke_width="3") + D(24, 23, 3.2))
add("TERM-conf-level", "".join(P(f"M{a} {y}h{b}", stroke_opacity="1" if i != 3 else ".35") for i, (a, b, y) in enumerate([(10, 22, 10), (14, 20, 17), (8, 24, 24), (26, 14, 31), (12, 22, 38)])) + P("M24 6v36", stroke_dasharray="2 2.5") + T("95%", 40, 46, 7, 600))
add("TERM-interval-est", AX() + P(bell(24, 13, 12, 40), stroke_opacity=".4") + P("M13 30v8 M13 34h22 M35 30v8", stroke_width="3"))

# ── 確率分布：山と棒
add("TERM-normal", AX() + f'<path d="{bell(24, 13, 10, 40)}" fill="currentColor" fill-opacity=".18"/>')
add("TERM-rv", T("X", 12, 31, 16) + arrow(19, 25, 30, 25) + T("x", 38, 31, 14) + T("?", 38, 15, 9))
add("TERM-dist", AXES() + P("M10 34 C16 34 18 14 24 14 S34 30 40 32") + T("P", 30, 13, 9))
add("TERM-cov", P("M24 6v36 M6 24h36", stroke_opacity=".45") + scatter([(30, 16), (34, 12), (14, 32), (18, 30)]) + R(24, 12, 10, 12, 0, op=".25") + R(14, 24, 10, 8, 0, op=".25"))
# 標準正規分布：中心を0にそろえた山と、0の位置の縦線（#289）
add("TERM-std-normal", AX() + f'<path d="{bell(24, 13, 10, 40)}" fill="currentColor" fill-opacity=".18"/>' + P("M24 10v30", stroke_opacity=".55") + T("0", 24, 47, 9))
# 無相関：直線の傾きがない散らばり（横に寝た点の帯）（#289）
add("TERM-uncorr", P("M24 6v36 M6 24h36", stroke_opacity=".45") + scatter([(12, 20), (17, 28), (22, 21), (27, 27), (32, 22), (37, 26)]))
add("TERM-binom", AX() + bars([4, 12, 22, 28, 22, 12, 4], 8, 5))
add("TERM-poisson", AX() + bars([16, 28, 24, 14, 7, 3, 1], 8, 5))
add("TERM-geom", AX() + bars([28, 20, 14, 10, 7, 5, 3], 8, 5))
add("TERM-negbinom", AX() + bars([3, 10, 18, 22, 19, 14, 9], 8, 5))
add("TERM-hyper", AX() + bars([2, 10, 26, 30, 26, 10, 2], 8, 5) + C(40, 10, 3.5) + P("M37 10h-4", stroke_dasharray="1.5 1.5"))
add("TERM-expo", AX() + P("M8 10 C12 26 22 36 42 38") + f'<path d="M8 10 C12 26 22 36 42 38 V40 H8Z" fill="currentColor" fill-opacity=".15" stroke="none"/>')
add("TERM-pdf", AX() + P(bell(24, 13, 10, 40)) + tail(20, 31, 24, 13, 10, 40, .45) + T("f", 10, 16, 11))
add("TERM-uniform", AX() + R(10, 20, 28, 20, 0, op=".18") + P("M10 40V20h28v20"))
add("TERM-bernoulli", AX() + R(13, 26, 6, 14, 1, fill=True) + R(29, 14, 6, 26, 1, fill=True) + T("0", 16, 47, 8) + T("1", 32, 47, 8))

# ── 時系列
add("TERM-ma", P("M5 30 l5 -9 l5 12 l5 -14 l5 10 l5 -12 l5 9 l5 -8", stroke_opacity=".45") + P("M5 27 C15 25 25 22 43 18", stroke_width="3.2"))
add("TERM-acf", P("M6 26h36") + "".join(P(f"M{x} 26v{h}") + D(x, 26+h, 2.2) for x, h in [(9, -16), (15, -11), (21, -6), (27, 4), (33, -3), (39, 2)]))

# ── 相関・回帰：散布と直線
add("TERM-corr", P("M8 38 L40 10", stroke_opacity=".5") + scatter([(12, 33), (17, 31), (20, 26), (26, 23), (29, 19), (34, 16), (37, 12)]) + T("r", 13, 16, 12))
add("TERM-partial-corr", P("M8 36 L40 14", stroke_opacity=".5") + scatter([(13, 32), (19, 31), (24, 26), (30, 22), (36, 17)]) + T("Z", 38, 40, 9) + P("M34 34l8 8 M42 34l-8 8", stroke_width="1.8"))
add("TERM-spurious", T("Z", 24, 15, 10) + arrow(20, 17, 12, 28) + arrow(28, 17, 36, 28) + T("X", 10, 39, 10) + T("Y", 38, 39, 10) + P("M16 35h16", stroke_dasharray="2 2.5") + T("?", 24, 33, 8))
add("TERM-ols", P("M6 36 L42 14") + "".join(R(x, min(y, ly), abs(ly-y), abs(ly-y), 0, op=".22") for x, y, ly in [(12, 26, 32.3), (30, 14, 21.3)]) + D(12, 26) + D(30, 14) + D(22, 30) + D(38, 19))
add("TERM-regcoef", P("M6 38 L42 14") + P("M18 30h12v-8", stroke_dasharray="2.5 2") + T("1", 24, 36, 7, 600) + T("b", 35, 28, 9))
add("TERM-resid", P("M6 36 L42 14") + "".join(P(f"M{x} {y}V{ly}", stroke_dasharray="2 2") + D(x, y, 2.4) for x, y, ly in [(12, 24, 32.4), (22, 34, 26.3), (30, 16, 21.4), (38, 22, 16.4)]))
add("TERM-r2", C(24, 24, 15) + f'<path d="M24 24 L24 9 A15 15 0 1 1 10.7 30.9 Z" fill="currentColor" fill-opacity=".45" stroke="none"/>' + T("R²", 24, 29, 10))
add("TERM-extrap", AXES() + scatter([(12, 34), (16, 31), (20, 28), (24, 26)]) + P("M10 36 L26 24") + P("M26 24 L40 13", stroke_dasharray="3 3") + D(40, 13, 2.6) + T("?", 40, 26, 8))
add("TERM-mreg", f'<path d="M6 32 L20 20 L42 22 L28 36 Z" fill="currentColor" fill-opacity=".15"/>' + D(16, 14) + D(32, 15) + D(26, 42) + P("M16 14v12 M32 15v9", stroke_dasharray="2 2"))
add("TERM-dummy", R(8, 16, 14, 16, 3) + R(26, 16, 14, 16, 3, op=".4") + T("0", 15, 28, 11) + T("1", 33, 28, 11), "記号")
add("TERM-adjr2", C(24, 24, 15) + f'<path d="M24 24 L24 9 A15 15 0 1 1 13 34 Z" fill="currentColor" fill-opacity=".45" stroke="none"/>' + T("R̄²", 24, 29, 10))
add("TERM-multicol", AXES() + scatter([(13, 34), (17, 30), (21, 27), (25, 23), (29, 20), (33, 16), (37, 13)], 2) + T("x₁", 40, 46, 7, 600) + T("x₂", 6, 10, 7, 600))
add("TERM-slr", AXES() + scatter([(13, 32), (18, 30), (22, 25), (28, 24), (33, 17)]) + P("M10 35 L40 14"))

# ── 標本分布・極限：たくさんの標本と山
add("TERM-sampdist", AX() + P(bell(24, 8, 12, 40)) + "".join(P(f"M{x} 6v6", stroke_opacity=".5") for x in (14, 20, 26, 32)) + "".join(D(x, 9, 1.4) for x in (17, 23, 29)))
add("TERM-se", AX() + P(bell(24, 8, 10, 40)) + arrow(24, 30, 32, 30) + T("SE", 38, 16, 8))
add("TERM-lln", P("M6 24h36", stroke_dasharray="2 3") + P("M6 10 L10 34 L14 16 L18 30 L22 20 L27 27 L32 22 L37 25 L42 24"))
add("TERM-clt", AX() + bars([5, 9, 16, 22, 16, 9, 5], 8, 5, 3.6, 40, fill=None, op=".25") + P(bell(24, 10, 12, 40)))
add("TERM-cc", AX() + R(16, 16, 8, 24, 0, op=".25") + P(bell(20, 11, 10, 40)) + P("M16 12v28 M24 12v28", stroke_dasharray="2 2") + T("±0.5", 20, 9, 7, 600))
add("TERM-t", AX() + P(bell(24, 11, 9, 40), stroke_opacity=".4") + P("M4 37 C12 36 16 15 24 15 S36 36 44 37", stroke_width="3"))
add("TERM-chi2", AX() + P("M7 40 C10 40 12 12 18 12 S28 34 42 38"))
add("TERM-f", AX() + P("M7 40 C9 40 10 10 15 10 S24 34 42 39") + T("F", 34, 18, 11))
add("TERM-df", T("n−1", 24, 31, 16), "記号")
add("TERM-sample-mean", "".join(D(x, y, 2) for x, y in [(10, 14), (16, 10), (22, 15), (28, 11), (34, 14)]) + arrow(22, 20, 22, 29) + T("x̄", 22, 42, 13))
add("TERM-sample-prop", "".join(D(10+i*7, 16, 2.6) if i in (0, 2, 3) else C(10+i*7, 16, 2.6) for i in range(5)) + T("3/5", 24, 38, 13), "記号")

# ── 検定：山と裾・仮説
add("TERM-paired-t", P("M12 10v28 M36 10v28", stroke_opacity=".35") + "".join(D(12, y, 2) + D(36, y-5+((y//6) % 3), 2) + P(f"M14 {y}L34 {y-5+((y//6) % 3)}", stroke_dasharray="1.5 2") for y in (16, 26, 36)))
add("TERM-welch", AX() + P(bell(17, 6, 12, 40)) + P(bell(31, 10, 22, 40)))
add("TERM-h0", T("H₀", 24, 32, 20), "記号")
add("TERM-h1", T("H₁", 24, 32, 20), "記号")
add("TERM-test-stat", AX() + P(bell(22, 12, 10, 40)) + f'<path d="M36 42 l-3 -6 h6z" fill="currentColor" stroke="none"/>' + P("M36 36V14", stroke_dasharray="2 2"))
add("TERM-pvalue", AX() + P(bell(20, 12, 10, 40)) + tail(32, 42, 20, 12, 10, 40, .45) + P("M32 40V24", stroke_dasharray="2 2") + T("p", 40, 18, 10))
add("TERM-alpha", AX() + P(bell(22, 12, 10, 40)) + tail(34, 43, 22, 12, 10, 40, .45) + T("α", 40, 22, 10))
add("TERM-reject", AX() + P(bell(24, 11, 10, 40)) + R(36, 26, 8, 14, 0, op=".45") + R(4, 26, 8, 14, 0, op=".45"))
add("TERM-sides", AX() + P(bell(24, 11, 10, 40)) + tail(4, 11, 24, 11, 10, 40, .5) + tail(37, 44, 24, 11, 10, 40, .5) + arrow(10, 30, 6, 36) + arrow(38, 30, 42, 36))
add("TERM-type1", AX() + P(bell(22, 12, 10, 40)) + tail(32, 41, 22, 12, 10, 40, .45) + P("M33 40V26", stroke_dasharray="2 2") + T("α", 40, 22, 10))
add("TERM-type2", AX() + P(bell(17, 9, 12, 40), stroke_opacity=".5") + P(bell(31, 9, 12, 40)) + tail(18, 26, 31, 9, 12, 40, .45) + P("M26 8v34", stroke_width="2") + T("β", 22, 9, 9))
add("TERM-power", AX() + P(bell(15, 8, 14, 40), stroke_opacity=".5") + P(bell(31, 9, 12, 40)) + tail(26, 44, 31, 9, 12, 40, .4) + P("M26 8v34", stroke_width="2") + T("1−β", 36, 9, 7, 600))
add("TERM-pool", R(6, 14, 12, 20, 3) + R(30, 14, 12, 20, 3) + arrow(18, 24, 22, 24) + arrow(30, 24, 26, 24) + C(24, 24, 3, True) + T("p̂", 24, 44, 10))
add("TERM-expected", R(7, 8, 34, 32, 2) + P("M7 24h34 M24 8v32") + "".join(T("e", x, y, 9, 600, ".75") for x, y in ((15.5, 19), (32.5, 19), (15.5, 35), (32.5, 35))))
add("TERM-indep-test", R(7, 8, 24, 24, 2) + P("M7 20h24 M19 8v24") + P("M30 42 C32 42 33 26 36 26 S39 38 44 41"))
add("TERM-gof", AX() + bars([10, 20, 26, 14], 9, 8, 6, 40, fill=None, op=".28") + P("M9 30h6 M17 22h6 M25 12h6 M33 28h6", stroke_width="2.6"))
add("TERM-ms", T("SS", 24, 21, 11) + P("M12 25h24") + T("df", 24, 39, 11), "記号")
add("TERM-anova", AX() + P(bell(12, 5, 14, 40)) + P(bell(24, 5, 10, 40)) + P(bell(36, 5, 16, 40)) + T("F", 40, 10, 9))
add("TERM-multcomp", "".join(C(x, y, 4) for x, y in ((24, 10), (11, 34), (37, 34))) + P("M21 13.5 L14 30 M27 13.5 L34 30 M15 34 H33", stroke_dasharray="2.5 2"))
add("TERM-test", AX() + P(bell(19, 9, 12, 40)) + P(bell(31, 9, 12, 40), stroke_dasharray="3 2.5") + P("M27 8v34", stroke_width="3"))


SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'


def svg(term_id: str) -> str | None:
    i = I.get(term_id)
    return f"{SVG_HEAD}{i['svg']}</svg>\n" if i else None


# 画面は CSS の mask で読むので中のスクリプトは動かないが、教科書・Notion などほかの読み方もあるので、動く物・外を指す物を入れない
UNSAFE = re.compile(r"<script|<foreignObject|\son\w+\s*=|href\s*=|url\(|<image|<use", re.I)


def icon_errors(term_ids: list[str]) -> list[str]:
    """全部の語に印があり、印に動く物・外を指す物がないか（build が止める）"""
    err = [f"語の印がない：{t}" for t in term_ids if t not in I]
    err += [f"語の印に語がない（terms.yaml にない）：{k}" for k in I if k not in set(term_ids)]
    err += [f"語の印に使えない物がある：{k}" for k, v in I.items() if UNSAFE.search(v["svg"])]
    return err
