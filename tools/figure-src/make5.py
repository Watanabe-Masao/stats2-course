import sys, math
sys.path.insert(0, ".")
from svgkit import *
out = {}

def tpdf(x, v):
    c = math.gamma((v + 1) / 2) / (math.sqrt(v * math.pi) * math.gamma(v / 2))
    return c * (1 + x * x / v) ** (-(v + 1) / 2)

def two_sided(title, f, crit, stat, statlab, foot1, foot2, pcol):
    s = Svg(480, 290); s.text(16, 26, title, 15, INK, weight="bold")
    p = Plot(s, 20, 56, 460, 222, -4, 4, 0, 0.44)
    for a, b in [(-4, -crit), (crit, 4)]:
        p.fill_under(f, a, b, color=RED, opacity=0.18)
    if stat is not None and abs(stat) > crit:
        for a, b in [(-4, -abs(stat)), (abs(stat), 4)]:
            p.fill_under(f, a, b, color=pcol, opacity=0.75)
    p.curve(f, -4, 4, color=BLUE); p.baseline()
    for x in range(-4, 5):
        s.text(p.sx(x), 240, str(x), 11, INK2, "middle")
    for x in (-crit, crit):
        s.line(p.sx(x), p.sy(0), p.sx(x), p.sy(0.2), RED, 1.5, "4 3")
        lab = (f"{crit:.3f}" if crit != 1.96 else "1.96"); lab = ("＋" if x > 0 else "−") + lab
        right = (x < 0) or (stat < crit)
        s.text(p.sx(x) + (4 if right else -4), p.sy(0.2) + 4, lab, 11, RED, "start" if right else "end", "bold")
    s.text(p.sx(-3.3), p.sy(0.06), "棄却域", 11, RED, "middle"); s.text(p.sx(3.3), p.sy(0.06), "棄却域", 11, RED, "middle")
    s.line(p.sx(stat), 56, p.sx(stat), p.sy(0), INK, 2.5)
    s.text(p.sx(stat) + (5 if stat < 3 else -5), 68, statlab, 12, INK, "start" if stat < 3 else "end", "bold")
    s.text(16, 264, foot1, 12, INK2); s.text(16, 282, foot2, 12, INK2)
    return s.svg()

# 24
out["c24"] = two_sided("両側検定：z＝2.2 は棄却域（|z|＞1.96）に入る", npdf, 1.96, 2.2, "z＝2.2",
                       "薄い赤＝棄却域（両側合計5%）、濃い色＝p値（両側合計約0.028）",
                       "p≈0.028 ≤ α＝0.05 → H0を棄却", ORANGE)
# 25
out["c25"] = two_sided("t(15)：t＝2 は ±2.131 の内側 → 棄却しない", lambda x: tpdf(x, 15), 2.131, 2.0, "t＝2.0",
                       "薄い赤＝棄却域（両側5%）。t＝2は届いていない",
                       "平均104でも、16店舗の散らばりでは偶然の範囲", ORANGE)

# 26: two proportions with pooled line
s = Svg(480, 280); s.text(16, 26, "2群の購入率：差10ポイントでも z≈−1.63（有意でない）", 15, INK, weight="bold")
p = Plot(s, 50, 50, 464, 220, 0, 2, 0, 0.4)
p.ygrid([0, 0.1, 0.2, 0.3, 0.4], "{:.0%}".replace("%", "%")); p.baseline()
for x, v, c, lab in [(0.5, 0.20, BLUE, "A店（20/100）"), (1.5, 0.30, ORANGE, "B店（30/100）")]:
    p.bar(x, 0.5, v, c); s.text(p.sx(x), p.sy(v) - 6, f"{v:.0%}", 14, INK, "middle", "bold")
p.xlabels([(0.5, "A店（20/100）"), (1.5, "B店（30/100）")])
s.line(p.sx(0.05), p.sy(0.25), p.sx(1.95), p.sy(0.25), INK, 1.5, "6 4")
s.text(p.sx(0.55), p.sy(0.25) - 6, "H0の共通比率 p_pool＝50/200＝25%", 11, INK, "middle", "bold")
s.text(16, 260, "SE＝√(0.25×0.75×(1/100＋1/100))≈0.0612", 12, INK2)
s.text(16, 276, "z＝(0.20−0.30)/0.0612≈−1.63 → |z|＜1.96", 12, INK2)
out["c26"] = s.svg()

# 27: observed vs expected
s = Svg(480, 280); s.text(16, 26, "観測度数 O と 期待度数 E（独立なら全セル25）", 15, INK, weight="bold")
p = Plot(s, 44, 50, 464, 214, 0, 4, 0, 36)
p.ygrid([0, 10, 20, 30], "{}"); p.baseline()
cells = [("A・あり", 30), ("A・なし", 20), ("B・あり", 20), ("B・なし", 30)]
for i, (lab, o) in enumerate(cells):
    x = i + 0.5
    p.bar(x, 0.5, o, ORANGE if o > 25 else BLUE)
    s.text(p.sx(x), p.sy(o) - 6, f"{o}", 13, INK, "middle", "bold")
    s.text(p.sx(x), p.sy(o) + 16 if o > 25 else p.sy(25) - 6, f"{'+' if o > 25 else '−'}5", 11, "#fff" if o > 25 else INK2, "middle", "bold")
p.xlabels([(i + 0.5, c[0]) for i, c in enumerate(cells)])
s.line(p.sx(0.05), p.sy(25), p.sx(3.95), p.sy(25), INK, 1.5, "6 4")
s.text(p.sx(1.0), p.sy(25) - 6, "E＝25", 11, INK, "middle", "bold")
s.text(16, 256, "各セル (O−E)²/E＝25/25＝1 → χ²＝1×4＝4", 12, INK2)
s.text(16, 272, "自由度1の基準3.841を超える → 独立とは言いにくい", 12, INK2)
out["c27"] = s.svg()

import json; json.dump(out, open("g5.json", "w"), ensure_ascii=False)
for k, v in out.items():
    open(f"{k}.svg", "w").write(v); print(k, len(v.encode()))
from statistics import NormalDist
N = NormalDist()
print(2 * (1 - N.cdf(2.2)), 2 * (1 - N.cdf(2.5)), (0.2 - 0.3) / math.sqrt(0.25 * 0.75 * 0.02))
