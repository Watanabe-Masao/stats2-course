import sys, math
sys.path.insert(0, ".")
from svgkit import *
out = {}

# 10: Venn
s = Svg(480, 270); s.text(16, 26, "サイコロ：A＝偶数、B＝4以上", 15, INK, weight="bold")
s.rect(20, 42, 440, 196, "#f4f3ef", 8, INK2)
s.text(452, 230, "標本空間 Ω＝{1,…,6}", 11, INK2, "end")
s.circle(190, 140, 78, BLUE, BLUE, 2, opacity=0.15)
s.circle(290, 140, 78, ORANGE, ORANGE, 2, opacity=0.15)
s.text(100, 66, "A（偶数）", 13, BLUE, "middle", "bold"); s.text(380, 66, "B（4以上）", 13, ORANGE, "middle", "bold")
s.text(150, 146, "2", 22, INK, "middle", "bold")
s.text(240, 134, "4", 22, INK, "middle", "bold"); s.text(240, 162, "6", 22, INK, "middle", "bold")
s.text(330, 146, "5", 22, INK, "middle", "bold")
s.text(52, 200, "1", 20, INK2, "middle"); s.text(430, 200, "3", 20, INK2, "middle")
s.text(240, 228, "A∩B", 11, INK2, "middle")
s.text(16, 260, "A∪B＝{2,4,5,6}：3＋3−2＝4 個 → 確率 4/6", 12, INK2)
out["c10"] = s.svg()

# 11: tree without replacement
s = Svg(480, 290); s.text(16, 26, "赤2・青3の袋から戻さず2回引く", 15, INK, weight="bold")
root = (40, 145)
first = [("赤", 2, 5, 90, RED), ("青", 3, 5, 200, BLUE)]
s.circle(*root, 6, INK2)
for name, a, b, y, c in first:
    s.line(root[0], root[1], 170, y, c, 2.5 if name == "赤" else 1.5)
    s.text(105, (root[1] + y) / 2 - 6, f"{a}/{b}", 13, c, "middle", "bold")
    s.rect(150, y - 14, 40, 28, BG, 6, c); s.text(170, y + 5, name, 13, c, "middle", "bold")
    rem_r = 1 if name == "赤" else 2
    for name2, n2, y2, c2 in [("赤", rem_r, y - 40, RED), ("青", 4 - rem_r, y + 40, BLUE)]:
        hl = name == "赤" and name2 == "赤"
        s.line(190, y, 310, y2, c2, 2.5 if hl else 1.5)
        s.text(250, (y + y2) / 2 - 6, f"{n2}/4", 13, c2, "middle", "bold")
        s.rect(310, y2 - 13, 40, 26, BG, 6, c2); s.text(330, y2 + 5, name2, 13, c2, "middle", "bold")
        num = (a * n2); s.text(362, y2 + 5, f"{a}/5×{n2}/4＝{num}/20", 12, INK if hl else INK2, "start", "bold" if hl else None)
s.text(16, 282, "2個目の確率は1個目の結果で変わる（分母が5→4）＝独立ではない", 12, INK2)
out["c11"] = s.svg()

# 12: frequency tree for Bayes
s = Svg(480, 290); s.text(16, 26, "1000個で考える：検出された67個のうち不良は18個", 15, INK, weight="bold")
def box(x, y, w, t1, t2, c, fill=BG):
    s.rect(x, y, w, 40, fill, 8, c); s.text(x + w / 2, y + 17, t1, 12, INK, "middle", "bold"); s.text(x + w / 2, y + 33, t2, 11, INK2, "middle")
box(180, 44, 120, "全体 1000個", "", INK2)
box(40, 120, 150, "不良 20個", "不良率 2%", RED)
box(290, 120, 150, "良品 980個", "98%", BLUE)
s.line(240, 84, 115, 120, INK2, 1.5); s.line(240, 84, 365, 120, INK2, 1.5)
box(16, 210, 100, "検出 18", "90%", RED, "#fdecec")
box(124, 210, 76, "見逃し 2", "10%", INK2)
box(270, 210, 90, "誤検出 49", "5%", ORANGE, "#fdf1ea")
box(368, 210, 96, "通過 931", "95%", INK2)
for x1, x2 in [(115, 66), (115, 162), (365, 315), (365, 416)]:
    s.line(x1, 160, x2, 210, INK2, 1.5)
s.text(16, 276, "P(不良｜検出)＝18÷(18＋49)＝18/67 ≈ 26.9%", 13, INK, weight="bold")
out["c12"] = s.svg()

# 15: Poisson lambda=2
lam = 2; ks = range(0, 8); pk = [math.exp(-lam) * lam ** k / math.factorial(k) for k in ks]
s = Svg(480, 270); s.text(16, 26, "1時間あたりの問い合わせ件数：ポアソン分布 λ＝2", 15, INK, weight="bold")
p = Plot(s, 44, 50, 464, 222, -0.5, 7.5, 0, 0.32)
p.ygrid([0, 0.1, 0.2, 0.3], "{:.1f}"); p.baseline()
for k, v in zip(ks, pk):
    p.bar(k, 0.62, v, ORANGE if k == 0 else BLUE)
    s.text(p.sx(k), p.sy(v) - 5, f"{v:.3f}", 11, INK, "middle")
p.xlabels([(k, f"{k}件") for k in ks])
s.text(16, 262, "0件の確率 e^(−2)≈0.135。平均も分散も λ＝2", 12, INK2)
out["c15"] = s.svg()

# 16: normal shaded 90-110
mu, sd = 100, 10
s = Svg(480, 260); s.text(16, 26, "N(100, 10²)：90〜110 の確率＝色の面積", 15, INK, weight="bold")
p = Plot(s, 20, 44, 460, 210, 65, 135, 0, npdf(0) / sd * 1.12)
p.fill_under(lambda x: npdf(x, mu, sd), 90, 110, color=BLUE, opacity=0.35)
p.curve(lambda x: npdf(x, mu, sd), 65, 135, color=BLUE); p.baseline()
for x in [70, 80, 90, 100, 110, 120, 130]:
    s.text(p.sx(x), 228, str(x), 11, INK2, "middle")
for x, z in [(90, "z＝−1"), (110, "z＝＋1")]:
    s.line(p.sx(x), p.sy(npdf(x, mu, sd)), p.sx(x), p.sy(0), BLUE, 1.5, "4 3")
    s.text(p.sx(x), 244, z, 11, BLUE, "middle")
s.text(p.sx(100), p.sy(npdf(100, mu, sd) * 0.45), "約68.3%", 15, INK, "middle", "bold")
out["c16"] = s.svg()

import json; json.dump(out, open("g2.json", "w"), ensure_ascii=False)
for k, v in out.items():
    open(f"{k}.svg", "w").write(v); print(k, len(v.encode()))
print([round(v, 4) for v in pk])
