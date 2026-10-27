"""U04 の図：尺度の階段（上がるほど使える計算が増える）。
使い方: python3 tools/figure-src/make_u04.py  → assets/figures/c04_scale.svg"""
from pathlib import Path
from svgkit import Svg, INK, INK2, BLUE, ORANGE, LIGHT, GRID

s = Svg(480, 300)
s.text(16, 26, "尺度の階段：上がるほど、意味のある計算が増える", 15, INK, weight="bold")
steps = [  # 名前, 例, 加わる計算, 判断の鍵
    ("名義", "店番・血液型", "＝ ≠", "区別だけ"),
    ("順序", "満足度・順位", "＜ ＞", "順番まで"),
    ("間隔", "気温℃・西暦", "＋ −", "差まで"),
    ("比例", "個数・重さ・売上", "× ÷", "比（何倍）まで"),
]
x0, w, base, hstep = 18, 111, 262, 48
for i, (name, ex, op, key) in enumerate(steps):
    x = x0 + i * w
    top = base - (i + 1) * hstep
    fill = "#fdf0e9" if i < 2 else LIGHT
    edge = ORANGE if i < 2 else BLUE
    s.rect(x, top, w - 6, base - top, fill, rx=6, stroke=edge)
    s.text(x + (w - 6) / 2, top + 20, name, 14, INK, "middle", "bold")
    s.text(x + (w - 6) / 2, top + 38, op if i == 0 else f"＋（{op}）", 13, edge, "middle", "bold")
    if i == 0:
        s.text(x + (w - 6) / 2, top - 8, ex, 10, INK2, "middle")
    else:
        s.text(x + (w - 6) / 2, top + 58, key, 11, INK2, "middle")
        s.text(x + (w - 6) / 2, top + 76, ex, 10, INK2, "middle")
    if i == 2:
        s.text(x + (w - 6) / 2, top + 104, "0℃でも温度はある", 10, INK2, "middle")
        s.text(x + (w - 6) / 2, top + 118, "→ 何倍は言えない", 10, INK2, "middle")
    if i == 3:
        s.text(x + (w - 6) / 2, top + 104, "0個＝何も無い", 10, INK2, "middle")
        s.text(x + (w - 6) / 2, top + 118, "→ 何倍が言える", 10, INK2, "middle")
# 下の区分
s.line(x0, base + 8, x0 + 2 * w - 6, base + 8, ORANGE, 2)
s.text(x0 + w - 3, base + 24, "質的変数（数えて割合で見る）", 11, ORANGE, "middle")
s.line(x0 + 2 * w, base + 8, x0 + 4 * w - 6, base + 8, BLUE, 2)
s.text(x0 + 3 * w - 3, base + 24, "量的変数（平均・分散が使える）", 11, BLUE, "middle")
out = Path(__file__).resolve().parents[2] / "assets" / "figures" / "c04_scale.svg"
out.write_text(s.svg(), encoding="utf-8")
print(out)
