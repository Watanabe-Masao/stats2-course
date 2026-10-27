import sys, statistics as st
sys.path.insert(0, ".")
from svgkit import *

out = {}

# 01: base changes
s = Svg(480, 280); s.text(16, 26, "20%増やしてから20%減らすと元に戻らない", 15, INK, weight="bold")
p = Plot(s, 50, 50, 464, 236, 0, 3, 0, 1300)
p.ygrid([0, 400, 800, 1200]); p.baseline()
vals = [(0.5, 1000, MUTED, "元の値段"), (1.5, 1200, BLUE, "20%増"), (2.5, 960, ORANGE, "そこから20%減")]
for x, v, c, lab in vals:
    p.bar(x, 0.55, v, c); s.text(p.sx(x), p.sy(v) - 6, f"{v}", 14, INK, "middle", "bold")
p.xlabels([(x, lab) for x, v, c, lab in vals])
s.text(p.sx(1.0), p.sy(1250), "×1.2", 13, INK2, "middle"); s.text(p.sx(2.0), p.sy(1250), "×0.8", 13, INK2, "middle")
s.text(16, 270, "減らすときの基準は1000ではなく1200 → 1000×1.2×0.8＝960", 12, INK2)
out["c01"] = s.svg()

# 03: population vs sample
s = Svg(480, 250); s.text(16, 26, "母集団から標本を取り、標本から母集団を推測する", 15, INK, weight="bold")
s.circle(130, 140, 92, LIGHT, BLUE, 2); s.text(130, 76, "母集団（全100店舗）", 12, INK, "middle", "bold")
s.text(130, 192, "母数 μ（本当の平均）", 12, INK2, "middle"); s.text(130, 208, "＝ふつうは分からない", 11, INK2, "middle")
import random; random.seed(3)
for i in range(60):
    import math as m
    r = 62 * m.sqrt(random.random()); a = random.random() * 6.283
    s.circle(130 + r * m.cos(a), 128 + r * m.sin(a) * 0.6, 3, MUTED)
for (x, y) in [(110, 118), (150, 124), (125, 146), (95, 132), (160, 145), (135, 104), (100, 150), (145, 156), (118, 130), (170, 130)]:
    s.circle(x, y, 4.5, ORANGE)
s.circle(370, 140, 62, "#fdf1ea", ORANGE, 2); s.text(370, 112, "標本（10店舗）", 13, INK, "middle", "bold")
s.text(370, 140, "統計量 x̄", 13, INK, "middle"); s.text(370, 158, "（標本の平均）", 11, INK2, "middle")
s.arrow(228, 110, 302, 118, ORANGE, 2); s.text(265, 100, "抽出", 12, ORANGE, "middle")
s.arrow(302, 170, 228, 172, BLUE, 2); s.text(265, 192, "推測", 12, BLUE, "middle")
s.text(16, 244, "x̄ は標本を取り直すと変わる。μ は固定だが未知。", 12, INK2)
out["c03"] = s.svg()

# 05: histogram + box plot
data = [12, 15, 18, 19, 21, 22, 22, 24, 25, 26, 27, 28, 29, 30, 31, 33, 35, 38, 42, 55]
s = Svg(480, 340); s.text(16, 26, "20日分の売上（万円）：ヒストグラムと箱ひげ図", 15, INK, weight="bold")
p = Plot(s, 44, 48, 464, 210, 10, 60, 0, 10)
p.ygrid([0, 2, 4, 6, 8]); p.baseline()
counts = [4, 9, 5, 1, 1]
for i, c in enumerate(counts):
    x0 = 10 + 10 * i
    s.rect(p.sx(x0) + 1, p.sy(c), p.sx(x0 + 10) - p.sx(x0) - 2, p.sy(0) - p.sy(c), BLUE, 2)
    s.text((p.sx(x0) + p.sx(x0 + 10)) / 2, p.sy(c) - 5, f"{c}日", 12, INK, "middle")
s.text(16, 44, "日数", 11, INK2)
q1, med, q3 = 21.5, 26.5, 32
yb = 262
s.line(p.sx(12), yb, p.sx(q1), yb, INK2, 1.5); s.line(p.sx(q3), yb, p.sx(42), yb, INK2, 1.5)
s.line(p.sx(12), yb - 8, p.sx(12), yb + 8, INK2, 1.5); s.line(p.sx(42), yb - 8, p.sx(42), yb + 8, INK2, 1.5)
s.rect(p.sx(q1), yb - 14, p.sx(q3) - p.sx(q1), 28, LIGHT, 2, BLUE)
s.line(p.sx(med), yb - 14, p.sx(med), yb + 14, ORANGE, 2.5)
s.circle(p.sx(55), yb, 5, "none", RED, 2); s.text(p.sx(55), yb - 12, "外れ値 55", 11, RED, "middle")
for x, lab in [(10, "10"), (20, "20"), (30, "30"), (40, "40"), (50, "50"), (60, "60")]:
    s.text(p.sx(x), 312, lab, 11, INK2, "middle")
