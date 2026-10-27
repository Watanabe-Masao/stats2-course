import sys, math, random
sys.path.insert(0, ".")
from svgkit import *
out = {}

def chi(x, k):
    if x <= 0: return 0
    return x ** (k / 2 - 1) * math.exp(-x / 2) / (2 ** (k / 2) * math.gamma(k / 2))

# 21: n-divided vs (n-1)-divided variance estimators, sigma^2=4, n=5
s = Svg(480, 280); s.text(16, 26, "推定量の分布（母分散 σ²＝4、n＝5 を何度も繰り返す）", 15, INK, weight="bold")
p = Plot(s, 20, 56, 460, 222, 0, 14, 0, 0.24)
fs = lambda x: chi(x, 4)                 # s^2 = sigma^2/(n-1) * chi2(4) = chi2(4)
fv = lambda x: chi(x / 0.8, 4) / 0.8     # v = 0.8 s^2
p.fill_under(fv, 0.01, 14, color=ORANGE, opacity=0.12); p.curve(fv, 0.01, 14, color=ORANGE, width=2.5)
p.fill_under(fs, 0.01, 14, color=BLUE, opacity=0.12); p.curve(fs, 0.01, 14, color=BLUE); p.baseline()
for x in [0, 2, 4, 6, 8, 10, 12, 14]:
    s.text(p.sx(x), 240, str(x), 11, INK2, "middle")
s.line(p.sx(4), 52, p.sx(4), p.sy(0), INK, 2); s.text(p.sx(4) + 4, 52, "真の σ²＝4", 12, INK, "start", "bold")
s.line(p.sx(3.2), 70, p.sx(3.2), p.sy(0), ORANGE, 1.5, "4 3")
s.text(p.sx(6.5), p.sy(0.17), "nで割る v：平均3.2（小さめに偏る）", 12, ORANGE, "start", "bold")
s.text(p.sx(7.2), p.sy(0.10), "n−1で割る s²：平均4（不偏）", 12, BLUE, "start", "bold")
s.text(16, 270, "不偏でも1回ごとの値は大きくばらつく（偏り と ばらつき は別）", 12, INK2)
out["c21"] = s.svg()

# 22: 20 confidence intervals
random.seed(7)
mu, se = 50, 1
while True:
    xs = [random.gauss(mu, se) for _ in range(20)]
    miss = [abs(x - mu) > 1.96 * se for x in xs]
    if sum(miss) == 1: break
s = Svg(480, 330); s.text(16, 26, "95%信頼区間を20回つくると、約1本が μ を外す", 15, INK, weight="bold")
p = Plot(s, 30, 50, 464, 290, 45.5, 54.5, 0, 21)
s.line(p.sx(mu), 46, p.sx(mu), 290, INK, 2, "5 3"); s.text(p.sx(mu), 44, "真の μ＝50（固定・未知）", 11, INK, "middle", "bold")
for i, (x, m) in enumerate(zip(xs, miss)):
    y = p.sy(20 - i)
    c = RED if m else BLUE
    s.line(p.sx(x - 1.96), y, p.sx(x + 1.96), y, c, 3 if m else 2)
    s.circle(p.sx(x), y, 3.5, c)
    if m: s.text(max(p.sx(x + 1.96), p.sx(mu)) + 8, y + 4, "外した1本", 11, RED, "start", "bold")
for x in [46, 48, 50, 52, 54]:
    s.text(p.sx(x), 306, str(x), 11, INK2, "middle")
s.text(16, 324, "動くのは区間の方。1本ごとに「当たり/外れ」は決まっている", 12, INK2)
out["c22"] = s.svg()

# 23: chi2(9) with 2.5% tails
k = 9
s = Svg(480, 270); s.text(16, 26, "χ²(9)：左右2.5%の点は 2.700 と 19.023（非対称）", 15, INK, weight="bold")
p = Plot(s, 20, 50, 460, 214, 0, 26, 0, 0.115)
p.fill_under(lambda x: chi(x, k), 0.01, 2.7, color=ORANGE, opacity=0.45)
p.fill_under(lambda x: chi(x, k), 19.023, 26, color=ORANGE, opacity=0.45)
p.fill_under(lambda x: chi(x, k), 2.7, 19.023, color=BLUE, opacity=0.12)
p.curve(lambda x: chi(x, k), 0.01, 26, n=60, color=BLUE); p.baseline()
for x in [0, 5, 10, 15, 20, 25]:
    s.text(p.sx(x), 230, str(x), 11, INK2, "middle")
for x, lab in [(2.7, "2.700"), (19.023, "19.023")]:
    s.line(p.sx(x), p.sy(0), p.sx(x), p.sy(0.05), ORANGE, 1.5, "4 3")
    s.text(p.sx(x), p.sy(0.05) - 4, lab, 12, ORANGE, "middle", "bold")
s.text(p.sx(9), p.sy(0.06), "95%", 15, INK, "middle", "bold")
s.text(p.sx(1.3), p.sy(0.0) - 6, "", 10, INK2)
s.text(16, 248, "(n−1)s²＝36 を両端で割る → 36/19.023〜36/2.700", 12, INK2)
s.text(16, 264, "＝ 1.892〜13.333（s²＝4 は真ん中ではない）", 12, INK2)
out["c23"] = s.svg()

import json; json.dump(out, open("g4.json", "w"), ensure_ascii=False)
for k2, v in out.items():
    open(f"{k2}.svg", "w").write(v); print(k2, len(v.encode()))
print([round(x, 2) for x in xs])
