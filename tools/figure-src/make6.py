import sys, math
sys.path.insert(0, ".")
from svgkit import *
out = {}
X = [1, 2, 3, 4, 5]; Y = [3, 5, 4, 6, 7]

def axes(s, p, xt, yt):
    p.ygrid(yt, "{}"); p.baseline()
    for x in xt:
        s.text(p.sx(x), p.box[3] + 16, str(x), 11, INK2, "middle")

# 28: scatter with mean quadrants
s = Svg(480, 310); s.text(16, 26, "散布図：平均の線で4つに分けると、点は右上と左下に集まる", 14, INK, weight="bold")
p = Plot(s, 44, 50, 464, 226, 0.5, 5.5, 2, 8)
axes(s, p, X, [2, 4, 6, 8])
s.rect(p.sx(3), p.sy(8), p.sx(5.5) - p.sx(3), p.sy(5) - p.sy(8), ORANGE, 0, None, 0.08)
s.rect(p.sx(0.5), p.sy(5), p.sx(3) - p.sx(0.5), p.sy(2) - p.sy(5), ORANGE, 0, None, 0.08)
s.line(p.sx(3), 50, p.sx(3), 226, INK2, 1.5, "5 3"); s.line(44, p.sy(5), 464, p.sy(5), INK2, 1.5, "5 3")
s.text(p.sx(3) + 4, 62, "xの平均＝3", 11, INK2); s.text(460, p.sy(5) - 5, "yの平均＝5", 11, INK2, "end")
s.text(p.sx(5.2), p.sy(7.7), "積＋", 12, ORANGE, "middle", "bold"); s.text(p.sx(0.8), p.sy(2.4), "積＋", 12, ORANGE, "middle", "bold")
s.text(p.sx(0.8), p.sy(7.7), "積−", 12, INK2, "middle"); s.text(p.sx(5.2), p.sy(2.4), "積−", 12, INK2, "middle")
for x, y in zip(X, Y):
    s.circle(p.sx(x), p.sy(y), 7, BLUE, BG, 2)
    s.text(p.sx(x) + 10, p.sy(y) - 8, f"({x},{y})", 10, INK2)
s.text(16, 266, "偏差の積：(−2)(−2)＋(−1)(0)＋(0)(−1)＋(1)(1)＋(2)(2)＝9", 12, INK2)
s.text(16, 284, "r＝9/√(10×10)＝0.9 → 強い正の相関", 12, INK2)
s.text(16, 302, "横軸 x＝広告回数、縦軸 y＝来店者数（架空）", 11, INK2)
out["c28"] = s.svg()

# 29: regression with residuals
s = Svg(480, 280); s.text(16, 26, "回帰直線（予測値）＝2.3＋0.9x と残差（縦の線）", 15, INK, weight="bold")
p = Plot(s, 44, 50, 464, 226, 0.5, 5.5, 2, 8)
axes(s, p, X, [2, 4, 6, 8])
s.line(p.sx(0.5), p.sy(2.3 + 0.45), p.sx(5.5), p.sy(2.3 + 0.9 * 5.5), ORANGE, 2.5)
for x, y in zip(X, Y):
    yh = 2.3 + 0.9 * x
    s.line(p.sx(x), p.sy(y), p.sx(x), p.sy(yh), RED, 2)
    s.circle(p.sx(x), p.sy(y), 7, BLUE, BG, 2)
    e = y - yh
    lab = f"e＝{e:+.1f}".replace("+", "＋").replace("-", "−")
    ty = p.sy(y) - 12 if e > 0 else p.sy(y) + 20
    s.text(p.sx(x), ty, lab, 11, RED, "middle", "bold")
s.text(p.sx(1.0), p.sy(7.6), "残差の2乗和 SSE＝1.9 が最小になる直線", 12, ORANGE, "start", "bold")
s.text(16, 256, "x＝3 の予測値は 5.0（平均の点 (3,5) を必ず通る）", 12, INK2)
s.text(16, 274, "R²＝1−1.9/10＝0.81", 12, INK2)
out["c29"] = s.svg()

# 30: SST decomposition stacked bar
s = Svg(480, 230); s.text(16, 26, "全体の変動 300 ＝ 回帰で説明 180 ＋ 残差 120", 15, INK, weight="bold")
x0, x1 = 30, 450; w = x1 - x0
y = 60; h = 50
s.rect(x0, y, w * 180 / 300 - 1, h, BLUE, 4); s.rect(x0 + w * 180 / 300 + 1, y, w * 120 / 300 - 1, h, MUTED, 4)
s.text(x0 + w * 0.3, y + 31, "SSR 180（60%）", 14, "#fff", "middle", "bold")
s.text(x0 + w * 0.8, y + 31, "SSE 120（40%）", 14, INK, "middle", "bold")
s.line(x0, y + h + 14, x1, y + h + 14, INK2, 1.5); s.line(x0, y + h + 8, x0, y + h + 20, INK2, 1.5); s.line(x1, y + h + 8, x1, y + h + 20, INK2, 1.5)
s.text((x0 + x1) / 2, y + h + 34, "SST 300（自由度19）", 12, INK2, "middle")
s.text(16, 172, "R²＝180/300＝0.6（＝1−120/300）", 13, INK, weight="bold")
s.text(16, 194, "F＝(180/2)÷(120/17)＝90÷7.06≈12.75", 12, INK2)
s.text(16, 214, "調整済みR²＝1−0.4×19/17≈0.553（変数の数で割り引く）", 12, INK2)
out["c30"] = s.svg()

