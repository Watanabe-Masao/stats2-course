import sys, math
sys.path.insert(0, ".")
from svgkit import *
out = {}

# 17: population / frame / sample
s = Svg(480, 270); s.text(16, 26, "母集団・抽出枠・標本：枠から漏れた所は選ばれない", 15, INK, weight="bold")
s.rect(20, 44, 440, 190, LIGHT, 10, BLUE); s.text(32, 64, "母集団：対象の全店舗（105店）", 13, BLUE, weight="bold")
s.rect(40, 76, 300, 146, "#f4f3ef", 8, INK2); s.text(52, 96, "抽出枠：店舗台帳（100店）", 12, INK, weight="bold")
s.rect(150, 118, 150, 84, "#fdf1ea", 8, ORANGE); s.text(225, 152, "標本", 14, ORANGE, "middle", "bold"); s.text(225, 172, "無作為に10店", 12, INK2, "middle")
s.text(100, 150, "各店の", 11, INK2, "middle"); s.text(100, 166, "確率 10/100", 11, INK2, "middle"); s.text(100, 182, "＝0.1", 11, INK2, "middle")
for i in range(5):
    s.circle(370 + (i % 3) * 26, 130 + (i // 3) * 30, 8, RED, None, opacity=0.85)
s.text(396, 196, "新店5店", 12, RED, "middle", "bold"); s.text(396, 212, "台帳に無い→確率0", 11, RED, "middle")
s.text(16, 260, "無作為化しても、枠の漏れ（カバー誤差）は直らない", 12, INK2)
out["c17"] = s.svg()

# 18: sampling distribution n=9 vs 36
mu, sig = 50, 12
s = Svg(480, 280); s.text(16, 26, "標本平均 x̄ の分布：n を4倍にすると幅は半分", 15, INK, weight="bold")
p = Plot(s, 20, 50, 460, 222, 14, 86, 0, npdf(0) / 2 * 1.1)
p.curve(lambda x: npdf(x, mu, sig), 14, 86, color=MUTED, dash="5 4")
p.fill_under(lambda x: npdf(x, mu, 4), 14, 86, color=BLUE, opacity=0.12)
p.curve(lambda x: npdf(x, mu, 4), 14, 86, color=BLUE)
p.fill_under(lambda x: npdf(x, mu, 2), 38, 62, color=ORANGE, opacity=0.15)
p.curve(lambda x: npdf(x, mu, 2), 38, 62, color=ORANGE); p.baseline()
for x in [20, 30, 40, 50, 60, 70, 80]:
    s.text(p.sx(x), 240, str(x), 11, INK2, "middle")
s.text(p.sx(55.5), p.sy(npdf(0) / 2 * 0.9), "n＝36：SE＝12/√36＝2", 12, ORANGE, "start", "bold")
s.text(p.sx(58), p.sy(0.062), "n＝9：SE＝12/√9＝4", 12, BLUE, "start", "bold")
s.text(p.sx(15), p.sy(0.026), "1個ずつのデータ SD＝12（点線）", 11, INK2, "start")
s.text(16, 268, "中心はどれも μ＝50。データのSDは12のまま変わらない", 12, INK2)
out["c18"] = s.svg()

# 19: binomial n=100 p=.5 with normal approx, P(X<=55)
n, pp = 100, 0.5
pmf = lambda k: math.comb(n, k) * pp ** k * (1 - pp) ** (n - k)
s = Svg(480, 280); s.text(16, 26, "二項 n＝100, p＝0.5 を正規 N(50, 5²) で近似", 15, INK, weight="bold")
p = Plot(s, 20, 50, 460, 220, 34.5, 65.5, 0, 0.088)
for k in range(35, 66):
    p.bar(k, 0.8, pmf(k), BLUE if k <= 55 else MUTED)
p.curve(lambda x: npdf(x, 50, 5), 34.5, 65.5, color=ORANGE, width=2.5); p.baseline()
x = p.sx(55.5); s.line(x, 60, x, p.sy(0), INK, 1.5, "4 3")
s.text(x + 4, 74, "55.5で切る", 12, INK, "start", "bold"); s.text(x + 4, 90, "（連続修正）", 11, INK2)
for k in [35, 40, 45, 50, 55, 60, 65]:
    s.text(p.sx(k), 238, str(k), 11, INK2, "middle")
s.text(16, 268, "棒＝二項の確率、曲線＝正規近似。55以下の棒は55.5までの面積", 12, INK2)
out["c19"] = s.svg()

# 20: t vs normal
def tpdf(x, v):
    c = math.gamma((v + 1) / 2) / (math.sqrt(v * math.pi) * math.gamma(v / 2))
    return c * (1 + x * x / v) ** (-(v + 1) / 2)
s = Svg(480, 270); s.text(16, 26, "t分布は正規分布より裾が厚い（自由度が小さいほど）", 15, INK, weight="bold")
p = Plot(s, 20, 50, 460, 222, -4.2, 4.2, 0, 0.44)
p.curve(lambda x: npdf(x), -4.2, 4.2, color=INK2, width=2, dash="5 4")
p.curve(lambda x: tpdf(x, 15), -4.2, 4.2, color=BLUE)
p.curve(lambda x: tpdf(x, 3), -4.2, 4.2, color=ORANGE, width=2.5); p.baseline()
for xx in range(-4, 5):
    s.text(p.sx(xx), 240, str(xx), 11, INK2, "middle")
s.text(p.sx(1.0), p.sy(0.40), "標準正規（点線）", 11, INK2, "start")
s.text(p.sx(1.25), p.sy(0.31), "t(15)", 12, BLUE, "start", "bold")
s.text(p.sx(2.3), p.sy(0.085), "t(3)：裾が厚い", 12, ORANGE, "start", "bold")
s.text(16, 262, "両側5%の点：正規1.96、t(15)2.131、t(3)3.182", 12, INK2)
out["c20"] = s.svg()

import json; json.dump(out, open("g3.json", "w"), ensure_ascii=False)
for k, v in out.items():
    open(f"{k}.svg", "w").write(v); print(k, len(v.encode()))
from statistics import NormalDist
print(sum(pmf(k) for k in range(0, 56)), NormalDist(50, 5).cdf(55.5), NormalDist().cdf(1.1))