s.text(p.sx(q1) - 2, yb + 28, "Q1 21.5", 11, BLUE, "end"); s.text(p.sx(med), yb - 20, "中央値 26.5", 11, ORANGE, "middle")
s.text(p.sx(q3) + 2, yb + 28, "Q3 32", 11, BLUE, "start")
s.text(16, 332, "箱＝真ん中50%（IQR 10.5）、ひげの外の点＝外れ値候補", 12, INK2)
out["c05"] = s.svg()

# 06: skewed: mean vs median (dot plot)
vals = [1, 1, 2, 2, 2, 3, 3, 4, 5, 17]
s = Svg(480, 250); s.text(16, 26, "10人の購入額（千円）：平均は大きな値に引っ張られる", 15, INK, weight="bold")
p = Plot(s, 30, 50, 464, 190, 0, 18, 0, 4)
p.baseline()
from collections import Counter
for v, c in Counter(vals).items():
    for k in range(c):
        s.circle(p.sx(v), p.sy(0) - 12 - 22 * k, 9, BLUE)
for x in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]:
    s.text(p.sx(x), 208, str(x), 11, INK2, "middle")
mean, medn = st.mean(vals), st.median(vals)
s.line(p.sx(medn), 56, p.sx(medn), p.sy(0), AQUA, 2.5, "5 3"); s.text(p.sx(medn) - 4, 66, f"中央値 {medn}", 12, AQUA, "end", "bold")
s.line(p.sx(mean), 56, p.sx(mean), p.sy(0), ORANGE, 2.5); s.text(p.sx(mean) + 4, 66, f"平均 {mean:g}", 12, ORANGE, "start", "bold")
s.text(p.sx(17), p.sy(0) - 34, "1人だけ17", 11, INK2, "middle")
s.text(16, 236, "最頻値2・中央値2.5・平均4。典型的な人は中央値に近い。", 12, INK2)
out["c06"] = s.svg()

# 07: same mean, different spread
A = [8, 9, 10, 11, 12]; B = [4, 7, 10, 13, 16]
s = Svg(480, 250); s.text(16, 26, "平均はどちらも10。散らばりが違う", 15, INK, weight="bold")
p = Plot(s, 70, 40, 464, 200, 2, 18, 0, 2)
for row, (name, d, c) in enumerate([("売場A", A, BLUE), ("売場B", B, ORANGE)]):
    y = 85 + row * 70
    s.line(p.sx(2), y, p.sx(18), y, GRID, 1)
    s.text(16, y + 4, name, 13, INK, weight="bold")
    for v in d:
        s.line(p.sx(10), y, p.sx(v), y, c, 1.5, "3 3") if v != 10 else None
        s.circle(p.sx(v), y, 7, c)
    ss = sum((v - 10) ** 2 for v in d)
    s.text(p.sx(18), y + 26, f"偏差平方和 {ss}・不偏分散 {ss/4:g}", 11, INK2, "end")
s.line(p.sx(10), 55, p.sx(10), 190, INK2, 1.5, "4 3"); s.text(p.sx(10), 52, "平均 10", 11, INK2, "middle")
for x in [2, 6, 10, 14, 18]:
    s.text(p.sx(x), 222, str(x), 11, INK2, "middle")
s.text(16, 244, "点線＝平均からの距離（偏差）。これを2乗して足す。", 12, INK2)
out["c07"] = s.svg()

# 08: z-scores on two scales
s = Svg(480, 290); s.text(16, 26, "物差しが違っても z でそろえると同じ位置", 15, INK, weight="bold")
rows = [("店舗A：平均50・SD10", 50, 10, 70, BLUE), ("店舗B：平均80・SD5", 80, 5, 90, ORANGE)]
for i, (name, mu, sd, x, c) in enumerate(rows):
    top = 46 + i * 118
    p = Plot(s, 30, top + 18, 464, top + 84, mu - 3.3 * sd, mu + 3.3 * sd, 0, npdf(0) / sd * 1.1)
    p.fill_under(lambda t: npdf(t, mu, sd), mu - 3.3 * sd, mu + 3.3 * sd, color=c, opacity=0.12)
    p.curve(lambda t: npdf(t, mu, sd), mu - 3.3 * sd, mu + 3.3 * sd, color=c)
    p.baseline()
    s.text(30, top + 12, name, 13, INK, weight="bold")
    for k in range(-3, 4):
        s.text(p.sx(mu + k * sd), top + 100, f"{mu + k * sd:g}", 10, INK2, "middle")
    s.line(p.sx(x), top + 18, p.sx(x), p.sy(0), INK, 2); s.text(p.sx(x) + 4, top + 32, f"{x} → z＝2", 12, INK, "start", "bold")
out["c08"] = s.svg()

import json; json.dump(out, open("g1.json", "w"), ensure_ascii=False)
for k, v in out.items():
    open(f"{k}.svg", "w").write(v); print(k, len(v.encode()))