# 31: stratified weighting as areas
s = Svg(480, 290); s.text(16, 26, "層の大きさで重みを付ける：全体平均は80（125ではない）", 14, INK, weight="bold")
p = Plot(s, 50, 50, 464, 226, 0, 1, 0, 220)
p.ygrid([0, 50, 100, 150, 200], "{}"); p.baseline()
s.rect(p.sx(0), p.sy(200), p.sx(0.2) - p.sx(0) - 1, p.sy(0) - p.sy(200), ORANGE, 2, None, 0.85)
s.rect(p.sx(0.2) + 1, p.sy(50), p.sx(1) - p.sx(0.2) - 1, p.sy(0) - p.sy(50), BLUE, 2, None, 0.85)
s.text((p.sx(0) + p.sx(0.2)) / 2, p.sy(200) + 20, "大規模", 12, "#fff", "middle", "bold")
s.text((p.sx(0) + p.sx(0.2)) / 2, p.sy(200) + 36, "20店", 11, "#fff", "middle")
s.text((p.sx(0) + p.sx(0.2)) / 2, p.sy(200) + 52, "平均200", 11, "#fff", "middle")
s.text((p.sx(0.2) + p.sx(1)) / 2, p.sy(25) + 5, "小規模 80店・平均50", 12, "#fff", "middle", "bold")
s.line(p.sx(0), p.sy(80), p.sx(1), p.sy(80), INK, 2, "6 4"); s.text(p.sx(0.98), p.sy(80) - 6, "加重平均 80 ○", 12, INK, "end", "bold")
s.line(p.sx(0), p.sy(125), p.sx(1), p.sy(125), RED, 1.5, "3 3"); s.text(p.sx(0.98), p.sy(125) - 6, "無重みの平均 125 ×", 12, RED, "end", "bold")
s.text(p.sx(0.1), 242, "20%", 11, INK2, "middle"); s.text(p.sx(0.6), 242, "80%", 11, INK2, "middle")
s.text(16, 266, "0.2×200＋0.8×50＝80。横幅＝層の構成比、高さ＝層の平均", 12, INK2)
s.text(16, 284, "面積の合計を全体の幅でならした高さが全体平均", 12, INK2)
out["c31"] = s.svg()

# 32: dot plot A/B/C
s = Svg(480, 290); s.text(16, 26, "群間のばらつき（平均の違い）と群内のばらつき", 15, INK, weight="bold")
p = Plot(s, 44, 50, 464, 226, 0, 3, 0, 8)
p.ygrid([0, 2, 4, 6, 8], "{}"); p.baseline()
s.line(44, p.sy(4), 464, p.sy(4), INK, 1.5, "6 4"); s.text(48, p.sy(4) - 6, "全体平均 4", 11, INK, "start", "bold")
groups = [("A", [1, 3], BLUE), ("B", [3, 5], AQUA), ("C", [5, 7], ORANGE)]
for i, (g, vals, c) in enumerate(groups):
    xc = i + 0.5; m = sum(vals) / 2
    s.line(p.sx(xc) - 34, p.sy(m), p.sx(xc) + 34, p.sy(m), c, 3)
    s.text(p.sx(xc) + 38, p.sy(m) - 6, f"平均{m:g}", 11, c, "start", "bold")
    for v in vals:
        s.line(p.sx(xc) - 10, p.sy(v), p.sx(xc) - 10, p.sy(m), c, 1.5, "3 2")
        s.circle(p.sx(xc) - 10, p.sy(v), 7, c, BG, 2)
    if m != 4:
        s.arrow(p.sx(xc) + 14, p.sy(4), p.sx(xc) + 14, p.sy(m) + (4 if m > 4 else -4), INK2, 1.5)
p.xlabels([(i + 0.5, f"施策{g}") for i, (g, _, _) in enumerate(groups)])
s.text(16, 262, "矢印（平均→群平均）＝群間 SS_B＝16、点線（点→群平均）＝群内 SS_W＝6", 11, INK2)
s.text(16, 280, "F＝(16/2)÷(6/3)＝4 ＜ F(2,3)の5%点 9.552 → 有意でない", 12, INK2)
out["c32"] = s.svg()

import json; json.dump(out, open("g6.json", "w"), ensure_ascii=False)
for k, v in out.items():
    open(f"{k}.svg", "w").write(v); print(k, len(v.encode()))
